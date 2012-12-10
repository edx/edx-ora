from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import timezone

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction

import time
import logging
import statsd

from controller.models import Submission

log = logging.getLogger(__name__)

class Command(NoArgsCommand):
    """
    "Poll grading controller and send items to be graded to ml"
    """

    def handle_noargs(self, **options):
        """
        Polls ml model creator to evaluate database, decide what needs to have a model created, and do so.
        Persistent loop.
        """
        flag= True

        while flag:
            unique_locations = [x['location'] for x in list(Submission.objects.values('location').distinct())]
            for location in unique_locations:
                self.handle_single_location(location)
            transaction.commit_unless_managed()

            log.debug("Finished looping through.")

            time.sleep(settings.TIME_BETWEEN_ML_CREATOR_CHECKS)














