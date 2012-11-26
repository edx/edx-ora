import json
import logging
import random

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from controller.models import Submission
from controller import util
import requests
import urlparse

from models import CalibrationHistory, CalibrationRecord
from controller.models import Submission,Grader

log = logging.getLogger(__name__)

feedback_template = u"""

<section>
    <header>Feedback</header>
    <div class="shortform">
        <div class="result-output">
          <p>Score: {score}</p>
        </div>
    </div>
    <div class="longform">
        <div class="result-output">
          <div class="feedback">
            Feedback: {feedback}
          </div>
        </div>
    </div>
</section>

"""

_INTERFACE_VERSION=1

def get_next_submission(request):
    """
    Gets next submission from controller for peer grading.
    Input:
        Get request with the following keys:
           grader_id - Student id of the grader
           location - The problem id to get peer grading for.
    """

    if request.method!="GET":
        raise Http404

    grader_id = request.GET.get("grader_id")
    location = request.GET.get("location")

    if not grader_id or not location:
        return util._error_response("Failed to find needed keys 'grader_id' and 'location'",_INTERFACE_VERSION )

    (found,sub_id) = util.get_single_peer_grading_item(location,grader_id)

    if not found:
        return  util._error_response("No current grading.",_INTERFACE_VERSION)

    try:
        sub=Submission.objects.get(id=sub_id)
    except:
        log.debug("Could not find submission with id {0}".format(sub_id))
        return util._error_response("Error getting grading.",_INTERFACE_VERSION)

    if sub.state!="C":
        log.debug("Submission with id {0} has incorrect internal state {1}.".format(sub_id,sub.state))
        return util._error_response("Error getting grading.",_INTERFACE_VERSION)

    response={
        'submission_id' : sub_id,
        'submission_key' : sub.xqueue_submission_key,
        'student_response' : sub.student_response,
        'prompt' : sub.prompt,
        'rubric' : sub.rubric,
        'max_score' : sub.max_score,
        }

    return util._success_response(response,_INTERFACE_VERSION)

def save_grade(request):
    """
    Supports POST requests with the following arguments:

    location: string
    grader_id: int
    submission_id: int
    score: int
    feedback: string
    submission_key : string

    Returns json dict with keys

    version: int
    success: bool
    error: string, present if not success
    """
    if request.method != "POST":
        raise Http404

    post_data=request.POST.dict().copy()

    for tag in ['location','grader_id','submission_id','submission_key','score','feedback']:
        if not tag in post_data:
            return util._error_response("Cannot find needed key {0} in request.".format(tag),_INTERFACE_VERSION)

    location = post_data['location']
    grader_id = post_data['grader_id']
    submission_id = post_data['submission_id']

    #Submission key currently unused, but plan to use it for validation in the future.
    submission_key = post_data['submission_key']
    score = post_data['score']

    #This is done to ensure that response is properly formatted on the lms side.
    feedback_string = post_data['feedback']
    feedback=feedback_template.format(feedback=feedback_string,score=score)

    try:
        score = int(score)
    except ValueError:
        return util._error_response("Expected integer score.  Got {0}".format(score),_INTERFACE_VERSION )

    d = {'submission_id': submission_id,
         'score': score,
         'feedback': feedback,
         'grader_id': grader_id,
         'grader_type': 'PE',
         # Humans always succeed (if they grade at all)...
         'status': 'S',
         # ...and they're always confident too.
         'confidence': 1.0}

    #Currently not posting back to LMS.  Only saving grader object, and letting controller decide when to post back.
    (success,header) = util.create_and_save_grader_object(d)
    if not success:
        return util._error_response("There was a problem saving the grade.  Contact support.",_INTERFACE_VERSION)

    #xqueue_session=util.xqueue_login()
    #error,msg = util.post_results_to_xqueue(xqueue_session,json.dumps(header),json.dumps(post_data))

    return util._success_response({'msg' : "Posted to queue."},_INTERFACE_VERSION)

def is_student_calibrated(request):
    """
    Decides if student has fulfilled criteria for peer grading calibration for a given location (problem id).
    Input:
        student id, problem_id
    Output:
        Dictionary with boolean calibrated indicating whether or not student has finished calibration.

    Note: Location in the database is currently being used as the problem id.
    """

    if request.method!="GET":
        raise Http404

    problem_id=request.GET.get("problem_id")
    student_id=request.GET.get("student_id")

    matching_submissions=Submission.objects.filter(problem_id=problem_id)

    if matching_submissions.count<1:
        return util._error_response("Invalid problem id specified: {0}".format(problem_id),_INTERFACE_VERSION)

    calibration_history=CalibrationHistory.objects.get_or_create(student_id=student_id, location=problem_id)
    max_score=matching_submissions[0].max_score
    calibration_record_count=calibration_history.get_calibration_record_count()
    if (calibration_record_count>=settings.PEER_GRADER_MINIMUM_TO_CALIBRATE and
        calibration_record_count<settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE):
        calibration_error=calibration_history.get_average_calibration_error()
        normalized_calibration_error=calibration_error/float(max_score)
        if normalized_calibration_error>= settings.PEER_GRADER_MIN_NORMALIZED_CALIBRATION_ERROR:
            return util._success_response({'calibrated' : False}, _INTERFACE_VERSION)
        else:
            return util._success_response({'calibrated' : True}, _INTERFACE_VERSION)
    elif calibration_record_count>=settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE:
        return util._success_response({'calibrated' : True}, _INTERFACE_VERSION)
    else:
        return util._success_response({'calibrated' : False},_INTERFACE_VERSION)

