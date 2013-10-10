import json
from django.conf import settings

class SubmissionControl():
    """
    Class to hold control parameters for a submission
    """
    def __init__(self, sub):
        """
        Initialize the control class
        sub - A submission model object
        """
        self.cd = {}
        try:
            self.cd = json.loads(sub.control_fields)
        except Exception:
            pass

        if not isinstance(self.cd, dict):
            self.cd = {}

    @property
    def min_to_calibrate(self):
        return self.cd.get('min_to_calibrate',settings.PEER_GRADER_MINIMUM_TO_CALIBRATE)

    @property
    def max_to_calibrate(self):
        return self.cd.get('max_to_calibrate',settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE)

    @property
    def peer_grader_count(self):
        return self.cd.get('peer_grader_count',settings.PEER_GRADER_COUNT)

    @property
    def required_peer_grading_per_student(self):
        return self.cd.get('required_peer_grading',settings.REQUIRED_PEER_GRADING_PER_STUDENT)

    @property
    def peer_grade_finished_submissions_when_none_pending(self):
        return self.cd.get('peer_grade_finished_submissions_when_none_pending',
                           settings.PEER_GRADE_FINISHED_SUBMISSIONS_WHEN_NONE_PENDING)

    @property
    def minimum_to_use_peer(self):
        return self.cd.get('staff_minimum_for_peer_grading', settings.MIN_TO_USE_PEER)

    @property
    def minimum_to_use_ai(self):
        return self.cd.get('staff_minimum_for_ai_grading', settings.MIN_TO_USE_ML)

    @classmethod
    def peer_grade_finished_subs(cls, peer_location):
        # When there are no subs, return default
        if not peer_location.submitted_count():
            return settings.PEER_GRADE_FINISHED_SUBMISSIONS_WHEN_NONE_PENDING
        sub = peer_location.submitted().order_by('-date_modified')[:1].get()
        return cls(sub).peer_grade_finished_submissions_when_none_pending
