from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction

import requests
import urlparse
import time
import json
import logging
from statsd import statsd

import controller.util as util
from controller.models import Submission, SubmissionState
import controller.expire_submissions as expire_submissions
from staff_grading import staff_grading_util

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "<queue_name>"
    help = "Pull items from given queues and send to grading controller"

    def handle(self, *args, **options):
        flag = True
        log.debug("Starting check for expired subs.")
        while flag:
            try:
                transaction.commit_unless_managed()
                subs = Submission.objects.all()
                expire_submissions.reset_timed_out_submissions(subs)
                expired_list = expire_submissions.get_submissions_that_have_expired(subs)
                if len(expired_list) > 0:
                    success = expire_submissions.finalize_expired_submissions(expired_list)
                    statsd.increment("open_ended_assessment.grading_controller.remove_expired_subs",
                        tags=["success:{0}".format(success)])

                #Reset submissions marked ML to instructor if there are not enough instructor submissions to grade
                #This happens if the instructor skips too many submissions
                unique_locations=[x['location'] for x in list(Submission.objects.values('location').distinct())]
                for location in unique_locations:
                    subs_graded, subs_pending = staff_grading_util.count_submissions_graded_and_pending_instructor(location)
                    subs_pending_total= Submission.objects.filter(location=location, state=SubmissionState.waiting_to_be_graded)
                    if (subs_graded+subs_pending) < settings.MIN_TO_USE_ML and subs_pending_total.count() > subs_pending:
                        counter=0
                        for sub in subs_pending_total:
                            if sub.next_grader_type=="ML":
                                staff_grading_util.set_instructor_grading_item_back_to_ml(sub)
                                counter+=1
                            if (counter+subs_graded + subs_pending)> settings.MIN_TO_USE_ML:
                                break

            except Exception as err:
                    log.error("Could not get submissions to expire! Error: {0}".format(err))
                    statsd.increment("open_ended_assessment.grading_controller.remove_expired_subs",
                        tags=["success:Exception"])
                    transaction.commit_unless_managed()
                    time.sleep(settings.TIME_BETWEEN_EXPIRED_CHECKS)