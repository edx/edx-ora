from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from statsd import statsd

import json
import logging

from models import Submission, GRADER_TYPE, Grader, STATUS_CODES
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

    found,sub_id=util.get_instructor_grading(course_id)

    if not found:
        return HttpResponse(util.compose_reply(False,"Nothing to grade."))

    return HttpResponse(util.compose_reply(True,to_be_graded.id))



@login_required
def put_result(request):
    if request.method != 'POST':
        return HttpResponse(util.compose_reply(False, "'put_result' must use HTTP POST"))
    else:
        post_data=request.POST.dict()

        for tag in ['assessment','feedback', 'submission_id', 'grader_type', 'status', 'confidence', 'grader_id']:
            if not post_data.has_key(tag):
                return HttpResponse(compose_reply(False,"Failed to find needed keys."))

        if post_data['grader_type'] not in GRADER_TYPE:
            return HttpResponse(compose_reply(False,"Invalid grader type."))

        if post_data['status'] not in STATUS_CODES:
            return HttpResponse(compose_reply(False,"Invalid grader status."))

        try:
            post_data['assessment']=int(post_data['assessment'])
        except:
            return HttpResponse(compose_reply(False,"Can't parse assessment into an int."))

        success=util.create_grader(post_data)
        if not success:
            return HttpResponse(compose_reply(False,"Could not save grader."))

        return HttpResponse(compose_reply(True,"Saved successfully."))


