from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime
import logging

from models import Submission,Grader
import util
import json

log = logging.getLogger(__name__)

@csrf_exempt
@login_required
def submit(request):
    '''
    Xqueue pull script posts objects here.
    '''
    if request.method != 'POST':
        return HttpResponse(util.compose_reply(False, "'submit' must use HTTP POST"))
    else:
        reply_is_valid, header, body = _is_valid_reply(request.POST)

        log.debug("Header: {0}\n Body: {1}".format(header,body))
        if not reply_is_valid:
            log.error("Invalid xqueue object added: request_ip: {0} request.POST: {1}".format(
                util.get_request_ip(request),
                request.POST,
            ))
            return HttpResponse(util.compose_reply(False, 'Incorrect format'))
        else:
            try:
                prompt=util._value_or_default(body['grader_payload']['prompt'],"")
                student_id=util._value_or_default(body['student_info']['anonymous_student_id'])
                location=util._value_or_default(body['grader_payload']['location'])
                course_id=util._value_or_default(body['grader_payload']['course_id'])
                problem_id=util._value_or_default(body['grader_payload']['problem_id'],location)
                grader_settings=util._value_or_default(body['grader_payload']['grader'],"")
                student_response=util._value_or_default(body['student_response'])
                xqueue_submission_id=util._value_or_default(header['submission_id'])
                xqueue_submission_key=util._value_or_default(header['submission_key'])
                state_code="W"
                xqueue_queue_name=util._value_or_default(header["queue_name"])

                submission_time_string=util._value_or_default(body['student_info']['submission_time'])
                student_submission_time=datetime.strptime(submission_time_string,"%Y%m%d%H%M%S")

                sub, created = Submission.objects.get_or_create(
                    prompt=prompt,
                    student_id=student_id,
                    problem_id=problem_id,
                    state=state_code,
                    student_response=student_response,
                    student_submission_time=student_submission_time,
                    xqueue_submission_id=xqueue_submission_id,
                    xqueue_submission_key=xqueue_submission_key,
                    xqueue_queue_name=xqueue_queue_name,
                    location=location,
                    course_id=course_id,
                )

            except Exception as err:
                xqueue_submission_id=util._value_or_default(header['submission_id'])
                xqueue_submission_key=util._value_or_default(header['submission_key'])
                log.error("Error creating submission and adding to database: sender: {0}, submission_id: {1}, submission_key: {2}".format(
                    util.get_request_ip(request),
                    xqueue_submission_id,
                    xqueue_submission_key,
                ))
                return HttpResponse(util.compose_reply(False,'Unable to create submission.'))

            #Handle submission and write to db

            success=handle_submission(sub)

            return HttpResponse(util.compose_reply(success=success, content=''))

def handle_submission(sub):
    try:
        subs_graded_by_instructor,subs_pending_instructor=util.subs_by_instructor(sub.location)

        if((subs_graded_by_instructor+subs_pending_instructor)>=settings.MIN_TO_USE_ML):
            sub.next_grader_type="ML"
        else:
            sub.next_grader_type="IN"

        sub.save()
        log.debug("Created successfully!")
    except:
        log.debug("Creation failed!")
        return False

    return True

def _is_valid_reply(external_reply):
    '''
    Check if external reply is in the right format
        1) Presence of 'xqueue_header' and 'xqueue_body'
        2) Presence of specific metadata in 'xqueue_header'
            ['submission_id', 'submission_key']

    Returns:
        is_valid:       Flag indicating success (Boolean)
        submission_id:  Graded submission's database ID in Xqueue (int)
        submission_key: Secret key to match against Xqueue database (string)
        score_msg:      Grading result from external grader (string)
    '''
    fail = (False,-1,'')

    try:
        header = json.loads(external_reply['xqueue_header'])
        body = json.loads(external_reply['xqueue_body'])
    except KeyError:
        return fail

    if not isinstance(header,dict) or not isinstance(body,dict):
        return fail

    for tag in ['submission_id', 'submission_key', 'queue_name']:
        if not header.has_key(tag):
            log.debug("{0} not found in header".format(tag))
            return fail

    for tag in ['grader_payload', 'student_response', 'student_info']:
        if not body.has_key(tag):
            log.debug("{0} not found in body".format(tag))
            return fail

    try:
        body['grader_payload']=json.loads(body['grader_payload'])
        body['student_info']=json.loads(body['student_info'])
    except:
        return fail

    return True,header,body

