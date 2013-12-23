import os
from path import path
from django.conf import settings
import re
from django.utils import timezone
from django.db import transaction
import pickle
import logging

from models import CreatedModel

from boto.s3.connection import S3Connection
from boto.s3.key import Key

import controller.rubric_functions
from controller.models import Submission, SubmissionState, Grader, GraderStatus
log=logging.getLogger(__name__)

def create_directory(model_path):
    directory=path(model_path).dirname()
    if not os.path.exists(directory):
        os.makedirs(directory)

    return True

def get_model_path(location, suffix=""):
    """
    Generate a path from a location
    """
    base_path=settings.ML_MODEL_PATH
    #Ensure that directory exists, create if it doesn't
    create_directory(base_path)

    fixed_location=re.sub("[/:]","_",location)
    fixed_location+="_"+timezone.now().strftime("%Y%m%d%H%M%S")
    fixed_location+=suffix
    full_path=os.path.join(base_path,fixed_location)
    return fixed_location,full_path


def get_latest_created_model(location):
    """
    Gets the current model file for a given location
    Input:
        location
    Output:
        Boolean success/fail, createdmodel object/error message
    """
    created_models=CreatedModel.objects.filter(
        location=location,
        creation_succeeded=True,
        creation_finished = True,
    ).order_by("-date_created")[:1]

    if created_models.count()==0:
        return False, "No valid models for location."

    return True, created_models[0]

def check_if_model_started(location):
    """
    Gets the currently active model file for a given location
    Input:
        location
    Output:
        Boolean success/fail, Boolean started/not started
    """
    model_started = False
    created_models=CreatedModel.objects.filter(
        location=location,
        creation_started=True
    ).order_by("-date_created")[:1]

    if created_models.count()==0:
        return True, model_started, ""

    created_model = created_models[0]
    if created_model.creation_finished==False:
        model_started = True

    return True, model_started, created_model

def check_for_all_model_and_rubric_success(location):
    subs_graded_by_instructor = Submission.objects.filter(location=location,
        previous_grader_type="IN",
        state=SubmissionState.finished,
    )

    location_suffixes=generate_rubric_location_suffixes(subs_graded_by_instructor, grading = True)
    overall_success=True
    for m in xrange(0,len(location_suffixes)):
        suffix = location_suffixes[m]
        success, created_model=get_latest_created_model(location + suffix)
        if not success:
            overall_success=False
    return overall_success

def save_created_model(model_data, update_model=False, update_id=0):
    """
    Creates and saves a createdmodel object from an input dictionary.
    Input:
        Dict with keys shown below in the 'tags' variable
    Output:
        Boolean success/fail, and model id/error message
    """

    initial_tags=[
        'max_score',
        'prompt',
        'rubric',
        'location',
        'course_id',
        'submission_ids_used',
        'problem_id',
        'model_relative_path',
        'model_full_path',
        'number_of_essays',
        'creation_succeeded',
        'creation_started',
        'creation_finished',
    ]

    final_tags = [
        'cv_kappa',
        'cv_mean_absolute_error',
        'creation_succeeded',
        's3_public_url',
        'model_stored_in_s3',
        's3_bucketname',
        'creation_finished',
        'model_relative_path',
        'model_full_path',
        'location',
    ]
    if update_model:
        tags = final_tags
    else:
        tags = initial_tags

    for tag in tags:
        if tag not in model_data:
            return False, "Does not contain needed tag {0}".format(tag)

    try:
        if not update_model:
            created_model=CreatedModel(**model_data)
            created_model.save()
        else:
            created_model = CreatedModel.objects.filter(id=update_id).order_by('-date_modified')
            created_model_count = created_model.count()
            if created_model_count >1 or created_model_count==0:
                return False, ("Too few or too many records to update: {0} records exist, 1 needed for parameters "
                               "location: {1}, relative_path: {2}").format(created_model_count, model_data['location'],
                                model_data['model_relative_path'])
            created_model.update(**model_data)
            created_model = created_model[0]
    except Exception:
        log.exception("Could not make ModelCreator object.")
        return False, "Failed to create model!"

    return True, created_model.id


def check(model_path):
    try:
        with open(model_path) as f: pass
    except IOError as e:
        return False

    return True

