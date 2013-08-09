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

