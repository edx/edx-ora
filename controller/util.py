from django.conf import settings
import json
import logging
import requests
import urlparse
import project_urls

from django.http import HttpResponse

log = logging.getLogger(__name__)

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
    except ValueError, err:
        log.error(err)
        return (False, 'Unexpected reply from server.')

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
    except ValueError, err:
        log.error(err)
        return (False, 'unexpected reply from server')

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

    response.raise_for_status()
    log.debug("login response from %r: %r", url, response.json)
    (success, msg) = parse_xreply(response.content)
    return success, msg


def _http_get(session, url, data={}):
    """
    Send an HTTP get request:
    session: requests.session object.
    url : url to send request to
    data: optional dictionary to send
    """
    try:
        r = session.get(url, params=data)
    except requests.exceptions.ConnectionError, err:
        log.error(err)
        return (False, 'Cannot connect to server.')

    if r.status_code not in [200]:
        return (False, 'Unexpected HTTP status code [%d]' % r.status_code)
    return parse_xreply(r.text)


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
        log.error('Could not connect to server at %s in timeout=%f' % (url, timeout))
        return (False, 'Cannot connect to server.')

    if r.status_code not in [200]:
        log.error('Server %s returned status_code=%d' % (url, r.status_code))
        return (False, 'Unexpected HTTP status code [%d]' % r.status_code)
    return (True, r.text)


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
    xqueue_body = {
        'feedback': feedback,
        'score': score,
        'grader_type' : grader_type,
        'success' : success,
    }

    return xqueue_header, xqueue_body


def _error_response(msg, version):
    """
    Return a failing response with the specified message.
    """
    response = {'version': version,
                'success': False,
                'error': msg}
    return HttpResponse(json.dumps(response), mimetype="application/json")


def _success_response(data, version):
    """
    Return a successful response with the specified data.
    """
    response = {'version': version,
                'success': True}
    response.update(data)
    return HttpResponse(json.dumps(response), mimetype="application/json")






