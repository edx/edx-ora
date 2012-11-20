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
    next_grader_type=models.CharField(max_length=2, choices=GRADER_TYPE,default="NA")
    previous_grader_type=models.CharField(max_length=2, choices=GRADER_TYPE, default="NA")

    prompt = models.TextField(default="")
    rubric=models.TextField(default="")
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    student_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)
    problem_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)
    course_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)
    state = models.CharField(max_length=1, choices= STATE_CODES)
    student_response = models.TextField(default="")
    student_submission_time=models.DateTimeField(default=datetime.datetime.now)
    xqueue_submission_id=models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    xqueue_submission_key=models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    xqueue_queue_name = models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    location=models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    max_score=models.IntegerField(default=1)
    grader_settings=models.TextField(default="")

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

class Grader(models.Model):
    submission = models.ForeignKey('Submission')
    score=models.IntegerField()
    feedback = models.TextField()
    status_code = models.CharField(max_length=1,choices=STATUS_CODES)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified= models.DateTimeField(auto_now=True)
    grader_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)
    grader_type=models.CharField(max_length=2, choices=GRADER_TYPE)
    confidence=models.DecimalField(max_digits=10, decimal_places=9)






