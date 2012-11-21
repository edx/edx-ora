from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

import requests
import urlparse
import time
import json
import logging

import controller.util as util
from controller.models import Submission

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

                #Check for new submissions on xqueue, and send to controller
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

                #Check for finalized results from controller, and post back to xqueue
                submissions_to_post=self.check_for_completed_submissions()
                for submission in list(submissions_to_post):
                    xqueue_header,xqueue_body=util.create_xqueue_header_and_body(submission)
                    (success,msg) = util.post_results_to_xqueue(
                        self.xqueue_session,
                        json.dumps(xqueue_header),
                        json.dumps(xqueue_body),
                    )
                    if success==0:
                        log.debug("Successful post back to xqueue!")
                        submission.posted_results_back_to_queue=True
                        submission.save()
                    else:
                        log.debug("Could not post back.  Error: {0}".format(msg))

                time.sleep(settings.TIME_BETWEEN_XQUEUE_PULLS)

    def check_for_completed_submissions(self):
        submissions_to_post=Submission.objects.filter(
            state="F",
            posted_results_back_to_queue=False,
        )
        return submissions_to_post


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