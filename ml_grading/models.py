from django.db import models
from django.utils import timezone
import json

CHARFIELD_LEN_SMALL=1024

class CreatedModel(models.Model):
    #When it was created/modified
    date_modified=models.DateTimeField(auto_now=True)
    date_created=models.DateTimeField(auto_now_add=True)

    #Properties of the problem the model was created with
    max_score=models.IntegerField()
    prompt=models.TextField()
    rubric=models.TextField()
    location=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    course_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)

    #Stores a json serialized list of all the submission ids of essays used in this model.
    #Not currently used, but good to store in case it is used down the road.
    submission_ids_used=models.TextField()

    #Currently unused, but may be in the future.  See comment in controller/models.py above problem_id for details
    problem_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)

    #Properties of the model file
    model_relative_path=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    model_full_path=models.CharField(max_length=CHARFIELD_LEN_SMALL)

    #Properties of the model itself
    number_of_essays=models.IntegerField()
    cv_kappa=models.DecimalField(max_digits=10,decimal_places=9)
    cv_mean_absolute_error=models.DecimalField(max_digits=15,decimal_places=10)
    creation_succeeded=models.BooleanField(default=False)

    def get_submission_ids_used(self):
        """
        Returns a list of submission ids of essays used to create the model.
        Output:
            Boolean success, list of ids/error message as appropriate
        """

        try:
            submission_id_list=json.loads(self.submission_ids_used)
        except:
            return False, "No essays used or not in json format."

        return True, submission_id_list




