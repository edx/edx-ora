from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import timezone

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction
from django import db

import time
import logging
from statsd import statsd
import random

from controller.models import Submission
from . import ml_model_creation
import gc
from controller import util
from . import ml_grader
from controller.single_instance_task import single_instance_task

RESULT_FAILURE_DICT={'success' : False, 'errors' : 'Errors!', 'confidence' : 0, 'feedback' : ""}

from celery.task import periodic_task

log = logging.getLogger(__name__)

@periodic_task(run_every=settings.TIME_BETWEEN_ML_CREATOR_CHECKS)
@single_instance_task(60*10)
@transaction.commit_manually
def create_ml_models():
    """
    Polls ml model creator to evaluate database, decide what needs to have a model created, and do so.
    """

    unique_locations = [x['location'] for x in list(Submission.objects.values('location').distinct())]
    for location in unique_locations:
        gc.collect()
        ml_model_creation.handle_single_location(location)

    db.reset_queries()
    transaction.commit()

@periodic_task(run_every=settings.TIME_BETWEEN_ML_GRADER_CHECKS)
@single_instance_task(30*60)
@transaction.commit_manually
def grade_essays():
    """
    Polls grading controller for essays to grade and tries to grade them.
    """
    controller_session = util.controller_login()
    log.info(' [*] Polling grading controller...')

    try:
        #See if there are any submissions waiting
        success, pending_count=ml_grader.get_pending_length_from_controller(controller_session)
        while success and pending_count>0:
            success = ml_grader.handle_single_item(controller_session)
        transaction.commit()

    except Exception as err:
        log.exception("Error getting submission: {0}".format(err))
        statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
                         tags=["success:Exception"])

    db.reset_queries()

    # Log out of the controller session, which deletes the database row.
    util.controller_logout(controller_session)
    transaction.commit()



