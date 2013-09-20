from django.db.models import Count
from controller.models import SubmissionState, GraderStatus, Grader, Submission, NotificationTypes
import logging
from metrics import metrics_util
from django.conf import settings
from metrics import utilize_student_metrics
from metrics.models import StudentProfile
from controller import control_util
from controller.capsules import CourseCapsule, LocationCapsule

log = logging.getLogger(__name__)

class PeerLocation(LocationCapsule):
    """
    Ecapsulates information that graders may want about a location.
    """
    def __init__(self, location, student_id):
        self.student_id = student_id
        super(PeerLocation, self).__init__(location)

    def submitted(self):
        return self.location_submissions().filter(student_id=self.student_id, preferred_grader_type="PE")

    def submitted_count(self):
        return self.submitted().count()

    def required_count(self):
        required_list = []
        for sub in self.submitted():
            control = control_util.SubmissionControl(sub)
            required_list.append(control.required_peer_grading_per_student)
        return sum(required_list)

    def graded(self):
        """
        Finds all submissions that have been graded, and are now complete.
        """
        return self.location_submissions().filter(
            grader__status_code= GraderStatus.success,
            grader__grader_id = self.student_id,
            )

    def graded_count(self):
        """
        Counts graded submissions.
        """
        return self.graded().count()

    def submissions_completed_peer_grading(self):
        """
        Gets all non-duplicate submissions that have "completed" the peer evaluation process.
        @return:
        """
        return self.location_submissions().exclude(student_id=self.student_id).filter(
            state=SubmissionState.finished,
            posted_results_back_to_queue=True,
            is_duplicate=False,
            preferred_grader_type="PE",
            ).exclude(grader__grader_id=self.student_id)

    def pending(self):
        """
        Gets all non-duplicate submissions that are pending instructor grading.
        """
        return self.location_submissions().exclude(student_id=self.student_id).filter(
            state=SubmissionState.waiting_to_be_graded,
            next_grader_type="PE",
            is_duplicate=False,
            grader__status_code=GraderStatus.success,
            grader__grader_type__in=["PE","BC"],
            ).exclude(grader__grader_id=self.student_id)

    def pending_count(self):
        """
        Counts pending submissions.
        """
        return self.pending().count()


    def next_item(self):
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
        to_be_graded = self.pending()
        #Do some checks to ensure that there are actually items to grade
        if to_be_graded.count()>0:
            course_id = to_be_graded[0].course_id
            submissions_to_grade = (to_be_graded
                                    .annotate(num_graders=Count('grader'))
                                    .values("num_graders", "id")
                                    .order_by("date_created")[:50])
            return self._determine_next_submission_to_grade(submissions_to_grade, course_id)

        # In the case where we set the number of peer assessments that a student must give
        # to a number higher than the number that each submission is expected to get receive,
        # we might starve a peer grader because all submissions have received the requisite number of grades.
        # In this case, we want to give the waiting peer grader an already "complete" submission, so s/he can
        # add a grade to that one.
        if control_util.SubmissionControl.peer_grade_finished_subs(self):
            already_completed = self.submissions_completed_peer_grading()
            if already_completed.count() > 0 and self.graded_count() < self.required_count():
                log.info("location {}: finding completed submission to give to peer grader {}".format(self.location,
                                                                                                      self.student_id))
                course_id = already_completed[0].course_id
                submissions_to_grade = (already_completed
                                        .annotate(num_graders=Count('grader'))
                                        .values("num_graders", "id")
                                        .order_by("num_graders")[:50])
                return self._determine_next_submission_to_grade(submissions_to_grade, course_id)
        return found, sub_id

    def _determine_next_submission_to_grade(self, submissions_to_grade, course_id):
        """
        Helper function that
        #Ensure that student hasn't graded this submission before!
        #Also ensures that all submissions are searched through if student has graded the minimum one
        @param submissions_to_grade:
        @param course_id:
        @return:
        """
        found = False
        sub_id = 0

        submission_grader_counts = [p['num_graders'] for p in submissions_to_grade]

        submission_ids = [p['id'] for p in submissions_to_grade]

        student_profile_success, profile_dict = utilize_student_metrics.get_student_profile(self.student_id, course_id)
        fallback_sub_id = None
        for i in xrange(len(submission_ids)):
            minimum_index = submission_grader_counts.index(min(submission_grader_counts))
            grade_item = Submission.objects.get(id=int(submission_ids[minimum_index]))
            previous_graders = [p.grader_id for p in grade_item.get_successful_peer_graders()]
            if self.student_id not in previous_graders:
                found = True
                sub_id = grade_item.id

                if fallback_sub_id is None:
                    fallback_sub_id = grade_item.id

                if not student_profile_success:
                    grade_item.state = SubmissionState.being_graded
                    grade_item.save()
                    return found, sub_id
                else:
                    success, similarity_score = utilize_student_metrics.get_similarity_score(profile_dict, grade_item.student_id, course_id)
                    if similarity_score <= settings.PEER_GRADER_MIN_SIMILARITY_FOR_MATCHING:
                        grade_item.state = SubmissionState.being_graded
                        grade_item.save()
                        return found, sub_id
            else:
                if len(submission_ids) > 1:
                    submission_ids.pop(minimum_index)
                    submission_grader_counts.pop(minimum_index)
        if found:
            grade_item = Submission.objects.get(id=fallback_sub_id)
            grade_item.state = SubmissionState.being_graded
            grade_item.save()
            return found, fallback_sub_id

        return found, sub_id


