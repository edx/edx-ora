from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

import requests
import urlparse
import time
import json
import logging
import sys

from controller.models import Submission
import controller.util as util

sys.path.append(settings.ML_PATH)
import create

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "None"
    help = "Poll grading controller and send items to be graded to ml"

    def handle(self, *args, **options):
        """
        Calls ml model creator to evaluate database, decide what needs to have a model created, and do so.
        """
        unique_locations=[x['location'] for x in list(Submission.objects.values('location').distinct())]
        for location in unique_locations:
            subs_graded_by_instructor=util.finished_submissions_graded_by_instructor(location)
            log.debug("Checking location {0} to see if essay count {1} greater than min {2}".format(
                location,
                subs_graded_by_instructor.count(),
                settings.MIN_TO_USE_ML,
            ))
            if len(subs_graded_by_instructor)>=settings.MIN_TO_USE_ML:
                if not create.check(location) or len(subs_graded_by_instructor)%10==0:
                    text=[str(i['student_response'].encode('ascii', 'ignore')) for i in list(subs_graded_by_instructor.values('student_response'))]
                    scores=[i.get_last_grader().score for i in list(subs_graded_by_instructor)]
                    prompt=str(subs_graded_by_instructor[0].prompt.encode('ascii', 'ignore'))
                    model_path=subs_graded_by_instructor[0].location
                    results=create.create(text,scores,prompt,model_path)
                    log.debug("Location: {0} Creation Status: {1} Errors: {2}".format(
                        model_path,
                        results['created'],
                        results['errors'],
                    ))

        return "Finished looping through."

