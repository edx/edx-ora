from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

import requests
import urlparse
import time
import json
import logging

import controller.util as util

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
                    return_code,content=util.parse_xobject(queue_item,queue_name)
                    log.debug(content)

                    #Post to grading controller here!
                    if return_code==0:
                        #Post to controller
                        log.debug("Trying to post.")
                        util._http_post(
                            self.controller_session,
                            urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],'/grading_controller/submit/'),
                            content,
                            settings.REQUESTS_TIMEOUT,
                        )
                        log.debug("Successful post!")
                    else:
                        log.info("Error getting queue item or no queue items to get.")
                except Exception as err:
                    log.debug("Error getting submission: ".format(err))

                time.sleep(settings.TIME_BETWEEN_XQUEUE_PULLS)

    def login(self):
        '''
        Login to xqueue to pull submissions
        '''
        xqueue_login_url = urlparse.urljoin(settings.XQUEUE_INTERFACE['url'],'/xqueue/login/')
        controller_login_url = urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],'/grading_controller/login/')

        (xqueue_error,xqueue_msg)=util.login(
            self.xqueue_session,
            xqueue_login_url,
            settings.XQUEUE_INTERFACE['django_auth']['username'],
            settings.XQUEUE_INTERFACE['django_auth']['password'],
        )

        (controller_error,controller_msg)=util.login(
            self.controller_session,
            controller_login_url,
            settings.GRADING_CONTROLLER_INTERFACE['django_auth']['username'],
            settings.GRADING_CONTROLLER_INTERFACE['django_auth']['password'],
        )

        return max(controller_error,xqueue_error)

    def get_from_queue(self,queue_name):
        """
        Get a single submission from xqueue
        """
        try:
            response = util._http_get(self.xqueue_session,urlparse.urljoin(settings.XQUEUE_INTERFACE['url'],'/xqueue/get_submission/'),
                {'queue_name' : queue_name})
        except Exception as err:
            return 1,"Error getting response: {0}".format(err)

        return response