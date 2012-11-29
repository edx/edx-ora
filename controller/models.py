from django.db import models
import datetime

class GraderStatus():
    failure="F"
    success="S"

class SubmissionState():
    being_graded="C"
    waiting_to_be_graded="W"
    finished="F"

GRADER_TYPE = (
    ('ML', 'ML'),
    ('IN', 'Instructor'),
    ('PE', 'Peer'),
    ('SE', 'Self'),
    ('NA', 'None'),
    )

STATUS_CODES = (
    (GraderStatus.success, "Success"),
    (GraderStatus.failure, "Failure"),
    )

STATE_CODES = (
    (SubmissionState.being_graded, "Currently being Graded"),
    (SubmissionState.waiting_to_be_graded, "Waiting to be Graded"),
    (SubmissionState.finished, "Finished" )
    )

CHARFIELD_LEN_SMALL = 128

# TODO: DB settings -- utf-8, innodb, store everything in UTC

class Submission(models.Model):
    # controller state
    next_grader_type = models.CharField(max_length=2, choices=GRADER_TYPE, default="NA")
    previous_grader_type = models.CharField(max_length=2, choices=GRADER_TYPE, default="NA")
    state = models.CharField(max_length=1, choices=STATE_CODES)
    grader_settings = models.TextField(default="")

    # data about the submission
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    prompt = models.TextField(default="")
    rubric = models.TextField(default="")
    # TODO: is this good enough?  unique per problem/student?
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
    xqueue_submission_id = models.CharField(max_length=CHARFIELD_LEN_SMALL, default="")
    xqueue_submission_key = models.CharField(max_length=CHARFIELD_LEN_SMALL, default="")
    xqueue_queue_name = models.CharField(max_length=CHARFIELD_LEN_SMALL, default="")
    posted_results_back_to_queue = models.BooleanField(default=False)

    def __unicode__(self):
        sub_row = "Essay to be graded from student {0}, in course {1}, and problem {2}.  ".format(
            self.student_id, self.course_id, self.problem_id)
        sub_row += "Submission created at {0} and modified at {1}.  ".format(self.date_created, self.date_modified)
        sub_row += "Current state is {0}, next grader is {1},".format(self.state, self.next_grader_type)
        sub_row += " previous grader is {0}".format(self.previous_grader_type)
        return sub_row

    def get_all_graders(self):
        return self.grader_set.all()

    def get_last_grader(self):
        all_graders = self.get_all_graders()
        grader_times = [x.date_created for x in all_graders]
        last_grader = all_graders[grader_times.index(max(grader_times))]
        return last_grader

    def set_previous_grader_type(self):
        last_grader = self.get_last_grader()
        self.previous_grader_type = last_grader.grader_type
        self.save()
        return "Save ok."

    def get_successful_peer_graders(self):
        all_graders = self.get_all_graders()
        successful_peer_graders = all_graders.filter(
            status_code=GraderStatus.success,
            grader_type="PE",
        )
        return successful_peer_graders

    def get_successful_graders(self):
        all_graders = self.get_all_graders()
        successful_graders = all_graders.filter(
            status_code=GraderStatus.success,
        )
        return successful_graders

    def get_all_successful_scores_and_feedback(self):
        all_graders = list(self.get_successful_graders())
        if len(all_graders) == 0:
            return {'score': 0, 'feedback': "No finished graders!  Please contact course staff."}
        elif all_graders[0].grader_type in ["IN", "ML"]:
            return {'score': all_graders[0].score, 'feedback': all_graders[0].feedback}
        elif self.previous_grader_type == "PE":
            peer_graders = [p for p in all_graders if p.grader_type == "PE"]
            score = [p.score for p in peer_graders]
            feedback = [p.feedback for p in peer_graders]
            return {'score': score, 'feedback': feedback}
        else:
            return {'score': -1}

    def get_last_successful_instructor_grader(self):
        all_graders = self.get_all_graders()
        successful_instructor_graders = all_graders.filter(
            status_code=GraderStatus.success,
            grader_type="IN",
        ).order_by("-date_created")
        if successful_instructor_graders.count() == 0:
            return {'score': -1}

        last_successful_instructor = successful_instructor_graders[0]
        return {'score': last_successful_instructor.score}


# TODO: what's a better name for this?  GraderResult?
class Grader(models.Model):
    submission = models.ForeignKey('Submission')
    score = models.IntegerField()
    feedback = models.TextField()
    status_code = models.CharField(max_length=1, choices=STATUS_CODES)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    # For human grading, this is the id of the user that graded the submission.
    # For machine grading, it's the name and version of the algorithm that was
    # used.
    grader_id = models.CharField(max_length=CHARFIELD_LEN_SMALL)
    grader_type = models.CharField(max_length=2, choices=GRADER_TYPE)

    # should be between 0 and 1, with 1 being most confident.
    confidence = models.DecimalField(max_digits=10, decimal_places=9)

    #User for instructor grading to mark essays as calibration or not.
    is_calibration = models.BooleanField(default=False)

    def __unicode__(self):
        sub_row = "Grader object for submission {0} with status code {1}. ".format(self.submission.id, self.status_code)
        sub_row += "Grader type {0}, created on {1}, modified on {2}. ".format(self.grader_type, self.date_created,
            self.date_modified)
        return sub_row





