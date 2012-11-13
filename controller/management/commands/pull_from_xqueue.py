import json
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import requests
import urlparse
import time
import json

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<queue_name>"
    help = "Pull items from given queues and send to grading controller"

    def handle(self, *args, **options):
        """
        Constant loop that pulls from queue and posts to grading controller
        """
        log.info(' [*] Pulling from xqueues...')
        self.xqueue_session=requests.session()
        self.controller_session=requests.session()

        flag=True
        error = self.login()

        while flag:
            for queue_name in args:
                try:
                    response_code,queue_item=self.get_from_queue(queue_name)
                    return_code,content=parse_xobject(queue_item)
                    log.debug(content)

                    #Post to grading controller here!
                    if return_code==0:
                        #Post to controller
                        log.debug("Trying to post.")
                        self._http_post(urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                            '/grading_controller/submit/'),content,settings.REQUESTS_TIMEOUT)
                        log.debug("Successful post!")
                    else:
                        log.error("Error getting queue item.")

                except Exception as err:
                    log.debug("Error getting submission: ".format(err))
                time.sleep(2)

    def login(self):
        '''
        Login to xqueue to pull submissions
        '''
        xqueue_login_url = urlparse.urljoin(settings.XQUEUE_INTERFACE['url'],'/xqueue/login/')
        controller_login_url = urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],'/grading_controller/login/')
        log.debug(controller_login_url)

        xqueue_response = self.xqueue_session.post(xqueue_login_url,
            {'username': settings.XQUEUE_INTERFACE['django_auth']['username'],
            'password': settings.XQUEUE_INTERFACE['django_auth']['password']}
        )

        controller_response = self.controller_session.post(xqueue_login_url,
            {'username': settings.GRADING_CONTROLLER_INTERFACE['django_auth']['username'],
            'password': settings.GRADING_CONTROLLER_INTERFACE['django_auth']['password']}
        )

        xqueue_response.raise_for_status()
        controller_response.raise_for_status()

        log.debug("xqueue login response: %r", xqueue_response.json)
        log.debug("controller login response: %r", controller_response.json)

        (xqueue_error,xqueue_msg)= parse_xreply(xqueue_response.content)
        (controller_error,controller_msg) = parse_xreply(controller_response.content)

        return max(controller_error,xqueue_error)

    def get_from_queue(self,queue_name):
        """
        Get a single submission from xqueue
        """
        try:
            response = self._http_get(urlparse.urljoin(settings.XQUEUE_INTERFACE['url'],'/xqueue/get_submission/'),
                {'queue_name' : queue_name})
        except Exception as err:
            return "Error getting response: {0}".format(err)

        return response

    def _http_get(self,url, data):
        try:
            r = self.xqueue_session.get(url, params=data)
        except requests.exceptions.ConnectionError, err:
            log.error(err)
            return (1, 'cannot connect to server')

        if r.status_code not in [200]:
            return (1, 'unexpected HTTP status code [%d]' % r.status_code)

        return parse_xreply(r.text)

    def _http_post(self, url, data, timeout):
        '''
        Contact grading controller, but fail gently.

        Returns (success, msg), where:
            success: Flag indicating successful exchange (Boolean)
            msg: Accompanying message; Controller reply when successful (string)
        '''

        try:
            r = self.controller_session.post(url, data=data, timeout=timeout, verify=False)
        except (ConnectionError, Timeout):
            log.error('Could not connect to server at %s in timeout=%f' % (url, timeout))
            return (False, 'cannot connect to server')

        if r.status_code not in [200]:
            log.error('Server %s returned status_code=%d' % (url, r.status_code))
            return (False, 'unexpected HTTP status code [%d]' % r.status_code)
        return (True, r.text)


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

def parse_xobject(xobject):
    """
    Parse a queue object from xqueue:
        { 'return_code': 0 (success), 1 (fail)
          'content': Message from xqueue (string)
        }
    """
    try:
        xobject = json.loads(xobject)

        header= json.loads(xobject['xqueue_header'])
        body=json.loads(xobject['xqueue_body'])

        content={'xqueue_header' : header,
            'xqueue_body' : body
        }
    except ValueError, err:
        log.error(err)
        return (1, 'unexpected reply from server')

    return 0, content
