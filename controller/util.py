from django.conf import settings
from functools import wraps
import json
import logging
import requests
import urlparse
import project_urls
import re

from django.http import HttpResponse
from django.contrib.auth.models import User, Group, Permission

from django.db import connection

import traceback
from lxml.html.clean import Cleaner

log = logging.getLogger(__name__)

_INTERFACE_VERSION = 1

def is_submitter(view):
    """
    Check whether the user calling the view is in the submitters group.
    """
    @wraps(view)
    def wrapper(request, *args, **kwds):
        if not request.user.groups.filter(name=settings.SUBMITTERS_GROUP).count()>0:
            return _error_response('insufficient_permissions', _INTERFACE_VERSION)
        return view(request, *args, **kwds)
    return wrapper

def error_if_not_logged_in(view):
    """
    Check whether the user calling the view is logged in.
    If so, pass through to the view.
    If not, return {'success': False, 'error': 'login_required'}.
    """
    @wraps(view)
    def wrapper(request, *args, **kwds):
        # If not logged in, bail
        if not request.user.is_authenticated():
            return _error_response('login_required', _INTERFACE_VERSION)
        return view(request, *args, **kwds)
    return wrapper

def get_request_ip(request):
    '''
    Retrieve the IP origin of a Django request
    '''
    ip = request.META.get('HTTP_X_REAL_IP', '') # nginx reverse proxy
    if not ip:
        ip = request.META.get('REMOTE_ADDR', 'None')
    return ip


def _value_or_default(value, default=None):
    """
    If value isn't None, return value, default if it is.
    Error if value is None with no default.
    """
    if value is not None:
        return value
    elif default is not None:
        return default
    else:
        error = "Needed value not passed by xqueue."
        #TODO: Fix in future to fail in a more robust way
        raise Exception(error)


def compose_reply(success, content):
    """
    Return a reply given below values:
    JSON-serialized dict:
     {'return_code': 0(success)/1(error),
    'content'    : 'my content', }

    """
    return_code = 0 if success else 1
    return json.dumps({'return_code': return_code,
                       'content': content})


def parse_xreply(xreply):
    """
    Parse the reply from xqueue. Messages are JSON-serialized dict:
        { 'return_code': 0 (success), 1 (fail)
          'content': Message from xqueue (string)
        }
    """

    try:
        xreply = json.loads(xreply)
    except ValueError:
        error_message =  "Could not parse xreply."
        log.error(error_message)
        return (False, error_message)

    #This is to correctly parse xserver replies and internal success/failure messages
    if 'return_code' in xreply:
        return_code = (xreply['return_code']==0)
        content = xreply['content']
    elif 'success' in xreply:
        return_code = xreply['success']
        content=xreply
    else:
        return False, "Cannot find a valid success or return code."

    if return_code not in [True,False]:
        return (False, 'Invalid return code.')


    return return_code, content


def parse_xobject(xobject, queue_name):
    """
    Parse a queue object from xqueue:
        { 'return_code': 0 (success), 1 (fail)
          'content': Message from xqueue (string)
        }
    """
    try:
        xobject = json.loads(xobject)

        header = json.loads(xobject['xqueue_header'])
        header.update({'queue_name': queue_name})
        body = json.loads(xobject['xqueue_body'])

        content = {'xqueue_header': json.dumps(header),
                   'xqueue_body': json.dumps(body)
        }
    except ValueError:
        error_message = "Unexpected reply from server."
        log.error(error_message)
        return (False, error_message)

    return True, content

def login(session, url, username, password):
    """
    Login to given url with given username and password.
    Use given request session (requests.session)
    """

    log.debug("Trying to login to {0} with user: {1} and pass {2}".format(url,username,password))
    response = session.post(url,
        {'username': username,
         'password': password,
        }
    )

    if response.status_code == 500 and url.endswith("/"):
        response = session.post(url[:-1],
                                {'username': username,
                                 'password': password,
                                 }
        )


    response.raise_for_status()
    log.debug("login response from %r: %r", url, response.json)
    (success, msg) = parse_xreply(response.content)
    return success, msg


