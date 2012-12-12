"""
Run me with:
    python manage.py test --settings=grading_controller.test_settings staff_grading
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

log = logging.getLogger(__name__)

GET_NEXT= project_urls.StaffGradingURLs.get_next_submission
SAVE_GRADE= project_urls.StaffGradingURLs.save_grade
GET_PROBLEM_LIST=project_urls.StaffGradingURLs.get_problem_list

LOCATION="MITx/6.002x"
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
        test_sub=test_util.get_sub("IN",LOCATION,STUDENT_ID)
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
        self.save_grade(False)

    def test_save_grade_true(self):
        test_sub=test_util.get_sub("IN",LOCATION,STUDENT_ID)
        test_sub.save()

        #Should work because submission was just created
        self.save_grade(True)

    def save_grade(self, should_work):
        post_data={
            'course_id' : COURSE_ID,
            'grader_id' : STUDENT_ID,
            'submission_id' : 1,
            'score' : 0,
            'feedback' : 'string',
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
            test_sub=test_util.get_sub("IN",LOCATION,STUDENT_ID, course_id=COURSE_ID)
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
