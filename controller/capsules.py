from models import Submission, SubmissionState

class LocationCapsule(object):
    """
    Ecapsulates information that graders may want about a location.
    """
    def __init__(self, location):
        self.location = location

    @property
    def location_submissions(self):
        """
        Gets all submissions for a particular location.
        """
        return Submission.objects.filter(location=self.location)

    @property
    def all_pending(self):
        """
        Gets all submissions for the location that are waiting to be graded.
        """
        return self.location_submissions.filter(state=SubmissionState.waiting_to_be_graded)

    @property
    def all_pending_count(self):
        """
        Counts all pending submissions.
        """
        return self.all_pending.count()

class CourseCapsule(object):
    """
    Encapsulates information that graders may want about a course.
    """
    def __init__(self, course_id):
        self.course_id = course_id

    @property
    def locations(self):
        """
        Gets all locations in a course.
        """
        return [x['location'] for x in Submission.objects.filter(course_id=self.course_id).values('location').distinct()]
