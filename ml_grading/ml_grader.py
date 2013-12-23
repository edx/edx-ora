from django.conf import settings
from django.core.management.base import NoArgsCommand

from django.db import transaction

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
import pickle

log=logging.getLogger(__name__)

import controller.util as util
from controller.models import SubmissionState, GraderStatus, Submission, Grader
from controller import rubric_functions

from ml_grading.models import CreatedModel

import ml_grading.ml_grading_util as ml_grading_util

from ease import grade

from staff_grading import staff_grading_util

log = logging.getLogger(__name__)

RESULT_FAILURE_DICT={'success' : False, 'errors' : 'Errors!', 'confidence' : 0, 'feedback' : "", 'score' : 0}

def handle_single_item(controller_session):
    sub_get_success, content = get_item_from_controller(controller_session)
    #Grade and handle here
    if sub_get_success:
        transaction.commit()
        sub = Submission.objects.get(id=int(content['submission_id']))
        sl = staff_grading_util.StaffLocation(sub.location)
        subs_graded_by_instructor = sl.graded()
        first_sub = subs_graded_by_instructor.order_by('date_created')[0]
        parsed_rubric=rubric_functions.parse_rubric(first_sub.rubric)


        #strip out unicode and other characters in student response
        #Needed, or grader may potentially fail
        #TODO: Handle unicode in student responses properly
        student_response = sub.student_response.encode('ascii', 'ignore')

        #Get the latest created model for the given location
        transaction.commit()

        location_suffixes=ml_grading_util.generate_rubric_location_suffixes(subs_graded_by_instructor, grading = True)

        if len(location_suffixes)>0:
            rubric_scores_complete=True
            rubric_scores=[]

        for m in xrange(0,len(location_suffixes)):
            suffix = location_suffixes[m]
            success, created_model=ml_grading_util.get_latest_created_model(sub.location + suffix)

            if not success:
                log.error("Could not identify a valid created model!")
                if m==0:
                    results= RESULT_FAILURE_DICT
                    formatted_feedback="error"
                    status=GraderStatus.failure
                    statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
                        tags=["success:False"])

            else:

                #Create grader path from location in submission
                grader_path = os.path.join(settings.ML_MODEL_PATH,created_model.model_relative_path)
                model_stored_in_s3=created_model.model_stored_in_s3

                success, grader_data=load_model_file(created_model,use_full_path=False)
                if success:
                    results = grade.grade(grader_data, student_response)
                else:
                    results=RESULT_FAILURE_DICT

                #If the above fails, try using the full path in the created_model object
                if not results['success'] and not created_model.model_stored_in_s3:
                    grader_path=created_model.model_full_path
                    try:
                        success, grader_data=load_model_file(created_model,use_full_path=True)
                        if success:
                            results = grade.grade(grader_data, student_response)
                        else:
                            results=RESULT_FAILURE_DICT
                    except Exception:
                        error_message="Could not find a valid model file."
                        log.exception(error_message)
                        results=RESULT_FAILURE_DICT

                log.info("ML Grader:  Success: {0} Errors: {1}".format(results['success'], results['errors']))
                statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
                    tags=["success:{0}".format(results['success']), 'location:{0}'.format(sub.location)])

                #Set grader status according to success/fail
                if results['success']:
                    status = GraderStatus.success
                else:
                    status = GraderStatus.failure

            if m==0:
                final_results=results
            elif results['success']==False:
                rubric_scores_complete = False
            else:
                rubric_scores.append(int(results['score']))
        if len(rubric_scores)==0:
            rubric_scores_complete=False

        grader_dict = {
            'score': int(final_results['score']),
            'feedback': json.dumps(results['feedback']),
            'status': status,
            'grader_id': 1,
            'grader_type': "ML",
            'confidence': results['confidence'],
            'submission_id': sub.id,
            'errors' : ' ' .join(results['errors']),
            'rubric_scores_complete' : rubric_scores_complete,
            'rubric_scores' : json.dumps(rubric_scores),
            }
        #Create grader object in controller by posting back results
        created, msg = util._http_post(
            controller_session,
            urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                project_urls.ControllerURLs.put_result),
            grader_dict,
            settings.REQUESTS_TIMEOUT,
        )
    else:
        log.error("Error getting item from controller or no items to get.")
        statsd.increment("open_ended_assessment.grading_controller.call_ml_grader",
            tags=["success:False"])

    util.log_connection_data()
    return sub_get_success

def get_item_from_controller(controller_session):
    """
    Get a single submission from grading controller
    """
    success,content=query_controller(controller_session,project_urls.ControllerURLs.get_submission_ml)

    return success, content

def get_pending_length_from_controller(controller_session):
    """
    Get the number of pending submissions from the controller
    """
    success,content=query_controller(controller_session,project_urls.ControllerURLs.get_pending_count, data={'grader_type' : "ML"})
    return success, content['to_be_graded_count']

def query_controller(controller_session,end_path,data=None):
    """
    Get a single submission from grading controller
    """

    if data is None:
        data = {}

    try:
        success, content = util._http_get(
            controller_session,
            urlparse.urljoin(settings.GRADING_CONTROLLER_INTERFACE['url'],
                end_path),
            data=data,
        )
    except Exception as err:
        log.exception(err)
        return False, "Error getting response: {0}".format(err)

    return success, content

def load_model_file(created_model,use_full_path):
    try:
        if use_full_path:
            grader_data=pickle.load(file(created_model.model_full_path,"r"))
        else:
            grader_data=pickle.load(file(os.path.join(settings.ML_MODEL_PATH,created_model.model_relative_path),"r"))
        return True, grader_data
    except Exception:
        log.exception("Could not load model file.  This is okay.")
        #Move on to trying S3
        pass

    try:
        # Generate a temporary public URL to the model.
        public_url = ml_grading_util.get_s3_temporary_url(created_model.model_relative_path, settings.S3_BUCKETNAME)
        r = requests.get(public_url, timeout=30)
        grader_data=pickle.loads(r.text)
    except Exception:
        log.exception("Problem with S3 connection.")
        return False, "Could not load."

    try:
        store_model_locally(created_model,grader_data)
    except Exception:
        log.exception("Could not save model.  This is not a show-stopping error.")
        #This is okay if it isn't possible to save locally
        pass

    return True, grader_data

def store_model_locally(created_model,results):
    relative_model_path= created_model.model_relative_path
    full_model_path = os.path.join(settings.ML_MODEL_PATH,relative_model_path)
    try:
        ml_grading_util.dump_model_to_file(results['prompt'], results['extractor'],
            results['model'], results['text'],results['score'],full_model_path)
    except Exception:
        error_message="Could not save model to file."
        log.exception(error_message)
        return False, error_message

    return True, "Saved file."


