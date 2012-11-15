from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

import requests
import urlparse
import time
import json
import logging
import sys
from ConfigParser import SafeConfigParser

from controller.models import Submission,Grader

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "<filename>"
    help = "Poll grading controller and send items to be graded to ml"


    def handle(self, *args, **options):
        """
        Read from file
        """

        parser = SafeConfigParser()
        parser.read(args[0])

        location = parser.get('ImportData', 'location')
        course_id = parser.get('ImportData', 'course_id')
        problem_id = parser.get('ImportData', 'problem_id')
        prompt = parser.get('ImportData', 'prompt')
        essay_file = parser.get('ImportData', 'essay_file')

        score,text=[],[]
        combined_raw=open(essay_file).read()
        raw_lines=combined_raw.splitlines()
        for row in xrange(1,len(raw_lines)):
            score1,text1 = raw_lines[row].strip().split("\t")
            text.append(text1)
            score.append(int(score1))


        log.info(' [*] Pulling from xqueues...')
        self.xqueue_session=requests.session()
        self.controller_session=requests.session()

        flag=True
        error = self.login()

        while flag:
            for queue_name in args:
                try:
                    response_code,queue_item=self.get_from_queue(queue_name)
                    return_code,content=util.parse_xobject(queue_item,queue_name)
                    log.debug(content)

                    #Post to grading controller here!
                    if return_code==0:
                        #Post to controller
                        log.debug("Trying to post.")
                        util._http_post(
                            self.controller_session,
                            urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],'/grading_controller/submit/'),
                            content,settings.REQUESTS_TIMEOUT,
                        )
                        log.debug("Successful post!")
                    else:
                        log.info("Error getting queue item or no queue items to get.")
                except Exception as err:
                    log.debug("Error getting submission: ".format(err))

                time.sleep(settings.TIME_BETWEEN_XQUEUE_PULLS)
