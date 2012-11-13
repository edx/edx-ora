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