from models import Submission
import json

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