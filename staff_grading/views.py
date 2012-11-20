"""
Implements the staff grading views called by the LMS.

General idea: LMS asks for a submission to grade for a course.  Course staff member grades it, submits it back.

Authentication of users must be done by the LMS--this service requires a
login from the LMS to prevent arbitrary clients from connecting, but does not
validate that the passed-in grader_ids correspond to course staff.
"""

import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from controller.models import Submission
from controller import util

log = logging.getLogger(__name__)

_INTERFACE_VERSION = 1

def _error_response(msg):
    """
    Return a failing response with the specified message.
    """
    response = {'version': _INTERFACE_VERSION,
                'success': False,
                'error': msg}
    return HttpResponse(json.dumps(response), mimetype="application/json")

def _success_response(data):
    """
    Return a successful response with the specified data.
    """
    response = {'version': _INTERFACE_VERSION,
                'success': True}
    response.update(data)
    return HttpResponse(json.dumps(response), mimetype="application/json")


# TODO: implement login
#@login_required
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

    course_id = request.GET.get('course_id')
    grader_id = request.GET.get('grader_id')

    if not course_id or not grader_id:
        return _error_response("Missing required parameter")

    # TODO: save the grader id and match it in save_grade to make sure things
    # are consistent.
    (found, id) = util.get_instructor_grading(course_id)
    if not found:
        return _success_response({'message': 'No more submissions to grade.'})

    try:
        submission = Submission.objects.get(id=id)
    except Submission.DoesNotExist:
        log.error("Couldn't find submission %s for instructor grading", id)
        return _error_response('Failed to load submission %s.  Contact support.' % id)

    if submission.state != 'C':
        log.error("Instructor grading got a submission (%s) in an invalid state: ",
                  id, submission.state)
        return _error_response(
            'Wrong internal state for submission %s: %s. Contact support.' % (
                id, submission.state))

    response = {'submission_id': id,
                'submission': submission.student_response,
                # TODO: once client properly handles the 'prompt' field,
                # make this just submission.rubric
                'rubric': submission.prompt + "<br>" + submission.rubric,
                'prompt': submission.prompt,
                'max_score': submission.max_score,}

    return _success_response(response)


#@login_required
@csrf_exempt
def save_grade(request):
    """
    Supports POST requests with the following arguments:

    course_id: int
    grader_id: int
    submission_id: int
    score: int
    feedback: string

    returns json dict with keys

    version: int
    success: bool
    error: string, present if not success
    """
    response = {'version': _INTERFACE_VERSION,
                'success': False,
                'error': 'Not implemented'}

    return HttpResponse(json.dumps(response), mimetype="application/json")

