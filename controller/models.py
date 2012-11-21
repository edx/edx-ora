from django.db import models
import datetime

GRADER_TYPE = (
    ('ML', 'ML'),
    ('IN', 'Instructor'),
    ('PE', 'Peer'),
    ('SE', 'Self'),
    ('NA', 'None'),
    )

STATUS_CODES = (
    ("S", "Success"),
    ("F", "Failure"),
)

STATE_CODES = (
    ("C", "Currently being Graded"),
    ("W", "Waiting to be Graded"),
    ("F", "Finished" )
    )

CHARFIELD_LEN_SMALL = 128

class Submission(models.Model):
    # controller state
    next_grader_type=models.CharField(max_length=2, choices=GRADER_TYPE,default="NA")
    previous_grader_type=models.CharField(max_length=2, choices=GRADER_TYPE, default="NA")
    state = models.CharField(max_length=1, choices= STATE_CODES)
    grader_settings=models.TextField(default="")

    # data about the submission
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    prompt = models.TextField(default="")
    rubric = models.TextField(default="")
    student_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)

    # specified in the input type--can be reused between many different
    # problems.  (Should perhaps be named something like problem_type)
    problem_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)

    # passed by the LMS
    location = models.CharField(max_length=CHARFIELD_LEN_SMALL, default="")
    max_score = models.IntegerField(default=1)
    course_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)
    student_response = models.TextField(default="")
    student_submission_time = models.DateTimeField(default=datetime.datetime.now)

    # xqueue details
    xqueue_submission_id = models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    xqueue_submission_key = models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    xqueue_queue_name = models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    posted_results_back_to_queue=models.BooleanField(default=False)

    def __unicode__(self):
        sub_row = "Essay to be graded from student {0}, in course {1}, and problem {2}.  ".format(
            self.student_id,self.course_id,self.problem_id)
        sub_row+= "Submission created at {0} and modified at {1}.  ".format(self.date_created,self.date_modified)
        sub_row+= "Current state is {0}, next grader is {1},".format(self.state,self.next_grader_type)
        sub_row+=" previous grader is {0}".format(self.previous_grader_type)
        return sub_row

    def get_all_graders(self):
        return self.grader_set.all()

    def get_last_grader(self):
        all_graders=self.get_all_graders()
        grader_times=[x.date_created for x in all_graders]
        last_grader=all_graders[grader_times.index(max(grader_times))]
        return last_grader

    def set_previous_grader_type(self):
        last_grader=self.get_last_grader()
        self.previous_grader_type=last_grader.grader_type
        self.save()
        return "Save ok."

    def get_successful_peer_graders(self):
        all_graders=self.get_all_graders()
        successful_peer_graders=all_graders.filter(
            status_code="S",
            grader_type="PE",
        )
        return successful_peer_graders

# TODO: what's a better name for this?  GraderResult?
class Grader(models.Model):
    submission = models.ForeignKey('Submission')
    score=models.IntegerField()
    feedback = models.TextField()
    status_code = models.CharField(max_length=1,choices=STATUS_CODES)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified= models.DateTimeField(auto_now=True)

    # For human grading, this is the id of the user that graded the submission.
    # For machine grading, it's the name and version of the algorithm that was
    # used.
    grader_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    grader_type=models.CharField(max_length=2, choices=GRADER_TYPE)

    # should be between 0 and 1, with 1 being most confident.
    confidence=models.DecimalField(max_digits=10, decimal_places=9)






