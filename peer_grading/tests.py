"""
Run me with:
    python manage.py test --settings=edx_ora.test_settings peer_grading
"""
import json
import unittest
from datetime import datetime
import logging
import urlparse
from mock import Mock, patch

from django.contrib.auth.models import User
from django.test.client import Client
import requests
import test_util
from django.conf import settings
from controller.models import Submission, SubmissionState, Grader, GraderStatus
from peer_grading.models import CalibrationHistory,CalibrationRecord
from django.utils import timezone
import project_urls
from controller.xqueue_interface import handle_submission
import peer_grading_util
from views import create_and_save_calibration_record

log = logging.getLogger(__name__)

LOGIN_URL = project_urls.ControllerURLs.log_in
SUBMIT_URL = project_urls.ControllerURLs.submit
GET_NEXT = project_urls.PeerGradingURLs.get_next_submission
IS_CALIBRATED= project_urls.PeerGradingURLs.is_student_calibrated
SAVE_GRADE= project_urls.PeerGradingURLs.save_grade
SHOW_CALIBRATION= project_urls.PeerGradingURLs.show_calibration_essay
SAVE_CALIBRATION= project_urls.PeerGradingURLs.save_calibration_essay
GET_PROBLEM_LIST = project_urls.PeerGradingURLs.get_problem_list
GET_PEER_GRADING_DATA = project_urls.PeerGradingURLs.get_peer_grading_data_for_location

LOCATION="i4x://MITx/6.002x"
STUDENT_ID="5"
ALTERNATE_STUDENT="4"
COURSE_ID = "course_id"

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
    cal_hist,success=CalibrationHistory.objects.get_or_create(location=location,student_id=int(student_id))
    cal_hist.save()

    for i in xrange(0,num_to_create):
        sub=Submission.objects.get(id=int(sub_ids[i]))
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
        self.assertEqual(body['error'],u'You have completed all of the existing peer grading or there are no more submissions waiting to be peer graded.')

    def test_get_next_submission_true(self):
        test_sub = test_util.get_sub("PE", "1", LOCATION, "PE")
        test_sub.save()
        grader = test_util.get_grader("BC")
        grader.submission = test_sub
        grader.grader_id = "2"
        grader.save()

        for i in xrange(0,settings.MIN_TO_USE_PEER):
            test_sub = test_util.get_sub("PE", "1", LOCATION, "PE")
            test_sub.save()
            grader = test_util.get_grader("IN")
            grader.submission = test_sub
            grader.save()

        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        content = self.c.get(
            GET_NEXT,
            data={'grader_id' : STUDENT_ID, "location" : LOCATION},
            )

        body = json.loads(content.content)

        self.assertEqual(body['success'], True)

    def test_save_grade_false(self):
        test_dict={
            'location': LOCATION,
            'grader_id': STUDENT_ID,
            'submission_id': 1,
            'score': 0,
            'feedback': 'feedback',
            'submission_key' : 'string',
            'rubric_scores_complete' : True,
            'rubric_scores' : json.dumps([1,1]),
        }

        content = self.c.post(
            SAVE_GRADE,
            test_dict,
        )

        body=json.loads(content.content)

        #Should be false, submission id does not exist right now!
        self.assertEqual(body['success'], False)

    def test_get_next_submission_same_student(self):
        #Try to get an essay submitted by the same student for peer grading.  Should fail
        test_sub=test_util.get_sub("PE", STUDENT_ID,LOCATION, "PE")
        test_sub.save()

        content = self.c.get(
            GET_NEXT,
            data={'grader_id' : STUDENT_ID, "location" : LOCATION},
        )

        body = json.loads(content.content)

        #Ensure that correct response is received.
        self.assertEqual(body['success'], False)
        self.assertEqual(body['error'],u'You have completed all of the existing peer grading or there are no more submissions waiting to be peer graded.')

    def test_save_grade_true(self):
        test_sub=test_util.get_sub("PE", "blah",LOCATION, "PE")
        test_sub.save()

        test_dict={
            'location': LOCATION,
            'grader_id': STUDENT_ID,
            'submission_id': 1,
            'score': 0,
            'feedback': 'feedback',
            'submission_key' : 'string',
            'submission_flagged' : False,
            'rubric_scores_complete' : True,
            'rubric_scores' : [1,1],
            }

        content = self.c.post(
            SAVE_GRADE,
            test_dict,
        )

        body=json.loads(content.content)
        #Should succeed, as we created a submission above that save_grade can use
        self.assertEqual(body['success'], True)

        sub=Submission.objects.get(id=1)

        #Ensure that grader object is created
        self.assertEqual(sub.grader_set.all().count(),1)

    def test_get_problem_list(self):
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        request_data = {'course_id' : 'course_id', 'student_id' : STUDENT_ID}
        content = self.c.get(
            GET_PROBLEM_LIST,
            data=request_data,
        )
        body=json.loads(content.content)
        self.assertIsInstance(body['problem_list'], list)

    def test_get_peer_grading_data_for_location(self):
        request_data = {'student_id' : STUDENT_ID, 'location' : LOCATION}
        content = self.c.get(
            GET_PEER_GRADING_DATA,
            data=request_data,
            )
        body=json.loads(content.content)
        self.assertIsInstance(body['count_required'], int)


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

        body=json.loads(content.content)

        #Now records exist and error is 0, so student should be calibrated
        self.assertEqual(body['calibrated'], calibration_val)

    @patch('peer_grading.models.CalibrationHistory.save', Mock(side_effect=Exception()))
    def test_calibration_history_exception(self):

        calibration_data = {
                            'submission_id': 1234,
                            'score': 56,
                            'feedback': 'feedback',
                            'student_id': '789',
                            'location': '0123',
                            }

        success, data = create_and_save_calibration_record(calibration_data)
        self.assertRaises(Exception)
        

class PeerGradingUtilTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()
        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

        self.get_data={
            'student_id' : STUDENT_ID,
            'problem_id' : LOCATION,
            }

    def test_get_single_peer_grading_item(self):
        for i in xrange(0,settings.MIN_TO_USE_PEER):
            test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
            test_sub.save()
            handle_submission(test_sub)
            test_grader = test_util.get_grader("IN")
            test_grader.submission=test_sub
            test_grader.save()

            test_sub.state = SubmissionState.finished
            test_sub.previous_grader_type = "IN"
            test_sub.posted_results_back_to_queue = True
            test_sub.save()

        test_sub = test_util.get_sub("PE", ALTERNATE_STUDENT, LOCATION, "PE")
        test_sub.save()
        handle_submission(test_sub)
        test_sub.is_duplicate = False
        test_sub.save()

        found, grading_item = peer_grading_util.get_single_peer_grading_item(LOCATION, STUDENT_ID)
        self.assertEqual(found, True)

        subs_graded = peer_grading_util.peer_grading_submissions_graded_for_location(LOCATION,"1")

    def test_get_peer_grading_notifications(self):
        test_sub = test_util.get_sub("PE", ALTERNATE_STUDENT, LOCATION, "PE")
        test_sub.save()
        handle_submission(test_sub)
        test_sub.next_grader_type = "PE"
        test_sub.is_duplicate = False
        test_sub.save()

        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        handle_submission(test_sub)
        test_sub.next_grader_type = "PE"
        test_sub.is_duplicate = False
        test_sub.save()

        success, student_needs_to_peer_grade = peer_grading_util.get_peer_grading_notifications(COURSE_ID, ALTERNATE_STUDENT)
        self.assertEqual(success, True)
        self.assertEqual(student_needs_to_peer_grade, True)
    
    def test_get_flagged_submissions(self):
        test_sub = test_util.get_sub("PE", ALTERNATE_STUDENT, LOCATION, "PE")
        test_sub.state = SubmissionState.flagged
        test_sub.save()
        
        success, flagged_submission_list = peer_grading_util.get_flagged_submissions(COURSE_ID)

        self.assertTrue(len(flagged_submission_list)==1)

    def test_unflag_student_submission(self):
        test_sub = test_util.get_sub("PE", ALTERNATE_STUDENT, LOCATION, "PE")
        test_sub.state = SubmissionState.flagged
        test_sub.save()

        peer_grading_util.unflag_student_submission(COURSE_ID, ALTERNATE_STUDENT, test_sub.id)
        test_sub = Submission.objects.get(id=test_sub.id)

        self.assertEqual(test_sub.state, SubmissionState.waiting_to_be_graded)

        






