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
from controller.models import GraderStatus, SubmissionState
import project_urls

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
        self.xqueue_session = util.xqueue_login()
        self.controller_session = util.controller_login()
        #Login, then setup endless query loop
        flag = True

        while flag:
            #Loop through each queue that is given in arguments
            for queue_name in args:
                #Check for new submissions on xqueue, and send to controller
                try:
                    #Get and parse queue objects
                    success, queue_length= self.get_queue_length(queue_name)
                    while success and queue_length>0:
                        success, queue_item = self.get_from_queue(queue_name)
                        success, content = util.parse_xobject(queue_item, queue_name)
                        log.debug(content)

                        #Post to grading controller here!
                        if  success:
                            #Post to controller
                            log.debug("Trying to post.")
                            util._http_post(
                                self.controller_session,
                                urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                                    project_urls.ControllerURLs.submit),
                                content,
                                settings.REQUESTS_TIMEOUT,
                            )
                            log.debug("Successful post!")
                        else:
                            log.info("Error getting queue item or no queue items to get.")

                        success, queue_length= self.get_queue_length(queue_name)
                except Exception as err:
                    log.debug("Error getting submission: ".format(err))

                #Check for finalized results from controller, and post back to xqueue
                submissions_to_post = self.check_for_completed_submissions()
                for submission in list(submissions_to_post):
                    xqueue_header, xqueue_body = util.create_xqueue_header_and_body(submission)
                    (success, msg) = util.post_results_to_xqueue(
                        self.xqueue_session,
                        json.dumps(xqueue_header),
                        json.dumps(xqueue_body),
                    )
                    if success:
                        log.debug("Successful post back to xqueue!")
                        submission.posted_results_back_to_queue = True
                        submission.save()
                    else:
                        log.warning("Could not post back.  Error: {0}".format(msg))

                time.sleep(settings.TIME_BETWEEN_XQUEUE_PULLS)

    def check_for_completed_submissions(self):
        submissions_to_post = Submission.objects.filter(
            state=SubmissionState.finished,
            posted_results_back_to_queue=False,
        )
        return submissions_to_post


    def get_from_queue(self, queue_name):
        """
        Get a single submission from xqueue
        """
        try:
            success, response = util._http_get(self.xqueue_session,
                urlparse.urljoin(settings.XQUEUE_INTERFACE['url'], project_urls.XqueueURLs.get_submission),
                {'queue_name': queue_name})
        except Exception as err:
            return False, "Error getting response: {0}".format(err)

        return success, response

    def get_queue_length(self,queue_name):
            """
            Returns the length of the queue
            """
            try:
                success, response = util._http_get(self.xqueue_session,
                    urlparse.urljoin(settings.XQUEUE_INTERFACE['url'], project_urls.XqueueURLs.get_queuelen),
                    {'queue_name': queue_name})

                if not success:
                    return False,"Invalid return code in reply"

            except Exception as e:
                log.critical("Unable to get queue length: {0}".format(e))
                return False, "Unable to get queue length."

            return True, response