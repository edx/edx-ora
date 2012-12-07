from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import json
import logging
import requests
import urlparse

import util
import grader_util

from staff_grading import staff_grading_util

from models import Submission

log = logging.getLogger(__name__)

_INTERFACE_VERSION=1

@csrf_exempt
def log_in(request):
    """
    Handles external login request.
    """
    if request.method == 'POST':
        p = request.POST.copy()
        if p.has_key('username') and p.has_key('password'):
            user = authenticate(username=p['username'], password=p['password'])
            if user is not None:
                login(request, user)
                log.debug("Successful login!")
                return util._success_response({'message' : 'logged in'} , _INTERFACE_VERSION)
            else:
                return util._error_response('Incorrect login credentials', _INTERFACE_VERSION)
        else:
            return util._error_response('Insufficient login info', _INTERFACE_VERSION)
    else:
        return util._error_response('login_required', _INTERFACE_VERSION)


def log_out(request):
    """
    Uses django auth to handle a logout request
    """
    logout(request)
    return util._success_response({'message' : 'Goodbye'} , _INTERFACE_VERSION)


def status(request):
    """
    Returns a simple status update
    """
    return util._success_response({'content' : 'OK'}, _INTERFACE_VERSION)

def request_eta_for_submission(request):
    """
    Gets the ETA for a student submission to be graded for a given location
    Input:
        A problem location
    Output:
        Dictionary containing success, and eta indicating time a new submission for given location will take to be graded
    """
    if request.method != 'GET':
        return util._error_response("Request type must be GET", _INTERFACE_VERSION)

    location=request.GET.get("location")
    if not location:
        return util._error_response("Missing required key location", _INTERFACE_VERSION)

    success, eta = grader_util.get_eta_for_submission(location)

    if not success:
        return util._error_response(eta,_INTERFACE_VERSION)

    return util._success_response({
        'eta' : eta,
    }, _INTERFACE_VERSION)










