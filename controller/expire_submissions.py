import datetime
import json
from django.conf import settings
from django.utils import timezone
import grader_util
import util
import logging
from models import GraderStatus, SubmissionState, Submission
from staff_grading import staff_grading_util

log = logging.getLogger(__name__)

error_template = u"""

<section>
    <div class="shortform">
        <div class="result-errors">
          There was an error with your submission.  Please contact the course staff.
        </div>
    </div>
    <div class="longform">
        <div class="result-errors">
          {errors}
        </div>
    </div>
</section>

"""

def reset_timed_out_submissions(subs):
    """
    Check if submissions have timed out, and reset them to waiting to grade state if they have
    Input:
        subs - A QuerySet of submissions
    Output:
        status code indicating success
    """
    now = timezone.now()
    min_time = datetime.timedelta(seconds=settings.RESET_SUBMISSIONS_AFTER)
    timed_out_subs=subs.filter(date_modified__lt=now-min_time)
    timed_out_sub_count=timed_out_subs.count()
    count = 0

    for i in xrange(0, timed_out_sub_count):
        sub = subs[i]
        if sub.state == SubmissionState.being_graded:
            sub.state = SubmissionState.waiting_to_be_graded

            #If an instructor checks out a submission after ML grading has started,
            # this resets it to ML if the instructor times out
            if (sub.next_grader_type=="IN" and staff_grading_util.finished_submissions_graded_by_instructor(sub.location).count()>=settings.MIN_TO_USE_ML):
                sub.next_grader_type="ML"
            sub.save()
            count += 1

    if count>0:
        log.debug("Reset {0} submissions that had timed out in their current grader.".format(count))

    return True


def get_submissions_that_have_expired(subs):
    """
    Check if submissions have expired, and return them if they have.
    Input:
        subs - A queryset of submissions
    """
    now = timezone.now()
    min_time = datetime.timedelta(seconds=settings.EXPIRE_SUBMISSIONS_AFTER)
    expired_subs=subs.filter(date_modified__lt=now-min_time)

    return list(expired_subs)

def finalize_expired_submissions(timed_out_list):

    for sub in timed_out_list:
        finalize_expired_submission(sub)

    log.debug("Reset {0} submissions that had timed out in their current grader.".format(len(timed_out_list)))

    return True

def finalize_expired_submission(sub):
    """
    Expire submissions by posting back to LMS with error message.
    Input:
        timed_out_list from check_if_expired method
    Output:
        Success code.
    """

    grader_dict = {
        'score': 0,
        'feedback': error_template.format(errors="Error scoring submission."),
        'status': GraderStatus.failure,
        'grader_id': "0",
        'grader_type': sub.next_grader_type,
        'confidence': 1,
        'submission_id' : sub.id,
        }

    sub.state = SubmissionState.finished
    sub.save()

    grade = grader_util.create_grader(grader_dict,sub)

    return True

def reset_ml_to_in_if_too_few(sub):
    """
    Resets a submission marked for ml grading to instructor grading if there are too few instructor graded submissions
    in the queue.  This happens when the instructor skips a lot of submissions.
    Input:
        A submission
    Output:
        Success code
    """

    sub.state=SubmissionState.waiting_to_be_graded
    sub.next_grader_type="IN"
    sub.save()

    return True