from django.conf import settings

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction

import time
import logging
from statsd import statsd
import random
from django import db

from . import util
from .models import Submission, SubmissionState
from . import expire_submissions
from metrics import generate_student_metrics
import gc
from statsd import statsd
import project_urls
from . single_instance_task import single_instance_task

from celery.task import periodic_task, task

import json
import urlparse

log = logging.getLogger(__name__)

@periodic_task(run_every=settings.TIME_BETWEEN_EXPIRED_CHECKS)
@single_instance_task(60*10)
@transaction.commit_manually
def expire_submissions_task():
    flag = True
    log.debug("Starting check for expired subs.")
    #Sleep for some time to allow other processes to get ahead/behind
    time_sleep_value = random.uniform(0, 100)
    time.sleep(time_sleep_value)
    try:
        gc.collect()
        db.reset_queries()
        transaction.commit()

        #Comment out submission expiration for now.  Not really needed while testing.
        expire_submissions.reset_timed_out_submissions()
        """
        expired_list = expire_submissions.get_submissions_that_have_expired(subs)
        if len(expired_list) > 0:
            success = grader_util.finalize_expired_submissions(expired_list)
            statsd.increment("open_ended_assessment.grading_controller.remove_expired_subs",
                tags=["success:{0}".format(success)])
        """
        try:
            expire_submissions.reset_in_subs_to_ml()
            transaction.commit()
        except Exception:
            log.exception("Could not reset in to ml!")
        try:
            expire_submissions.reset_subs_in_basic_check()
            transaction.commit()
        except Exception:
            log.exception("Could reset subs in basic check!")

        try:
            expire_submissions.reset_failed_subs_in_basic_check()
            transaction.commit()
        except Exception:
            log.exception("Could not reset failed subs in basic check!")

        try:
            expire_submissions.reset_ml_subs_to_in()
            transaction.commit()
        except Exception:
            log.exception("Could not reset ml to in!")

        try:
            #See if duplicate peer grading items have been finished grading
            expire_submissions.add_in_duplicate_ids()
            transaction.commit()
        except Exception:
            log.exception("Could not finish checking for duplicate ids!")

        try:
            #See if duplicate peer grading items have been finished grading
            expire_submissions.check_if_grading_finished_for_duplicates()
            transaction.commit()
        except Exception:
            log.exception("Could not finish checking if duplicates are graded!")

        try:
            #Mark submissions as duplicates if needed
            expire_submissions.mark_student_duplicate_submissions()
            transaction.commit()
        except Exception:
            log.exception("Could not mark subs as duplicate!")

        try:
            generate_student_metrics.regenerate_student_data()
            transaction.commit()
        except Exception:
            log.exception("Could not regenerate student data!")

        try:
            #Remove old ML grading models
            expire_submissions.remove_old_model_files()
            transaction.commit()
        except Exception:
            log.exception("Could not remove ml grading models!")

        log.debug("Finished looping through.")

    except Exception as err:
        log.exception("Could not get submissions to expire! Error: {0}".format(err))
        statsd.increment("open_ended_assessment.grading_controller.remove_expired_subs",
                         tags=["success:Exception"])
    util.log_connection_data()
    transaction.commit()

@periodic_task(run_every=settings.TIME_BETWEEN_XQUEUE_PULLS)
@single_instance_task(60*10)
@transaction.commit_manually
def pull_from_xqueue():
    """
    Constant loop that pulls from queue and posts to grading controller
    """
    log.info(' [*] Pulling from xqueues...')

    #Define sessions for logging into xqueue and controller
    xqueue_session = util.xqueue_login()
    controller_session = util.controller_login()

    #Sleep for some time to allow other pull_from_xqueue processes to get behind/ahead
    time_sleep_value = random.uniform(0, .1)
    time.sleep(time_sleep_value)

    #Loop through each queue that is given in arguments
    for queue_name in settings.GRADING_QUEUES_TO_PULL_FROM:
        #Check for new submissions on xqueue, and send to controller
        pull_from_single_grading_queue(queue_name,controller_session,xqueue_session, project_urls.ControllerURLs.submit, project_urls.ControllerURLs.status)

    #Loop through message queues to see if there are any messages
    for queue_name in settings.MESSAGE_QUEUES_TO_PULL_FROM:
        pull_from_single_grading_queue(queue_name,controller_session,xqueue_session, project_urls.ControllerURLs.submit_message, project_urls.ControllerURLs.status)

    #Check for finalized results from controller, and post back to xqueue
    transaction.commit()

    submissions_to_post = check_for_completed_submissions()
    for submission in list(submissions_to_post):
        post_one_submission_back_to_queue(submission, xqueue_session)

    # Log out of the controller session, which deletes the database row.
    util.controller_logout(controller_session)
    transaction.commit()


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
                post_data = util._http_post(
                    controller_session,
                    urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                                     post_url),
                    content,
                    settings.REQUESTS_TIMEOUT,
                    )
                statsd.increment("open_ended_assessment.grading_controller.pull_from_xqueue",
                                 tags=["success:True", "queue_name:{0}".format(queue_name)])
            else:
                log.error("Error getting queue item or no queue items to get.")
                statsd.increment("open_ended_assessment.grading_controller.pull_from_xqueue",
                                 tags=["success:False", "queue_name:{0}".format(queue_name)])

            success, queue_length= get_queue_length(queue_name, xqueue_session)
    except Exception:
        log.exception("Error getting submission")
        statsd.increment("open_ended_assessment.grading_controller.pull_from_xqueue",
                         tags=["success:Exception", "queue_name:{0}".format(queue_name)])
