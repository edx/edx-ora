import datetime
import json
from django.conf import settings
from django.utils import timezone
import controller.grader_util as grader_util
import controller.util as util
import logging
from controller.models import GRADER_STATUS,SUBMISSION_STATE

log = logging.getLogger(__name__)

def reset_timed_out_submissions(subs):
    """
    Check if submissions have timed out, and reset them to waiting to grade state if they have
    Input:
        subs - A QuerySet of submissions
    Output:
        status code indicating success
    """
    now = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
    min_time = datetime.timedelta(seconds=settings.RESET_SUBMISSIONS_AFTER)
    timed_out_subs=subs.filter(date_modified__lt=now-min_time)
    timed_out_sub_count=timed_out_subs.count()
    count = 0

    for i in xrange(0, timed_out_sub_count):
        sub = subs[i]
        if sub.state == SUBMISSION_STATE['being_graded']:
            sub.state = SUBMISSION_STATE['waiting_to_be_graded']
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
    now = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
    min_time = datetime.timedelta(seconds=settings.EXPIRE_SUBMISSIONS_AFTER)
    expired_subs=subs.filter(date_modified__lt=now-min_time)

    return list(expired_subs)


def post_expired_submissions_to_xqueue(timed_out_list):
    """
    Expire submissions by posting back to LMS with error message.
    Input:
        timed_out_list from check_if_expired method
    Output:
        Success code.
    """
    for sub in timed_out_list:
        sub.state = SUBMISSION_STATE['finished']
        grader_dict = {
            'score': 0,
            'feedback': "Error scoring submission.",
            'status_code': GRADER_STATUS['finished'],
            'grader_id': "0",
            'grader_type': sub.next_grader_type,
            'confidence': 1,
        }
        sub.save()
        #TODO: Currently looks up submission object twice.  Fix in future.
        success, header = grader_util.create_and_save_grader_object(grader_dict)

        xqueue_session = util.xqueue_login()

        error, msg = util.post_results_to_xqueue(xqueue_session, json.dumps(header), json.dumps(grader_dict))

    log.debug("Reset {0} submissions that had timed out in their current grader.".format(len(timed_out_list)))
    return error, msg