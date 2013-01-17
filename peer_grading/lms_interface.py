import logging

from django.conf import settings
from django.http import  Http404
from django.contrib.auth.decorators import login_required
import controller.grader_util as grader_util
from django.views.decorators.csrf import csrf_exempt

from controller.models import Submission, Grader
from controller.models import SubmissionState, GraderStatus
from controller import util

import calibration
import peer_grading_util

log = logging.getLogger(__name__)

_INTERFACE_VERSION = 1

@csrf_exempt
@util.error_if_not_logged_in
def get_next_submission(request):
    """
    Gets next submission from controller for peer grading.
    Input:
        Get request with the following keys:
           grader_id - Student id of the grader
           location - The problem id to get peer grading for.
    """

    if request.method != "GET":
        log.debug("Improper request method")
        raise Http404

    grader_id = request.GET.get("grader_id")
    location = request.GET.get("location")

    if not grader_id or not location:
        error_message="Failed to find needed keys 'grader_id' and 'location'"
        log.debug(error_message)
        return util._error_response(error_message, _INTERFACE_VERSION)

    (found, sub_id) = peer_grading_util.get_single_peer_grading_item(location, grader_id)

    if not found:
        error_message="No current grading."
        log.debug(error_message)
        return  util._error_response(error_message, _INTERFACE_VERSION)

    try:
        sub = Submission.objects.get(id=int(sub_id))
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

    #log.debug(response)
    return util._success_response(response, _INTERFACE_VERSION)

@csrf_exempt
@util.error_if_not_logged_in
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
    feedback_dict = post_data['feedback']

    rubric_scores_complete = request.POST.get('rubric_scores_complete', False)
    rubric_scores = request.POST.getlist('rubric_scores', [])

    try:
        score = int(score)
    except ValueError:
        return util._error_response("Expected integer score.  Got {0}".format(score), _INTERFACE_VERSION)

    try:
        sub=Submission.objects.get(id=submission_id)
    except:
        return util.error_response(
            "grade_save_error",
            _INTERFACE_VERSION,
            data={"msg": "Submission id {0} is not valid.".format(submission_id)}
        )

    success, error_message = grader_util.validate_rubric_scores(rubric_scores, rubric_scores_complete, sub)
    if not success:
        return util.error_response(
            "grade_save_error",
            _INTERFACE_VERSION,
            data={"msg": error_message}
        )

    d = {'submission_id': submission_id,
         'score': score,
         'feedback': feedback_dict,
         'grader_id': grader_id,
         'grader_type': 'PE',
         # Humans always succeed (if they grade at all)...
         'status': 'S',
         # ...and they're always confident too.
         'confidence': 1.0,
         #And they don't make any errors
         'errors' : "",
         'rubric_scores_complete' : rubric_scores_complete,
         'rubric_scores' : rubric_scores
    }

    #Currently not posting back to LMS.  Only saving grader object, and letting controller decide when to post back.
    (success, header) = grader_util.create_and_handle_grader_object(d)
    if not success:
        return util._error_response("There was a problem saving the grade.  Contact support.", _INTERFACE_VERSION)

    #xqueue_session=util.xqueue_login()
    #error,msg = util.post_results_to_xqueue(xqueue_session,json.dumps(header),json.dumps(post_data))

    return util._success_response({'msg': "Posted to queue."}, _INTERFACE_VERSION)

@csrf_exempt
@util.error_if_not_logged_in
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

@csrf_exempt
@util.error_if_not_logged_in
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

@csrf_exempt
@util.error_if_not_logged_in
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

    rubric_scores_complete = request.POST.get('rubric_scores_complete', False)
    rubric_scores = request.POST.getlist('rubric_scores', [])

    try:
        score = int(score)
    except ValueError:
        return util._error_response("Expected integer score.  Got {0}".format(score), _INTERFACE_VERSION)

    try:
        sub=Submission.objects.get(id=submission_id)
    except:
        return util.error_response(
            "grade_save_error",
            _INTERFACE_VERSION,
            data={"msg": "Submission id {0} is not valid.".format(submission_id)}
        )

    d = {'submission_id': submission_id,
         'score': score,
         'feedback': feedback,
         'student_id': student_id,
         'location': location,
         'rubric_scores_complete' : rubric_scores_complete,
         'rubric_scores' : rubric_scores,
    }

    (success, data) = calibration.create_and_save_calibration_record(d)

    if not success:
        return util._error_response("Failed to create and save calibration record.", _INTERFACE_VERSION)

    return util._success_response({'message' : "Successfully saved calibration record.", 'actual_score' : data['actual_score']}, _INTERFACE_VERSION)

