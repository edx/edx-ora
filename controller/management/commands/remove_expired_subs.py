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
import controller.expire_submissions as expire_submissions

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "<queue_name>"
    help = "Pull items from given queues and send to grading controller"

    def handle(self, *args, **options):
        flag = True
        log.debug("Starting check for expired subs.")
        while flag:
            try:
                subs = Submission.objects.all()
                expire_submissions.reset_timed_out_submissions(subs)
                expired_list = expire_submissions.get_submissions_that_have_expired(subs)
                if len(expired_list) > 0:
                    success = expire_submissions.finalize_expired_submissions(expired_list)
                    statsd.increment("open_ended_assessment.grading_controller.remove_expired_subs",
                        tags=["success:{0}".format(success)])
            except Exception as err:
                log.error("Could not get submissions to expire! Error: {0}".format(err))
                statsd.increment("open_ended_assessment.grading_controller.remove_expired_subs",
                    tags=["success:Exception"])

            time.sleep(settings.TIME_BETWEEN_EXPIRED_CHECKS)