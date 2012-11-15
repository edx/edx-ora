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

sys.path.append(settings.ML_PATH)
import create

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "None"
    help = "Poll grading controller and send items to be graded to ml"

    unique_locations=[x['location'] for x in Submission.objects.values('location').distinct()]
    for location in unique_locations:
        subs_graded_by_instructor=util.subs_graded_by_instructor(location)
        if len(subs_graded_by_instructor)>=settings.MIN_TO_USE_ML:
            if not create.check(location) or if len(subs_graded_by_instructor)%10==0:
                text=[i.student_response for i in subs_graded_by_instructor]
                scores=[i.get_last_grader().score for i in subs_graded_by_instructor]
                text,scores,prompt,model_path)
                prompt=subs_graded_by_instructor[0].prompt
                model_path=subs_graded_by_instructor[0].location
                results=create.create(text,scores,prompt,model_path)
                log.debug("Location: {0} Creation Status: {1} Errors: {2}".format(
                    model_path,
                    results['created'],
                    results['errors'],
                ))

    return "Finished looping through."

