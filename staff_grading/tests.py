"""
Run me with:
    python manage.py test --settings=edx_ora.test_settings staff_grading
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
from staff_grading_util import StaffLocation, StaffCourse
import mock

log = logging.getLogger(__name__)

GET_NEXT= project_urls.StaffGradingURLs.get_next_submission
SAVE_GRADE= project_urls.StaffGradingURLs.save_grade
GET_PROBLEM_LIST=project_urls.StaffGradingURLs.get_problem_list

LOCATION="i4x://MITx/6.002x/OETest"
STUDENT_ID="5"
COURSE_ID="course_id"


class StaffGradingViewTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        test_util.delete_all()

    def test_get_next_submission_false(self):
        content = self.c.get(
            GET_NEXT,
            data={'course_id' : COURSE_ID, "grader_id" : STUDENT_ID},
        )

        body = json.loads(content.content)

        #Should return true, but with message of no submissions to grade
        self.assertEqual(body['message'], "No more submissions to grade.")
        self.assertEqual(body['success'], True)

    def test_get_next_submission_true(self):
        test_sub=test_util.get_sub("IN",STUDENT_ID, LOCATION)
        test_sub.save()

        content = self.c.get(
            GET_NEXT,
            data={'course_id' : COURSE_ID, "grader_id" : STUDENT_ID},
        )

        body = json.loads(content.content)

        #Should return true, and resulting dictionary should have submission id one
        self.assertDictContainsSubset({'submission_id' : 1}, body)
        self.assertEqual(body['success'], True)

    def test_save_grade_false(self):
        post_data={
            'blah' : 'blah'
        }

        content = self.c.post(
            SAVE_GRADE,
            post_data,
        )

        body=json.loads(content.content)

        #Should fail, dictionary does not have needed keys
        self.assertEqual(body['success'], False)

    def test_save_grade_submission_id_does_not_exist(self):
        #Should fail, the submission id that is posted to the view does not exist
        self.save_grade(False, False)

    def test_save_grade_true(self):
        test_sub=test_util.get_sub("IN",STUDENT_ID, LOCATION)
        test_sub.save()

        #Should work because submission was just created
        self.save_grade(True, False)
        test_sub = Submission.objects.get(id=test_sub.id)
        # make sure the submission isn't skipped
        self.assertNotEqual(test_sub.next_grader_type,"ML")

    def save_grade(self, should_work, skipped):
        post_data={
            'course_id' : COURSE_ID,
            'grader_id' : STUDENT_ID,
            'submission_id' : 1,
            'score' : 0,
            'feedback' : 'string',
            'skipped': skipped,
            'rubric_scores_complete' : True,
            'rubric_scores' : [1,1]
        }

        content = self.c.post(
            SAVE_GRADE,
            post_data,
        )

        body=json.loads(content.content)
        self.assertEqual(body['success'], should_work)

    def test_get_problem_list_false(self):
        get_data={
            'course_id' : 0,
        }

        content=self.c.get(
            GET_PROBLEM_LIST,
            get_data,
        )

        body=json.loads(content.content)

        self.assertEqual(body['success'], False)
        self.assertEqual(body['error'], "No problems associated with course.")

    def test_get_problem_list_true(self):

        for i in xrange(0,10):
            test_sub=test_util.get_sub("IN",STUDENT_ID,LOCATION, course_id=COURSE_ID)
            test_sub.save()

        get_data={
            'course_id' : COURSE_ID,
            }

        content=self.c.get(
            GET_PROBLEM_LIST,
            get_data,
        )

        body=json.loads(content.content)

        self.assertEqual(body['problem_list'][0]['num_graded'],0)
        self.assertEqual(body['problem_list'][0]['num_pending'],10)


    def test_skip_problem_success(self):
        test_sub = test_util.get_sub("IN", LOCATION, STUDENT_ID, course_id=COURSE_ID)
        test_sub.save()
        self.save_grade(True, True)
        test_sub = Submission.objects.get(id=test_sub.id)
        self.assertEqual(test_sub.next_grader_type,"ML")

    def test_skip_problem_next_grader_type_pe(self):
        """Next grader type should be PE."""
        test_sub = test_util.get_sub("IN", LOCATION, STUDENT_ID, course_id=COURSE_ID, preferred_grader_type="PE")
        test_sub.save()
        self.save_grade(True, True)
        test_sub = Submission.objects.get(id=test_sub.id)
        self.assertEqual(test_sub.next_grader_type, "PE")

    def test_skip_problem_next_grader_type_ml(self):
        """Next grader type should be ML."""
        test_sub = test_util.get_sub("IN", LOCATION, STUDENT_ID, course_id=COURSE_ID, preferred_grader_type="ML")
        test_sub.save()
        self.save_grade(True, True)
        test_sub = Submission.objects.get(id=test_sub.id)
        self.assertEqual(test_sub.next_grader_type, "ML")

    def test_submission_location(self):
        Submission.objects.all().delete()
        test_sub=test_util.get_sub("IN",STUDENT_ID, LOCATION)
        test_sub.save()

        test_sub2=test_util.get_sub("PE",STUDENT_ID, LOCATION)
        test_sub2.state = SubmissionState.finished
        test_sub2.previous_grader_type = "PE"
        test_sub2.save()

        test_grader_in=test_util.get_grader("IN")
        test_grader_in.submission=test_sub2
        test_grader_in.save()

        test_grader_pe=test_util.get_grader("PE")
        test_grader_pe.submission=test_sub2
        test_grader_pe.save()


        sl = StaffLocation(LOCATION)
        self.assertEqual(sl.location_submissions().count(),2)
        self.assertEqual(sl.all_pending_count(),1)
        self.assertEqual(sl.graded_count(),1)
        self.assertEqual(sl.pending_count(),1)
        self.assertEqual(len(sl.graded_submission_text()),1)
        test_sub2.delete()
        next_item_id = sl.item_to_score()[1]
        self.assertEqual(next_item_id ,test_sub.id)

        test_sub = Submission.objects.get(id=next_item_id)
        self.assertEqual(test_sub.state,SubmissionState.being_graded)
        test_sub.state = SubmissionState.waiting_to_be_graded
        test_sub.save()
        self.assertEqual(sl.next_item()[1],test_sub.id)


    def test_submission_course(self):
        test_sub=test_util.get_sub("IN",STUDENT_ID,LOCATION)
        test_sub.save()

        sc = StaffCourse(COURSE_ID)
        self.assertEqual(len(sc.locations()),1)
        self.assertEqual(sc.notifications()[1],True)
        self.assertEqual(sc.next_item()[1],test_sub.id)

    @mock.patch('ml_grading.ml_grading_util.check_for_all_model_and_rubric_success', new=mock.Mock(return_value=True))
    def test_submission_location_rescore(self):
        Submission.objects.all().delete()
        test_sub=test_util.get_sub("IN",STUDENT_ID, LOCATION)
        test_sub.save()

        test_grader = test_util.get_grader("BC")
        test_grader.submission = test_sub
        test_grader.save()

        test_grader = test_util.get_grader("ML")
        test_grader.submission = test_sub
        test_grader.save()

        sl = StaffLocation(LOCATION)

        rescore = sl.item_to_rescore()[1]

        self.assertEqual(rescore,test_sub.id)

    def test_get_problem_name(self):
        """
        Test to see if the correct problem name is returned by a location capsule.
        Saves two submissions, and tests to see if the problem name is updated.
        """
        problem_id_one = "Problem One"
        problem_id_two = "Problem Two"

        test_sub=test_util.get_sub("IN",STUDENT_ID,LOCATION)
        test_sub.problem_id = problem_id_one
        test_sub.save()

        sl = StaffLocation(LOCATION)
        self.assertEqual(sl.problem_name(), problem_id_one)

        test_sub2=test_util.get_sub("IN",STUDENT_ID,LOCATION)
        test_sub2.problem_id = problem_id_two
        test_sub2.save()

        self.assertEqual(sl.problem_name(), problem_id_two)



