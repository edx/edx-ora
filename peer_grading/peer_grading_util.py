from django.db.models import Count
from controller.models import SubmissionState, GraderStatus, Grader, Submission
import logging
from metrics import metrics_util
from metrics.timing_functions import initialize_timing
from django.conf import settings
from metrics import utilize_student_metrics
from metrics.models import StudentProfile

log = logging.getLogger(__name__)

def get_single_peer_grading_item(location, grader_id):
    """
    Gets peer grading for a given location and grader.
    Returns one submission id corresponding to the location and the grader.
    Input:
        location - problem location.
        grader_id - student id of the peer grader
    Returns:
        found - Boolean indicating whether or not something to grade was found
        sub_id - If found, the id of a submission to grade
    """
    found = False
    sub_id = 0
    to_be_graded = peer_grading_submissions_pending_for_location(location, grader_id) 
    #Do some checks to ensure that there are actually items to grade
    if to_be_graded is not None:
        to_be_graded_length = to_be_graded.count()
        if to_be_graded_length > 0:
            course_id = to_be_graded[0].course_id
            submissions_to_grade = (to_be_graded
                                    .filter(grader__status_code=GraderStatus.success, grader__grader_type__in=["PE","BC"])
                                    .exclude(grader__grader_id=grader_id)
                                    .annotate(num_graders=Count('grader'))
                                    .values("num_graders", "id")
                                    .order_by("num_graders")[:50])

            if submissions_to_grade is not None:
                submission_grader_counts = [p['num_graders'] for p in submissions_to_grade]
                #log.debug("Submissions to grade with graders: {0} {1}".format(submission_grader_counts, submissions_to_grade))

                submission_ids = [p['id'] for p in submissions_to_grade]

                student_profile_success, profile_dict = utilize_student_metrics.get_student_profile(grader_id, course_id)
                #Ensure that student hasn't graded this submission before!
                #Also ensures that all submissions are searched through if student has graded the minimum one
                fallback_sub_id = None
                for i in xrange(0, len(submission_ids)):
                    #log.debug("Looping through graders, on {0}".format(i))
                    minimum_index = submission_grader_counts.index(min(submission_grader_counts))
                    grade_item = Submission.objects.get(id=int(submission_ids[minimum_index]))
                    previous_graders = [p.grader_id for p in grade_item.get_successful_peer_graders()]
                    if grader_id not in previous_graders:
                        found = True
                        sub_id = grade_item.id

                        #Insert timing initialization code
                        if fallback_sub_id is None:
                            fallback_sub_id = grade_item.id

                        if not student_profile_success:
                            initialize_timing(sub_id)
                            grade_item.state = SubmissionState.being_graded
                            grade_item.save()
                            return found, sub_id
                        else:
                            success, similarity_score = utilize_student_metrics.get_similarity_score(profile_dict, grade_item.student_id, course_id)
                            log.debug(similarity_score)
                            if similarity_score <= settings.PEER_GRADER_MIN_SIMILARITY_FOR_MATCHING:
                                initialize_timing(sub_id)
                                grade_item.state = SubmissionState.being_graded
                                grade_item.save()
                                return found, sub_id
                    else:
                        if len(submission_ids) > 1:
                            submission_ids.pop(minimum_index)
                            submission_grader_counts.pop(minimum_index)
                if found:
                    initialize_timing(fallback_sub_id)
                    grade_item = Submission.objects.get(id=fallback_sub_id)
                    grade_item.state = SubmissionState.being_graded
                    grade_item.save()
                    return found, fallback_sub_id

    return found, sub_id


def is_peer_grading_finished_for_submission(submission_id):
    """
    Checks to see whether there are enough reliable peer evaluations of submission to ensure that grading is done.
    Input:
        submission id
    Output:
        Boolean indicating whether or not there are enough reliable evaluations.
    """
    pass




def peer_grading_submissions_pending_for_location(location, grader_id):
    """
    Get submissions that are to graded be graded by the student
    """
    to_be_graded = Submission.objects.filter(
        location=location,
        state=SubmissionState.waiting_to_be_graded,
        next_grader_type="PE",
        is_duplicate=False,
    ).exclude(student_id=grader_id)

    log.debug("Looking for grading for student {0}, found {1}".format(grader_id, to_be_graded))
    #Do some checks to ensure that there are actually items to grade
    return to_be_graded

def peer_grading_submissions_graded_for_location(location, student_id):
    """
    Get submissions that are graded by instructor
    """
    subs_graded = Submission.objects.filter(
        location=location,
        grader__status_code=GraderStatus.success,
        grader__grader_id = student_id,
    )

    return subs_graded

