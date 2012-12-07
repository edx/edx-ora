"""
Implements the staff grading views called by the LMS.

General idea: LMS asks for a submission to grade for a course.  Course staff member grades it, submits it back.

Authentication of users must be done by the LMS--this service requires a
login from the LMS to prevent arbitrary clients from connecting, but does not
validate that the passed-in grader_ids correspond to course staff.
"""

import json
import logging
from statsd import statsd

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from controller.models import Submission, GraderStatus
from controller import util
from controller import grader_util
import staff_grading_util
from ml_grading import ml_grading_util

log = logging.getLogger(__name__)

_INTERFACE_VERSION = 1


@statsd.timed('open_ended_assessment.grading_controller.staff_grading.views.time', tags=['function:get_next_submission'])
def get_next_submission(request):
    """
    Supports GET request with the following arguments:
    course_id -- the course for which to return a submission.
    grader_id -- LMS user_id of the requesting user

    Returns json dict with the following keys:

    version: '1'  (number)

    success: bool

    if success:
      'submission_id': a unique identifier for the submission, to be passed
                       back with the grade.

      'submission': the submission, rendered as read-only html for grading

      'rubric': the rubric, also rendered as html.

      'message': if there was no submission available, but nothing went wrong,
                there will be a message field.
    else:
      'error': if success is False, will have an error message with more info.
    }
    """

    if request.method != "GET":
        raise Http404

    course_id = request.GET.get('course_id')
    grader_id = request.GET.get('grader_id')
    location = request.GET.get('location')

    log.debug("Getting next submission for instructor grading for course: {0}.".format(course_id))


    if not (course_id or location) or not grader_id:
        return util._error_response("Missing required parameter", _INTERFACE_VERSION)

    if location:
        (found, id) = staff_grading_util.get_single_instructor_grading_item_for_location(location)

    # TODO: save the grader id and match it in save_grade to make sure things
    # are consistent.
    if not location:
        (found, id) = staff_grading_util.get_single_instructor_grading_item(course_id)

    if not found:
        return util._success_response({'message': 'No more submissions to grade.'}, _INTERFACE_VERSION)

    try:
        submission = Submission.objects.get(id=int(id))
    except Submission.DoesNotExist:
        log.error("Couldn't find submission %s for instructor grading", id)
        return util._error_response('Failed to load submission %s.  Contact support.' % id, _INTERFACE_VERSION)

    #Get error metrics from ml grading, and get into dictionary form to pass down to staff grading view
    success, ml_error_info=ml_grading_util.get_ml_errors(submission.location)
    if success:
        ml_error_message=staff_grading_util.generate_ml_error_message(ml_error_info)
    else:
        ml_error_message=ml_error_info

    ml_error_message="Machine learning error information: " + ml_error_message

    if submission.state != 'C':
        log.error("Instructor grading got a submission (%s) in an invalid state: ",
            id, submission.state)
        return util._error_response(
            'Wrong internal state for submission %s: %s. Contact support.' % (
                id, submission.state), _INTERFACE_VERSION)

    response = {'submission_id': id,
                'submission': submission.student_response,
                # TODO: once client properly handles the 'prompt' field,
                # make this just submission.rubric
                'rubric': submission.prompt + "<br>" + submission.rubric,
                'prompt': submission.prompt,
                'max_score': submission.max_score,
                'ml_error_info' : ml_error_message,
                'problem_name' : submission.problem_id,
                'num_graded' : staff_grading_util.finished_submissions_graded_by_instructor(submission.location).count(),
                'num_pending' : staff_grading_util.submissions_pending_for_location(submission.location).count(),
                'min_for_ml' : settings.MIN_TO_USE_ML,
                }

    log.debug("Sending success response back to instructor grading!")
    return util._success_response(response, _INTERFACE_VERSION)


@csrf_exempt
@statsd.timed(
    'open_ended_assessment.grading_controller.staff_grading.views.time',
    tags=['function:save_grade'])
def save_grade(request):
    """
    Supports POST requests with the following arguments:

    course_id: int
    grader_id: int
    submission_id: int
    score: int
    feedback: string

    Returns json dict with keys

    version: int
    success: bool
    error: string, present if not success
    """
    if request.method != "POST":
        raise Http404

    course_id = request.POST.get('course_id')
    grader_id = request.POST.get('grader_id')
    submission_id = request.POST.get('submission_id')
    score = request.POST.get('score')
    feedback = request.POST.get('feedback')

    if (# These have to be truthy
        not (course_id and grader_id and submission_id) or
        # These have to be non-None
        score is None or feedback is None):
        return util._error_response("Missing required parameters", _INTERFACE_VERSION)

    try:
        score = int(score)
    except ValueError:
        return util._error_response("Expected integer score.  Got {0}"
        .format(score), _INTERFACE_VERSION)

    d = {'submission_id': submission_id,
         'score': score,
         'feedback': feedback,
         'grader_id': grader_id,
         'grader_type': 'IN',
         # Humans always succeed (if they grade at all)...
         'status': GraderStatus.success,
         # ...and they're always confident too.
         'confidence': 1.0,
         #And they don't make errors
         'errors' : ""}

    success, header = grader_util.create_and_handle_grader_object(d)

    if not success:
        return util._error_response("There was a problem saving the grade.  Contact support.", _INTERFACE_VERSION)

    return util._success_response({}, _INTERFACE_VERSION)