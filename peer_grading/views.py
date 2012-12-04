import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from controller.grader_util import create_and_handle_grader_object

from controller.models import Submission
from controller import util
import lms_interface
import requests
import urlparse
from django.template.loader import render_to_string
from peer_grading.calibration import create_and_save_calibration_record, get_calibration_essay, check_calibration_status
from peer_grading.peer_grading_util import get_single_peer_grading_item
from controller.models import SubmissionState, GraderStatus

log = logging.getLogger(__name__)

@csrf_exempt
@login_required
def peer_grading(request):
    """
    Temporary peer grading view.  Can be removed once real peer grading is wired in.
    Handles both rendering and AJAX Posts.
    """
    post_data = {}
    saved = False
    location = "MITx/6.002x/problem/OETest"
    student_id = "2"

    if request.method == 'POST':
        post_data = request.POST.dict().copy()
        for tag in ['score', 'submission_id', 'max_score', 'student_id', 'feedback', 'type']:
            if not post_data.has_key(tag):
                return HttpResponse("Failed to find needed key {0}".format(tag))

        try:
            post_data['score'] = int(post_data['score'])
            post_data['max_score'] = int(post_data['max_score'])
            post_data['submission_id'] = int(post_data['submission_id'])
            post_data['student_id'] = post_data['student_id']
            post_data['feedback'] = {'feedback' : post_data['feedback']}
        except:
            return HttpResponse("Can't parse score into an int.")

        if post_data['type'] == "calibration":
            calibration_data = {
                'submission_id': post_data['submission_id'],
                'score': post_data['score'],
                'feedback': post_data['feedback'],
                'student_id': student_id,
                'location': location,
            }
            try:
                success, data = create_and_save_calibration_record(calibration_data)
            except:
                return HttpResponse("Could not create calibration record.")

            if not success:
                return HttpResponse(data)

            return HttpResponse("Calibration record created!  Reload for next essay.")

        elif post_data['type'] == "submission":
            try:
                created, header = create_and_handle_grader_object({
                    'score': post_data['score'],
                    'status': GraderStatus.success,
                    'grader_id': student_id,
                    'grader_type': "PE",
                    'confidence': 1,
                    'submission_id': post_data['submission_id'],
                    'feedback': post_data['feedback'],
                    'errors' : "",
                })
            except:
                return HttpResponse("Cannot create grader object.")

            return HttpResponse("Submission object created!  Reload for next essay.")
        else:
            return HttpResponse("Invalid grader type.")

    if request.method == 'GET':
        post_data = {}
        success, data = check_calibration_status(location, student_id)
        if not success:
            return HttpResponse(data)

        calibrated = data['calibrated']
        url_base = settings.GRADING_CONTROLLER_INTERFACE['url']
        if not url_base.endswith("/"):
            url_base += "/"

        if calibrated:
            found, sub_id = get_single_peer_grading_item(location, student_id)
            post_data['submission_id'] = sub_id
            if not found:
                try:
                    post_data.pop('submission_id')
                except:
                    return HttpResponse("Could not find submission_id in post_data")
                return HttpResponse("No available grading.  Check back later.")

            try:
                sub_id = post_data['submission_id']
                sub = Submission.objects.get(id=int(sub_id))
            except:
                try:
                    post_data.pop('submission_id')
                except:
                    return HttpResponse("Could not find key submission_id in post data.")
                return HttpResponse("Invalid submission id in session.  Cannot find it.  Try reloading.")

            if sub.state in [SubmissionState.finished]:
                post_data.pop('submission_id')
                return HttpResponse("Invalid submission id in session.  Sub is marked finished.  Try reloading.")

            rendered = render_to_string('instructor_grading.html', {
                'score_points': [i for i in xrange(0, sub.max_score + 1)],
                'ajax_url': url_base,
                'text': sub.student_response,
                'location': sub.location,
                'prompt': sub.prompt,
                'rubric': sub.rubric,
                'sub_id': sub.id,
                'max_score': sub.max_score,
                'type': 'submission',
                'student_id': student_id,
            })
            return HttpResponse(rendered)
        else:
            success, data = get_calibration_essay(location, student_id)

            if not success:
                return HttpResponse(data)

            rendered = render_to_string("instructor_grading.html", {
                'score_points': [i for i in xrange(0, data['max_score'] + 1)],
                'ajax_url': url_base,
                'text': data['student_response'],
                'location': location,
                'prompt': data['prompt'],
                'rubric': data['rubric'],
                'sub_id': data['submission_id'],
                'max_score': data['max_score'],
                'type': 'calibration',
                'student_id': student_id,
            })

            return HttpResponse(rendered)


