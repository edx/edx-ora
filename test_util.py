from django.contrib.auth.models import User, Group, Permission
from django.test.client import Client
from django.conf import settings

from controller.models import Submission, Grader, SubmissionState , GraderStatus

from django.utils import timezone

from controller.models import Submission,Grader
from peer_grading.models import CalibrationHistory,CalibrationRecord
import random
import json
from ml_grading import ml_model_creation
from django.db.models import Max
import string
import random
from controller.control_util import SubmissionControl
from peer_grading.peer_grading_util import PeerLocation

import logging
log = logging.getLogger(__name__)

MAX_SCORE = 3

RUBRIC_XML = """
<rubric>
    <category>
        <description>One</description>
        <option>0</option>
        <option>1</option>
    </category>
    <category>
        <description>Two</description>
        <option>0</option>
        <option>1</option>
    </category>
</rubric>
            """

def create_user():

    if(User.objects.filter(username='test').count() == 0):
        user = User.objects.create_user('test', 'test@test.com', 'CambridgeMA')
        user.is_staff = True
        user.is_superuser = True
        submitters, created = Group.objects.get_or_create(name=settings.SUBMITTERS_GROUP)
        view_submission = Permission.objects.get(codename=settings.EDIT_SUBMISSIONS_PERMISSION)
        submitters.permissions.add(view_submission)
        user.groups.add(submitters)
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

def get_sub(grader_type,student_id,location, preferred_grader_type="ML", course_id="course_id", rubric=RUBRIC_XML, student_response = "This is a response that will hopefully pass basic sanity checks."):
    prefix = "ml"
    if preferred_grader_type=="PE":
        prefix = "peer"

    # Get all existing xqueue ids
    xqueue_id = generate_new_xqueue_id()

    test_sub = Submission(
        prompt="prompt",
        student_id=student_id,
        problem_id="id",
        state=SubmissionState.waiting_to_be_graded,
        student_response= student_response,
        student_submission_time=timezone.now(),
        xqueue_submission_id=xqueue_id,
        xqueue_submission_key="key",
        xqueue_queue_name="MITx-6.002x",
        location=location,
        course_id=course_id,
        max_score=MAX_SCORE,
        next_grader_type=grader_type,
        previous_grader_type=grader_type,
        grader_settings= prefix + "_grading.conf",
        preferred_grader_type=preferred_grader_type,
        rubric = rubric,
        )
    return test_sub

def get_grader(grader_type, status_code=GraderStatus.success, score = None):
    if score is None:
        score = random.randint(0, MAX_SCORE)
    test_grader=Grader(
        score= score,
        feedback="",
        status_code=status_code,
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

def generate_new_xqueue_id():
    xqueue_ids = [i['xqueue_submission_id'] for i in Submission.objects.all().values('xqueue_submission_id')]

    # Xqueue id needs to be unique, so ensure you generate a unique value.
    xqueue_id = 'a'
    while xqueue_id in xqueue_ids:
        id_length = random.randint(1,10)
        xqueue_id = 'a'
        for i in xrange(0, id_length):
            xqueue_id += random.choice(string.ascii_letters)
    return xqueue_id

def get_xqueue_header():
    xqueue_header = {
        'submission_id': generate_new_xqueue_id(),
        'submission_key': 1,
        'queue_name': "MITx-6.002x",
    }
    return json.dumps(xqueue_header)

def create_ml_model(student_id, location):
    sub = get_sub("IN",student_id,location, "ML")
    sub.state = SubmissionState.finished
    sub.save()

    pl = PeerLocation(location, student_id)
    control = SubmissionControl(pl.latest_submission())

    # Create enough instructor graded submissions that ML will work.
    for i in xrange(0, control.minimum_to_use_ai):
        sub = get_sub("IN", student_id, location, "ML")
        sub.state = SubmissionState.finished
        sub.save()

        grade = get_grader("IN")
        grade.submission = sub
        grade.save()

    # Create ML Model
    ml_model_creation.handle_single_location(location)
