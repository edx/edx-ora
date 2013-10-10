from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import json
import logging
import requests
import urlparse

import util
import grader_util

from staff_grading import staff_grading_util
from peer_grading import peer_grading_util

from models import Submission

from statsd import statsd
from boto.s3.connection import S3Connection
from metrics.tasks import get_course_data_filename

from django.db import connection

log = logging.getLogger(__name__)

_INTERFACE_VERSION=1


@csrf_exempt
def log_in(request):
    """
    Handles external login request.
    """
    if request.method == 'POST':
        p = request.POST.copy()
        if p.has_key('username') and p.has_key('password'):
            log.debug("Username: {0} Password: {1}".format(p['username'], p['password']))
            user = authenticate(username=p['username'], password=p['password'])
            if user is not None:
                login(request, user)
                log.debug("Successful login!")
                return util._success_response({'message' : 'logged in'} , _INTERFACE_VERSION)
            else:
                return util._error_response('Incorrect login credentials', _INTERFACE_VERSION)
        else:
            return util._error_response('Insufficient login info', _INTERFACE_VERSION)
    else:
        return util._error_response('login_required', _INTERFACE_VERSION)

@csrf_exempt
def log_out(request):
    """
    Uses django auth to handle a logout request
    """
    logout(request)
    return util._success_response({'message' : 'Goodbye'} , _INTERFACE_VERSION)


def status(request):
    """
    Returns a simple status update
    """
    return util._success_response({'content' : 'OK'}, _INTERFACE_VERSION)

@csrf_exempt
@util.error_if_not_logged_in
@util.is_submitter
def request_eta_for_submission(request):
    """
    Gets the ETA (in seconds) for a student submission to be graded for a given location
    Input:
        A problem location
    Output:
        Dictionary containing success, and eta indicating time a new submission for given location will take to be graded
    """
    if request.method != 'GET':
        return util._error_response("Request type must be GET", _INTERFACE_VERSION)

    location=request.GET.get("location")
    if not location:
        return util._error_response("Missing required key location", _INTERFACE_VERSION)

    success, eta = grader_util.get_eta_for_submission(location)

    if not success:
        return util._error_response(eta,_INTERFACE_VERSION)

    return util._success_response({
        'eta' : eta,
    }, _INTERFACE_VERSION)

@csrf_exempt
@login_required
@util.is_submitter
def verify_name_uniqueness(request):
    """
    Check if a given problem name, location tuple is unique
    Input:
        A problem location and the problem name
    Output:
        Dictionary containing success, and and indicator of whether or not the name is unique
    """
    if request.method != 'GET':
        return util._error_response("Request type must be GET", _INTERFACE_VERSION)

    for tag in ['location', 'problem_name', 'course_id']:
        if tag not in request.GET:
            return util._error_response("Missing required key {0}".format(tag), _INTERFACE_VERSION)

    location=request.GET.get("location")
    problem_name = request.GET.get("problem_name")
    course_id = request.GET.get('course_id')

    success, unique = grader_util.check_name_uniqueness(problem_name,location, course_id)

    if not success:
        return util._error_response(unique,_INTERFACE_VERSION)

    return util._success_response({
        'name_is_unique' : unique,
        }, _INTERFACE_VERSION)

@csrf_exempt
@statsd.timed('open_ended_assessment.grading_controller.controller.views.time',
    tags=['function:check_for_notifications'])
@util.error_if_not_logged_in
@util.is_submitter
def check_for_notifications(request):
    """
    Check if a given problem name, location tuple is unique
    Input:
        A problem location and the problem name
    Output:
        Dictionary containing success, and and indicator of whether or not the name is unique
    """
    if request.method != 'GET':
        return util._error_response("Request type must be GET", _INTERFACE_VERSION)

    for tag in ['course_id', 'user_is_staff', 'last_time_viewed', 'student_id']:
        if tag not in request.GET:
            return util._error_response("Missing required key {0}".format(tag), _INTERFACE_VERSION)

    request_dict = request.GET.copy()
    success, combined_notifications = grader_util.check_for_combined_notifications(request_dict)

    if not success:
        return util._error_response(combined_notifications,_INTERFACE_VERSION)

    util.log_connection_data()
    return util._success_response(combined_notifications, _INTERFACE_VERSION)

