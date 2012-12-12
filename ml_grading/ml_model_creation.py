from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import timezone

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction

import requests
import urlparse
import time
import json
import logging
import sys
from statsd import statsd
import pickle

from controller.models import Submission
from staff_grading import staff_grading_util

from ml_grading.models import CreatedModel
import ml_grading.ml_grading_util as ml_grading_util

sys.path.append(settings.ML_PATH)
import create

log = logging.getLogger(__name__)

def handle_single_location(location):
    try:
        transaction.commit_unless_managed()
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
            transaction.commit_unless_managed()
            success, latest_created_model=ml_grading_util.get_latest_created_model(location)

            if success:
                sub_count_diff=graded_sub_count-latest_created_model.number_of_essays
            else:
                sub_count_diff = graded_sub_count

            #Retrain if no model exists, or every 10 graded essays.
            if not success or graded_sub_count % 10 == 0 or sub_count_diff>=10:
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

                #Add in needed stuff that ml creator does not pass back
                results.update({'text' : text, 'score' : scores, 'model_path' : full_model_path,
                                'relative_model_path' : relative_model_path, 'prompt' : prompt})

                #Try to create model if ml model creator was successful
                if results['success']:
                    try:
                        success, s3_public_url = save_model_file(results,settings.USE_S3_TO_STORE_MODELS)
                        results.update({'s3_public_url' : s3_public_url, 'success' : success})
                        if not success:
                            results['errors'].append("Could not save model.")
                    except:
                        results['errors'].append("Could not save model.")
                        results['s3_public_url'] = ""
                        log.exception("Problem saving ML model.")

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
                    's3_public_url' : results['s3_public_url'],
                    'save_to_s3' : settings.USE_S3_TO_STORE_MODELS,
                    's3_bucketname' : str(settings.S3_BUCKETNAME),
                    }

                transaction.commit_unless_managed()
                success, id = ml_grading_util.save_created_model(created_model_dict)

                if not success:
                    log.error("ModelCreator creation failed.  Error: {0}".format(id))
                    statsd.increment("open_ended_assessment.grading_controller.call_ml_creator",
                        tags=["success:False", "location:{0}".format(location)])

                log.debug("Location: {0} Creation Status: {1} Errors: {2}".format(
                    full_model_path,
                    results['success'],
                    results['errors'],
                ))
                statsd.increment("open_ended_assessment.grading_controller.call_ml_creator",
                    tags=["success:{0}".format(results['success']), "location:{0}".format(location)])
    except:
        log.exception("Problem creating model for location {0}".format(location))
        statsd.increment("open_ended_assessment.grading_controller.call_ml_creator",
            tags=["success:Exception", "location:{0}".format(location)])

def save_model_file(results, save_to_s3):
    success=False
    if save_to_s3:
        pickled_model=ml_grading_util.get_pickle_data(results['prompt'], results['feature_ext'],
            results['classifier'], results['text'],
            results['score'])
        success, s3_public_url=ml_grading_util.upload_to_s3(pickled_model, results['relative_model_path'], str(settings.S3_BUCKETNAME))

    if success:
        return True, s3_public_url

    try:
        ml_grading_util.dump_model_to_file(results['prompt'], results['feature_ext'],
            results['classifier'], results['text'],results['score'],results['model_path'])
        return True, "Saved model to file."
    except:
        return False, "Could not save model."