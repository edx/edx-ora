from django.conf import settings
from controller.models import Submission
import logging

log=logging.getLogger(__name__)


def finished_submissions_graded_by_instructor(location):
    """
    Get submissions that are graded by instructor
    """
    subs_graded = Submission.objects.filter(location=location,
        previous_grader_type__in=["IN"],
        state__in=["F"],
    )

    return subs_graded


def submissions_pending_instructor(location, state_in=["C", "W"]):
    """
    Get submissions that are pending instructor grading.
    """
    subs_pending = Submission.objects.filter(location=location,
        next_grader_type__in=["IN"],
        state__in=state_in,
    )

    return subs_pending


def count_submissions_graded_and_pending_instructor(location):
    """
    Return length of submissions pending instructor grading and graded.
    """
    return finished_submissions_graded_by_instructor(location).count(), submissions_pending_instructor(location).count()


def get_single_instructor_grading_item(course_id):
    """
    Gets instructor grading for a given course id.
    Returns one submission id corresponding to the course.
    Input:
        course_id - Id of a course.
    Returns:
        found - Boolean indicating whether or not something to grade was found
        sub_id - If found, the id of a submission to grade
    """
    found = False
    sub_id = 0
    locations_for_course = [x['location'] for x in
                            list(Submission.objects.filter(course_id=course_id).values('location').distinct())]
    for location in locations_for_course:
        subs_graded = finished_submissions_graded_by_instructor(location).count()
        subs_pending = submissions_pending_instructor(location, state_in=["C"]).count()
        if (subs_graded + subs_pending) < settings.MIN_TO_USE_ML:
            to_be_graded = Submission.objects.filter(
                location=location,
                state="W",
                next_grader_type="IN",
            )

            if(to_be_graded.count() > 0):
                to_be_graded = to_be_graded[0]
                if to_be_graded is not None:
                    to_be_graded.state = "C"
                    to_be_graded.save()
                    found = True
                    sub_id = to_be_graded.id
                    return found, sub_id
    return found, sub_id