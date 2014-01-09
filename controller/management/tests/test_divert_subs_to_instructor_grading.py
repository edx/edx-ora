import json
import logging
import test_util
import unittest
from mock import Mock, patch
from django.conf import settings
from django.test.client import Client
from controller import expire_submissions
from controller.xqueue_interface import handle_submission
from controller.models import SubmissionState, GraderStatus, Submission, Grader
from controller.grader_util import finalize_expired_submission
from basic_check import basic_check_util
from staff_grading.staff_grading_util import StaffLocation
from controller.management.commands.divert_subs_to_instructor_grading import reset_and_divert_failed_basic_check_submissions

LOCATION = "MITx/6.002x"
STUDENT_ID = "5"
COURSE_ID = "MITx/6.002x"

quality_dict = {
    'feedback': json.dumps({
        'spelling': "Ok.",
        'grammar': "Ok.",
        'markup_text': "NA"
    }),
    'score': 0,
    'grader_type': 'BC',
    'status': GraderStatus.failure
}

log = logging.getLogger(__name__)


class PassBasicCheckCommandTest(unittest.TestCase):
    """
    Test the force pass basic check and divert submissions to
    instructor management command.
    """

    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

        settings.MIN_TO_USE_PEER = 0

    def test_subs_pass_basic_check_divert_to_instructor_grading(self):
        test_sub = test_util.get_sub("BC", STUDENT_ID, LOCATION,
                                     course_id=COURSE_ID,
                                     preferred_grader_type="PE",
                                     student_response="This is answer")
        test_sub.preferred_grader_type = "NA"
        test_sub.save()

        # Get the submission to fail basic check
        with patch('basic_check.basic_check_util.simple_quality_check') as simple_quality_check_mock:
            simple_quality_check_mock.return_value = (False, quality_dict)
            handle_submission(test_sub)

        # Check that it did
        self.assertEqual(test_sub.next_grader_type, "BC")
        self.assertEqual(test_sub.state, SubmissionState.waiting_to_be_graded)

        # Finalize it
        finalize_expired_submission(test_sub)
        self.assertEqual(test_sub.state, SubmissionState.finished)

        test_sub = Submission.objects.get(id=test_sub.id)
        test_sub.posted_results_back_to_queue = True
        test_sub.save()

        # Reset submissions for this course which failed basic check
        reset_and_divert_failed_basic_check_submissions(COURSE_ID, dry_run=False)

        # Its state should be waiting to be graded
        test_sub = Submission.objects.get(id=test_sub.id)
        self.assertEqual(test_sub.state, SubmissionState.waiting_to_be_graded)

        # This is called by a celery task.
        expire_submissions.reset_subs_in_basic_check()

        # Check that the submission is available for grading by staff
        test_sub = Submission.objects.get(id=test_sub.id)
        self.assertEqual(test_sub.next_grader_type, "IN")

        staff_location = StaffLocation(location=LOCATION)
        pending_submissions = staff_location.pending()
        self.assertEqual(pending_submissions.count(), 1)
