from django.db import models

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
    next_grader=models.CharField(max_length=2, choices=GRADER_TYPE)
    prompt = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    student_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)
    problem_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)
    course_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)
    state = models.CharField(max_length=1, choices= STATE_CODES)

    def __unicode__(self):
        sub_row = "Essay to be graded from student {0}, in course {1}, and problem {2}\n".format(
            self.student_id,self.course_id,self.problem_id)
        sub_row+= "Submission created at {0} and modified at {1}\n".format(self.date_created,self.date_modified)
        sub_row+= "Current state is {0} and next grader is {1}".format(self.state,self.next_grader)
        return sub_row


class Grader(models.Model):
    submission = models.ForeignKey('Submission')
    score=models.IntegerField()
    feedback = models.TextField()
    status_code = models.CharField(max_length=1,choices=STATUS_CODES)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified= models.DateTimeField(auto_now=True)
    grader_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)

    class Meta:
        abstract = True

class PeerGrader(Grader):
    pass

class MLGrader(Grader):
    confidence=models.DecimalField(max_digits=10, decimal_places=9)

class InstructorGrader(Grader):
    pass

class SelfAssessmentGrader(Grader):
    pass






