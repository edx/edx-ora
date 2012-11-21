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

@csrf_exempt
def peer_grading(request):
    """
    Temporary peer grading view.  Can be removed once real peer grading is wired in.
    Handles both rendering and AJAX Posts.
    """
    post_data={}
    saved=False
    if request.method == 'POST':
        post_data=request.POST.dict().copy()
        for tag in ['score', 'submission_id', 'max_score', 'student_id']:
            if not post_data.has_key(tag):
                return HttpResponse("Failed to find needed keys 'score' and 'feedback'")

        try:
            post_data['score']=int(post_data['score'])
            post_data['max_score']=int(post_data['max_score'])
            post_data['submission_id']=int(post_data['submission_id'])
        except:
            return HttpResponse("Can't parse score into an int.")

        try:
            created,header=util.create_and_save_grader_object({
                'score': post_data['score'],
                'status' : "S",
                'grader_id' : 1,
                'grader_type' : "IN",
                'confidence' : 1,
                'submission_id' : post_data['submission_id'],
                })
            saved=True
        except:
            return HttpResponse("Cannot create grader object.")

        post_data['feedback']="<p>" + post_data['feedback'] + "</p>"

        xqueue_session=util.xqueue_login()

        error,msg = util.post_results_to_xqueue(xqueue_session,json.dumps(header),json.dumps(post_data))

        log.debug("Posted to xqueue, got {0} and {1}".format(error,msg))

    found=False
    if post_data is None or post_data=={} or saved:
        post_data={}
        found,sub_id=util.get_single_instructor_grading_item("MITx/6.002x")
        post_data['submission_id']=sub_id
        if not found:
            try:
                post_data.pop('submission_id')
            except:
                return HttpResponse("Could not find submission_id in post_data")
            return HttpResponse("No available grading.  Check back later.")

    try:
        sub_id=post_data['submission_id']
        sub=Submission.objects.get(id=sub_id)
    except:
        try:
            post_data.pop('submission_id')
        except:
            return HttpResponse("Could not find key submission_id in post data.")
        return HttpResponse("Invalid submission id in session.  Cannot find it.  Try reloading.")

    if sub.state in ["F"] and not found:
        post_data.pop('submission_id')
        return HttpResponse("Invalid submission id in session.  Sub is marked finished.  Try reloading.")

    url_base=settings.GRADING_CONTROLLER_INTERFACE['url']
    if not url_base.endswith("/"):
        url_base+="/"
    rendered=render_to_string('instructor_grading.html', {
        'score_points': [i for i in xrange(0,sub.max_score+1)],
        'ajax_url' : url_base,
        'text' : sub.student_response,
        'location' : sub.location,
        'prompt' : sub.prompt,
        'sub_id' : sub.id,
        'max_score' : sub.max_score,
        })
    return HttpResponse(rendered)