def _http_get(session, url, data=None):
    """
    Send an HTTP get request:
    session: requests.session object.
    url : url to send request to
    data: optional dictionary to send
    """
    if data is None:
        data = {}
    try:
        r = session.get(url, params=data)
    except requests.exceptions.ConnectionError:
        error_message = "Cannot connect to server."
        log.error(error_message)
        return (False, error_message)

    if r.status_code == 500 and url.endswith("/"):
        r = session.get(url[:-1], params=data)

    if r.status_code not in [200]:
        return (False, 'Unexpected HTTP status code [%d]' % r.status_code)
    if hasattr(r, "text"):
        text = r.text
    elif hasattr(r, "content"):
        text = r.content
    else:
        error_message = "Could not get response from http object."
        log.exception(error_message)
        return False, error_message
    return parse_xreply(text)


def _http_post(session, url, data, timeout):
    '''
    Contact grading controller, but fail gently.
    Takes following arguments:
    session - requests.session object
    url - url to post to
    data - dictionary with data to post
    timeout - timeout in settings

    Returns (success, msg), where:
        success: Flag indicating successful exchange (Boolean)
        msg: Accompanying message; Controller reply when successful (string)
    '''

    try:
        r = session.post(url, data=data, timeout=timeout, verify=False)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        error_message = 'Could not connect to server at %s in timeout=%f' % (url, timeout)
        log.error(error_message)
        return (False, error_message)

    if r.status_code == 500 and url.endswith("/"):
        r = session.post(url[:-1], data=data, timeout=timeout, verify=False)

    if r.status_code not in [200]:
        error_message = "Server %s returned status_code=%d' % (url, r.status_code)"
        log.error(error_message)
        return (False, error_message)

    if hasattr(r, "text"):
        text = r.text
    elif hasattr(r, "content"):
        text = r.content
    else:
        error_message = "Could not get response from http object."
        log.exception(error_message)
        return False, error_message

    return (True, text)


def post_results_to_xqueue(session, header, body):
    """
    Post the results from a grader back to xqueue.
    Input:
        session - a requests session that is logged in to xqueue
        header - xqueue header.  Dict containing keys submission_key and submission_id
        body - xqueue body.  Arbitrary dict.
    """
    request = {
        'xqueue_header': header,
        'xqueue_body': body,
    }

    (success, msg) = _http_post(session, settings.XQUEUE_INTERFACE['url'] + project_urls.XqueueURLs.put_result, request,
        settings.REQUESTS_TIMEOUT)

    return success, msg

def xqueue_login():
    session = requests.session()
    xqueue_login_url = urlparse.urljoin(settings.XQUEUE_INTERFACE['url'], project_urls.XqueueURLs.log_in)
    (success, xqueue_msg) = login(
        session,
        xqueue_login_url,
        settings.XQUEUE_INTERFACE['django_auth']['username'],
        settings.XQUEUE_INTERFACE['django_auth']['password'],
    )

    return session

def controller_login():
    session = requests.session()
    controller_login_url = urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'], project_urls.ControllerURLs.log_in)
    (success, controller_msg) = login(
        session,
        controller_login_url,
        settings.GRADING_CONTROLLER_INTERFACE['django_auth']['username'],
        settings.GRADING_CONTROLLER_INTERFACE['django_auth']['password'],
    )
    return session

def controller_logout(session):
    """
    Log out of the grading controller.
    Logging out removes a row in the session database.
    """
    controller_logout_url = urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'], project_urls.ControllerURLs.log_out)
    session.post(controller_logout_url)

