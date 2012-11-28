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
from controller.models import SubmissionState, GraderStatus

from controller.models import Submission, Grader

from ml_grading.models import CreatedModel

sys.path.append(settings.ML_PATH)
import grade

log = logging.getLogger(__name__)

feedback_template = u"""

<section>
    <header>Feedback</header>
    <div class="shortform">
        <div class="result-output">
          <p>Score: {score}</p>
          <p>Number of potential problem areas identified: {problem_areas}</p>
        </div>
    </div>
    <div class="longform">
        <div class="result-output">
          <div class="topicality">
            Topicality: {topicality}
          </div>
          <div class="prompt_overlap">
            Prompt Overlap : {prompt_overlap}
          </div>
          <div class="spelling">
            Spelling: {spelling}
          </div>
          <div class="grammar">
            Grammar: {grammar}
          </div>
          <div class="markup-text">
            {markup_text}
          </div>
        </div>
    </div>
</section>

"""

error_template = u"""

<section>
    <div class="shortform">
        <div class="result-errors">
          There was an error with your submission.  Please contact course staff.
        </div>
    </div>
    <div class="longform">
        <div class="result-errors">
          {errors}
        </div>
    </div>
</section>

"""

class Command(BaseCommand):
    args = "None"
    help = "Poll grading controller and send items to be graded to ml"

    def handle(self, *args, **options):
        """
        Constant loop that polls grading controller
        """
        log.info(' [*] Polling grading controller...')
        self.controller_session = util.controller_login()

        flag = True

        while flag:
            try:
                success, content = self.get_item_from_controller()
                log.debug(content)
                #Grade and handle here
                if success:
                    sub = Submission.objects.get(id=content['submission_id'])
                    student_response = sub.student_response.encode('ascii', 'ignore')
                    grader_path = sub.location
                    results = grade.grade(grader_path, None,
                        student_response) #grader config is none for now, could be different later
                    formatted_feedback=add_results_to_template(results)

                    log.debug("ML Grader:  Success: {0} Errors: {1}".format(results['success'], results['errors']))
                    if results['success']:
                        status = GraderStatus.success
                    else:
                        status = GraderStatus.failure

                    grader_dict = {
                        'score': results['score'],
                        'feedback': formatted_feedback,
                        'status': status,
                        'grader_id': 1,
                        'grader_type': "ML",
                        'confidence': 1,
                        'submission_id': sub.id,
                    }

                    created, msg = util._http_post(
                        self.controller_session,
                        urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                            '/grading_controller/put_result/'),
                        grader_dict,
                        settings.REQUESTS_TIMEOUT,
                    )
                    log.debug("Got response of {0} from server, message: {1}".format(created, msg))
                else:
                    log.info("Error getting item from controller or no items to get.")

            except Exception as err:
                log.debug("Error getting submission: {0}".format(err))

            time.sleep(settings.TIME_BETWEEN_XQUEUE_PULLS)

    def get_item_from_controller(self):
        """
        Get a single submission from grading controller
        """
        try:
            success, content = util._http_get(
                self.controller_session,
                urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                    '/grading_controller/get_submission_ml/'),
            )
        except Exception as err:
            return False, "Error getting response: {0}".format(err)

        return success, content

def add_results_to_template(results):

    if results['success']:
        feedback=feedback_template.format(
            topicality=results['feedback']['topicality'],
            spelling=results['feedback']['spelling'],
            grammar=results['feedback']['grammar'],
            markup_text=results['feedback']['markup_text'],
            problem_areas=results['feedback']['problem_areas'],
            score=results['feedback']['score'],
            prompt_overlap=results['feedback']['prompt_overlap'],
        )
    else:
        feedback=error_template.format(
            errors=' '.join(results['errors'])
        )

    return feedback



