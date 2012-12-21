"""
Run me with:
    python manage.py test --settings=grading_controller.test_settings controller
"""
import json
import unittest
from datetime import datetime
from django.utils import timezone
import logging
import urlparse
from string import lower

from django.contrib.auth.models import User
from django.test.client import Client
import requests
from django.conf import settings

import xqueue_interface
import grader_interface
import util
import test_util

from models import Submission, Grader
from models import GraderStatus, SubmissionState

from staff_grading import staff_grading_util
from ml_grading import ml_model_creation

import management.commands.pull_from_xqueue as pull_from_xqueue

from mock import Mock

import project_urls

log = logging.getLogger(__name__)

LOGIN_URL = project_urls.ControllerURLs.log_in
SUBMIT_URL = project_urls.ControllerURLs.submit
SUBMIT_MESSAGE_URL = project_urls.ControllerURLs.submit_message
ML_GET_URL = project_urls.ControllerURLs.get_submission_ml
IN_GET_URL = project_urls.ControllerURLs.get_submission_in
PUT_URL= project_urls.ControllerURLs.put_result
ETA_URL=project_urls.ControllerURLs.get_eta_for_submission


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

class XQueueInterfaceTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()

        self.c = Client()

    def tearDown(self):
        test_util.delete_all()

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
        grader_payload = {
            'location': LOCATION,
            'course_id': u'MITx/6.002x',
            'problem_id': u'6.002x/Welcome/OETest',
            'grader': "temp",
            'prompt' : 'This is a prompt',
            'rubric' : 'This is a rubric.',
            'grader_settings' : "ml_grading.conf",
        }
        xqueue_body = {
            'grader_payload': json.dumps(grader_payload),
            'student_info': test_util.get_student_info(STUDENT_ID),
            'student_response': "Test! And longer now so tests pass.",
            'max_score': 1,
        }
        content = {
            'xqueue_header': test_util.get_xqueue_header(),
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


    def test_message_submission_with_score_success(self):
        sub = test_util.get_sub("IN",STUDENT_ID,LOCATION)
        sub.save()
        grade=test_util.get_grader("IN")
        grade.submission=sub
        grade.save()
        grader_id = grade.grader_id
        submission_id = sub.id
        # now send a new message
        message = {
            'grader_id': grader_id,
            'submission_id': submission_id,
            'feedback': 'Testing feedback for the message controller. Yay.',
            'student_info': test_util.get_student_info(STUDENT_ID),
            'score': '3'
        }
        content = {
            'xqueue_header': test_util.get_xqueue_header(),
            'xqueue_body': json.dumps(message),
        }

        content = self.c.post(
                SUBMIT_MESSAGE_URL,
                content
        )
        log.debug(content)
        body = json.loads(content.content)

        self.assertEqual(body['success'], True)


class GraderInterfaceTest(unittest.TestCase):
    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        test_util.delete_all()

    def test_submission_create(self):
        sub = test_util.get_sub("IN",STUDENT_ID,LOCATION)
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

        #Create enough instructor graded submissions that ML will work
        for i in xrange(0,settings.MIN_TO_USE_ML):
            sub=test_util.get_sub("IN",STUDENT_ID,LOCATION)
            sub.state=SubmissionState.finished
            sub.save()

            grade=test_util.get_grader("IN")
            grade.submission=sub
            grade.save()


        # Create ML Model
        ml_model_creation.handle_single_location(LOCATION)

        #Create a submission that requires ML grading
        sub=test_util.get_sub("ML",STUDENT_ID,LOCATION)
        sub.save()

        content = self.c.get(
            ML_GET_URL,
            data={}
        )
        body = json.loads(content.content)
        log.debug(body)

        #Ensure that submission is retrieved successfully
        self.assertEqual(body['success'],True)

        sub=Submission.objects.get(id=int(body['submission_id']))
        self.assertEqual(sub.prompt,"prompt")

    def test_get_sub_in(self):
        sub = test_util.get_sub("IN",STUDENT_ID,LOCATION)
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
        sub = Submission.objects.get(id=int(sub_id))
        self.assertEqual(sub.prompt, "prompt")

    def test_put_result(self):
        sub = test_util.get_sub("IN",STUDENT_ID,LOCATION)
        sub.save()
        post_dict={
            'feedback': "test feedback",
            'submission_id' : 1 ,
            'grader_type' : "ML" ,
            'status' : "S",
            'confidence' : 1,
            'grader_id' : 1,
            'score' : 1,
            'errors' : "test",
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

class ControllerUtilTests(unittest.TestCase):
    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        test_util.delete_all()

    def test_parse_xobject_false(self):
        sample_xqueue_return='blah'
        return_code, content= util.parse_xobject(sample_xqueue_return, "blah")

        #Should not parse properly
        self.assertEqual(return_code,False)

    def test_request_eta_for_submission_false(self):
        get_data={
            'location' : 'blah'
        }

        content=self.c.get(
            ETA_URL,
            get_data
        )

        body=json.loads(content.content)

        self.assertEqual(body['success'], False)

    def test_request_eta_for_submission_in_true(self):
        test_sub=test_util.get_sub("IN", STUDENT_ID, LOCATION)
        test_sub.save()

        get_data={
            'location' : LOCATION
        }

        content=self.c.get(
            ETA_URL,
            get_data
        )

        body=json.loads(content.content)

        self.assertEqual(body['success'], True)
        self.assertEqual(body['eta'], settings.DEFAULT_ESTIMATED_GRADING_TIME)




