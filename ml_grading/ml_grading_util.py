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
    ).order_by("-date_created")

    if created_models.count()==0:
        return False, "No valid models for location."

    return True, created_models[0]

def check(model_path):
    try:
        with open(model_path) as f: pass
    except IOError as e:
        return False

    return True