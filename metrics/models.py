from django.db import models

class Timing(models.Model):
    #All timing is done on a grader object.
    # When the timing object is instantiated, there is no corresponding grader object (that is added after
    #the end of the grading process), so it has to foreign key to the submission so it can be looked up
    #later on.  When the grading finished, the grader foreign key is added, along with end time.
    submission=models.ForeignKey("controller.Submission")
    grader=models.ForeignKey("controller.Grader", blank=True, null= True)
    start_time=models.DateField(auto_now_add=True)
    end_time=models.DateTimeField()
    finished_timing=models.BooleanField(default=False)

