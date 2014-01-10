import logging
import test_util
import unittest
from django.test.client import Client
from peer_grading.peer_grading_util import PeerLocation
from controller.xqueue_interface import handle_submission
from controller.models import SubmissionState, Submission
from controller.management.commands.allow_skipped_subs_to_peer_grade import update_subs_skipped_by_instructor
from staff_grading.staff_grading_util import set_instructor_grading_item_back_to_preferred_grader

LOCATION = "MITx/6.002x"
STUDENT_ID = "5"
COURSE_ID = "MITx/6.002x"

log = logging.getLogger(__name__)


class AllowSkippedToPeerCommandTest(unittest.TestCase):
    """
    Test allow submission to peer grade skipped by instructor.
    """

    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        test_util.delete_all()

    def test_subs_to_peer_grading(self):
        submission = test_util.get_sub(
            "BC",
            STUDENT_ID,
            LOCATION,
            course_id=COURSE_ID,
            preferred_grader_type="PE",
            student_response="This is answer."
        )
        submission.preferred_grader_type = "NA"
        submission.save()

        handle_submission(submission)

        submission = Submission.objects.get(id=submission.id)
        self.assertEqual(
            submission.state, SubmissionState.waiting_to_be_graded
        )
        self.assertEqual(submission.preferred_grader_type, "PE")
        self.assertEqual(submission.next_grader_type, "IN")

        # Skipping submission from instructor to ML.
        set_instructor_grading_item_back_to_preferred_grader(submission.id)
        submission = Submission.objects.get(id=submission.id)
        submission.next_grader_type = "ML"
        submission.save()

        # Divert skipped submission to peer grading.
        update_subs_skipped_by_instructor(COURSE_ID, dry_run=False)

        # Next grader type should be PE.
        submission = Submission.objects.get(id=submission.id)
        self.assertEqual(submission.next_grader_type, "PE")

        peer_location = PeerLocation(student_id="123", location=LOCATION)
        pending_submissions = peer_location.pending()
        self.assertEqual(pending_submissions.count(), 1)