def get_peer_grading_notifications(course_id, student_id):
    student_needs_to_peer_grade = False
    success = True

    student_responses_for_course = Submission.objects.filter(student_id = student_id, course_id=course_id, preferred_grader_type="PE")
    unique_student_locations = [x['location'] for x in
                                student_responses_for_course.values('location').distinct()]
    for location in unique_student_locations:
        location_response_count = student_responses_for_course.filter(location=location).count()
        required_peer_grading_for_location = location_response_count * settings.REQUIRED_PEER_GRADING_PER_STUDENT
        completed_peer_grading_for_location = Grader.objects.filter(grader_id = student_id, submission__location = location).count()
        submissions_pending = peer_grading_submissions_pending_for_location(location, student_id).count()

        if completed_peer_grading_for_location<required_peer_grading_for_location and submissions_pending>0:
            student_needs_to_peer_grade = True
            return success, student_needs_to_peer_grade

    return success, student_needs_to_peer_grade

def get_flagged_submission_notifications(course_id):
    success = False
    flagged_submissions_exist = False
    try:
        flagged_submissions = Submission.objects.filter(state = SubmissionState.flagged, course_id = course_id)
        success = True
        if flagged_submissions.count()>0:
            flagged_submissions_exist = True
    except:
        log.exception("Could not get flagged submissions for course: {0}".format(course_id))

    return success, flagged_submissions_exist

def get_flagged_submissions(course_id):
    success = False
    flagged_submissions_list=[]
    try:
        flagged_submissions = Submission.objects.filter(state = SubmissionState.flagged, course_id = course_id)
        for sub in flagged_submissions:
            f_student_id = sub.student_id
            f_student_response = sub.student_response
            f_submission_id = sub.id
            f_problem_name = sub.problem_id
            f_location = sub.location
            loop_dict = {
                'student_id' : f_student_id,
                'student_response' : f_student_response,
                'submission_id' : f_submission_id,
                'problem_name' : f_problem_name,
                'location' : f_location,
            }
            flagged_submissions_list.append(loop_dict)
        success = True
    except:
        error_message = "Could not retrieve the flagged submissions for course: {0}".format(course_id)
        log.exception(error_message)
        flagged_submissions_list = error_message

    #Have not actually succeeded if there is nothing to show!
    if len(flagged_submissions_list)==0:
        success = False
        error_message = "No flagged submissions exist for course: {0}".format(course_id)
        flagged_submissions_list = error_message

    return success, flagged_submissions_list

def ban_student_from_peer_grading(course_id, student_id, submission_id):
    try:
        student_profile = StudentProfile.objects.get(student_id=student_id)
    except:
        return False, "Could not find the student: {0}".format(student_id)

    student_profile.student_is_staff_banned = True
    student_profile.save()

    try:
        sub = Submission.objects.get(id=submission_id)
    except:
        return False, "Could not find submission with id: {0}".format(submission_id)

    sub.state = SubmissionState.finished
    sub.save()


    return True, "Successful save."

def unflag_student_submission(course_id, student_id, submission_id):
    try:
        sub = Submission.objects.get(id=submission_id)
    except:
        return False, "Could not find submission with id: {0}".format(submission_id)

    if sub.preferred_grader_type!="PE":
        return False, "Attempt to flag a non peer grading submission!"

    successful_peer_grader_count = sub.get_successful_peer_graders().count()
    #If number of successful peer graders equals the needed count, finalize submission.
    if successful_peer_grader_count >= settings.PEER_GRADER_COUNT:
        sub.state = SubmissionState.finished
    else:
        sub.state = SubmissionState.waiting_to_be_graded
    sub.save()

    return True, "Successful save."

def take_action_on_flags(course_id, student_id, submission_id, action):
    success = False
    if action not in VALID_ACTION_TYPES:
        return success, "Action not in valid action types."

    try:
        sub = Submission.objects.get(id=submission_id)
    except:
        error_message = "Could not find a submission with id: {0}".format(submission_id)
        log.exception(error_message)
        return success, error_message

    if sub.state!=SubmissionState.flagged:
        return success, "Submission is no longer flagged."

    success, data = ACTION_HANDLERS[action](course_id, student_id, submission_id)

    return success, data

ACTION_HANDLERS={
    'ban' : ban_student_from_peer_grading,
    'unflag' : unflag_student_submission,
    }

VALID_ACTION_TYPES = ACTION_HANDLERS.keys()


