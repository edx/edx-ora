from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import timezone

import requests
import urlparse
import time
import json
import logging
import sys
from statsd import statsd

from controller.models import Submission
from staff_grading import staff_grading_util

from ml_grading.models import CreatedModel
import ml_grading.ml_grading_util as ml_grading_util

sys.path.append(settings.ML_PATH)
import create

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

            log.debug("Finished looping through.")

            time.sleep(settings.TIME_BETWEEN_ML_CREATOR_CHECKS)

    def handle_single_location(self,location):
        try:
            subs_graded_by_instructor = staff_grading_util.finished_submissions_graded_by_instructor(location)
            log.debug("Checking location {0} to see if essay count {1} greater than min {2}".format(
                location,
                subs_graded_by_instructor.count(),
                settings.MIN_TO_USE_ML,
            ))
            graded_sub_count=subs_graded_by_instructor.count()

            #check to see if there are enough instructor graded essays for location
            if graded_sub_count >= settings.MIN_TO_USE_ML:

                #Get paths to ml model from database
                relative_model_path, full_model_path= ml_grading_util.get_model_path(location)
                #Get last created model for given location
                success, latest_created_model=ml_grading_util.get_latest_created_model(location)

                #Retrain if no model exists, or every 10 graded essays.
                if not success or graded_sub_count % 10 == 0:
                    combined_data=list(subs_graded_by_instructor.values('student_response', 'id'))
                    text = [str(i['student_response'].encode('ascii', 'ignore')) for i in combined_data]
                    ids=[i['id'] for i in combined_data]
                    #TODO: Make queries more efficient
                    scores = [i.get_last_grader().score for i in list(subs_graded_by_instructor)]

                    #Get the first graded submission, so that we can extract metadata like rubric, etc, from it
                    first_sub=subs_graded_by_instructor[0]

                    prompt = str(first_sub.prompt.encode('ascii', 'ignore'))
                    rubric = str(first_sub.rubric.encode('ascii', 'ignore'))

                    results = create.create(text, scores, prompt, full_model_path)

                    created_model_dict={
                        'max_score' : first_sub.max_score,
                        'prompt' : prompt,
                        'rubric' : rubric,
                        'location' : location,
                        'course_id' : first_sub.course_id,
                        'submission_ids_used' : json.dumps(ids),
                        'problem_id' :  first_sub.problem_id,
                        'model_relative_path' : relative_model_path,
                        'model_full_path' : full_model_path,
                        'number_of_essays' : graded_sub_count,
                        'cv_kappa' : results['cv_kappa'],
                        'cv_mean_absolute_error' : results['cv_mean_absolute_error'],
                        'creation_succeeded': results['success'],
                        }

                    success, id = ml_grading_util.save_created_model(created_model_dict)

                    if not success:
                        log.error("ModelCreator creation failed.  Error: {0}".format(id))
                        statsd.increment("open_ended_assessment.grading_controller.call_ml_creator",
                            tags=["success:False"])

                    log.debug("Location: {0} Creation Status: {1} Errors: {2}".format(
                        full_model_path,
                        results['success'],
                        results['errors'],
                    ))
                    statsd.increment("open_ended_assessment.grading_controller.call_ml_creator",
                        tags=["success:{0}".format(results['success'])])
        except:
            log.error("Problem creating model for location {0}".format(location))
            statsd.increment("open_ended_assessment.grading_controller.call_ml_creator",
                tags=["success:Exception"])






