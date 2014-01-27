"""
Run me with:
    python manage.py test --settings=grading_controller.test_settings controller
"""
import json
import unittest
import datetime
from django.utils import timezone
import logging
import urlparse
import time

from django.test.client import Client
from django.conf import settings

import util
import test_util

from models import Submission, Grader, GraderStatus, SubmissionState
import expire_submissions
import grader_util

from xqueue_interface import handle_submission
from tasks import expire_submissions_task, pull_from_xqueue
from control_util import SubmissionControl
from copy import deepcopy
import rubric_functions
from staff_grading.staff_grading_util import StaffLocation

from staff_grading import staff_grading_util

import datetime

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

UNICODE_RUBRIC_XML = u"""
<rubric>
    <category>
        <description>\u2655One</description>
        <option>\u26550</option>
        <option>\u26551</option>
    </category>
    <category>
        <description>\u2655Two</description>
        <option>\u26550</option>
        <option>\u26551</option>
    </category>
</rubric>
            """


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
    return True

class XQueueInterfaceTest(unittest.TestCase):
    grader_payload = {
        'location': LOCATION,
        'course_id': u'MITx/6.002x',
        'problem_id': u'6.002x/Welcome/OETest',
        'grader': "temp",
        'prompt' : 'This is a prompt',
        'rubric' : 'This is a rubric.',
        'grader_settings' : "ml_grading.conf",
        'skip_basic_checks': False
    }

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

    def get_content(self, grader_payload):
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
        return content

    def test_xqueue_submit(self):
        Submission.objects.all().delete()
        response = self.c.login(username='test', password='CambridgeMA')

        content = self.c.post(
            SUBMIT_URL,
            self.get_content(self.grader_payload),
        )

        body = json.loads(content.content)

        self.assertEqual(body['success'], True)

        sub = Submission.objects.all()[0]
        control = SubmissionControl(sub)
        self.assertEqual(control.min_to_calibrate, settings.PEER_GRADER_MINIMUM_TO_CALIBRATE)
        self.assertEqual(control.max_to_calibrate, settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE)
        self.assertEqual(control.peer_grader_count, settings.PEER_GRADER_COUNT)
        self.assertEqual(control.required_peer_grading_per_student, settings.REQUIRED_PEER_GRADING_PER_STUDENT)
        self.assertEqual(control.minimum_to_use_ai, settings.MIN_TO_USE_ML)
        self.assertEqual(control.minimum_to_use_peer, settings.MIN_TO_USE_PEER)

    def test_xqueue_control_submit(self):
        Submission.objects.all().delete()
        response = self.c.login(username='test', password='CambridgeMA')
        gp = deepcopy(self.grader_payload)
        gp['control'] = json.dumps({
            'min_to_calibrate' : 1,
            'max_to_calibrate' : 1,
            'peer_grader_count': 1,
            'required_peer_grading': 1,
            'staff_minimum_for_peer_grading': 1,
            'staff_minimum_for_ai_grading': 1,
        })

        content = self.c.post(
            SUBMIT_URL,
            self.get_content(gp),
        )
        body = json.loads(content.content)

        self.assertEqual(body['success'], True)

        sub = Submission.objects.all()[0]
        control = SubmissionControl(sub)
        self.assertEqual(control.min_to_calibrate, 1)
        self.assertEqual(control.max_to_calibrate, 1)
        self.assertEqual(control.peer_grader_count, 1)
        self.assertEqual(control.required_peer_grading_per_student, 1)
        self.assertEqual(control.minimum_to_use_ai, 1)
        self.assertEqual(control.minimum_to_use_peer, 1)

    def _message_submission(self, success, score=None, submission_id=None):
        sub = test_util.get_sub("IN",STUDENT_ID,LOCATION)
        sub.save()
        grade=test_util.get_grader("IN")
        grade.submission=sub
        grade.save()
        grader_id = grade.grader_id
        if submission_id is None:
            submission_id = sub.id

        message = {
            'grader_id': grader_id,
            'submission_id': submission_id,
            'feedback': "This is test feedback",
            'student_info': test_util.get_student_info(STUDENT_ID),
        }
        if score is not None:
            message['score'] = score
        
        content = {
            'xqueue_header': test_util.get_xqueue_header(),
            'xqueue_body': json.dumps(message),
        }
        content = self.c.post(
                SUBMIT_MESSAGE_URL,
                content
        )
        body = json.loads(content.content)
        self.assertEqual(body['success'], success)


    def test_message_submission_success(self):
        self._message_submission(True) 
        
    def test_message_submission_with_score_success(self):
        self._message_submission(True, score=3)

    def test_message_submission_without_base_submission_fail(self):
        self._message_submission(False, submission_id=5)


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

        #Make sure that there really isn't anything to grade
        self.assertEqual(body['error'], "Nothing to grade.")
        self.assertEqual(body['success'], False)

    def test_get_ml_subs_true(self):
        test_util.create_ml_model(STUDENT_ID, LOCATION)

        #Create a submission that requires ML grading
        sub=test_util.get_sub("ML",STUDENT_ID,LOCATION)
        sub.save()

        content = self.c.get(
            ML_GET_URL,
            data={}
        )
        body = json.loads(content.content)

        #Ensure that submission is retrieved successfully
        self.assertEqual(body['success'],True)

        sub=Submission.objects.get(id=int(body['submission_id']))
        self.assertEqual(sub.prompt,"prompt")

    def test_get_sub_in(self):
        Submission.objects.all().delete()
        sub = test_util.get_sub("IN",STUDENT_ID,LOCATION)
        sub.state = SubmissionState.waiting_to_be_graded
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
            "rubric_scores_complete" : True,
            "rubric_scores" : json.dumps([1,1]),
            }

        content = self.c.post(
            PUT_URL,
            post_dict,
        )

        body=json.loads(content.content)

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

    def test_sanitize_html(self):
        feedback = "This is a sample feedback. <img src='abc' onerror=alert(1)>"

        sanitized_feedback = util.sanitize_html(feedback)

        # Sanitized feedback should not contain onerror attribute.
        self.assertFalse("onerror" in sanitized_feedback)


