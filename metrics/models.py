from django.db import models
from controller.models import GRADER_TYPE, STATUS_CODES, STATE_CODES

CHARFIELD_LEN_SMALL=1024

class Timing(models.Model):

    #The need to store all of this could be solved by putting a foreign key on a submission object.
    #However, the point of not doing that is twofold:
    #1.  We want to keep this as separate as possible to we can switch to something else down the line.
    #2.  We don't want to tie up the main working submission and grader tables with queries.

    #Actual timing
    start_time=models.DateField(auto_now_add=True)
    end_time=models.DateTimeField()
    finished_timing=models.BooleanField(default=False)

    #Essay metadata
    student_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    location=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    problem_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    course_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    max_score=models.IntegerField()

    #This is so that we can query on it if we need to get more data
    submission_id=models.IntegerField(blank=True,null=True)

    #Grader Metadata
    grader_type=models.CharField(max_length=2,choices=GRADER_TYPE)
    status_code = models.CharField(max_length=1, choices=STATUS_CODES)
    confidence = models.DecimalField(max_digits=10, decimal_places=9)
    is_calibration = models.BooleanField(default=False)
    score=models.IntegerField()

    #Badly named, but it can't be grader_id for obvious reasons!
    #This contains the version # of the grader.  For humans, version number is the lms id for the person.
    grader_version=models.CharField(max_length=CHARFIELD_LEN_SMALL)

    #This is so that we can query on it if we need to get more data
    grader_id=models.IntegerField(blank=True,null=True)

