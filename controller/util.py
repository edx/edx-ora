from django.conf import settings
from models import Submission
import json
import logging

log=logging.getLogger(__name__)

def get_request_ip(request):
    '''
    Retrieve the IP origin of a Django request
    '''
    ip = request.META.get('HTTP_X_REAL_IP','') # nginx reverse proxy
    if not ip:
        ip = request.META.get('REMOTE_ADDR','None')
    return ip

def _value_or_default(value,default=None):
    if value is not None:
        return value
    elif default is not None:
        return default
    else:
        error="Needed value not passed by xqueue."
        #TODO: Fix in future to fail in a more robust way
        raise Exception(error)


def subs_graded_by_instructor(location):
    subs_graded=Submission.objects.filter(location=location,
        previous_grader_type__in=["IN"],
        state__in=["F"],
    )

    return len(subs_graded)

def subs_pending_instructor(location):
    subs_pending=Submission.objects.filter(location=location,
        next_grader_type__in=["IN"],
        state__in=["C","W"],
    )

    return len(subs_pending)

def subs_by_instructor(location):
    return subs_graded_by_instructor(location),subs_pending_instructor(location)

# Xqueue reply format:
#    JSON-serialized dict:
#    { 'return_code': 0(success)/1(error),
#      'content'    : 'my content', }
#--------------------------------------------------
def compose_reply(success, content):
    return_code = 0 if success else 1
    return json.dumps({ 'return_code': return_code,
                        'content': content })


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
        return (1, 'unexpected reply from server')

    return_code = xreply['return_code']
    content = xreply['content']
    return return_code, content

def parse_xobject(xobject,queue_name):
    """
    Parse a queue object from xqueue:
        { 'return_code': 0 (success), 1 (fail)
          'content': Message from xqueue (string)
        }
    """
    try:
        xobject = json.loads(xobject)

        header= json.loads(xobject['xqueue_header'])
        header.update({'queue_name' : queue_name})
        body=json.loads(xobject['xqueue_body'])

        content={'xqueue_header' : json.dumps(header),
                 'xqueue_body' : json.dumps(body)
        }
    except ValueError, err:
        log.error(err)
        return (1, 'unexpected reply from server')

    return 0, content

def login(session,url,username,password):
    response = session.post(url,
        {'username': username,
         'password': password,
         }
    )

    response.raise_for_status()
    log.debug("login response from %r: %r", url,response.json)
    (error,msg)= parse_xreply(response.content)
    return error,msg

def _http_get(session,url, data):
    try:
        r = session.get(url, params=data)
    except requests.exceptions.ConnectionError, err:
        log.error(err)
        return (1, 'cannot connect to server')

    if r.status_code not in [200]:
        return (1, 'unexpected HTTP status code [%d]' % r.status_code)
    log.debug(r.text)
    return parse_xreply(r.text)

def _http_post(session, url, data, timeout):
    '''
    Contact grading controller, but fail gently.

    Returns (success, msg), where:
        success: Flag indicating successful exchange (Boolean)
        msg: Accompanying message; Controller reply when successful (string)
    '''

    try:
        r = session.post(url, data=data, timeout=timeout, verify=False)
    except (ConnectionError, Timeout):
        log.error('Could not connect to server at %s in timeout=%f' % (url, timeout))
        return (False, 'cannot connect to server')

    if r.status_code not in [200]:
        log.error('Server %s returned status_code=%d' % (url, r.status_code))
        return (False, 'unexpected HTTP status code [%d]' % r.status_code)
    return (True, r.text)