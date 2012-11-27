"""
Run me with:
    python manage.py test --settings=grading_controller.settings peer_grading
"""
import json
import unittest
from datetime import datetime
import logging
import urlparse

from django.contrib.auth.models import User
from django.test.client import Client
import requests
import test_util
from django.conf import settings
from controller.models import Submission, SubmissionState, Grader, GraderStatus
from peer_grading.models import CalibrationHistory,CalibrationRecord
from django.utils import timezone

log = logging.getLogger(__name__)

LOGIN_URL = "/grading_controller/login/"
SUBMIT_URL = "/grading_controller/submit/"
GET_NEXT = "/peer_grading/get_next_submission/"
IS_CALIBRATED="/peer_grading/is_student_calibrated/"
SAVE_GRADE="/peer_grading/save_grade/"
SHOW_CALIBRATION="/peer_grading/show_calibration_essay/"
SAVE_CALIBRATION="/peer_grading/save_calibration_essay/"

STUDENT_ID="5"
PROBLEM_ID="MITx/6.002x"

TEST_SUB = Submission(
    prompt="prompt",
    student_id=STUDENT_ID,
    problem_id="id",
    state=SubmissionState.waiting_to_be_graded,
    student_response="response",
    student_submission_time=timezone.now(),
    xqueue_submission_id="id",
    xqueue_submission_key="key",
    xqueue_queue_name="MITx-6.002x",
    location=PROBLEM_ID,
    course_id="course_id",
    max_score=3,
    next_grader_type="IN",
)

def create_calibration_essays(num_to_create,scores,is_calibration):
    test_subs=[TEST_SUB for i in xrange(0,num_to_create)]
    sub_ids=[]

    for i in xrange(0,len(test_subs)):
        sub=test_subs[i]
        sub.save()
        grade=Grader(
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

def create_calibration_records(location,student_id,num_to_create,sub_ids,scores,actual_scores):
    cal_hist,success=CalibrationHistory.objects.get_or_create(location=location,student_id=student_id)
    cal_hist.save()

    for i in xrange(0,num_to_create):
        sub=Submission.objects.get(id=sub_ids[i])
        cal_record=CalibrationRecord(
            submission=sub,
            calibration_history=cal_hist,
            score=scores[i],
            actual_score=actual_scores[i],
            feedback="",
        )
        cal_record.save()

class LMSInterfaceTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        test_util.delete_all()

    def get_next_submission(self):
        pass



class IsCalibratedTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()
        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

        self.get_data={
            'student_id' : STUDENT_ID,
            'problem_id' : PROBLEM_ID,
            }

    def tearDown(self):
        test_util.delete_all()

    def test_is_calibrated_false(self):

        content = self.c.get(
            IS_CALIBRATED,
            data=self.get_data,
        )

        body=json.loads(content.content)

        #No records exist for given problem_id, so calibration check should fail and return an error
        self.assertEqual(body['success'], False)


        sub=TEST_SUB
        sub.save()

        content = self.c.get(
            IS_CALIBRATED,
            data=self.get_data,
        )

        log.debug(content)

        body=json.loads(content.content)

        #Now one record exists for given problem_id, so calibration check should return False (student is not calibrated)
        self.assertEqual(body['calibrated'], False)

    def test_is_calibrated_zero_error(self):
        num_to_use=settings.PEER_GRADER_MINIMUM_TO_CALIBRATE
        scores=[0] * num_to_use
        actual_scores=[0] * num_to_use
        self.check_is_calibrated(num_to_use,True,scores,actual_scores)

    def test_is_calibrated_over_max(self):
        num_to_use=settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE+1
        scores=[0] * num_to_use
        actual_scores=[3] * num_to_use
        self.check_is_calibrated(num_to_use,True,scores,actual_scores)

    def test_is_calibrated_high_error(self):
        num_to_use=settings.PEER_GRADER_MINIMUM_TO_CALIBRATE
        scores=[0] * num_to_use
        actual_scores=[3] * num_to_use
        self.check_is_calibrated(num_to_use,False,scores,actual_scores)

    def check_is_calibrated(self,num_to_add,calibration_val,scores,actual_scores):
        sub_ids=create_calibration_essays(num_to_add,actual_scores, True)
        create_calibration_records(PROBLEM_ID,STUDENT_ID,num_to_add,sub_ids,scores, actual_scores)
        content = self.c.get(
            IS_CALIBRATED,
            data=self.get_data,
        )

        log.debug(content)

        body=json.loads(content.content)

        #Now records exist and error is 0, so student should be calibrated
        self.assertEqual(body['calibrated'], calibration_val)







