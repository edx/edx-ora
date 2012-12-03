from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from statsd import statsd

import json
import logging
import requests
import urlparse
from metrics.timing_functions import initialize_timing

from models import Submission, GRADER_TYPE, Grader, STATUS_CODES, SubmissionState, GraderStatus
import util
import grader_util
from staff_grading import staff_grading_util
from peer_grading import peer_grading_util

from metrics import metrics_util

log = logging.getLogger(__name__)

_INTERFACE_VERSION=1

@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:get_submission_ml'])
def get_submission_ml(request):
    """
    Gets a submission for the ML grader
    Input:
        Get request with no parameters
    """
    unique_locations = [x['location'] for x in list(Submission.objects.values('location').distinct())]
    for location in unique_locations:
        subs_graded_by_instructor = staff_grading_util.finished_submissions_graded_by_instructor(location).count()
        if subs_graded_by_instructor >= settings.MIN_TO_USE_ML:
            to_be_graded = Submission.objects.filter(
                location=location,
                state=SubmissionState.waiting_to_be_graded,
                next_grader_type="ML",
            )
            if(to_be_graded.count() > 0):
                to_be_graded = to_be_graded[0]
                if to_be_graded is not None:
                    to_be_graded.state = SubmissionState.being_graded
                    to_be_graded.save()

                    #Insert timing initialization code
                    initialize_timing(to_be_graded)

                    return util._success_response({'submission_id' : to_be_graded.id}, _INTERFACE_VERSION)

    return util._error_response("Nothing to grade.", _INTERFACE_VERSION)

@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:get_pending_count'])
def get_pending_count(request):
    """
    Returns the number of submissions pending grading
    """
    if request.method != 'GET':
        return util._error_response("'get_pending_count' must use HTTP GET", _INTERFACE_VERSION)

    grader_type = request.GET.get("grader_type")

    if not grader_type:
        return util._error_response("grader type is a needed key", _INTERFACE_VERSION)

    if grader_type not in [i[0] for i in GRADER_TYPE]:
        return util._error_response("invalid grader type", _INTERFACE_VERSION)

    to_be_graded_count = Submission.objects.filter(
        state=SubmissionState.waiting_to_be_graded,
        next_grader_type=grader_type,
    ).count()

    return util._success_response({'to_be_graded_count' : to_be_graded_count}, _INTERFACE_VERSION)

@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:get_submission_instructor'])
def get_submission_instructor(request):
    """
    Gets a submission for the Instructor grading view
    """
    try:
        course_id = util._value_or_default(request.GET['course_id'], None)
    except:
        return util._error_response("'get_submission' requires parameter 'course_id'", _INTERFACE_VERSION)

    found, sub_id = staff_grading_util.get_single_instructor_grading_item(course_id)

    if not found:
        return util._error_response("Nothing to grade.", _INTERFACE_VERSION)

    #Insert timing initialization code
    initialize_timing(sub_id)

    return util._success_response({'submission_id' : sub_id}, _INTERFACE_VERSION)


@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:get_submission_peer'])
def get_submission_peer(request):
    """
    Gets a submission for the Peer grading view
    """
    try:
        location = util._value_or_default(request.GET['location'], None)
        grader_id = util._value_or_default(request.GET['grader_id'], None)
    except KeyError:
        return util._error_response("'get_submission' requires parameters 'location', 'grader_id'", _INTERFACE_VERSION)

    found, sub_id = peer_grading_util.get_single_peer_grading_item(location, grader_id)

    if not found:
        return util._error_response("Nothing to grade.", _INTERFACE_VERSION)

    #Insert timing initialization code
    initialize_timing(sub_id)

    return util._success_response({'submission_id' : sub_id}, _INTERFACE_VERSION)


@csrf_exempt
@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:put_result'])
def put_result(request):
    """
    Used by external interfaces to post results back to controller
    """
    if request.method != 'POST':
        return util._error_response("'put_result' must use HTTP POST", _INTERFACE_VERSION)
    else:
        post_data = request.POST.dict().copy()
        log.debug(post_data)

        for tag in ['feedback', 'submission_id', 'grader_type', 'status', 'confidence', 'grader_id', 'score', 'errors']:
            if not post_data.has_key(tag):
                return util._error_response("Failed to find needed key {0}.".format(tag), _INTERFACE_VERSION)

        #list comprehension below just gets all available grader types ['ML','IN', etc
        if post_data['grader_type'] not in [i[0] for i in GRADER_TYPE]:
            return util._error_response("Invalid grader type {0}.".format(post_data['grader_type']),_INTERFACE_VERSION)

        #list comprehension below gets all available status codes ['F',"S']
        if post_data['status'] not in [i[0] for i in STATUS_CODES]:
            return util._error_response("Invalid grader status.".format(post_data['status']), _INTERFACE_VERSION)

        try:
            post_data['score'] = int(post_data['score'])
        except:
            return util._errors_response("Can't parse score {0} into an int.".format(post_data['score']), _INTERFACE_VERSION)

        success, header = grader_util.create_and_handle_grader_object(post_data)
        if not success:
            return util._errors_response("Could not save grader.", _INTERFACE_VERSION)

        return util._success_response({'message' : "Saved successfully."}, _INTERFACE_VERSION)


