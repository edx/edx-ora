import os
from path import path
from django.conf import settings
import re
from django.utils import timezone

from models import CreatedModel

def create_directory(model_path):
    directory=path(model_path).dirname()
    if not os.path.exists(directory):
        os.makedirs(directory)

    return True

def get_model_path(location):
    """
    Generate a path from a location
    """
    base_path=settings.ML_MODEL_PATH
    #Ensure that directory exists, create if it doesn't
    create_directory(base_path)

    fixed_location=re.sub("/","_",location)
    fixed_location+="_"+timezone.now().strftime("%Y%m%d%H%M%S")
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
    ).order_by("-date_created")[:1]

    if created_models.count()==0:
        return False, "No valid models for location."

    return True, created_models[0]

def save_created_model(model_data):
    """
    Creates and saves a createdmodel object from an input dictionary.
    Input:
        Dict with keys shown below in the 'tags' variable
    Output:
        Boolean success/fail, and model id/error message
    """

    tags=['max_score', 'prompt', 'rubric', 'location', 'course_id',
          'submission_ids_used', 'problem_id', 'model_relative_path',
          'model_full_path', 'number_of_essays', 'cv_kappa',
          'cv_mean_absolute_error', 'creation_succeeded']

    for tag in tags:
        if tag not in model_data:
            return False, "Does not contain needed tag {0}".format(tag)

    try:
        created_model=CreatedModel(
            max_score=model_data['max_score'],
            prompt=model_data['prompt'],
            rubric=model_data['rubric'],
            location=model_data['location'],
            course_id=model_data['course_id'],
            submission_ids_used=model_data['submission_ids_used'],
            problem_id=model_data['problem_id'],
            model_relative_path=model_data['model_relative_path'],
            model_full_path=model_data['model_full_path'],
            number_of_essays=model_data['number_of_essays'],
            cv_kappa=model_data['cv_kappa'],
            cv_mean_absolute_error=model_data['cv_mean_absolute_error'],
            creation_succeeded=model_data['creation_succeeded'],
        )
        created_model.save()
    except:
        return False, "Failed to create model!"

    return True, created_model.id


def check(model_path):
    try:
        with open(model_path) as f: pass
    except IOError as e:
        return False

    return True