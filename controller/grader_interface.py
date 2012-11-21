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

from models import Submission, GRADER_TYPE, Grader, STATUS_CODES
import util

log=logging.getLogger(__name__)

@login_required
def get_submission_ml(request):
    """
    Gets a submission for the ML grader
    Input:
        Get request with no parameters
    """
    unique_locations=[x['location'] for x in list(Submission.objects.values('location').distinct())]
    for location in unique_locations:
        subs_graded_by_instructor=util.subs_graded_by_instructor(location).count()
        if subs_graded_by_instructor>=settings.MIN_TO_USE_ML:
            to_be_graded=Submission.objects.filter(
                location=location,
                state="W",
                next_grader_type="ML",
            )
            if(to_be_graded.count()>0):
                to_be_graded=to_be_graded[0]
                if to_be_graded is not None:
                    to_be_graded.state="C"
                    to_be_graded.save()
                    return HttpResponse(util.compose_reply(True,to_be_graded.id))

    return HttpResponse(util.compose_reply(False,"Nothing to grade."))

@login_required
def get_submission_instructor(request):
    """
    Gets a submission for the Instructor grading view
    """
    try:
        course_id = util._value_or_default(request.GET['course_id'],None)
    except KeyError:
        return HttpResponse(util.compose_reply(False,
        "'get_submission' requires parameter 'course_id'"))

    #TODO: Bring this back into this module once instructor grading stub view is gone.
    found,sub_id=util.get_instructor_grading(course_id)

    if not found:
        return HttpResponse(util.compose_reply(False,"Nothing to grade."))

    return HttpResponse(util.compose_reply(True,sub_id))

@login_required
def get_submission_peer(request):
    """
    Gets a submission for the Peer grading view
    """
    try:
        location = util._value_or_default(request.GET['location'],None)
        grader_id = util._value_or_default(request.GET['grader_id'],None)
    except KeyError:
        return HttpResponse(util.compose_reply(False,
            "'get_submission' requires parameters 'location', 'grader_id'"))

    #TODO: Bring this back into this module once instructor grading stub view is gone.
    found,sub_id=util.get_peer_grading(location,grader_id)

    if not found:
        return HttpResponse(util.compose_reply(False,"Nothing to grade."))

    return HttpResponse(util.compose_reply(True,sub_id))


@csrf_exempt
@login_required
def put_result(request):
    """
    Used by external interfaces to post results back to controller
    """
    if request.method != 'POST':
        return HttpResponse(util.compose_reply(False, "'put_result' must use HTTP POST"))
    else:
        post_data=request.POST.dict().copy()
        log.debug(post_data)

        for tag in ['feedback', 'submission_id', 'grader_type', 'status', 'confidence', 'grader_id', 'score']:
            if not post_data.has_key(tag):
                return HttpResponse(util.compose_reply(False,"Failed to find needed keys."))

        if post_data['grader_type'] not in [i[0] for i in GRADER_TYPE]:
            return HttpResponse(util.compose_reply(False,"Invalid grader type."))

        if post_data['status'] not in [i[0] for i in STATUS_CODES]:
            return HttpResponse(util.compose_reply(False,"Invalid grader status."))

        try:
            post_data['score']=int(post_data['score'])
        except:
            return HttpResponse(util.compose_reply(False,"Can't parse score into an int."))

        success,header=util.create_grader(post_data)
        if not success:
            return HttpResponse(util.compose_reply(False,"Could not save grader."))

        #Add in call to xqueue here
        #sub.xqueue_submission_key, sub.xqueue_submission_id, sub.xqueue_queue_name

        #xqueue_session=util.xqueue_login()
        #error,msg = util.post_results_to_xqueue(xqueue_session,json.dumps(header),json.dumps(post_data))

        log.debug("Posted to xqueue, got {0} and {1}".format(error,msg))

        return HttpResponse(util.compose_reply(True,"Saved successfully."))


