from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from statsd import statsd
from control_util import SubmissionControl

import json
import logging
import requests
import urlparse

from models import Submission, GRADER_TYPE, Grader, STATUS_CODES, SubmissionState, GraderStatus
import util
import grader_util
from staff_grading import staff_grading_util
from peer_grading import peer_grading_util
from django.core.cache import cache

from metrics import metrics_util
from ml_grading import ml_grading_util

from django.db import connection

log = logging.getLogger(__name__)

_INTERFACE_VERSION=1
NOTHING_TO_ML_GRADE_LOCATION_CACHE_KEY = 'nothing_to_ml_grade:{location}'
NOTHING_TO_ML_GRADE_CACHE_KEY = "nothing_to_ml_grade"

@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:get_submission_ml'])
@util.is_submitter
def get_submission_ml(request):
    """
    Gets a submission for the ML grader
    Input:
        Get request with no parameters
    """
    unique_locations = [x['location'] for x in list(Submission.objects.values('location').distinct())]
    for location in unique_locations:
        nothing_to_ml_grade_for_location_key = NOTHING_TO_ML_GRADE_LOCATION_CACHE_KEY.format(location=location)
        # Go to the next location if we have recently determined that a location
        # has no ML grading ready.
        if cache.get(nothing_to_ml_grade_for_location_key):
            continue

        sl = staff_grading_util.StaffLocation(location)
        control = SubmissionControl(sl.latest_submission())

        subs_graded_by_instructor = sl.graded_count()
        success = ml_grading_util.check_for_all_model_and_rubric_success(location)
        if subs_graded_by_instructor >= control.minimum_to_use_ai and success:
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

                    return util._success_response({'submission_id' : to_be_graded.id}, _INTERFACE_VERSION)
        # If we don't get a submission to return, then there is no ML grading for this location.
        # Cache this boolean to avoid an expensive loop iteration.
        cache.set(nothing_to_ml_grade_for_location_key, True, settings.RECHECK_EMPTY_ML_GRADE_QUEUE_DELAY)

    util.log_connection_data()

    # Set this cache key to ensure that this expensive function isn't repeatedly called when not needed.
    cache.set(NOTHING_TO_ML_GRADE_CACHE_KEY, True, settings.RECHECK_EMPTY_ML_GRADE_QUEUE_DELAY)
    return util._error_response("Nothing to grade.", _INTERFACE_VERSION)

@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:get_pending_count'])
@util.is_submitter
def get_pending_count(request):
    """
    Returns the number of submissions pending grading
    """
    if cache.get(NOTHING_TO_ML_GRADE_CACHE_KEY):
        # If get_submission_ml resulted in no ml grading being found, then return pending count as 0.
        # When cache timeout expires, it will check again.  This saves us from excessive calls to
        # get_submission_ml.
        to_be_graded_count = 0
    else:
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

    util.log_connection_data()
    return util._success_response({'to_be_graded_count' : to_be_graded_count}, _INTERFACE_VERSION)

@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:get_submission_instructor'])
@util.is_submitter
def get_submission_instructor(request):
    """
    Gets a submission for the Instructor grading view
    """
    try:
        course_id = util._value_or_default(request.GET['course_id'], None)
    except Exception:
        return util._error_response("'get_submission' requires parameter 'course_id'", _INTERFACE_VERSION)

    sc = staff_grading_util.StaffCourse(course_id)
    found, sub_id = sc.next_item()

    if not found:
        return util._error_response("Nothing to grade.", _INTERFACE_VERSION)

    util.log_connection_data()
    return util._success_response({'submission_id' : sub_id}, _INTERFACE_VERSION)


@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:get_submission_peer'])
@util.is_submitter
def get_submission_peer(request):
    """
    Gets a submission for the Peer grading view
    """
    try:
        location = util._value_or_default(request.GET['location'], None)
        grader_id = util._value_or_default(request.GET['grader_id'], None)
    except KeyError:
        return util._error_response("'get_submission' requires parameters 'location', 'grader_id'", _INTERFACE_VERSION)

    pl = peer_grading_util.PeerLocation(location, grader_id)
    found, sub_id = pl.next_item()

    if not found:
        return util._error_response("Nothing to grade.", _INTERFACE_VERSION)

    util.log_connection_data()
    return util._success_response({'submission_id' : sub_id}, _INTERFACE_VERSION)


@csrf_exempt
@login_required
@statsd.timed('open_ended_assessment.grading_controller.controller.grader_interface.time', tags=['function:put_result'])
@util.is_submitter
def put_result(request):
    """
    Used by external interfaces to post results back to controller
    """
    if request.method != 'POST':
        return util._error_response("'put_result' must use HTTP POST", _INTERFACE_VERSION)
    else:
        post_data = request.POST.dict().copy()

        for tag in ['feedback', 'submission_id', 'grader_type', 'status', 'confidence', 'grader_id', 'score', 'errors', 'rubric_scores_complete', 'rubric_scores']:
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
        except Exception:
            return util._error_response("Can't parse score {0} into an int.".format(post_data['score']), _INTERFACE_VERSION)

        try:
            sub=Submission.objects.get(id=int(post_data['submission_id']))
        except Exception:
            return util._error_response(
                "Submission id {0} is not valid.".format(post_data.get('submission_id', "NA")),
                _INTERFACE_VERSION,
            )

        rubric_scores_complete = request.POST.get('rubric_scores_complete', False)
        rubric_scores = request.POST.get('rubric_scores', [])

        try:
            rubric_scores=json.loads(rubric_scores)
        except Exception:
            pass

        success, error_message = grader_util.validate_rubric_scores(rubric_scores, rubric_scores_complete, sub)
        if not success:
            return util._error_response(
                error_message,
                _INTERFACE_VERSION,
            )

        post_data['rubric_scores']=rubric_scores
        post_data['rubric_scores_complete'] = rubric_scores_complete
        success, header = grader_util.create_and_handle_grader_object(post_data)
        if not success:
            return util._error_response("Could not save grader.", _INTERFACE_VERSION)

        util.log_connection_data()
        return util._success_response({'message' : "Saved successfully."}, _INTERFACE_VERSION)


