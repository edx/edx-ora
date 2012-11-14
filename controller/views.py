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
@csrf_exempt
def status(request):
    return HttpResponse(util.compose_reply(success=True, content='OK'))

def instructor_grading(request):
    if request.method == 'POST':
        post_data=request.POST
        for tag in ['assessment','feedback']:
            if not post_data.has_key(tag):
                return HttpResponse("Failed to find needed keys 'assessment' and 'feedback'")
        try:
            post_data['assessment']=int(post_data['assessment'])
        except:
            return HttpResponse("Can't parse assessment into an int.")



    else:
        url_base=settings.GRADING_CONTROLLER_INTERFACE['url']
        if not url_base.endswith("/"):
            url_base+="/"
        rendered=render_to_string('instructor_grading.html', {
            'score_points': [0,1],
            'ajax_url' : url_base
        })
        return HttpResponse(rendered)

