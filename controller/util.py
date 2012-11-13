def get_request_ip(request):
    '''
    Retrieve the IP origin of a Django request
    '''
    ip = request.META.get('HTTP_X_REAL_IP','') # nginx reverse proxy
    if not ip:
        ip = request.META.get('REMOTE_ADDR','None')
    return ip