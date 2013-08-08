from django.db import models

CHARFIELD_LEN_SMALL = 128
CHARFIELD_LEN_LONG = 1024

class CalibrationHistory(models.Model):
    student_id = models.CharField(max_length=CHARFIELD_LEN_SMALL, db_index = True)

    #Have problem_id and location in order to allow for one to be user_defined, and one system defined
    #This allows for the same problem to be used across classes without re-calibration if needed.
    #Currently use location instead of problem_id
    problem_id = models.CharField(max_length=CHARFIELD_LEN_LONG, default="")
    location = models.CharField(max_length=CHARFIELD_LEN_SMALL, default="", db_index = True)
    
    class Meta:
        unique_together = ("student_id", "location")

    def __unicode__(self):
        history_row = ("Calibration history for student {0} on problem {1} at location {2}").format(
            self.student_id, self.problem_id, self.location)
        return history_row

    def get_all_calibration_records(self):
        return self.calibrationrecord_set.all()

    def get_calibration_record_count(self):
        return self.get_all_calibration_records().count()

    def get_average_calibration_error(self):
        all_records = list(self.get_all_calibration_records())

        #Get average student error
        #mean(abs(student_score-actual_score))
        errors = [abs(all_records[i].actual_score - all_records[i].score) for i in xrange(0, len(all_records))]
        total_error = 0
        for i in xrange(0, len(errors)):
            total_error += errors[i]

        #If student has no records, return 0
        if len(errors)==0:
            return 0

        average_error = total_error / float(len(errors))
        return average_error


class CalibrationRecord(models.Model):
    calibration_history = models.ForeignKey("CalibrationHistory", db_index = True)
    submission = models.ForeignKey("controller.Submission", db_index = True)
    score = models.IntegerField()
    actual_score = models.IntegerField()

    #This is currently not used, but in case student offers feedback.  This may be useful in some way.
    feedback = models.TextField()

    rubric_scores = models.TextField(default="")
    rubric_scores_complete = models.BooleanField(default=False)

    #The plan is to display calibration records to students at two points:
    #1. Before they start grading (pre-calibration)
    #2. Randomly mixed in with essays while they are graded
    #This tracks whether the record was created during pre-calibration,
    #Or from a calibration essay inserted into the peer grading
    #Unused for now.
    is_pre_calibration = models.BooleanField(default=True)

    def __unicode__(self):
        history_row = (
        ("Calibration record for calibration history {0} and submission {1} with score {2} and actual score {3}")
        .format(self.calibration_history.id, self.submission.id, self.score, self.actual_score))
        return history_row
