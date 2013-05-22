from django.conf import settings

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction

import time
import logging
from statsd import statsd
import random
from django import db
from controller.pull_from_xqueue_util import check_for_completed_submissions, post_one_submission_back_to_queue, pull_from_single_grading_queue

import controller.util as util
from controller.models import Submission
import controller.expire_submissions as expire_submissions
from metrics import generate_student_metrics
import gc
from statsd import statsd
import project_urls

from celery.task import periodic_task, task

log = logging.getLogger(__name__)

@periodic_task(run_every=settings.TIME_BETWEEN_EXPIRED_CHECKS)
def expire_submissions():
    flag = True
    log.debug("Starting check for expired subs.")
    #Sleep for some time to allow other processes to get ahead/behind
    time_sleep_value = random.uniform(0, 100)
    time.sleep(time_sleep_value)
    try:
        gc.collect()
        db.reset_queries()
        transaction.commit_unless_managed()
        subs = Submission.objects.all()

        #Comment out submission expiration for now.  Not really needed while testing.
        expire_submissions.reset_timed_out_submissions(subs)
        """
        expired_list = expire_submissions.get_submissions_that_have_expired(subs)
        if len(expired_list) > 0:
            success = expire_submissions.finalize_expired_submissions(expired_list)
            statsd.increment("open_ended_assessment.grading_controller.remove_expired_subs",
                tags=["success:{0}".format(success)])
        """
        try:
            expire_submissions.reset_in_subs_to_ml(subs)
            transaction.commit_unless_managed()
        except:
            log.exception("Could not reset in to ml!")
        try:
            expire_submissions.reset_subs_in_basic_check(subs)
            transaction.commit_unless_managed()
        except:
            log.exception("Could reset subs in basic check!")

        try:
            expire_submissions.reset_failed_subs_in_basic_check(subs)
            transaction.commit_unless_managed()
        except:
            log.exception("Could not reset failed subs in basic check!")

        try:
            expire_submissions.reset_ml_subs_to_in()
            transaction.commit_unless_managed()
        except:
            log.exception("Could not reset ml to in!")

        try:
            #See if duplicate peer grading items have been finished grading
            expire_submissions.add_in_duplicate_ids()
            transaction.commit_unless_managed()
        except:
            log.exception("Could not finish checking for duplicate ids!")

        try:
            #See if duplicate peer grading items have been finished grading
            expire_submissions.check_if_grading_finished_for_duplicates()
            transaction.commit_unless_managed()
        except:
            log.exception("Could not finish checking if duplicates are graded!")

        try:
            #Mark submissions as duplicates if needed
            expire_submissions.mark_student_duplicate_submissions()
            transaction.commit_unless_managed()
        except:
            log.exception("Could not mark subs as duplicate!")

        try:
            generate_student_metrics.regenerate_student_data()
            transaction.commit_unless_managed()
        except:
            log.exception("Could not regenerate student data!")

        try:
            #Remove old ML grading models
            expire_submissions.remove_old_model_files()
            transaction.commit_unless_managed()
        except:
            log.exception("Could not remove ml grading models!")

        log.debug("Finished looping through.")

    except Exception as err:
        log.exception("Could not get submissions to expire! Error: {0}".format(err))
        statsd.increment("open_ended_assessment.grading_controller.remove_expired_subs",
                         tags=["success:Exception"])
        transaction.commit_unless_managed()

@periodic_task(run_every=settings.TIME_BETWEEN_XQUEUE_PULLS)
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
    transaction.commit_unless_managed()

    submissions_to_post = check_for_completed_submissions()
    for submission in list(submissions_to_post):
        post_one_submission_back_to_queue(submission, xqueue_session)
    transaction.commit_unless_managed()
