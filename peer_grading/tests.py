"""
Run me with:
    python manage.py test --settings=xqueue.test_settings queue
"""
import json
import unittest
from datetime import datetime
import logging
import urlparse

from django.contrib.auth.models import User
from django.test.client import Client
import requests
from django.conf import settings

import xqueue_interface
import grader_interface
import util

from models import Submission, Grader
from models import GraderStatus, SubmissionState

log = logging.getLogger(__name__)

LOGIN_URL = "/grading_controller/login/"
SUBMIT_URL = "/grading_controller/submit/"
GET_NEXT = "/peer_grading/get_next_submission/"
IS_CALIBRATED="/peer_grading/is_student_calibrated/"
SAVE_GRADE="/peer_grading/save_grade/"
SHOW_CALIBRATION="/peer_grading/show_calibration_essay/"
SAVE_CALIBRATION="/peer_grading/save_calibration_essay/"


class CalibrationTest(unittest.TestCase):
    def setUp(self):
        if(User.objects.filter(username='test').count() == 0):
            user = User.objects.create_user('test', 'test@test.com', 'CambridgeMA')
            user.save()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')


