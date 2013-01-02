from django.contrib.auth.models import User
from django.test.client import Client
from django.conf import settings

from controller.models import Submission, Grader, SubmissionState , GraderStatus

from django.utils import timezone

from controller.models import Submission,Grader
from peer_grading.models import CalibrationHistory,CalibrationRecord
import random
import json
from ml_grading import ml_model_creation

MAX_SCORE = 3

def create_user():

    if(User.objects.filter(username='test').count() == 0):
        user = User.objects.create_user('test', 'test@test.com', 'CambridgeMA')
        user.save()

def delete_all():
    for sub in Submission.objects.all():
        sub.delete()

    for grade in Grader.objects.all():
        grade.delete()

    for cal_hist in CalibrationHistory.objects.all():
        cal_hist.delete()

    for cal_record in CalibrationRecord.objects.all():
        cal_record.delete()

def get_sub(grader_type,student_id,location, course_id="course_id"):
    test_sub = Submission(
        prompt="prompt",
        student_id=student_id,
        problem_id="id",
        state=SubmissionState.waiting_to_be_graded,
        student_response="This is a response that will hopefully pass basic sanity checks.",
        student_submission_time=timezone.now(),
        xqueue_submission_id="id",
        xqueue_submission_key="key",
        xqueue_queue_name="MITx-6.002x",
        location=location,
        course_id=course_id,
        max_score=MAX_SCORE,
        next_grader_type=grader_type,
        previous_grader_type=grader_type,
        grader_settings="ml_grading.conf",
    )
    return test_sub

def get_grader(grader_type):
    test_grader=Grader(
        score= random.randint(0, MAX_SCORE),
        feedback="",
        status_code=GraderStatus.success,
        grader_id="1",
        grader_type=grader_type,
        confidence=1,
        is_calibration=False,
    )

    return test_grader

def get_student_info(student_id):
    student_info = {
        'submission_time': timezone.now().strftime("%Y%m%d%H%M%S"),
        'anonymous_student_id': student_id
    }
    return json.dumps(student_info)

def get_xqueue_header():
    xqueue_header = {
        'submission_id': 1,
        'submission_key': 1,
        'queue_name': "MITx-6.002x",
    }
    return json.dumps(xqueue_header)

def create_ml_model(student_id, location):
    #Create enough instructor graded submissions that ML will work
    for i in xrange(0,settings.MIN_TO_USE_ML):
        sub=get_sub("IN",student_id,location)
        sub.state=SubmissionState.finished
        sub.save()

        grade=get_grader("IN")
        grade.submission=sub
        grade.save()

    # Create ML Model
    ml_model_creation.handle_single_location(location)
