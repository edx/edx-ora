import json
import random
import time
import urlparse
from django.conf import settings
from controller import util as util
from controller.models import Submission, SubmissionState
from controller.tasks import log
import project_urls
from statsd import statsd


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
        log.debug("Successful post back to xqueue! Success: {0} Message: {1} Xqueue Header: {2} Xqueue body: {3}".format(
            success,msg, xqueue_header, xqueue_body))
        submission.posted_results_back_to_queue = True
        submission.save()
    else:
        log.warning("Could not post back.  Error: {0}".format(msg))


def pull_from_single_grading_queue(queue_name,controller_session,xqueue_session,post_url, status_url):
    try:
        #Get and parse queue objects
        success, queue_length= get_queue_length(queue_name,xqueue_session)

        #Check to see if the grading_controller server is up so that we can post to it
        (is_alive, status_string) = util._http_get(controller_session, urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                                                                                        status_url))

        #Only post while we were able to get a queue length from the xqueue, there are items in the queue, and the grading controller is up for us to post to.
        while success and queue_length>0 and is_alive:
            #Sleep for some time to allow other pull_from_xqueue processes to get behind/ahead
            time_sleep_value = random.uniform(0, .1)
            time.sleep(time_sleep_value)

            success, queue_item = get_from_queue(queue_name, xqueue_session)
            success, content = util.parse_xobject(queue_item, queue_name)

            #Post to grading controller here!
            if  success:
                #Post to controller
                log.debug("Trying to post.")
                post_data = util._http_post(
                    controller_session,
                    urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                                     post_url),
                    content,
                    settings.REQUESTS_TIMEOUT,
                    )
                log.debug(post_data)
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