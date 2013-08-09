from django.conf import settings
from controller.create_grader import create_grader
from controller.models import Submission
import logging
from controller.models import SubmissionState, GraderStatus
from metrics import metrics_util
from metrics.timing_functions import initialize_timing
from controller import util
from ml_grading import ml_grading_util

log = logging.getLogger(__name__)

class StaffLocation(object):
    """
    Encapsulates student submissions that need staff action for a particular location.
    """
    def __init__(self,location):
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
        Finds all submissions that have been instructor graded, and are now complete.
        """
        return self.location_submissions.filter(previous_grader_type="IN", state=SubmissionState.finished)

    @property
    def graded_count(self):
        """
        Counts graded submissions.
        """
        return self.graded.count()

    @property
    def pending(self):
        """
        Gets all non-duplicate submissions that are pending instructor grading.
        """
        return self.location_submissions.filter(
            next_grader_type="IN",
            state=SubmissionState.waiting_to_be_graded,
            is_duplicate=False,
            is_plagiarized=False
        )

    @property
    def pending_count(self):
        """
        Counts pending submissions.
        """
        return self.pending.count()

    @property
    def graded_submission_text(self):
        """
        Gets the text for all submissions that have been instructor scored.
        """
        sub_text=self.graded.values('student_response').distinct()
        return [s['student_response'] for s in sub_text]

    @property
    def item_to_score(self):
        """
        Gets an item for an instructor to score.
        """
        subs_graded = self.graded_count
        success= ml_grading_util.check_for_all_model_and_rubric_success(self.location)

        if subs_graded < settings.MIN_TO_USE_ML or not success:
            to_be_graded = self.pending

            finished_submission_text=self.graded_submission_text

            for tbg in to_be_graded:
                #In some cases, this causes a model query error without the try/except block due to the checked out state
                if tbg is not None and tbg.student_response not in finished_submission_text:
                    tbg.state = SubmissionState.being_graded
                    tbg.next_grader_type="IN"
                    tbg.save()
                    found = True
                    sub_id = tbg.id

                    #Insert timing initialization code
                    initialize_timing(sub_id)

                    return found, sub_id

        #If nothing is found, return false
        return False, 0
    
    @property
    def item_to_rescore(self):
        """
        Gets an item for an instructor to rescore (items have already been machine scored, ML)
        """
        success= ml_grading_util.check_for_all_model_and_rubric_success(self.location)
        
        if success:
            #Order by confidence if we are looking for finished ML submissions
            finished_submission_text=self.graded_submission_text
            to_be_graded = self.pending.filter(grader__status_code=GraderStatus.success).order_by('grader__confidence')
    
            for tbg in to_be_graded:
                if tbg is not None and tbg.student_response not in finished_submission_text:
                    tbg.state = SubmissionState.being_graded
                    tbg.next_grader_type="IN"
                    tbg.save()
                    found = True
                    sub_id = tbg.id
    
                    #Insert timing initialization code
                    initialize_timing(sub_id)
    
                    return found, sub_id
    
                    #If nothing is found, return false
        return False, 0

    @property
    def next_item(self):
        """
        Looks for submissions to score.  If nothing exists, look for something to rescore.
        """
        success, sid = self.item_to_score
        if not success:
            success, sid = self.item_to_rescore
        return success, sid


class StaffCourse(object):
    """
    Encapsulates information that staff may want about a course.
    """
    def __init__(self, course_id):
        self.course_id = course_id

    @property
    def locations(self):
        """
        Gets all locations in a course.
        """
        return [x['location'] for x in
                list(Submission.objects.filter(course_id=self.course_id).values('location').distinct())]

    @property
    def next_item(self):
        """
        Gets the next item that a staff member needs to grade in the course.
        """
        for location in self.locations:
            sl = StaffLocation(location)
            success, sub_id = sl.item_to_score
            if success:
                return success, sub_id

        for location in self.locations:
            sl = StaffLocation(location)
            success, sub_id = sl.item_to_rescore
            if success:
                return success, sub_id

        return False, 0

    @property
    def notifications(self):
        """
        Checks to see if the staff member needs to be shown a notification (ie, needs to grade something)
        """
        staff_needs_to_grade = False
        success = True

        for location in self.locations:
            sl = StaffLocation(location)
            min_scored_for_location=settings.MIN_TO_USE_PEER
            location_ml_count = Submission.objects.filter(location=location, preferred_grader_type="ML").count()
            if location_ml_count>0:
                min_scored_for_location=settings.MIN_TO_USE_ML

            location_scored_count = sl.graded_count
            submissions_pending = sl.all_pending_count

            if location_scored_count<min_scored_for_location and submissions_pending>0:
                staff_needs_to_grade= True
                return success, staff_needs_to_grade

        return success, staff_needs_to_grade

def generate_ml_error_message(ml_error_info):
    """
    Generates a message to send to the staff grading service from a dictionary returned by ml_grading_util.get_ml_errors
    Input:
        Dictionary with keys 'kappa', 'mean_absolute_error', 'date_created', 'number_of_essays'
    Output:
        String to send to staff grading service
    """

    ml_message_template="""
    Latest model created on {date_created}.  Contains {number_of_essays} essays.
    Mean absolute error is {mean_absolute_error} and kappa is {kappa}.
    """

    ml_message=ml_message_template.format(
        date_created=ml_error_info['date_created'],
        number_of_essays=ml_error_info['number_of_essays'],
        mean_absolute_error=ml_error_info['mean_absolute_error'],
        kappa=ml_error_info['kappa'],
    )

    return ml_message

def set_instructor_grading_item_back_to_ml(submission_id):
    """
    Sets a submission from instructor grading to ML.
    Input:
        Submission id
    Output:
        Boolean success, submission or error message
    """
    success, sub=check_submission_id(submission_id)

    if not success:
        return success, sub

    grader_dict={
        'feedback' : 'Instructor skipped',
        'status' : GraderStatus.failure,
        'grader_id' : 1,
        'grader_type' : "IN",
        'confidence' : 1,
        'score' : 0,
        'errors' : "Instructor skipped the submission."
    }

    sub.next_grader_type="ML"
    sub.state=SubmissionState.waiting_to_be_graded
    sub.save()
    create_grader(grader_dict,sub)

    return True, sub

def check_submission_id(submission_id):
    if not isinstance(submission_id,Submission):
        try:
            sub=Submission.objects.get(id=submission_id)
        except Exception:
            error_message="Could not find a submission id."
            log.exception(error_message)
            return False, error_message
    else:
        sub=submission_id

    return True, sub

def set_ml_grading_item_back_to_instructor(submission_id):
    """
    Sets a submission from ML grading to instructor without creating a grader object.
    Input:
        Submission id
    Output:
        Boolean success, submission or error message
    """
    success, sub=check_submission_id(submission_id)

    if not success:
        return success, sub

    sub.next_grader_type="IN"
    sub.state=SubmissionState.waiting_to_be_graded
    sub.save()

    return True, sub