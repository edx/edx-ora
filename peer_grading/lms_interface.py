import logging

from django.http import  Http404
from django.contrib.auth.decorators import login_required
import controller.grader_util as grader_util

from controller.models import Submission
from controller.models import SUBMISSION_STATE,GRADER_STATUS
from controller import util

import calibration
import peer_grading_util

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

_INTERFACE_VERSION = 1

@login_required
def get_next_submission(request):
    """
    Gets next submission from controller for peer grading.
    Input:
        Get request with the following keys:
           grader_id - Student id of the grader
           location - The problem id to get peer grading for.
    """

    if request.method != "GET":
        raise Http404

    grader_id = request.GET.get("grader_id")
    location = request.GET.get("location")

    if not grader_id or not location:
        return util._error_response("Failed to find needed keys 'grader_id' and 'location'", _INTERFACE_VERSION)

    (found, sub_id) = peer_grading_util.get_single_peer_grading_item(location, grader_id)

    if not found:
        return  util._error_response("No current grading.", _INTERFACE_VERSION)

    try:
        sub = Submission.objects.get(id=sub_id)
    except:
        log.debug("Could not find submission with id {0}".format(sub_id))
        return util._error_response("Error getting grading.", _INTERFACE_VERSION)

    if sub.state != SubmissionState.being_graded:
        log.debug("Submission with id {0} has incorrect internal state {1}.".format(sub_id, sub.state))
        return util._error_response("Error getting grading.", _INTERFACE_VERSION)

    response = {
        'submission_id': sub_id,
        'submission_key': sub.xqueue_submission_key,
        'student_response': sub.student_response,
        'prompt': sub.prompt,
        'rubric': sub.rubric,
        'max_score': sub.max_score,
    }

    return util._success_response(response, _INTERFACE_VERSION)


@login_required
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

    post_data = request.POST.dict().copy()

    for tag in ['location', 'grader_id', 'submission_id', 'submission_key', 'score', 'feedback']:
        if not tag in post_data:
            return util._error_response("Cannot find needed key {0} in request.".format(tag), _INTERFACE_VERSION)

    location = post_data['location']
    grader_id = post_data['grader_id']
    submission_id = post_data['submission_id']

    #Submission key currently unused, but plan to use it for validation in the future.
    submission_key = post_data['submission_key']
    score = post_data['score']

    #This is done to ensure that response is properly formatted on the lms side.
    feedback_string = post_data['feedback']
    feedback = feedback_template.format(feedback=feedback_string, score=score)

    try:
        score = int(score)
    except ValueError:
        return util._error_response("Expected integer score.  Got {0}".format(score), _INTERFACE_VERSION)

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
    (success, header) = grader_util.create_and_save_grader_object(d)
    if not success:
        return util._error_response("There was a problem saving the grade.  Contact support.", _INTERFACE_VERSION)

    #xqueue_session=util.xqueue_login()
    #error,msg = util.post_results_to_xqueue(xqueue_session,json.dumps(header),json.dumps(post_data))

    return util._success_response({'msg': "Posted to queue."}, _INTERFACE_VERSION)


@login_required
def is_student_calibrated(request):
    """
    Decides if student has fulfilled criteria for peer grading calibration for a given location (problem id).
    Input:
        student id, problem_id
    Output:
        Dictionary with boolean calibrated indicating whether or not student has finished calibration.

    Note: Location in the database is currently being used as the problem id.
    """

    if request.method != "GET":
        raise Http404

    problem_id = request.GET.get("problem_id")
    student_id = request.GET.get("student_id")

    success, data = calibration.check_calibration_status(problem_id, student_id)

    if not success:
        return util._error_response(data, _INTERFACE_VERSION)

    return util._success_response(data, _INTERFACE_VERSION)


@login_required
def show_calibration_essay(request):
    """
    Shows a calibration essay when it receives a GET request.
    Input:
        Http request containing problem_id and student_id
    Output:
        Http response containing essay data (submission id, submission key, student response, prompt, rubric, max_score)
        Or error
    """
    if request.method != "GET":
        raise Http404

    problem_id = request.GET.get("problem_id")
    student_id = request.GET.get("student_id")

    success, data = calibration.get_calibration_essay(problem_id, student_id)

    if not success:
        return util._error_response(data, _INTERFACE_VERSION)

    return util._success_response(data, _INTERFACE_VERSION)


@login_required
def save_calibration_essay(request):
    """
    Saves a calibration essay sent back from LMS.
    Input:
        request dict containing keys student_id, location, calibration_essay_id, score, submission_key, feedback
    Output:
        Boolean indicating success in saving calibration essay or not.
    """

    if request.method != "POST":
        raise Http404

    post_data = request.POST.dict().copy()

    for tag in ['location', 'student_id', 'calibration_essay_id', 'submission_key', 'score', 'feedback']:
        if not tag in post_data:
            return util._error_response("Cannot find needed key {0} in request.".format(tag), _INTERFACE_VERSION)

    location = post_data['location']
    student_id = post_data['student_id']
    submission_id = post_data['calibration_essay_id']
    score = post_data['score']
    feedback = post_data['feedback']

    #Submission key currently unused, but plan to use it for validation in the future.
    submission_key = post_data['submission_key']

    try:
        score = int(score)
    except ValueError:
        return util._error_response("Expected integer score.  Got {0}".format(score), _INTERFACE_VERSION)

    d = {'submission_id': submission_id,
         'score': score,
         'feedback': feedback,
         'student_id': student_id,
         'location': location,
    }

    (success, data) = calibration.create_and_save_calibration_record(d)

    return success