from django.db import models
from controller.models import GRADER_TYPE, STATUS_CODES, STATE_CODES
from django.utils import timezone

CHARFIELD_LEN_SMALL=128
CHARFIELD_LEN_LONG = 1024
MAX_DECIMAL_DIGITS = 10
DECIMAL_PLACES = 5
DEFAULT_VALUE=0

FIELDS_TO_EVALUATE = [
    "problems_attempted",
    "attempts_per_problem",
    "graders_per_attempt",
    "stdev_percent_score",
    "average_percent_score",
    "average_percent_score_last20",
    "average_percent_score_last10",
    "problems_attempted_peer",
    "completed_peer_grading",
    "average_length_of_peer_feedback_given",
    "stdev_length_of_peer_feedback_given",
    "average_peer_grading_score_given",
    "attempts_per_problem_peer",
    "average_percent_score_peer",
    "problems_attempted_ml",
    "attempts_per_problem_ml",
    "average_ml_confidence",
    "average_percent_score_ml",
    "average_submission_length",
    "stdev_submission_length",
    ]

class Timing(models.Model):

    #The need to store all of this could be solved by putting a foreign key on a submission object.
    #However, the point of not doing that is twofold:
    #1.  We want to keep this as separate as possible to we can switch to something else down the line.
    #2.  We don't want to tie up the main working submission and grader tables with queries.

    #Actual timing
    start_time=models.DateTimeField(auto_now_add=True)
    end_time=models.DateTimeField(blank=True, null=True, default=timezone.now)
    finished_timing=models.BooleanField(default=False)

    #Essay metadata
    student_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    location=models.CharField(max_length=CHARFIELD_LEN_SMALL, db_index = True)
    problem_id=models.CharField(max_length=CHARFIELD_LEN_LONG)
    course_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    max_score=models.IntegerField(default=1)

    #This is so that we can query on it if we need to get more data
    submission_id=models.IntegerField(blank=True,null=True)

    #Grader Metadata
    grader_type=models.CharField(max_length=2,choices=GRADER_TYPE,null=True, blank=True)
    status_code = models.CharField(max_length=1, choices=STATUS_CODES,null=True, blank=True)
    confidence = models.DecimalField(max_digits=10, decimal_places=9,null=True, blank=True)
    is_calibration = models.BooleanField(default=False)
    score=models.IntegerField(null=True, blank=True)

    #Badly named, but it can't be grader_id for obvious reasons!
    #This contains the version # of the grader.  For humans, version number is the lms id for the person.
    grader_version=models.CharField(max_length=CHARFIELD_LEN_LONG,null=True, blank=True)

    #This is so that we can query on it if we need to get more data
    grader_id=models.IntegerField(blank=True,null=True)

class StudentProfile(models.Model):
    student_id = models.CharField(max_length=CHARFIELD_LEN_SMALL, db_index = True, unique=True)

    #Message data
    messages_sent = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=0)
    messages_received = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=0)
    average_message_feedback_length = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=0)

    #Student metadata (ban state, etc)
    student_is_staff_banned = models.BooleanField(default=False)
    student_cannot_submit_more_for_peer_grading = models.BooleanField(default=False)

class StudentCourseProfile(models.Model):
    student_profile = models.ForeignKey('StudentProfile')

    date_modified = models.DateTimeField(auto_now=True)
    date_created = models.DateTimeField(auto_now_add=True)

    course_id = models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    student_id = models.CharField(max_length=CHARFIELD_LEN_SMALL,default="", db_index = True)

    #Attempt data
    problems_attempted = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    attempts_per_problem = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    graders_per_attempt = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)

    #Score data
    stdev_percent_score = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    average_percent_score = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    average_percent_score_last20 = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    average_percent_score_last10 = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)

    #Peer grading data
    problems_attempted_peer = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    completed_peer_grading = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    average_length_of_peer_feedback_given = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    stdev_length_of_peer_feedback_given = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    average_peer_grading_score_given = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    attempts_per_problem_peer = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    average_percent_score_peer = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)

    #ML grading data
    problems_attempted_ml = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    attempts_per_problem_ml = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    average_ml_confidence = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    average_percent_score_ml = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)

    #Submission data
    average_submission_length = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)
    stdev_submission_length = models.DecimalField(max_digits=MAX_DECIMAL_DIGITS, decimal_places=DECIMAL_PLACES, default=DEFAULT_VALUE)

    class Meta(object):
        unique_together = ("student_profile", "course_id")



