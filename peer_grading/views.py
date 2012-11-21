import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from controller.models import Submission
from controller import util
import requests
import urlparse

log = logging.getLogger(__name__)

feedback_template = u"""

<section>
    <header>Feedback</header>
    <div class="shortform">
        <div class="result-output">
          <p>Score: {score}</p>
        </div>
    </div>
    <div class="longform">
        <div class="result-output">
          <div class="feedback">
            Feedback: {feedback}
          </div>
        </div>
    </div>
</section>

"""

_INTERFACE_VERSION=1

#Fix with central import once everything is merged, but just copy definitions for now!
def _error_response(msg,version):
    """
    Return a failing response with the specified message.
    """
    response = {'version': version,
                'success': False,
                'error': msg}
    return HttpResponse(json.dumps(response), mimetype="application/json")


def _success_response(data,version):
    """
    Return a successful response with the specified data.
    """
    response = {'version': version,
                'success': True}
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
        return _error_response("Failed to find needed keys 'grader_id' and 'location'")

    (found,sub_id) = util.get_peer_grading(location,grader_id)

    if not found:
        return  _error_response("No current grading.",_INTERFACE_VERSION)

    try:
        sub=Submission.objects.get(id=sub_id)
    except:
        log.debug("Could not find submission with id {0}".format(sub_id))
        return _error_response("Error getting grading.",_INTERFACE_VERSION)

    if sub.state!="C":
        log.debug("Submission with id {0} has incorrect internal state {1}.".format(sub_id,sub.state))
        return _error_response("Error getting grading.",_INTERFACE_VERSION)

    response={
        'submission_id' : sub_id,
        'submission_key' : sub.xqueue_submission_key,
        'student_response' : sub.student_response,
        'prompt' : sub.prompt,
        'rubric' : sub.rubric,
        'max_score' : sub.max_score,
    }

    return _success_response(response,_INTERFACE_VERSION)

def save_grade(request):
    """
    Supports POST requests with the following arguments:

    location: string
    grader_id: int
    submission_id: int
    score: int
    feedback: string
    submission_key : string

    Returns json dict with keys

    version: int
    success: bool
    error: string, present if not success
    """
    if request.method != "POST":
        raise Http404

    post_data=request.POST.dict().copy()

    for tag in ['location','grader_id','submission_id','submission_key','score','feedback']:
        if not tag in post_data:
            return _error_response("Cannot find needed key {0} in request.".format(tag),_INTERFACE_VERSION)

    location = post_data['location']
    grader_id = post_data['grader_id']
    submission_id = post_data['submission_id']

    #Submission key currently unused, but plan to use it for validation in the future.
    submission_key = post_data['submission_key']
    score = post_data['score']

    #This is done to ensure that response is properly formatted on the lms side.
    feedback_string = post_data['feedback']
    feedback=feedback_template.format(feedback=feedback_string,score=score)

    try:
        score = int(score)
    except ValueError:
        return _error_response("Expected integer score.  Got {0}".format(score))

    d = {'submission_id': submission_id,
         'score': score,
         'feedback': feedback,
         'grader_id': grader_id,
         'grader_type': 'PE',
         # Humans always succeed (if they grade at all)...
         'status': 'S',
         # ...and they're always confident too.
         'confidence': 1.0}

    #We need to figure out how/when to post peer grading results back to LMS given the "multiple peers" problem.
    #The best solution is probably to post back to LMS each time, and LMS have logic dictating when/which peer
    #graded results to show the student.
    (success,header) = util.create_grader(d)
    if not success:
        return _error_response("There was a problem saving the grade.  Contact support.",_INTERFACE_VERSION)

    xqueue_session=util.xqueue_login()

    error,msg = util.post_results_to_xqueue(xqueue_session,json.dumps(header),json.dumps(post_data))

    return _success_response({'msg' : "Posted to queue."},_INTERFACE_VERSION)