class ExpireSubmissionsTests(unittest.TestCase):
    fixtures = ['/controller/test_data.json']
    def setUp(self):
        test_util.create_user()

        self.c = Client()
        response = self.c.login(username='test', password='CambridgeMA')

    def tearDown(self):
        test_util.delete_all()

    def test_reset_subs_to_in(self):
        test_sub = test_util.get_sub("ML", STUDENT_ID, LOCATION)
        test_sub.save()
        
        expire_submissions.reset_ml_subs_to_in()

        test_sub = Submission.objects.get(id=test_sub.id)

        self.assertEqual(test_sub.next_grader_type, "IN")

    def test_reset_in_subs_to_ml(self):
        test_util.create_ml_model(STUDENT_ID, LOCATION)

        new_sub = test_util.get_sub("IN", STUDENT_ID, LOCATION)
        new_sub.save()

        success = expire_submissions.reset_in_subs_to_ml()
        
        new_sub = Submission.objects.get(id = new_sub.id)

        self.assertEqual(new_sub.next_grader_type, "ML")
        self.assertTrue(success)

    def test_reset_subs_in_basic_check(self):
        test_sub = test_util.get_sub("BC", STUDENT_ID, LOCATION)
        test_sub.save()
        subs = Submission.objects.all()

        success = expire_submissions.reset_subs_in_basic_check()

        test_sub = Submission.objects.get(id = test_sub.id)
        test_grader = Grader.objects.get(submission_id = test_sub.id)

        self.assertTrue(success)
        self.assertNotEqual(test_sub.next_grader_type, "BC")
        self.assertEqual(test_grader.grader_type, "BC")

    def test_reset_failed_subs_in_basic_check(self):
        test_sub = test_util.get_sub("IN", STUDENT_ID, LOCATION)
        test_sub.save()

        grader = test_util.get_grader("BC", status_code = GraderStatus.failure)
        grader.submission = test_sub
        grader.save()

        success = expire_submissions.reset_failed_subs_in_basic_check()
        self.assertTrue(success)

        graders = test_sub.grader_set.all()
        success_grader = graders[1]

        self.assertEqual(success_grader.status_code, GraderStatus.success)

    def test_reset_timed_out_submissions(self):
        test_sub = test_util.get_sub("IN", STUDENT_ID, LOCATION)
        test_sub.state = SubmissionState.being_graded
        test_sub.save()

        success = expire_submissions.reset_timed_out_submissions()
        self.assertEqual(success, True)

        test_sub = Submission.objects.all()[0]
        self.assertEqual(test_sub.state, SubmissionState.waiting_to_be_graded)

    def test_reset_timed_out_submissions_finished(self):
        test_sub_f = test_util.get_sub("PE", STUDENT_ID, LOCATION)
        test_sub_f.state = SubmissionState.being_graded
        test_sub_f.control_fields = json.dumps({'peer_grade_finished_submissions_when_none_pending': True})
        test_sub_f.posted_results_back_to_queue = True
        test_sub_f.save()

        success = expire_submissions.reset_timed_out_submissions()
        self.assertEqual(success, True)

        test_sub = Submission.objects.all()[0]
        self.assertEqual(test_sub.state, SubmissionState.finished)

    def test_get_submissions_that_have_expired(self):
        test_sub = test_util.get_sub("IN", STUDENT_ID, LOCATION)
        test_sub.save()

        expired_submissions = expire_submissions.get_submissions_that_have_expired()
        self.assertEqual(len(expired_submissions),1)

    def test_get_duplicate_scores_and_feedback(self):
        """
        Want to test that a submission with a single BC grade returns that grade, but
        a submission with BCs and multiple PEs returns the PE grade set
        (this situation happens with duplicates)
        """
        sub1 = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        sub1.save()

        sub1_bc = test_util.get_grader("BC", score=1)
        sub1_bc.submission = sub1
        sub1_bc.save()

        sub2 = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        sub2.is_duplicate_checked = True
        sub2.state = "F"
        sub2.save()

        sub2_bc = test_util.get_grader("BC", score=1)
        sub2_bc.submission = sub2
        sub2_bc.save()

        for pe_score in [2, 3, 4]:
            pe = test_util.get_grader("PE", score=pe_score)
            pe.submission = sub2
            pe.save()

        dup2 = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        dup2.is_duplicate = True
        dup2.duplicate_submission_id = sub2.id
        dup2.save()

        expire_submissions.check_if_grading_finished_for_duplicates()

        fb1 = sub1.get_all_successful_scores_and_feedback()
        fb2 = sub2.get_all_successful_scores_and_feedback()
        fb_dup2 = dup2.get_all_successful_scores_and_feedback()
        self.assertEquals(fb1['score'], 1)
        self.assertEquals(set(fb2['score']), set([2,3,4]))
        self.assertEquals(set(fb_dup2['score']), set([2,3,4]))

    def test_finalize_expired_submissions(self):
        test_sub = test_util.get_sub("IN", STUDENT_ID, LOCATION)
        test_sub.save()

        success = expire_submissions.finalize_expired_submissions(Submission.objects.all())
        self.assertEqual(success, True)

        test_sub = Submission.objects.all()[0]

        self.assertEqual(test_sub.state, SubmissionState.finished)

    def test_check_if_grading_finished_for_duplicates(self):
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        handle_submission(test_sub)

        sl = StaffLocation(LOCATION)
        control = SubmissionControl(sl.latest_submission())

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

        test_sub2 = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub2.save()
        handle_submission(test_sub2)
        self.assertTrue(test_sub2.is_duplicate)

        success = expire_submissions.check_if_grading_finished_for_duplicates()
        self.assertEqual(success, True)
        test_sub2.is_duplicate = False
        test_sub2.save()

        test_sub3 = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub3.is_duplicate = False
        test_sub3.save()

        self.assertEqual(test_sub3.is_duplicate, False)
        test_sub3.has_been_duplicate_checked = False
        test_sub3.save()
        expire_submissions.mark_student_duplicate_submissions()
        test_sub3 = Submission.objects.get(id=test_sub3.id)
        self.assertEqual(test_sub3.is_duplicate,True)

        test_sub3.duplicate_submission_id = None
        test_sub3.is_plagiarized = False
        test_sub3.save()
        expire_submissions.add_in_duplicate_ids()
        test_sub3 = Submission.objects.get(id=test_sub3.id)
        self.assertTrue(test_sub3.duplicate_submission_id is not None)

