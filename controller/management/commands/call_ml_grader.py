from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

import requests
import urlparse
import time
import json
import logging
import sys

import controller.util as util

sys.path.append(settings.ML_PATH)
import grade

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "None"
    help = "Poll grading controller and send items to be graded to ml"

    def handle(self, *args, **options):
        """
        Constant loop that polls grading controller
        """
        log.info(' [*] Polling grading controller...')
        self.controller_session=requests.session()

        flag=True
        error = self.login()

        while flag:
            try:
                response_code,content=self.get_item_from_controller()
                log.debug(content)

                #Grade and handle here
                if response_code==0:
                    #Post to controller
                    log.debug("All ok.")
                else:
                    log.info("Error getting item from controller or no items to get.")
            except Exception as err:
                log.debug("Error getting submission: ".format(err))

            time.sleep(settings.TIME_BETWEEN_XQUEUE_PULLS)

    def login(self):
        controller_login_url = urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],'/grading_controller/login/')

        (controller_error,controller_msg)=util.login(
            self.controller_session,
            controller_login_url,
            settings.GRADING_CONTROLLER_INTERFACE['django_auth']['username'],
            settings.GRADING_CONTROLLER_INTERFACE['django_auth']['password'],
        )

        return controller_error

    def get_item_from_controller(self):
        """
        Get a single submission from grading controller
        """
        try:
            response = util._http_get(
                self.controller_session,
                urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],'/grading_controller/get_submission_ml/'),
            )
        except Exception as err:
            return False,"Error getting response: {0}".format(err)

        return response

