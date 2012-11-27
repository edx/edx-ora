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

LOCATION="MITx/6.002x"
STUDENT_ID="5"

def create_calibration_essays(num_to_create,scores,is_calibration):
    test_subs=[test_util.get_sub("IN",STUDENT_ID,LOCATION) for i in xrange(0,num_to_create)]
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

class LMSInterfacePeerGradingTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        test_util.delete_all()

    def test_get_next_submission_false(self):
        content = self.c.get(
            GET_NEXT,
            data={'grader_id' : STUDENT_ID, "location" : LOCATION},
        )

        body = json.loads(content.content)

        #Ensure that correct response is received.
        self.assertEqual(body['success'], False)
        self.assertEqual(body['error'],"No current grading.")

    def test_save_grade_false(self):
        test_dict={
            'location': LOCATION,
            'grader_id': STUDENT_ID,
            'submission_id': 1,
            'score': 0,
            'feedback': 'feedback',
            'submission_key' : 'string',
        }

        content = self.c.post(
            SAVE_GRADE,
            test_dict,
        )

        log.debug(content)

        body=json.loads(content.content)

        #Should be false, submission id does not exist right now!
        self.assertEqual(body['success'], False)

    def test_get_next_submission_same_student(self):
        #Try to get an essay submitted by the same student for peer grading.  Should fail
        test_sub=test_util.get_sub("PE", STUDENT_ID,LOCATION)
        test_sub.save()

        content = self.c.get(
            GET_NEXT,
            data={'grader_id' : STUDENT_ID, "location" : LOCATION},
        )

        body = json.loads(content.content)
        log.debug(body)

        #Ensure that correct response is received.
        self.assertEqual(body['success'], False)
        self.assertEqual(body['error'],"No current grading.")

    def test_save_grade_true(self):
        test_sub=test_util.get_sub("PE", "blah",LOCATION)
        test_sub.save()

        test_dict={
            'location': LOCATION,
            'grader_id': STUDENT_ID,
            'submission_id': 1,
            'score': 0,
            'feedback': 'feedback',
            'submission_key' : 'string',
            }

        content = self.c.post(
            SAVE_GRADE,
            test_dict,
        )

        log.debug(content)

        body=json.loads(content.content)
        #Should succeed, as we created a submission above that save_grade can use
        self.assertEqual(body['success'], True)

        sub=Submission.objects.get(id=1)

        #Ensure that grader object is created
        self.assertEqual(sub.grader_set.all().count(),1)

class LMSInterfaceCalibrationEssayTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        test_util.delete_all()

    def test_show_calibration_essay_false(self):
        content = self.c.get(
            SHOW_CALIBRATION,
            data={'problem_id' : LOCATION, "student_id" : STUDENT_ID},
        )

        body = json.loads(content.content)
        log.debug(body)

        #No calibration essays exist, impossible to get any
        self.assertEqual(body['success'], False)

    def test_show_calibration_essay_not_enough(self):
        #We added one calibration essay, so this should not work (below minimum needed).
        self.show_calibration_essay(1,False)

    def test_show_calibration_essay_enough(self):
        #We added enough calibration essays, so this should work (equal to minimum needed).
        self.show_calibration_essay(settings.PEER_GRADER_MINIMUM_TO_CALIBRATE, True)

    def show_calibration_essay(self,count,should_work):
        sub_ids=create_calibration_essays(count,[0] * count,True)
        content = self.c.get(
            SHOW_CALIBRATION,
            data={'problem_id' : LOCATION, "student_id" : STUDENT_ID},
        )

        body = json.loads(content.content)
        log.debug(body)

        self.assertEqual(body['success'], should_work)

    def test_save_calibration_essay_false(self):
        #Will not work because calibration essay is not associated with a real essay id
        self.save_calibration_essay(False)

    def test_save_calibration_essay_false(self):
        sub_ids=create_calibration_essays(1,[0],True)
        #Should work because essay has been created.
        self.save_calibration_essay(True)

    def save_calibration_essay(self,should_work):
        test_dict={
            'location': LOCATION,
            'student_id': STUDENT_ID,
            'calibration_essay_id': 1,
            'score': 0,
            'feedback': 'feedback',
            'submission_key' : 'string',
            }

        content = self.c.post(
            SAVE_CALIBRATION,
            test_dict,
        )

        body = json.loads(content.content)
        log.debug(body)

        self.assertEqual(body['success'], should_work)



class IsCalibratedTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()
        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

        self.get_data={
            'student_id' : STUDENT_ID,
            'problem_id' : LOCATION,
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


        sub=test_util.get_sub("IN",STUDENT_ID,LOCATION)
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
        create_calibration_records(LOCATION,STUDENT_ID,num_to_add,sub_ids,scores, actual_scores)
        content = self.c.get(
            IS_CALIBRATED,
            data=self.get_data,
        )

        log.debug(content)

        body=json.loads(content.content)

        #Now records exist and error is 0, so student should be calibrated
        self.assertEqual(body['calibrated'], calibration_val)