class TasksTest(unittest.TestCase):
    def test_expire_submissions(self):
        test_sub = test_util.get_sub("ML", STUDENT_ID, LOCATION)
        test_sub.save()

        expire_submissions_task.apply()

        test_sub = Submission.objects.get(id=test_sub.id)

        self.assertEqual(test_sub.next_grader_type, "IN")

    def test_pull_from_xqueue(self):
        pull_from_xqueue.apply()

class GraderUtilTest(unittest.TestCase):
    def test_check_name_uniqueness(self):
        success, name_unique = grader_util.check_name_uniqueness("temp", LOCATION, "course_id")
        self.assertTrue(name_unique)
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION + "1", "PE")
        test_sub.save()
        success, name_unique = grader_util.check_name_uniqueness("id", LOCATION, "course_id")
        self.assertFalse(name_unique)

    def test_check_for_student_grading_notifications(self):
        success, new_student_grading = grader_util.check_for_student_grading_notifications(STUDENT_ID, "course_id", datetime.datetime.now() - datetime.timedelta(minutes=10))
        self.assertFalse(new_student_grading)

    def test_get_problems_student_has_tried(self):
        success, sub_list = grader_util.get_problems_student_has_tried(STUDENT_ID, "course_id")
        self.assertTrue(isinstance(sub_list, list))
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        success, sub_list = grader_util.get_problems_student_has_tried(STUDENT_ID, "course_id")
        self.assertTrue(len(sub_list)>0)

    def test_check_for_combined_notifications(self):
        notification_dict = {
            'course_id' : 'course_id',
            'user_is_staff' : False,
            'last_time_viewed' : datetime.datetime.now() - datetime.timedelta(minutes=10),
            'student_id' : STUDENT_ID
        }

        success, combined_notifications = grader_util.check_for_combined_notifications(notification_dict)
        self.assertEqual(len(combined_notifications.keys()), 3)

        notification_dict['user_is_staff'] = True
        success, combined_notifications = grader_util.check_for_combined_notifications(notification_dict)
        self.assertEqual(len(combined_notifications.keys()), 5)

    def test_finalize_expired_submission(self):
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        grader_util.finalize_expired_submission(test_sub)
        self.assertEqual(test_sub.state, SubmissionState.finished)

