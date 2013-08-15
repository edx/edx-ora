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

    @property
    def graded(self):
        """
        Finds all submissions that have been graded, and are now complete.
        """
        raise NotImplementedError()

    @property
    def graded_count(self):
        """
        Counts graded submissions.
        """
        raise NotImplementedError()

    @property
    def pending(self):
        """
        Gets all non-duplicate submissions that are pending instructor grading.
        """
        raise NotImplementedError()

    @property
    def pending_count(self):
        """
        Counts pending submissions.
        """
        raise NotImplementedError()

    @property
    def next_item(self):
        """
        Looks for submissions to score.  If nothing exists, look for something to rescore.
        """
        raise NotImplementedError()

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

    @property
    def next_item(self):
        """
        Gets the next item to grade in the course.
        """
        raise NotImplementedError()

    @property
    def notifications(self):
        """
        Checks to see if  a notification needs to be shown
        """
        raise NotImplementedError()