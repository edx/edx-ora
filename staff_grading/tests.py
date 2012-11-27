"""
Run me with:
    python manage.py test --settings=grading_controller.settings staff_grading
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

GET_NEXT="/staff_grading/get_next_submission/"
SAVE_GRADE="/staff_grading/save_grade/"

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