class UtilTest(unittest.TestCase):
    def test_create_xqueue_header_and_body(self):
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()
        grader = test_util.get_grader("BC", status_code = GraderStatus.failure)
        grader.submission = test_sub
        grader.save()
        xqueue_header, xqueue_body = util.create_xqueue_header_and_body(test_sub)
        self.assertIsInstance(xqueue_header, dict)
        self.assertIsInstance(xqueue_body, dict)

class TestControl(unittest.TestCase):
    def test_control_create(self):
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.control_fields = json.dumps({'min_to_calibrate' : 1,
                                              'max_to_calibrate' : 1,
                                              'peer_grader_count' : 1,
                                              'required_peer_grading' : 1,
                                              'peer_grade_finished_submissions_when_none_pending' : True,
                                              'staff_minimum_for_peer_grading': 1,
                                              'staff_minimum_for_ai_grading': 1,
        })
        test_sub.save()

        control = SubmissionControl(test_sub)

        self.assertEqual(control.min_to_calibrate, 1)
        self.assertEqual(control.max_to_calibrate, 1)
        self.assertEqual(control.peer_grader_count, 1)
        self.assertEqual(control.required_peer_grading_per_student, 1)
        self.assertEqual(control.peer_grade_finished_submissions_when_none_pending, True)
        self.assertEqual(control.minimum_to_use_peer, 1)
        self.assertEqual(control.minimum_to_use_ai, 1)

    def test_control_default(self):
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE")
        test_sub.save()

        control = SubmissionControl(test_sub)

        self.assertEqual(control.min_to_calibrate, settings.PEER_GRADER_MINIMUM_TO_CALIBRATE)
        self.assertEqual(control.max_to_calibrate, settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE)
        self.assertEqual(control.peer_grader_count, settings.PEER_GRADER_COUNT)
        self.assertEqual(control.required_peer_grading_per_student, settings.REQUIRED_PEER_GRADING_PER_STUDENT)
        self.assertEqual(control.peer_grade_finished_submissions_when_none_pending,
                         settings.PEER_GRADE_FINISHED_SUBMISSIONS_WHEN_NONE_PENDING)
        self.assertEqual(control.minimum_to_use_ai, settings.MIN_TO_USE_ML)
        self.assertEqual(control.minimum_to_use_peer, settings.MIN_TO_USE_PEER)

class RubricTest(unittest.TestCase):
    def test_unicode_rubric(self):
        test_sub = test_util.get_sub("PE", STUDENT_ID, LOCATION, "PE", rubric=UNICODE_RUBRIC_XML)
        test_sub.save()
        scores = [0,1]

        for i in xrange(0, settings.PEER_GRADER_COUNT):
            grader = test_util.get_grader("PE")
            grader.submission = test_sub
            grader.save()

            success, rubric = rubric_functions.generate_rubric_object(grader, scores, UNICODE_RUBRIC_XML)
            self.assertEqual(success, True)

            rubric.save()

        test_sub.state = "F"
        test_sub.previous_grader_type = "PE"
        test_sub.save()

        all_graders = test_sub.get_all_successful_scores_and_feedback()

        self.assertEqual(all_graders['grader_type'], "PE")











