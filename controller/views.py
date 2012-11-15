from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.conf import settings

import json
import logging
import requests
import urlparse

import util

from models import Submission

log = logging.getLogger(__name__)

# Log in
#--------------------------------------------------
@csrf_exempt
def log_in(request):
    if request.method == 'POST':
        p = request.POST.copy()
        if p.has_key('username') and p.has_key('password'):
            user = authenticate(username=p['username'], password=p['password'])
            if user is not None:
                login(request, user)
                log.debug("Successful login!")
                return HttpResponse(util.compose_reply(True, 'Logged in'))
            else:
                return HttpResponse(util.compose_reply(False, 'Incorrect login credentials'))
        else:
            return HttpResponse(util.compose_reply(False, 'Insufficient login info'))
    else:
        return HttpResponse(util.compose_reply(False,'login_required'))

def log_out(request):
    logout(request)
    return HttpResponse(util.compose_reply(success=True,content='Goodbye'))

# Status check
#--------------------------------------------------
def status(request):
    return HttpResponse(util.compose_reply(success=True, content='OK'))

@csrf_exempt
def instructor_grading(request):
    post_data={}
    if request.method == 'POST':
        post_data=request.POST.dict()
        for tag in ['score','feedback', 'submission_id']:
            if not post_data.has_key(tag):
                return HttpResponse("Failed to find needed keys 'score' and 'feedback'")

        try:
            post_data['score']=int(post_data['score'])
            post_data['submission_id']=int(post_data['submission_id'])
        except:
            return HttpResponse("Can't parse score into an int.")

        try:
            created,header=util.create_grader({
                'score': post_data['score'],
                'feedback' : post_data['feedback'],
                'status' : "S",
                'grader_id' : 1,
                'grader_type' : "IN",
                'confidence' : 1,
                'submission_id' : post_data['submission_id'],
                })
            post_data.pop('submission_id')

        except:
            return HttpResponse("Cannot create grader object.")
        post_data['feedback']="<p>" + post_data['feedback'] + "</p>"
        post_data=post_data.update({
            ''
        })
        xqueue_session=requests.session()
        xqueue_login_url = urlparse.urljoin(settings.XQUEUE_INTERFACE['url'],'/xqueue/login/')
        (xqueue_error,xqueue_msg)=util.login(
            xqueue_session,
            xqueue_login_url,
            settings.XQUEUE_INTERFACE['django_auth']['username'],
            settings.XQUEUE_INTERFACE['django_auth']['password'],
        )

        error,msg = util.post_results_to_xqueue(xqueue_session,json.dumps(header),json.dumps(post_data))

        log.debug("Posted to xqueue, got {0} and {1}".format(error,msg))

    found=False
    if 'submission_id' not in post_data.keys():
        found,sub_id=util.get_instructor_grading("MITx/6.002x")
        post_data['submission_id']=sub_id
        log.debug(sub_id)
        if not found:
            post_data.pop('submission_id')
            return HttpResponse("No available grading.  Check back later.")

    sub_id=post_data['submission_id']
    try:
        sub=Submission.objects.get(id=sub_id)
    except:
        post_data.pop('current_sub')
        return HttpResponse("Invalid submission id in session.  Cannot find it.  Try reloading.")

    if sub.state in ["F"] and not found:
        post_data.pop('current_sub')
        return HttpResponse("Invalid submission id in session.  Sub is marked finished.  Try reloading.")

    url_base=settings.GRADING_CONTROLLER_INTERFACE['url']
    if not url_base.endswith("/"):
        url_base+="/"
    rendered=render_to_string('instructor_grading.html', {
        'score_points': [0,1],
        'ajax_url' : url_base,
        'text' : sub.student_response,
        'location' : sub.location,
        'prompt' : sub.prompt,
        'sub_id' : sub.id,
    })
    return HttpResponse(rendered)

