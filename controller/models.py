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

class Submission(models.Model):
    next_grader_type=models.CharField(max_length=2, choices=GRADER_TYPE)
    prompt = models.CharField(max_length=200)
    date_created = models.DateTimeField('date created')
    date_modified = models.DateTimeField(auto_now=True)
    student_id = models.IntegerField()
    problem_id = models.CharField(max_length=200)
    course_id = models.CharField(max_length=200)

    #grader type, problem id, prompt, course id, score, student id, state/version blob, and peer grader student id.

class PeerGrader(models.Model):
    submission = models.ForeignKey('Submission')
    peer_grader_id = models.CharField(max_length=200)
    score = models.IntegerField()
    status_code = models.CharField(max_length=1,choices=STATUS_CODES)
    date_created = models.DateTimeField('date created')
    date_modified= models.DateTimeField(auto_now=True)

class MLGrader(models.Model):
    submission = models.ForeignKey('Submission')
    score=models.IntegerField()
    ml_confidence=models.DecimalField(max_digits=10, decimal_places=10)
    status_code = models.CharField(max_length=1,choices=STATUS_CODES)
    ml_grader_id = models.CharField(max_length=200)
    date_created = models.DateTimeField('date created')
    date_modified= models.DateTimeField(auto_now=True)

class InstructorGrader(models.Model):
    submission = models.ForeignKey('Submission')
    score=models.IntegerField()
    status_code = models.CharField(max_length=1,choices=STATUS_CODES)
    instructor_id=models.CharField(max_length=200)
    date_created = models.DateTimeField('date created')
    date_modified= models.DateTimeField(auto_now=True)

class SelfAssessmentGrader(models.Model):
    submission = models.ForeignKey('Submission')
    score=models.IntegerField()
    status_code = models.CharField(max_length=1,choices=STATUS_CODES)
    date_created = models.DateTimeField('date created')
    date_modified= models.DateTimeField(auto_now=True)



