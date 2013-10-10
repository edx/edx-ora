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

from controller import util

from controller.models import Submission
from staff_grading import staff_grading_util
from controller.control_util import SubmissionControl

from ml_grading.models import CreatedModel
import ml_grading.ml_grading_util as ml_grading_util

from ease import create

import controller.rubric_functions

import gc

log = logging.getLogger(__name__)

def handle_single_location(location):
    try:
        transaction.commit()
        gc.collect()
        sl = staff_grading_util.StaffLocation(location)
        control = SubmissionControl(sl.latest_submission())

        subs_graded_by_instructor = sl.graded()
        log.info("Checking location {0} to see if essay count {1} greater than min {2}".format(
            location,
            subs_graded_by_instructor.count(),
            control.minimum_to_use_ai,
        ))
        graded_sub_count=subs_graded_by_instructor.count()

        #check to see if there are enough instructor graded essays for location
        if graded_sub_count >= control.minimum_to_use_ai:

            location_suffixes=ml_grading_util.generate_rubric_location_suffixes(subs_graded_by_instructor, grading=False)

            if settings.MAX_TO_USE_ML<graded_sub_count:
                graded_sub_count = settings.MAX_TO_USE_ML

            subs_graded_by_instructor  = subs_graded_by_instructor[:settings.MAX_TO_USE_ML]

            sub_rubric_scores=[]
            if len(location_suffixes)>0:
                for sub in subs_graded_by_instructor:
                    success, scores = controller.rubric_functions.get_submission_rubric_instructor_scores(sub)
                    sub_rubric_scores.append(scores)

            for m in xrange(0,len(location_suffixes)):
                log.info("Currently on location {0}.  Greater than zero is a rubric item.".format(m))
                suffix=location_suffixes[m]
                #Get paths to ml model from database
                relative_model_path, full_model_path= ml_grading_util.get_model_path(location + suffix)
                #Get last created model for given location
                transaction.commit()
                success, latest_created_model=ml_grading_util.get_latest_created_model(location + suffix)

                if success:
                    sub_count_diff=graded_sub_count-latest_created_model.number_of_essays
                else:
                    sub_count_diff = graded_sub_count

                #Retrain if no model exists, or every 5 graded essays.
                if not success or sub_count_diff>=5:

                    text = [str(i.student_response.encode('ascii', 'ignore')) for i in subs_graded_by_instructor]
                    ids=[i.id for i in subs_graded_by_instructor]

                    #TODO: Make queries more efficient
                    #This is for the basic overall score
                    if m==0:
                        scores = [z.get_last_grader().score for z in list(subs_graded_by_instructor)]
                    else:
                        scores=[z[m-1] for z in sub_rubric_scores]

                    #Get the first graded submission, so that we can extract metadata like rubric, etc, from it
                    first_sub=subs_graded_by_instructor[0]

                    prompt = str(first_sub.prompt.encode('ascii', 'ignore'))
                    rubric = str(first_sub.rubric.encode('ascii', 'ignore'))

                    transaction.commit()

                    #Checks to see if another model creator process has started amodel for this location
                    success, model_started, created_model = ml_grading_util.check_if_model_started(location + suffix)

                    #Checks to see if model was started a long time ago, and removes and retries if it was.
                    if model_started:
                        now = timezone.now()
                        second_difference = (now - created_model.date_modified).total_seconds()
                        if second_difference > settings.TIME_BEFORE_REMOVING_STARTED_MODEL:
                            log.error("Model for location {0} started over {1} seconds ago, removing and re-attempting.".format(
                                location + suffix, settings.TIME_BEFORE_REMOVING_STARTED_MODEL))
                            created_model.delete()
                            model_started = False

                    if not model_started:
                        created_model_dict_initial={
                            'max_score' : first_sub.max_score,
                            'prompt' : prompt,
                            'rubric' : rubric,
                            'location' : location + suffix,
                            'course_id' : first_sub.course_id,
                            'submission_ids_used' : json.dumps(ids),
                            'problem_id' :  first_sub.problem_id,
                            'model_relative_path' : relative_model_path,
                            'model_full_path' : full_model_path,
                            'number_of_essays' : graded_sub_count,
                            'creation_succeeded': False,
                            'creation_started' : True,
                            'creation_finished' : False,
                            }
                        transaction.commit()
                        success, initial_id = ml_grading_util.save_created_model(created_model_dict_initial)
                        transaction.commit()

                        results = create.create(text, scores, prompt)

                        scores = [int(score_item) for score_item in scores]
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
                            except Exception:
                                results['errors'].append("Could not save model.")
                                results['s3_public_url'] = ""
                                log.exception("Problem saving ML model.")

                            created_model_dict_final={
                                'cv_kappa' : results['cv_kappa'],
                                'cv_mean_absolute_error' : results['cv_mean_absolute_error'],
                                'creation_succeeded': results['success'],
                                's3_public_url' : results['s3_public_url'],
                                'model_stored_in_s3' : settings.USE_S3_TO_STORE_MODELS,
                                's3_bucketname' : str(settings.S3_BUCKETNAME),
                                'creation_finished' : True,
                                'model_relative_path' : relative_model_path,
                                'model_full_path' : full_model_path,
                                'location' : location + suffix,
                                }

                            transaction.commit()
                            success, id = ml_grading_util.save_created_model(created_model_dict_final,update_model=True,update_id=initial_id)
                        else:
                            log.error("Could not create an ML model.  Have you installed all the needed requirements for ease?  This is for location {0} and rubric item {1}".format(location, m))

                        if not success:
                            log.error("ModelCreator creation failed.  Error: {0}".format(id))
                            statsd.increment("open_ended_assessment.grading_controller.call_ml_creator",
                                tags=["success:False", "location:{0}".format(location)])

                        log.info("Location: {0} Creation Status: {1} Errors: {2}".format(
                            full_model_path,
                            results['success'],
                            results['errors'],
                        ))
                        statsd.increment("open_ended_assessment.grading_controller.call_ml_creator",
                            tags=["success:{0}".format(results['success']), "location:{0}".format(location)])
        util.log_connection_data()
    except Exception:
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

    try:
        ml_grading_util.dump_model_to_file(results['prompt'], results['feature_ext'],
            results['classifier'], results['text'],results['score'],results['model_path'])
        if success:
            return True, s3_public_url
        else:
            return True, "Saved model to file."
    except Exception:
        return False, "Could not save model."