def get_calibration_essay(student_id,location):
    """
    Gets a calibration essay for a particular student and location (problem id).
    Input:
        student id, location
    Output:
        dict containing text of calibration essay, prompt, rubric, max score, calibration essay id
    """

    calibration_submissions=Submission.objects.filter(
        location=location,
        grader__grader_type="IN",
        grader__is_calibration=True,
    )

    calibration_submission_count=calibration_submissions.count()
    if calibration_submission_count<settings.PEER_GRADER_MINIMUM_TO_CALIBRATE:
        return util._error_response("Not enough calibration essays.")

    student_calibration_history=CalibrationHistory.get(student_id=student_id,location=location)
    student_calibration_records=student_calibration_history.get_all_calibration_records()

    student_calibration_ids=[cr.id for cr in list(student_calibration_records)]
    calibration_essay_ids=[cr.id for cr in list(calibration_submissions)]

    for i in xrange(0,len(calibration_essay_ids)):
        if calibration_essay_ids[i] not in student_calibration_ids:
            calibration_data=get_calibration_essay_data(calibration_essay_ids[i])
            return util._success_response(calibration_data)

    if len(student_calibration_ids)>len(calibration_essay_ids):
        random_calibration_essay_id=random.sample(calibration_essay_ids,1)[0]
        calibration_data=get_calibration_essay_data(random_calibration_essay_id)
        return util._success_response(calibration_data)

    return util._error_response("Unexpected error.")



def get_calibration_essay_data(calibration_essay_id):
    """
    From a calibration essay id, lookup prompt, rubric, max score, prompt, essay text, and return
    Input:
        calibration essay id
    """

    try:
        sub=Submission.objects.get(id=calibration_essay_id)
    except:
        return "Could not find submission!"


    response={
        'submission_id' : calibration_essay_id,
        'submission_key' : sub.xqueue_submission_key,
        'student_response' : sub.student_response,
        'prompt' : sub.prompt,
        'rubric' : sub.rubric,
        'max_score' : sub.max_score,
        }

    return response


def is_peer_grading_finished_for_student(student_id):
    """
    Checks to see whether there are enough reliable peer evaluations of student to ensure that grading is done.
    Input:
        student id
    Output:
        Boolean indicating whether or not there are enough reliable evaluations.
    """
    pass

def save_calibration(request):
    """
    Saves a calibration essay sent back from LMS.
    Input:
        request dict containing keys student_id, location, calibration_essay_id, score, submission_key, feedback
    Output:
        Boolean indicating success in saving calibration essay or not.
    """

    if request.method != "POST":
        raise Http404

    post_data=request.POST.dict().copy()

    for tag in ['location','student_id','calibration_essay_id','submission_key','score','feedback']:
        if not tag in post_data:
            return util._error_response("Cannot find needed key {0} in request.".format(tag),_INTERFACE_VERSION)

    location = post_data['location']
    student_id = post_data['student_id']
    submission_id = post_data['calibration_essay_id']
    score = post_data['score']
    feedback=post_data['feedback']

    #Submission key currently unused, but plan to use it for validation in the future.
    submission_key = post_data['submission_key']

    try:
        score = int(score)
    except ValueError:
        return util._error_response("Expected integer score.  Got {0}".format(score),_INTERFACE_VERSION )

    d = {'submission_id': submission_id,
         'score': score,
         'feedback': feedback,
         'student_id' : student_id,
         'location' : location,
        }

    (success,message)=create_and_save_calibration_record(d)


def create_and_save_calibration_record(calibration_data):
    """
    This function will create and save a calibration record object.
    Input:
        Dictionary containing
    Output:
        Boolean indicating success or error message
    """

    for tag in ['submission_id','score','feedback','student_id','location']:
        if not tag in calibration_data:
            return util._error_response("Cannot find needed key {0} in request.".format(tag),_INTERFACE_VERSION)

    try:
        calibration_history=CalibrationHistory.objects.get_or_create(
            student_id=calibration_data['student_id'],
            location=calibration_data['location'],
        )
    except:
        return util._error_response("Cannot get or create CalibrationRecord with "
                                    "student id {0} and location {1}.".format(calibration_data['student_id'],
                                    calibration_data['location']),_INTERFACE_VERSION)
    try:
        submission=Submission.objects.get(
            id=calibration_data['submission_id']
        )
    except:
        return util._error_response("Invalid submission id {0}.".format(calibration_data['submission_id']),
                                    _INTERFACE_VERSION)

    try:
        actual_score=submission.get_last_successful_instructor_grader()['score']
    except:
        return util._error_response("Error getting actual.".format(calibration_data['submission_id']),
            _INTERFACE_VERSION)

    cal_record=CalibrationRecord(
        submission=submission,
        calibration_history=calibration_history,
        score=calibration_data['score'],
        actual_score=actual_score,
    )