def get_ml_errors(location):
    """
    Gets the latest error metrics from the last created ML model
    Input:
        location of the problem
    Output:
        boolean success, Dictionary with keys kappa, mean_absolute_error or error message
    """

    data_dict={'kappa' : 0, 'mean_absolute_error' : 0, 'date_created' : "", 'number_of_essays' : 0}

    success, created_model=get_latest_created_model(location)

    if not success:
        return False, "No model exists yet for this problem."

    data_dict['kappa']=round(created_model.cv_kappa,3)
    data_dict['mean_absolute_error'] = round(created_model.cv_mean_absolute_error,3)
    data_dict['date_created'] = created_model.date_created.strftime("%Y-%m-%d %H:%M")
    data_dict['number_of_essays'] = created_model.number_of_essays

    return True, data_dict

def get_s3_temporary_url(keyname, bucketname):
    """
    Get a temporary public url for a given file in a bucket.
    keyname - a string keyname in a bucket. (similar to a filename in the bucket)
    bucketname - a string S3 bucket name
    returns: a url to a the public file.
    """
    s3 = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, is_secure=False)
    file_url = s3.generate_url(settings.S3_FILE_TIMEOUT, 'GET', bucket=bucketname.lower(), key=keyname)
    return file_url

def upload_to_s3(string_to_upload, keyname, bucketname):
    '''
    Upload file to S3 using provided keyname.

    Returns:
        public_url: URL to access uploaded file
    '''
    try:
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        bucketname = str(bucketname)
        bucket = conn.create_bucket(bucketname.lower())

        k = Key(bucket)
        k.key = keyname
        k.set_contents_from_string(string_to_upload)
        public_url = k.generate_url(60*60*24*365) # URL timeout in seconds.

        return True, public_url
    except Exception:
        error = "Could not connect to S3."
        log.exception(error)
        return False, error

def get_pickle_data(prompt_string, feature_ext, classifier, text, score):
    """
    Writes out a model to a file.
    prompt string is a string containing the prompt
    feature_ext is a trained FeatureExtractor object
    classifier is a trained classifier
    model_path is the path of write out the model file to
    """
    model_file = {'prompt': prompt_string, 'extractor': feature_ext, 'model': classifier, 'text' : text, 'score' : score}
    return pickle.dumps(model_file)

def dump_model_to_file(prompt_string, feature_ext, classifier, text, score,model_path):
    model_file = {'prompt': prompt_string, 'extractor': feature_ext, 'model': classifier, 'text' : text, 'score' : score}
    pickle.dump(model_file, file=open(model_path, "w"))

def generate_rubric_location_suffixes(subs, grading=False):
    location_suffixes=[""]
    first_graded_subs=list(subs.order_by('date_created'))
    if len(first_graded_subs)>0:
        first_graded_sub=first_graded_subs[0]
        success, rubric_targets = controller.rubric_functions.generate_targets_from_rubric(first_graded_sub.rubric)
        if success:
            min_to_check = len(first_graded_subs)
            if grading:
                min_to_check = min(2,len(first_graded_subs))

            for m in xrange(0,min_to_check):
                sub=first_graded_subs[m]
                scores_match_target=check_if_sub_scores_match_targets(sub, rubric_targets)
                if not scores_match_target:
                    return location_suffixes

            for i in xrange(0,len(rubric_targets)):
                location_suffixes.append("_rubricitem_{0}".format(i))
    return location_suffixes

def check_if_sub_scores_match_targets(sub, targets):
    success, sub_scores = controller.rubric_functions.get_submission_rubric_instructor_scores(sub)
    if success:
        if len(sub_scores)==len(targets):
            success=True
        else:
            success=False
    return success

def regrade_ml(location):
    """
    Regrades all of the ML problems in a given location.  Returns boolean success.
    """
    success = check_for_all_model_and_rubric_success(location)
    if not success:
        log.error("No models trained yet for location {0}, so cannot regrade.".format(location))
        return False

    subs = Submission.objects.filter(location=location, previous_grader_type="ML")
    for sub in subs:
        for grade in sub.grader_set.all():
            grade.status_code = GraderStatus.failure
            grade.save()
        sub.state= SubmissionState.waiting_to_be_graded
        sub.posted_results_back_to_queue = False
        sub.next_grader_type = "ML"
        sub.save()

    return True









