from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from statsd import statsd

import json
import logging

from models import Submission, GRADER_TYPE
import util

@login_required
def get_submission_ml(request):
    unique_locations=[x['location'] for x in Submission.objects.values('location').distinct()]
    for location in unique_locations:
        subs_graded_by_instructor=util.subs_graded_by_instructor(location)
        if subs_graded_by_instructor>=settings.MIN_TO_USE_ML:
            to_be_graded=Submission.objects.filter(
                location=location,
                state="W",
                next_grader_type="ML",
            )[0]
            if to_be_graded is not None:
                to_be_graded.state="C"
                to_be_graded.save()
                return HttpResponse(util.compose_reply(True,to_be_graded.id))

    return HttpResponse(util.compose_reply(False,"Nothing to grade."))

@login_required
def get_submission_in(request):
    try:
        course_id = util._value_or_default(request.GET['course_id'],None)
    except KeyError:
        return HttpResponse(util.compose_reply(False,
        "'get_submission' requires parameter 'course_id'"))

    locations_for_course=[x['location'] for x in Submission.objects.filter(course_id=course_id).values('location').distinct()]
    for location in locations_for_course:
        subs_graded_by_instructor, subs_pending_instructor=util.subs_by_instructor(location)
        if (subs_graded_by_instructor+subs_pending_instructor)<settings.MIN_TO_USE_ML:
            to_be_graded=Submission.objects.filter(
                location=location,
                state="W",
                next_grader_type="IN",
            )[0]
            if to_be_graded is not None:
                to_be_graded.state="C"
                to_be_graded.save()
                return HttpResponse(util.compose_reply(True,to_be_graded.id))

    return HttpResponse(util.compose_reply(False,"Nothing to grade."))


@login_required
def put_result():
    #Accept a post request from external grader, and handle properly
    pass
