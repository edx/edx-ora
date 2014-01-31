from models import Submission, SubmissionState

class LocationCapsule(object):
    """
    Ecapsulates information that graders may want about a location.
    """
    def __init__(self, location):
        self.location = location

    def location_submissions(self):
        """
        Gets all submissions for a particular location.
        """
        return Submission.objects.filter(location=self.location)

    def all_pending(self):
        """
        Gets all submissions for the location that are waiting to be graded.
        """
        # Filter out duplicates and plagiarized submissions, because they are not pending, and will be
        # automatically scored.
        return self.location_submissions().filter(
            state=SubmissionState.waiting_to_be_graded,
            is_duplicate=False,
            is_plagiarized=False
        )

    def all_pending_count(self):
        """
        Counts all pending submissions.
        """
        return self.all_pending().count()

    def graded(self):
        """
        Finds all submissions that have been graded, and are now complete.
        """
        raise NotImplementedError()

    def graded_count(self):
        """
        Counts graded submissions.
        """
        raise NotImplementedError()

    def pending(self):
        """
        Gets all non-duplicate submissions that are pending instructor grading.
        """
        raise NotImplementedError()

    def pending_count(self):
        """
        Counts pending submissions.
        """
        raise NotImplementedError()

    def next_item(self):
        """
        Looks for submissions to score.  If nothing exists, look for something to rescore.
        """
        raise NotImplementedError()

    def problem_name(self):
        """
        Get the problem name for this location.
        """

        # Get the last problem submitted and read its name.
        # Do this to support course staff changing problem names.
        return self.latest_submission().problem_id

    def latest_submission(self):
        """
        Get the latest submission for this location.
        """
        return self.location_submissions().order_by("-date_modified")[0]

class CourseCapsule(object):
    """
    Encapsulates information that graders may want about a course.
    """
    def __init__(self, course_id):
        self.course_id = course_id

    def locations(self):
        """
        Gets all locations in a course.
        """
        return [x['location'] for x in Submission.objects.filter(course_id=self.course_id).values('location').distinct()]

    def next_item(self):
        """
        Gets the next item to grade in the course.
        """
        raise NotImplementedError()

    def notifications(self):
        """
        Checks to see if  a notification needs to be shown
        """
        raise NotImplementedError()