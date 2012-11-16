from django.conf import settings
from models import Submission, Grader
import json
import logging
from django.utils import timezone
import datetime

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
    """
    If value isn't None, return value, default if it is.
    Error if value is None with no default.
    """
    if value is not None:
        return value
    elif default is not None:
        return default
    else:
        error="Needed value not passed by xqueue."
        #TODO: Fix in future to fail in a more robust way
        raise Exception(error)


def subs_graded_by_instructor(location):
    """
    Get submissions that are graded by instructor
    """
    subs_graded=Submission.objects.filter(location=location,
        previous_grader_type__in=["IN"],
        state__in=["F"],
    )

    return subs_graded

def subs_pending_instructor(location):
    """
    Get submissions that are pending instructor grading.
    """
    subs_pending=Submission.objects.filter(location=location,
        next_grader_type__in=["IN"],
        state__in=["C","W"],
    )

    return subs_pending

def subs_by_instructor(location):
    """
    Return length of submissions pending instructor grading and graded.
    """
    return subs_graded_by_instructor(location).count(),subs_pending_instructor(location).count()


def compose_reply(success, content):
    """
    Return a reply given below values:
    JSON-serialized dict:
     {'return_code': 0(success)/1(error),
    'content'    : 'my content', }

    """
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
    """
    Login to given url with given username and password.
    Use given request session (requests.session)
    """
    response = session.post(url,
        {'username': username,
         'password': password,
         }
    )

    response.raise_for_status()
    log.debug("login response from %r: %r", url,response.json)
    (error,msg)= parse_xreply(response.content)
    return error,msg

def _http_get(session,url, data={}):
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
        return (1, 'cannot connect to server')

    if r.status_code not in [200]:
        return (1, 'unexpected HTTP status code [%d]' % r.status_code)
    log.debug(r.text)
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
    except (ConnectionError, Timeout):
        log.error('Could not connect to server at %s in timeout=%f' % (url, timeout))
        return (False, 'cannot connect to server')

    if r.status_code not in [200]:
        log.error('Server %s returned status_code=%d' % (url, r.status_code))
        return (False, 'unexpected HTTP status code [%d]' % r.status_code)
    return (True, r.text)

def create_grader(grader_dict):
    """
    Creates a grader object and associates it with a given submission
    Input is grader dictionary with keys:
     feedback, status, grader_id, grader_type, confidence.
    """
    try:
        sub=Submission.objects.get(id=grader_dict['submission_id'])
    except:
        return False

    grade=Grader(
        score=grader_dict['score'],
        feedback = grader_dict['feedback'],
        status_code = grader_dict['status'],
        grader_id= grader_dict['grader_id'],
        grader_type= grader_dict['grader_type'],
        confidence= grader_dict['confidence'],
    )

    grade.submission=sub
    grade.save()

    #TODO: Need some kind of logic somewhere else to handle setting next_grader

    sub.previous_grader_type=grade.grader_type
    sub.next_grader_type=grade.grader_type

    if(grade.status_code=="S" and grade.grader_type in ["IN","ML"]):
        sub.state="F"

    sub.save()

    return True,{'submission_id' : sub.xqueue_submission_id, 'submission_key' : sub.xqueue_submission_key }

def post_results_to_xqueue(session,header,body):
    """
    Post the results from a grader back to xqueue.

    """
    request={
        'xqueue_header' : header,
        'xqueue_body' : body,
    }

    (error,msg)=_http_post(session, settings.XQUEUE_INTERFACE['url'] + '/xqueue/put_result/', request, settings.REQUESTS_TIMEOUT)

    return error,msg

def get_instructor_grading(course_id):
    """
    Gets instructor grading for a given course id.
    Returns one submission id corresponding to the course.
    """
    found=False
    sub_id=0
    locations_for_course=[x['location'] for x in Submission.objects.filter(course_id=course_id).values('location').distinct()]
    for location in locations_for_course:
        subs_graded_by_instructor, subs_pending_instructor=subs_by_instructor(location)
        if (subs_graded_by_instructor+subs_pending_instructor)<settings.MIN_TO_USE_ML:
            to_be_graded=Submission.objects.filter(
                location=location,
                state="W",
                next_grader_type="IN",
            )

            if(len(to_be_graded)>0):
                to_be_graded=to_be_graded[0]
                if to_be_graded is not None:
                    to_be_graded.state="C"
                    to_be_graded.save()
                    found=True
                    sub_id=to_be_graded.id
                    return found,sub_id
    return found,sub_id

def check_if_timed_out(subs):
    """
    Check if submissions have timed out, and reset them to waiting to grade state if they have
    """
    now=datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
    sub_times=[now-sub.date_modified for sub in subs]
    min_time=datetime.timedelta(minutes=settings.RESET_SUBMISSIONS_AFTER)

    for i in xrange(0,len(sub_times)):
        if sub_times>min_time:
            sub=subs[i]
            if sub.state=="C":
                sub.state="W"
                sub.save()

    return True


def check_if_expired(subs):
    """
    Check if submissions have expired, and return them if they have
    """
    now=datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
    sub_times=[now-sub.date_modified for sub in subs]
    min_time=datetime.timedelta(minutes=settings.EXPIRE_SUBMISSIONS_AFTER)

    timed_out_list=[]
    for i in xrange(0,len(sub_times)):
        if sub_times>min_time:
            timed_out_list.append(subs[i])

    return timed_out_list

def expire_submissions():
    subs=Submission.objects.filter(

    )