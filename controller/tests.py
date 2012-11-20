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

log=logging.getLogger(__name__)

SUBMIT_URL="/grading_controller/submit/"
LOGIN_URL="/grading_controller/login/"

def parse_xreply(xreply):
    xreply = json.loads(xreply)
    return (xreply['return_code'], xreply['content'])

class xqueue_interface_test(unittest.TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='test',password='CambridgeMA')

    def tearDown(self):
        self.user.delete()

    def test_log_in(self):
        '''
        Test Xqueue login behavior. Particularly important is the response for GET (e.g. by redirect)
        '''
        c = Client()

        # 0) Attempt login with GET, must fail with message='login_required'
        #    The specific message is important, as it is used as a flag by LMS to reauthenticate!
        response = c.get(LOGIN_URL)
        (error, msg) = parse_xreply(response.content)
        self.assertEqual(error, True)

        # 1) Attempt login with POST, but no auth
        response = c.post(LOGIN_URL)
        (error,_) = parse_xreply(response.content)
        self.assertEqual(error, True)

        # 2) Attempt login with POST, incorrect auth
        response = c.post(LOGIN_URL,{'username':'test','password':'PaloAltoCA'})
        (error,_) = parse_xreply(response.content)
        self.assertEqual(error, True)

        # 3) Login correctly
        response = c.post(LOGIN_URL,{'username':'test','password':'CambridgeMA'})
        (error,_) = parse_xreply(response.content)
        self.assertEqual(error, False)

    def test_xqueue_submit(self):
        controller_session=requests.session()

        xqueue_header={
            'submission_id' : 1,
            'submission_key' : 1,
            'queue_name' : "MITx-6.002x",
        }
        grader_payload={
            'location' : u'MITx/6.002x/problem/OETest',
            'course_id' : u'MITx/6.002x',
            'problem_id' : u'6.002x/Welcome/OETest' ,
            'grader' : "temp",
        }
        student_info={
            'submission_time' : datetime.now().strftime("%Y%m%d%H%M%S"),
            'anonymous_student_id' : "blah"
        }
        xqueue_body={
            'grader_payload' : grader_payload,
            'student_info' : student_info,
            'student_response' : "Test!",
            'max_score' : 1,
        }
        content={
            'xqueue_header' : json.dumps(xqueue_header),
            'xqueue_body' : json.dumps(xqueue_body),
        }

        controller_login_url = urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],'/grading_controller/login/')

        (controller_error,controller_msg)=util.login(
            controller_session,
            controller_login_url,
            settings.GRADING_CONTROLLER_INTERFACE['django_auth']['username'],
            settings.GRADING_CONTROLLER_INTERFACE['django_auth']['password'],
        )

        success,msg = util._http_post(
            controller_session,
            urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],'/grading_controller/submit/'),
            content,
            settings.REQUESTS_TIMEOUT,
        )

        self.assertEqual(success,True)


class grader_interface_test(unittest.TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='test',password='CambridgeMA')

    def tearDown(self):
        self.user.delete()