def create_xqueue_header_and_body(submission):
    xqueue_header = {
        'submission_id': submission.xqueue_submission_id,
        'submission_key': submission.xqueue_submission_key,
    }

    score_and_feedback = submission.get_all_successful_scores_and_feedback()
    score = score_and_feedback['score']
    feedback = score_and_feedback['feedback']
    grader_type=score_and_feedback['grader_type']
    success=score_and_feedback['success']
    grader_id = score_and_feedback['grader_id']
    submission_id = score_and_feedback['submission_id']
    rubric_scores_complete = score_and_feedback['rubric_scores_complete']
    rubric_xml = score_and_feedback['rubric_xml']
    xqueue_body = {
        'feedback': feedback,
        'score': score,
        'grader_type' : grader_type,
        'success' : success,
        'grader_id' : grader_id,
        'submission_id' : submission_id,
        'rubric_scores_complete' : rubric_scores_complete,
        'rubric_xml' : rubric_xml,
    }

    return xqueue_header, xqueue_body


def _error_response(msg, version, data=None):
    """
    Return a failing response with the specified message.

    Args:
        msg: used as the 'error' key
        version: specifies the protocol version
        data: if specified, a dict that's included in the response
    """
    response = {'version': version,
                'success': False,
                'error': msg}

    if data is not None:
        response.update(data)
    return HttpResponse(json.dumps(response), mimetype="application/json")


def _success_response(data, version):
    """
    Return a successful response with the specified data.
    """
    response = {'version': version,
                'success': True}
    response.update(data)
    return HttpResponse(json.dumps(response), mimetype="application/json")

def update_users_from_file():
    auth_path = settings.ENV_ROOT / settings.CONFIG_PREFIX + "auth.json"
    log.info(' [*] reading {0}'.format(auth_path))

    with open(auth_path) as auth_file:
        AUTH_TOKENS = json.load(auth_file)
        users = AUTH_TOKENS.get('USERS', {})

        submitters, created = Group.objects.get_or_create(name=settings.SUBMITTERS_GROUP)
        view_submission = Permission.objects.get(codename=settings.EDIT_SUBMISSIONS_PERMISSION)
        submitters.permissions.add(view_submission)

        for username, pwd in users.items():
            log.info(' [*] Creating/updating user {0}'.format(username))
            try:
                user = User.objects.get(username=username)
                user.set_password(pwd)
                user.groups.add(submitters)
                user.is_staff = True
                user.is_superuser = True
                user.save()
            except User.DoesNotExist:
                log.info('     ... {0} does not exist. Creating'.format(username))

                user = User.objects.create(username=username,
                    email=username + '@dummy.edx.org',
                    is_active=True, is_staff=True, is_superuser=True)
                user.set_password(pwd)
                user.groups.add(submitters)
                user.save()
        log.info(' [*] All done!')

def log_connection_data():
    if settings.PRINT_QUERIES == True:
        query_data = connection.queries
        query_time = [float(q['time']) for q in query_data]
        query_sql = [q['sql'] for q in query_data]

        for i in xrange(0,len(query_time)):
            try:
                if query_time[i]>.02:
                    log.info("Time: {0} SQL: {1}".format(query_time[i], query_sql[i].encode('ascii', 'ignore')))
            except Exception:
                pass

        log.info("Query Count: {0} Total time: {1}".format(len(query_time), sum(query_time)))
        if len(query_time)>30:
            for i in xrange(0,30):
                log.info("{0} Time: {1}".format(query_sql[i], str(float(query_time[i]))))
            traceback.print_stack()

def sanitize_html(text):
    try:
        cleaner = Cleaner(
            style=True,
            links=True,
            add_nofollow=False,
            page_structure=True,
            safe_attrs_only=False,
            remove_unknown_tags=False,
            allow_tags=["img", "a"]
        )
        clean_html = cleaner.clean_html(text)
        clean_html = re.sub(r'</p>$', '', re.sub(r'^<p>', '', clean_html))
    except Exception:
        clean_html = text
    return clean_html
