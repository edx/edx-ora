from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from statsd import statsd

import json
import logging

from models import Submission, GRADER_TYPE
from views import compose_reply
import util

@login_required
def get_submission(request):
    try:
        grader_type = request.GET['grader_type']
        grader_location = util._value_or_default(request.GET['grader_location'],None)
    except KeyError:
        return HttpResponse(compose_reply(False, "'get_submission' requires parameter 'grader_type'"))

    if grader_type not in [x[0] for x in GRADER_TYPE]:
        return HttpResponse(compose_reply(False, ("Invalid grader type: {0}.  "
                                                 "Valid grader types in models file.").format(grader_type)))
    else:
        to_be_graded=

def put_result():
    #Accept a post request from external grader, and handle properly
    pass