@csrf_exempt
@statsd.timed('open_ended_assessment.grading_controller.controller.views.time',
    tags=['function:get_grading_status_list'])
@util.error_if_not_logged_in
@util.is_submitter
def get_grading_status_list(request):
    """
    Get a list of locations where student has submitted open ended questions and the status of each.
    Input:
        Course id, student id
    Output:
        Dictionary containing success, and a list of problems in the course with student submission status.
        See grader_util for format details.
    """
    if request.method != 'GET':
        return util._error_response("Request type must be GET", _INTERFACE_VERSION)

    for tag in ['course_id', 'student_id']:
        if tag not in request.GET:
            return util._error_response("Missing required key {0}".format(tag), _INTERFACE_VERSION)

    course_id = request.GET.get('course_id')
    student_id = request.GET.get('student_id')

    success, sub_list = grader_util.get_problems_student_has_tried(student_id, course_id)

    if not success:
        return util._error_response("Could not generate a submission list. {0}".format(sub_list),_INTERFACE_VERSION)

    problem_list_dict={
        'success' : success,
        'problem_list' : sub_list,
        }

    util.log_connection_data()
    return util._success_response(problem_list_dict, _INTERFACE_VERSION)

@csrf_exempt
@statsd.timed('open_ended_assessment.grading_controller.controller.views.time',
    tags=['function:get_flagged_problem_list'])
@util.error_if_not_logged_in
@util.is_submitter
def get_flagged_problem_list(request):
    if request.method != 'GET':
        return util._error_response("Request type must be GET", _INTERFACE_VERSION)

    for tag in ['course_id']:
        if tag not in request.GET:
            return util._error_response("Missing required key {0}".format(tag), _INTERFACE_VERSION)

    success, flagged_submissions = peer_grading_util.get_flagged_submissions(request.GET.get('course_id'))

    if not success:
        return util._error_response(flagged_submissions,_INTERFACE_VERSION)

    flagged_submission_dict={
        'success' : success,
        'flagged_submissions' : flagged_submissions,
        }

    util.log_connection_data()
    return util._success_response(flagged_submission_dict, _INTERFACE_VERSION)

@csrf_exempt
@statsd.timed('open_ended_assessment.grading_controller.controller.views.time',
    tags=['function:take_action_on_flags'])
@util.error_if_not_logged_in
@util.is_submitter
def take_action_on_flags(request):
    if request.method != 'POST':
        return util._error_response("Request type must be POST", _INTERFACE_VERSION)

    for tag in ['course_id', 'student_id', 'submission_id', 'action_type']:
        if tag not in request.POST:
            return util._error_response("Missing required key {0}".format(tag), _INTERFACE_VERSION)

    course_id = request.POST.get('course_id')
    student_id = request.POST.get('student_id')
    submission_id = request.POST.get('submission_id')
    action_type = request.POST.get('action_type')

    success, data = peer_grading_util.take_action_on_flags(course_id, student_id, submission_id, action_type)

    if not success:
        return util._error_response(data,_INTERFACE_VERSION)

    submission_dict={
        'success' : success,
        'data' : data,
        }

    util.log_connection_data()
    return util._success_response(submission_dict, _INTERFACE_VERSION)


@csrf_exempt
@util.error_if_not_logged_in
@util.is_submitter
def get_course_data(request):
    """
    Get the course data for a given course.
    """

    if request.method != "GET":
        return util._error_response("Request type must be GET", _INTERFACE_VERSION)

    course = request.GET.get('course')

    # Throw an error if user does not specify a course.
    if course is None:
        return util._error_response("You must specify a course.", _INTERFACE_VERSION)

    # Generate a data filename for the course.
    filename = get_course_data_filename(course)

    # Get the data file from S3.  There is a periodic task that puts the files here.
    s3 = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, is_secure=False)
    file_url = s3.generate_url(settings.S3_FILE_TIMEOUT, 'GET', bucket=settings.S3_BUCKETNAME.lower(), key=filename)

    # Return a temporary url.
    return util._success_response({'file_url': file_url}, _INTERFACE_VERSION)