@csrf_exempt
@util.error_if_not_logged_in
def get_problem_list(request):
    """
    Get the list of problems that need grading in course_id request.GET['course_id'].

    Returns:
        list of dicts with keys
           'location'
           'problem_name'
           'num_graded' -- number graded
           'num_pending' -- number pending in the queue
    """

    if request.method!="GET":
        error_message="Request needs to be GET."
        log.error(error_message)
        return util._error_response(error_message, _INTERFACE_VERSION)

    course_id=request.GET.get("course_id")
    student_id = request.GET.get("student_id")

    if not course_id or not student_id:
        error_message="Missing needed tag course_id or student_id"
        log.error(error_message)
        return util._error_response(error_message, _INTERFACE_VERSION)

    locations_for_course = [x['location'] for x in
                            list(Submission.objects.filter(course_id=course_id).values('location').distinct())]

    location_info=[]
    for location in locations_for_course:
        student_sub_count=Submission.objects.filter(student_id=student_id, location=location, preferred_grader_type="PE").count()
        if student_sub_count>0:
            problem_name = Submission.objects.filter(location=location)[0].problem_id
            submissions_pending = peer_grading_util.peer_grading_submissions_pending_for_location(location).count()
            submissions_graded = peer_grading_util.peer_grading_submissions_graded_for_location(location,student_id).count()
            submissions_required = max([0,(settings.REQUIRED_PEER_GRADING_PER_STUDENT*student_sub_count)-submissions_graded])

            problem_name_from_location=location.split("://")[1]
            if submissions_graded>0 or submissions_pending>0:
                location_dict={
                    'location' : location,
                    'problem_name' : problem_name,
                    'num_graded' : submissions_graded,
                    'num_required' : submissions_required,
                    'num_pending' : submissions_pending,
                    }
                location_info.append(location_dict)

    return util._success_response({'problem_list' : location_info},
        _INTERFACE_VERSION)

@csrf_exempt
@util.error_if_not_logged_in
def get_notifications(request):
    if request.method!="GET":
        error_message="Request needs to be GET."
        log.error(error_message)
        return util._error_response(error_message, _INTERFACE_VERSION)

    course_id=request.GET.get("course_id")
    student_id = request.GET.get("student_id")

    if not course_id or not student_id:
        error_message="Missing needed tag course_id or student_id"
        log.error(error_message)
        return util._error_response(error_message, _INTERFACE_VERSION)

    student_needs_to_peer_grade = False

    student_responses_for_course = Submission.objects.filter(student_id = student_id, course_id=course_id, preferred_grader_type="PE")
    unique_student_locations = [x['location'] for x in
                                student_responses_for_course.values('location').distinct()]
    for location in unique_student_locations:
        location_response_count = student_responses_for_course.filter(location=location).count()
        required_peer_grading_for_location = location_response_count * settings.REQUIRED_PEER_GRADING_PER_STUDENT
        completed_peer_grading_for_location = Grader.objects.filter(grader_id = student_id, submission__location = location).count()
        submissions_pending = peer_grading_util.peer_grading_submissions_pending_for_location(location).count()

        if completed_peer_grading_for_location<required_peer_grading_for_location and submissions_pending>0:
            student_needs_to_peer_grade = True
            return util._success_response({'student_needs_to_peer_grade' : student_needs_to_peer_grade}, _INTERFACE_VERSION)

    return util._success_response({'student_needs_to_peer_grade' : student_needs_to_peer_grade}, _INTERFACE_VERSION)

