from django.conf import settings
from django.core.management.base import NoArgsCommand

from django.utils import timezone
import requests
import urlparse
import time
import json
import logging
import sys
import os
from path import path
import logging
import project_urls
from statsd import statsd

log=logging.getLogger(__name__)

import controller.util as util
from controller.models import SubmissionState, GraderStatus

from controller.models import Submission, Grader

from ml_grading.models import CreatedModel

import ml_grading.ml_grading_util as ml_grading_util

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
                success, pending_count=self.get_pending_length_from_controller()
                log.debug("Success : {0}, Pending Count: {1}".format(success, pending_count))
                while success and pending_count>0:
                    self.handle_single_item()

                    #Refresh the pending submission count
                    success, pending_count=self.get_pending_length_from_controller()

            except Exception as err:
                log.debug("Error getting submission: {0}".format(err))
                statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
                    tags=["success:Exception"])

            #TODO: add in some logic that figures out how many submissions are left to grade and loops based on that
            time.sleep(settings.TIME_BETWEEN_ML_GRADER_CHECKS)

    def handle_single_item(self):
        success, content = self.get_item_from_controller()
        log.debug(content)
        #Grade and handle here
        if success:
            sub = Submission.objects.get(id=content['submission_id'])

            #strip out unicode and other characters in student response
            #Needed, or grader may potentially fail
            #TODO: Handle unicode in student responses properly
            student_response = sub.student_response.encode('ascii', 'ignore')

            #Get the latest created model for the given location
            success, created_model=ml_grading_util.get_latest_created_model(sub.location)

            if not success:
                log.debug("Could not identify a valid created model!")
                results={'score' : 0}
                formatted_feedback="error"
                status=GraderStatus.failure
                statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
                    tags=["success:False"])

            else:

                #Create grader path from location in submission
                grader_path = os.path.join(settings.ML_MODEL_PATH,created_model.model_relative_path)

                results = grade.grade(grader_path, None,
                    student_response) #grader config is none for now, could be different later

                #If the above, try using the full path in the created_model object
                if not results['success']:
                    grader_path=created_model.model_full_path
                    results = grade.grade(grader_path, None,
                        student_response) #grader config is none for now, could be different later

                #Add feedback/errors to appropriate template
                formatted_feedback=add_results_to_template(results)

                log.debug("ML Grader:  Success: {0} Errors: {1}".format(results['success'], results['errors']))
                statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
                    tags=["success:{0}".format(results['success']), 'location:{0}'.format(sub.location)])

                #Set grader status according to success/fail
                if results['success']:
                    status = GraderStatus.success
                else:
                    status = GraderStatus.failure

            grader_dict = {
                'score': results['score'],
                'feedback': json.dumps(results['feedback']),
                'status': status,
                'grader_id': 1,
                'grader_type': "ML",
                'confidence': 1,
                'submission_id': sub.id,
                'errors' : ' ' .join(results['errors']),
                }


            #Create grader object in controller by posting back results
            created, msg = util._http_post(
                self.controller_session,
                urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                    project_urls.ControllerURLs.put_result),
                grader_dict,
                settings.REQUESTS_TIMEOUT,
            )
            log.debug("Got response of {0} from server, message: {1}".format(created, msg))
        else:
            log.info("Error getting item from controller or no items to get.")
            statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
                tags=["success:False"])


    def get_item_from_controller(self):
        """
        Get a single submission from grading controller
        """
        success,content=self.query_controller(project_urls.ControllerURLs.get_submission_ml)

        return success, content

    def get_pending_length_from_controller(self):
        """
        Get the number of pending submissions from the controller
        """
        success,content=self.query_controller(project_urls.ControllerURLs.get_pending_count, data={'grader_type' : "ML"})
        return success, content['to_be_graded_count']

    def query_controller(self,end_path,data={}):
        """
        Get a single submission from grading controller
        """
        try:
            success, content = util._http_get(
                self.controller_session,
                urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                    end_path),
                data=data,
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

