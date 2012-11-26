from django.db import models

CHARFIELD_LEN_SMALL = 128
class CalibrationHistory(models.Model):
    student_id=models.CharField(max_length=CHARFIELD_LEN_SMALL)

    #Have problem_id and location in order to allow for one to be user_defined, and one system defined
    #This allows for the same problem to be used across classes without re-calibration if needed.
    #Currently use location instead of problem_id
    problem_id=models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")
    location=models.CharField(max_length=CHARFIELD_LEN_SMALL,default="")

    def __unicode__(self):
        history_row=("Calibration history for student {0} on problem {1} at location {2}").format(
            self.student_id,self.problem_id,self.location)
        return history_row

    def get_all_calibration_records(self):
        return self.calibrationrecord_set.all()

    def get_calibration_record_count(self):
        return self.get_all_calibration_records().count()

    def get_average_calibration_error(self):
        all_records=list(self.get_all_calibration_records())
        errors=[abs(all_records[i].actual_score-all_records[i].score) for i in xrange(0,len(all_records))]
        total_error=0
        for i in xrange(0,len(errors)):
            total_error+=errors[i]
        average_error=total_error/float(len(errors))
        return average_error

class CalibrationRecord(models.Model):
    calibration_history=models.ForeignKey("CalibrationHistory")
    submission=models.ForeignKey("controller.Submission")
    score=models.IntegerField()
    actual_score=models.IntegerField()

    #This is currently not used, but in case student offers feedback.  This may be useful in some way.
    feedback=models.TextField()

    #This tracks whether the record was created from a calibration essay prior to the student starting grading,
    #Or from a calibration essay inserted into the peer grading
    #Unused for now.
    is_pre_calibration=models.BooleanField(default=True)

    def __unicode__(self):
        history_row=(("Calibration record for calibration history {0} and submission {1} with score {2} and actual score {3}")
                    .format(self.calibration_history.id,self.submission.id,self.score,self.actual_score))
        return history_row
