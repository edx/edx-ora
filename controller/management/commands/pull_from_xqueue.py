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

        #Define sessions for logging into xqueue and controller
        self.xqueue_session=util.xqueue_login()
        self.controller_session=util.controller_login()
        #Login, then setup endless query loop
        flag=True

        while flag:
            #Loop through each queue that is given in arguments
            for queue_name in args:
                try:
                    #Get and parse queue objects
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