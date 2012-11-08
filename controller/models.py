from django.db import models

GRADER_TYPE = (
    ('ML', 'ML'),
    ('IN', 'Instructor'),
    ('PE', 'Peer'),
    ('SE', 'Self'),
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

class Submission(models.Model):
    next_grader_type=models.CharField(max_length=2, choices=GRADER_TYPE)
    prompt = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    student_id = models.CharField(max_length=200)
    problem_id = models.CharField(max_length=200)
    course_id = models.CharField(max_length=200)
    state = models.CharField(max_length=1, choices= STATE_CODES)

class PeerGrader(Grader):
    pass

class MLGrader(Grader):
    confidence=models.DecimalField(max_digits=10, decimal_places=9)

class InstructorGrader(Grader):
    pass

class SelfAssessmentGrader(Grader):
    pass


class Grader(models.Model):
    submission = models.ForeignKey('Submission')
    score=models.IntegerField()
    feedback = models.CharField(max_length=2000)
    status_code = models.CharField(max_length=1,choices=STATUS_CODES)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified= models.DateTimeField(auto_now=True)
    grader_id=models.CharField(max_length=200)

    class Meta:
        abstract = True



