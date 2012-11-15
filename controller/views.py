from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.conf import settings

import json
import logging

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
    log.debug(request.session)
    if request.method == 'POST':
        post_data=request.POST.dict()
        for tag in ['assessment','feedback']:
            if not post_data.has_key(tag):
                return HttpResponse("Failed to find needed keys 'assessment' and 'feedback'")

        if 'current_sub' not in request.session.keys():
            return HttpResponse("No submission id in session.  Cannot match assessment.  Please reload.")

        try:
            post_data['assessment']=int(post_data['assessment'])
            created=util.create_grader({
                'assessment': post_data['assessment'],
                'feedback' : post_data['feedback'],
                'status' : "S",
                'grader_id' : 1,
                'grader_type' : "IN",
                'confidence' : 1,
                'submission_id' : requests.session['current_sub'],
            })
            request.session.pop('current_sub')
        except:
            return HttpResponse("Can't parse assessment into an int.")

    found=False
    if 'current_sub' not in request.session.keys():
        found,sub_id=util.get_instructor_grading("MITx/6.002x")
        request.session['current_sub']=sub_id
        log.debug(sub_id)
        if not found:
            return HttpResponse("No available grading.  Check back later.")

    sub_id=request.session['current_sub']
    try:
        sub=Submission.objects.get(id=sub_id)
    except:
        request.session.pop('current_sub')
        return HttpResponse("Invalid submission id in session.  Try reloading.")

    if sub.state in ["C", "F"] and not found:
        request.session.pop('current_sub')
        return HttpResponse("Invalid submission id in session.  Try reloading.")

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

