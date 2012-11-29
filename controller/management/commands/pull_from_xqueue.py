#Tests for this module are in tests.py in the controller app

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

import requests
import urlparse
import time
import json
import logging
from statsd import statsd

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
                pull_from_single_queue(queue_name,self.controller_session,self.xqueue_session)

                #Check for finalized results from controller, and post back to xqueue
                submissions_to_post = check_for_completed_submissions()
                for submission in list(submissions_to_post):
                    post_one_submission_back_to_queue(submission, self.xqueue_session)

                time.sleep(settings.TIME_BETWEEN_XQUEUE_PULLS)

def post_one_submission_back_to_queue(submission,xqueue_session):
    xqueue_header, xqueue_body = util.create_xqueue_header_and_body(submission)
    (success, msg) = util.post_results_to_xqueue(
        xqueue_session,
        json.dumps(xqueue_header),
        json.dumps(xqueue_body),
    )

    statsd.increment("open_ended_assessment.grading_controller.post_to_xqueue",
        tags=["success:{0}".format(success)])

    if success:
        log.debug("Successful post back to xqueue!")
        submission.posted_results_back_to_queue = True
        submission.save()
    else:
        log.warning("Could not post back.  Error: {0}".format(msg))

def pull_from_single_queue(queue_name,controller_session,xqueue_session):
    try:
        #Get and parse queue objects
        success, queue_length= get_queue_length(queue_name,xqueue_session)
        while success and queue_length>0:
            success, queue_item = get_from_queue(queue_name, xqueue_session)
            success, content = util.parse_xobject(queue_item, queue_name)
            log.debug(content)

            #Post to grading controller here!
            if  success:
                #Post to controller
                log.debug("Trying to post.")
                util._http_post(
                    controller_session,
                    urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                        project_urls.ControllerURLs.submit),
                    content,
                    settings.REQUESTS_TIMEOUT,
                )
                log.debug("Successful post!")
                statsd.increment("open_ended_assessment.grading_controller.pull_from_xqueue",
                    tags=["success:True", "queue_name:{0}".format(queue_name)])
            else:
                log.info("Error getting queue item or no queue items to get.")
                statsd.increment("open_ended_assessment.grading_controller.pull_from_xqueue",
                    tags=["success:False", "queue_name:{0}".format(queue_name)])

            success, queue_length= get_queue_length(queue_name, xqueue_session)
    except Exception as err:
        log.debug("Error getting submission: {0}".format(err))
        statsd.increment("open_ended_assessment.grading_controller.pull_from_xqueue",
            tags=["success:Exception", "queue_name:{0}".format(queue_name)])


def check_for_completed_submissions():
    submissions_to_post = Submission.objects.filter(
        state=SubmissionState.finished,
        posted_results_back_to_queue=False,
    )
    return submissions_to_post


def get_from_queue(queue_name,xqueue_session):
    """
    Get a single submission from xqueue
    """
    try:
        success, response = util._http_get(xqueue_session,
            urlparse.urljoin(settings.XQUEUE_INTERFACE['url'], project_urls.XqueueURLs.get_submission),
            {'queue_name': queue_name})
    except Exception as err:
        return False, "Error getting response: {0}".format(err)

    return success, response

def get_queue_length(queue_name,xqueue_session):
        """
        Returns the length of the queue
        """
        try:
            success, response = util._http_get(xqueue_session,
                urlparse.urljoin(settings.XQUEUE_INTERFACE['url'], project_urls.XqueueURLs.get_queuelen),
                {'queue_name': queue_name})

            if not success:
                return False,"Invalid return code in reply"

        except Exception as e:
            log.critical("Unable to get queue length: {0}".format(e))
            return False, "Unable to get queue length."

        return True, response