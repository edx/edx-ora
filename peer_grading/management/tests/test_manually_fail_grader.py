"""
Run me with:
    python manage.py test --settings=edx_ora.testsettings peer_grading/management
"""

import json
import unittest
import test_util
import project_urls
from django.test.client import Client
from django.conf import settings
from controller.models import Submission, GraderStatus, Grader
from peer_grading.management.commands.manually_fail_grader import update_grader_to_manually_fail

SHOW_CALIBRATION = project_urls.PeerGradingURLs.show_calibration_essay

LOCATION = "i4x://MITx/6.002x"
STUDENT_ID = "1"
COURSE_ID = "course_id"


def create_calibration_essays(num_to_create, scores, is_calibration):
    sub_ids = []

    for i in xrange(num_to_create):
        sub = test_util.get_sub("IN", STUDENT_ID, LOCATION)
        sub.save()
        grade = Grader(
            submission=sub,
            score=scores[i],
            feedback="feedback",
            is_calibration=is_calibration,
            grader_id="1",
            grader_type="IN",
            status_code=GraderStatus.success,
            confidence=1,
        )
        sub_ids.append(sub.id)
        grade.save()

    return sub_ids


class CalibrationEssayTestAfterFailingGrader(unittest.TestCase):
    def setUp(self):
        test_util.create_user()

        self.client = Client()
        self.client.login(username='test', password='CambridgeMA')

        self.min_to_calibrate = settings.PEER_GRADER_MINIMUM_TO_CALIBRATE + 1
        self.sub_ids = create_calibration_essays(self.min_to_calibrate, [0] * self.min_to_calibrate, True)

        self.submission_id = self.sub_ids[0]
        self.grader_id = Grader.objects.filter(submission_id=self.submission_id, grader_type="IN")[0].id

    def tearDown(self):
        test_util.delete_all()

    def test_bad_grader_id(self):
        bad_grader_id = -1
        update_grader_to_manually_fail(bad_grader_id, dry_run=False)
        failed_calibration_submissions = Submission.objects.filter(
            location=LOCATION,
            grader__grader_type="IN",
            grader__status_code=GraderStatus.failure,
        )
        # check that there are no failed calibration essays
        self.assertFalse(failed_calibration_submissions.exists())

    def test_dry_run(self):
        update_grader_to_manually_fail(self.grader_id)
        # test there are no failed calibration submissions
        failed_calibration_submissions = Submission.objects.filter(
            location=LOCATION,
            grader__grader_type="IN",
            grader__status_code=GraderStatus.failure,
        )

        self.assertFalse(failed_calibration_submissions.exists())

    def test_show_calibration_essay_after_failing_grader(self):
        # test there are no failed calibration submissions
        failed_calibration_submissions = Submission.objects.filter(
            location=LOCATION,
            grader__grader_type="IN",
            grader__status_code=GraderStatus.failure,
        )
        self.assertFalse(failed_calibration_submissions.exists())

        # Failing grader manually.
        update_grader_to_manually_fail(self.grader_id, dry_run=False)

        content = self.client.get(
            SHOW_CALIBRATION,
            data={'problem_id': LOCATION, "student_id": STUDENT_ID},
        )

        body = json.loads(content.content)

        # Should have succeeded.
        self.assertEqual(body["success"], True)

        calibration_submissions = Submission.objects.filter(
            location=LOCATION,
            grader__grader_type="IN",
            grader__status_code=GraderStatus.success,
        )

        submission_ids = [submission.id for submission in calibration_submissions]

        # Submission id should not be in calibration submission ids.
        self.assertNotIn(self.submission_id, submission_ids)