class PeerCourse(CourseCapsule):
    """
    Encapsulates information that graders may want about a course.
    """

    def __init__(self, course_id, student_id):
        self.student_id = student_id
        super(PeerCourse, self).__init__(course_id)

    def next_item(self):
        """
        Gets the next item to grade in the course.
        """
        raise NotImplementedError()

    def submitted(self):
        return Submission.objects.filter(student_id = self.student_id, course_id=self.course_id, preferred_grader_type="PE")

    def notifications(self):
        """
        Checks to see if  a notification needs to be shown
        """
        student_needs_to_peer_grade = False
        success = True

        student_responses_for_course = self.submitted()
        unique_student_locations = [x['location'] for x in student_responses_for_course.values('location').distinct()]
        for location in unique_student_locations:
            pl = PeerLocation(location, self.student_id)

            if (pl.graded_count()<pl.required_count() and
                    (pl.pending_count()>0 or
                     control_util.SubmissionControl.peer_grade_finished_subs(pl))):
                student_needs_to_peer_grade = True
                break

        return success, student_needs_to_peer_grade

def get_flagged_submission_notifications(course_id):
    success = False
    flagged_submissions_exist = False
    try:
        flagged_submissions = Submission.objects.filter(state = SubmissionState.flagged, course_id = course_id)
        success = True
        if flagged_submissions.count()>0:
            flagged_submissions_exist = True
    except Exception:
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
    except Exception:
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
    except Exception:
        return False, "Could not find the student: {0}".format(student_id)

    student_profile.student_is_staff_banned = True
    student_profile.save()

    try:
        sub = Submission.objects.get(id=submission_id)
    except Exception:
        return False, "Could not find submission with id: {0}".format(submission_id)

    sub.state = SubmissionState.finished
    sub.save()


    return True, "Successful save."

def unflag_student_submission(course_id, student_id, submission_id):
    try:
        sub = Submission.objects.get(id=submission_id)
    except Exception:
        return False, "Could not find submission with id: {0}".format(submission_id)


    if sub.preferred_grader_type == "PE":
        control = control_util.SubmissionControl(sub)
        successful_peer_grader_count = sub.get_successful_peer_graders().count()
        #If number of successful peer graders equals the needed count, finalize submission.
        if successful_peer_grader_count >= control.peer_grader_count:
            sub.state = SubmissionState.finished
        else:
            sub.state = SubmissionState.waiting_to_be_graded
    else:
        # if we're not peer graded, assume that the submission still needs to be graded
        sub.state = SubmissionState.waiting_to_be_graded
        sub.next_grader_type = sub.preferred_grader_type
    sub.save()

    return True, "Successful save."

def take_action_on_flags(course_id, student_id, submission_id, action):
    success = False
    if action not in VALID_ACTION_TYPES:
        return success, "Action not in valid action types."

    try:
        sub = Submission.objects.get(id=submission_id)
    except Exception:
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


