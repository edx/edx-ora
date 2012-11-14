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
    try:
        grader_type = request.GET['grader_type']
        #grader_location = util._value_or_default(request.GET['grader_location'],None)
    except KeyError:
        return HttpResponse(util.compose_reply(False, "'get_submission' requires parameter 'grader_type'"))

    if grader_type not in [x[0] for x in GRADER_TYPE]:
        return HttpResponse(util.compose_reply(False, ("Invalid grader type: {0}.  "
                                                 "Valid grader types in models file.").format(grader_type)))
    else:
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
                    return HttpResponse(util.compose_reply(True,to_be_graded.id))

        return HttpResponse(util.compose_reply(False,"Nothing to grade."))

@login_required
def get_submission_in(request):
    pass


@login_required
def put_result():
    #Accept a post request from external grader, and handle properly
    pass
