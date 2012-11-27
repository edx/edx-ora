"""
Run me with:
    python manage.py test --settings=grading_controller.settings controller
"""
import json
import unittest
from datetime import datetime
from django.utils import timezone
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

from staff_grading import staff_grading_util

log = logging.getLogger(__name__)

LOGIN_URL = "/grading_controller/login/"
SUBMIT_URL = "/grading_controller/submit/"
ML_GET_URL = "/grading_controller/get_submission_ml/"
IN_GET_URL = "/grading_controller/get_submission_instructor/"
PUT_URL="/grading_controller/put_result/"

LOCATION="MITx/6.002x"
STUDENT_ID="5"


def parse_xreply(xreply):

    xreply = json.loads(xreply)
    if 'success' in xreply:
        return_code=xreply['success']
        content=xreply
    elif 'return_code' in xreply:
        return_code = (xreply['return_code']==0)
        content = xreply['content']
    else:
        return_code = False

    return (return_code, xreply)


def login_to_controller(session):
    controller_login_url = urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'], LOGIN_URL)

    response = session.post(controller_login_url,
        {'username': 'test',
         'password': 'CambridgeMA',
        }
    )
    response.raise_for_status()
    log.debug(response.content)
    return True

def get_test_sub(grader_type):
    test_sub = Submission(
        prompt="prompt",
        student_id=STUDENT_ID,
        problem_id="id",
        state=SubmissionState.waiting_to_be_graded,
        student_response="response",
        student_submission_time=timezone.now(),
        xqueue_submission_id="id",
        xqueue_submission_key="key",
        xqueue_queue_name="MITx-6.002x",
        location=LOCATION,
        course_id="course_id",
        max_score=3,
        next_grader_type=grader_type,
        previous_grader_type=grader_type,
    )
    return test_sub

def get_test_grader(grader_type):
    test_grader=Grader(
        score=0,
        feedback="",
        status_code=GraderStatus.success,
        grader_id="1",
        grader_type=grader_type,
        confidence=1,
        is_calibration=False,
    )

    return test_grader

class XQueueInterfaceTest(unittest.TestCase):
    def setUp(self):
        if(User.objects.filter(username='test').count() == 0):
            user = User.objects.create_user('test', 'test@test.com', 'CambridgeMA')
            user.save()
        self.c = Client()

    def test_log_in(self):
        '''
        Test Xqueue login behavior. Particularly important is the response for GET (e.g. by redirect)
        '''

        # 0) Attempt login with GET, must fail with message='login_required'
        #    The specific message is important, as it is used as a flag by LMS to reauthenticate!
        response = self.c.get(LOGIN_URL)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, False)

        # 1) Attempt login with POST, but no auth
        response = self.c.post(LOGIN_URL)
        (error, _) = parse_xreply(response.content)
        self.assertEqual(error, False)

        # 2) Attempt login with POST, incorrect auth
        response = self.c.post(LOGIN_URL, {'username': 'test', 'password': 'PaloAltoCA'})
        (error, _) = parse_xreply(response.content)
        self.assertEqual(error, False)

        # 3) Login correctly
        response = self.c.post(LOGIN_URL, {'username': 'test', 'password': 'CambridgeMA'})
        (error, _) = parse_xreply(response.content)
        self.assertEqual(error, True)

    def test_xqueue_submit(self):
        xqueue_header = {
            'submission_id': 1,
            'submission_key': 1,
            'queue_name': "MITx-6.002x",
        }
        grader_payload = {
            'location': LOCATION,
            'course_id': u'MITx/6.002x',
            'problem_id': u'6.002x/Welcome/OETest',
            'grader': "temp",
            'prompt' : 'This is a prompt',
            'rubric' : 'This is a rubric.',
            'grader_settings' : "ml_grading.conf",
        }
        student_info = {
            'submission_time': timezone.now().strftime("%Y%m%d%H%M%S"),
            'anonymous_student_id': STUDENT_ID
        }
        xqueue_body = {
            'grader_payload': json.dumps(grader_payload),
            'student_info': json.dumps(student_info),
            'student_response': "Test!",
            'max_score': 1,
        }
        content = {
            'xqueue_header': json.dumps(xqueue_header),
            'xqueue_body': json.dumps(xqueue_body),
        }

        response = self.c.login(username='test', password='CambridgeMA')

        content = self.c.post(
            SUBMIT_URL,
            content,
        )

        log.debug(content)

        body = json.loads(content.content)

        self.assertEqual(body['success'], True)


class GraderInterfaceTest(unittest.TestCase):
    def setUp(self):
        if(User.objects.filter(username='test').count() == 0):
            user = User.objects.create_user('test', 'test@test.com', 'CambridgeMA')
            user.save()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        for sub in Submission.objects.all():
            sub.delete()

    def test_submission_create(self):
        sub = get_test_sub("IN")
        sub.save()
        assert True

    def test_get_ml_subs_false(self):
        content = self.c.get(
            ML_GET_URL,
            data={}
        )

        body = json.loads(content.content)
        log.debug(body)

        #Make sure that there really isn't anything to grade
        self.assertEqual(body['error'], "Nothing to grade.")
        self.assertEqual(body['success'], False)

    def test_get_ml_subs_true(self):

        for i in xrange(0,settings.MIN_TO_USE_ML+1):
            sub=get_test_sub("IN")
            sub.state=SubmissionState.finished
            sub.save()

            grade=get_test_grader("IN")
            grade.submission=sub
            grade.save()

        log.debug("Submission count: {0}".format(staff_grading_util.finished_submissions_graded_by_instructor(LOCATION).count()))

        sub=get_test_sub("ML")
        sub.save()

        content = self.c.get(
            ML_GET_URL,
            data={}
        )
        body = json.loads(content.content)
        log.debug(body)

        self.assertEqual(body['success'],True)

        sub=Submission.objects.get(id=body['submission_id'])
        self.assertEqual(sub.prompt,"prompt")

    def test_get_sub_in(self):
        sub = get_test_sub("IN")
        sub.save()

        content = self.c.get(
            IN_GET_URL,
            data={'course_id': 'course_id'}
        )

        body = json.loads(content.content)

        sub_id = body['submission_id']

        return_code = body['success']
        #Check to see if a submission is received from the interface
        self.assertEqual(return_code, True)

        #Ensure that the submission exists and is the right one
        sub = Submission.objects.get(id=sub_id)
        self.assertEqual(sub.prompt, "prompt")

    def test_put_result(self):
        sub = get_test_sub("IN")
        sub.save()
        post_dict={
            'feedback': "test feedback",
            'submission_id' : 1 ,
            'grader_type' : "ML" ,
            'status' : "S",
            'confidence' : 1,
            'grader_id' : 1,
            'score' : 1,
            }

        content = self.c.post(
            PUT_URL,
            post_dict,
        )

        body=json.loads(content.content)

        log.debug(body)
        return_code=body['success']

        #Male sure that function returns true
        self.assertEqual(return_code,True)

        sub=Submission.objects.get(id=1)
        successful_grader_count=sub.get_successful_graders().count()

        #Make sure that grader object is actually created!
        self.assertEqual(successful_grader_count,1)



