"""
Run me with:
    python manage.py test --settings=edx_ora.test_settings peer_grading
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
import project_urls
from controller.xqueue_interface import handle_submission
import peer_grading_util
from controller.control_util import SubmissionControl

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
STUDENT3="6"
COURSE_ID = "course_id"

def create_calibration_essays(num_to_create,scores,is_calibration):
    sub_ids=[]

    for i in xrange(0,num_to_create):
        sub=test_util.get_sub("IN",STUDENT_ID,LOCATION)
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

        pl = peer_grading_util.PeerLocation(LOCATION, "1")
        control = SubmissionControl(pl.latest_submission())

        for i in xrange(0, control.minimum_to_use_peer):
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

    def test_save_grade_with_no_rubrics_and_submission_flagged(self):
        """
        Test save grade when submission is flagged and rubric score are not provided.
        """

        test_sub = test_util.get_sub("PE", "blah", LOCATION, "PE")
        test_sub.save()

        test_dict = {
            'location': LOCATION,
            'grader_id': STUDENT_ID,
            'submission_id': 1,
            'score': 5,
            'feedback': 'feedback',
            'submission_key': 'string',
            'submission_flagged': True,
            'rubric_scores_complete': False,
            'rubric_scores': [],
            }

        content = self.c.post(
            SAVE_GRADE,
            test_dict,
        )

        body = json.loads(content.content)
        #Should succeed, as we created a submission above that save_grade can use
        self.assertEqual(body["success"], True)

        sub = Submission.objects.get(id=1)

        #Score should be 0.
        self.assertEqual(sub.get_last_grader().score, 0)

    def test_save_grade_with_no_rubrics_and_submission_unknown(self):
        """
        Test save grade when submission is mark as unknown and rubric score are not provided.
        """

        test_sub = test_util.get_sub("PE", "blah", LOCATION, "PE")
        test_sub.save()

        test_dict = {
            'location': LOCATION,
            'grader_id': STUDENT_ID,
            'submission_id': 1,
            'score': 5,
            'feedback': 'feedback',
            'submission_key': 'string',
            'submission_flagged': False,
            'answer_unknown': True,
            'rubric_scores_complete': False,
            'rubric_scores': [],
            }

        content = self.c.post(
            SAVE_GRADE,
            test_dict,
        )

        body = json.loads(content.content)
        #Should succeed, as we created a submission above that save_grade can use
        self.assertEqual(body["success"], True)

        sub = Submission.objects.get(id=1)

        #Score should be 0.
        self.assertEqual(sub.get_last_grader().score, 0)

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
        self.assertIsInstance(body['count_available'], int)


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
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        handle_submission(test_sub)

        pl = peer_grading_util.PeerLocation(LOCATION, STUDENT_ID)
        control = SubmissionControl(pl.latest_submission())

        for i in xrange(0, control.minimum_to_use_peer):
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

        pl = peer_grading_util.PeerLocation(LOCATION, STUDENT_ID)
        found, grading_item = pl.next_item()
        self.assertEqual(found, True)

        pl = peer_grading_util.PeerLocation(LOCATION,"1")
        subs_graded = pl.graded()

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

        pc = peer_grading_util.PeerCourse(COURSE_ID, ALTERNATE_STUDENT)
        success, student_needs_to_peer_grade = pc.notifications()
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

    def test_get_required(self):
        pl = peer_grading_util.PeerLocation(LOCATION, STUDENT_ID)
        student_required = pl.required_count()
        test_sub = test_util.get_sub("PE", ALTERNATE_STUDENT, LOCATION, "PE")
        test_sub.save()

        self.assertEqual(pl.required_count(), student_required)

        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()

        self.assertEqual(pl.required_count(), settings.REQUIRED_PEER_GRADING_PER_STUDENT + student_required)

    def test_submission_location(self):
        Submission.objects.all().delete()
        test_sub=test_util.get_sub("PE",STUDENT_ID, LOCATION, preferred_grader_type="PE")
        test_sub.save()
        test_grader = test_util.get_grader("BC")
        test_grader.submission = test_sub
        test_grader.save()

        pl = peer_grading_util.PeerLocation(LOCATION,STUDENT_ID)

        self.assertEqual(pl.submitted_count(),1)
        self.assertEqual(pl.required_count(), settings.REQUIRED_PEER_GRADING_PER_STUDENT)


        test_sub2=test_util.get_sub("PE",ALTERNATE_STUDENT, LOCATION, preferred_grader_type="PE")
        test_sub2.save()

        test_grader2 = test_util.get_grader("BC")
        test_grader2.submission = test_sub2
        test_grader2.save()

        self.assertEqual(pl.pending_count(),1)

        found, next_item_id = pl.next_item()

        self.assertEqual(next_item_id, test_sub2.id)

        test_sub2 = Submission.objects.get(id=next_item_id)
        self.assertEqual(SubmissionState.being_graded, test_sub2.state)

        test_grader3 = test_util.get_grader("PE")
        test_grader3.submission = test_sub2
        test_grader3.grader_id = STUDENT_ID
        test_grader3.save()

        self.assertEqual(pl.graded_count(),1)

        self.assertEqual(pl.pending_count(),0)

    def test_get_next_get_finished_subs(self):
        Submission.objects.all().delete()
        all_students = [STUDENT_ID, ALTERNATE_STUDENT, STUDENT3]
        # setup 3 submissions from 3 students, passed basic check
        submissions = []
        for student in all_students:
            test_sub = test_util.get_sub("PE", student, LOCATION, preferred_grader_type="PE")
            test_sub.next_grader_type="PE"
            test_sub.is_duplicate=False
            test_sub.save()
            submissions.append(test_sub)
            bc_grader = test_util.get_grader("BC")
            bc_grader.submission = test_sub
            bc_grader.save()

        # have them each grade the other two and call that finished
        for student in all_students:
            for submission in Submission.objects.all().exclude(student_id=student):
                test_grader = test_util.get_grader("PE")
                test_grader.grader_id = student
                test_grader.submission = submission
                test_grader.save()
        for sub in submissions:
            sub.state = SubmissionState.finished
            sub.posted_results_back_to_queue = True
            sub.save()

        pls = []
        for student in all_students:
            pls.append(peer_grading_util.PeerLocation(LOCATION, student))

        # check that each student graded 2, and so no submissions are pending
        for pl in pls:
            self.assertEqual(pl.graded_count(),2)
            self.assertEqual(pl.pending_count(),0)
            # check that next_item() cannot returns a submission because each of these students
            # has graded the submissions by the other 2 students
            found, _ = pl.next_item()
            self.assertFalse(found)

        # now a 4th student comes along and submits.  They should get something to grade despite nothing pending
        student4 = "10"
        test_sub = test_util.get_sub("PE", student4, LOCATION, preferred_grader_type="PE")
        test_sub.next_grader_type="PE"
        test_sub.is_duplicate=False
        test_sub.control_fields=json.dumps({'peer_grade_finished_submissions_when_none_pending': True})
        test_sub.save()

        pl4 = peer_grading_util.PeerLocation(LOCATION, student4)
        self.assertEqual(pl4.pending_count(),0)
        found, next_sub_id = pl4.next_item()
        self.assertTrue(found)
        student4_sub_to_grade = Submission.objects.get(id=next_sub_id)
        self.assertIn(student4_sub_to_grade, submissions)
        self.assertEqual(student4_sub_to_grade.state, SubmissionState.being_graded)

    def test_submission_course(self):
        Submission.objects.all().delete()
        test_sub=test_util.get_sub("PE",STUDENT_ID, LOCATION, preferred_grader_type="PE")
        test_sub.save()
        test_grader = test_util.get_grader("BC")
        test_grader.submission = test_sub
        test_grader.save()

        test_sub2=test_util.get_sub("PE",ALTERNATE_STUDENT, LOCATION, preferred_grader_type="PE")
        test_sub2.save()

        test_grader2 = test_util.get_grader("BC")
        test_grader2.submission = test_sub2
        test_grader2.save()

        sc = peer_grading_util.PeerCourse(COURSE_ID, STUDENT_ID)
        success, needs_to_grade = sc.notifications()
        self.assertTrue(needs_to_grade)
        self.assertEqual(sc.submitted().count(),1)
        






