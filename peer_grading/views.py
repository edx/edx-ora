import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from controller.models import Submission
from controller import util

log = logging.getLogger(__name__)

_INTERFACE_VERSION=1

def json_response(success,data):
    response = {'version': _INTERFACE_VERSION,
                'success': success}
    response.update(data)
    return HttpResponse(json.dumps(response), mimetype="application/json")

def get_next_submission(request):
    """
    Gets next submission from controller for peer grading.
    Input:
        Get request with the following keys:
           grader_id - Student id of the grader
           location - The problem id to get peer grading for.
    """

    if request.method!="GET":
        raise Http404

    grader_id = request.GET.get("grader_id")
    location = request.GET.get("location")

    if not grader_id or not location:
        return json_response(False,{'error' : "Failed to find needed keys 'grader_id' and 'location'"})

    (found,sub_id) = util.get_peer_grading(location,grader_id)

    if not found:
        return json_response(False,{'error' : "No current grading."})

    try:
        sub=Submission.objects.get(id=sub_id)
    except:
        log.debug("Could not find submission with id {0}".format(sub_id))
        return json_response(False,{'error' : "Error getting grading."})

    if sub.state!="C":
        log.debug("Submission with id {0} has incorrect internal state {1}.".format(sub_id,sub.state))
        return json_response(False,{'error' : "Error getting grading."})

    response={
        'submission_id' : sub_id,
        'submission_key' : sub.xqueue_submission_key,
        'student_response' : sub.student_response,
        'prompt' : sub.prompt,
        'rubric' : sub.rubric,
        'max_score' : sub.max_score,
    }

    return json_response(True,response)

def save_grade():
    pass