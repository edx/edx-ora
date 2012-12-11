from django.conf import settings
from django.core.management.base import NoArgsCommand

from django.db import transaction

import time
import logging
from statsd import statsd

log=logging.getLogger(__name__)

import controller.util as util
from ml_grading import ml_grader

log = logging.getLogger(__name__)

RESULT_FAILURE_DICT={'success' : False, 'errors' : 'Errors!', 'confidence' : 0, 'feedback' : ""}

class Command(NoArgsCommand):
    """
    "Poll grading controller and send items to be graded to ml"
    """

    def __init__(self):
        self.controller_session = util.controller_login()

    def handle_noargs(self, **options):
        """
        Constant loop that polls grading controller
        """
        log.info(' [*] Polling grading controller...')

        flag = True

        while flag:
            try:
                #See if there are any submissions waiting
                success, pending_count=ml_grader.get_pending_length_from_controller(self.controller_session)
                log.debug("Success : {0}, Pending Count: {1}".format(success, pending_count))
                while success and pending_count>0:
                    sub_get_success = ml_grader.handle_single_item(self.controller_session)
                    if not sub_get_success:
                        log.info("Could not get a submission even though pending count is above 0."
                                 "Could be an error, or could just be that instructor has "
                                 "skipped submissions.")
                        break
                    #Refresh the pending submission count
                    success, pending_count=ml_grader.get_pending_length_from_controller(self.controller_session)
                transaction.commit_unless_managed()

            except Exception as err:
                log.exception("Error getting submission: {0}".format(err))
                statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
                    tags=["success:Exception"])

            #TODO: add in some logic that figures out how many submissions are left to grade and loops based on that
            time.sleep(settings.TIME_BETWEEN_ML_GRADER_CHECKS)



