import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from controller.models import Submission
from controller import util
import lms_interface
import requests
import urlparse
from django.template.loader import render_to_string

log = logging.getLogger(__name__)

@csrf_exempt
def peer_grading(request):
    """
    Temporary peer grading view.  Can be removed once real peer grading is wired in.
    Handles both rendering and AJAX Posts.
    """
    post_data={}
    saved=False
    location="MITx/6.002x"
    student_id="5"

    if request.method == 'POST':
        post_data=request.POST.dict().copy()
        for tag in ['score', 'submission_id', 'max_score', 'student_id', 'feedback', 'location', 'type']:
            if not post_data.has_key(tag):
                return HttpResponse("Failed to find needed key {0}".format(tag))

        try:
            post_data['score']=int(post_data['score'])
            post_data['max_score']=int(post_data['max_score'])
            post_data['submission_id']=int(post_data['submission_id'])
            post_data['student_id'] = post_data['student_id']
            post_data['feedback']="<p>" + post_data['feedback'] + "</p>"
        except:
            return HttpResponse("Can't parse score into an int.")

        if post_data['type']=="calibration":
            calibration_data={
                'submission_id' : post_data['submission_id'],
                'score' : post_data['score'],
                'feedback' : post_data['feedback'],
                'student_id' : post_data['student_id'],
                'location' : post_data['location'],
            }
            try:
                lms_interface.create_and_save_calibration_record(calibration_data)
            except:
                return HttpResponse("Could not create calibration record.")
        elif post_data['type'] == "submission":
            try:
                created,header=util.create_and_save_grader_object({
                    'score': post_data['score'],
                    'status' : "S",
                    'grader_id' : post_data['student_id'],
                    'grader_type' : "PE",
                    'confidence' : 1,
                    'submission_id' : post_data['submission_id'],
                    'feedback' : post_data['feedback'],
                    })
            except:
                return HttpResponse("Cannot create grader object.")
        else:
            return HttpResponse("Invalid grader type.")

    if request.method == 'GET':
        post_data={}
        (success,data)=lms_interface.check_calibration_status({'problem_id' : location, 'student_id' : student_id})
        calibrated=data['calibrated']
        url_base=settings.GRADING_CONTROLLER_INTERFACE['url']
        if not url_base.endswith("/"):
            url_base+="/"

        if calibrated:
            found,sub_id=util.get_single_peer_grading_item(location,student_id)
            post_data['submission_id']=sub_id
            if not found:
                try:
                    post_data.pop('submission_id')
                except:
                    return HttpResponse("Could not find submission_id in post_data")
                return HttpResponse("No available grading.  Check back later.")

            try:
                sub_id=post_data['submission_id']
                sub=Submission.objects.get(id=sub_id)
            except:
                try:
                    post_data.pop('submission_id')
                except:
                    return HttpResponse("Could not find key submission_id in post data.")
                return HttpResponse("Invalid submission id in session.  Cannot find it.  Try reloading.")

            if sub.state in ["F"]:
                post_data.pop('submission_id')
                return HttpResponse("Invalid submission id in session.  Sub is marked finished.  Try reloading.")

            rendered=render_to_string('instructor_grading.html', {
                'score_points': [i for i in xrange(0,sub.max_score+1)],
                'ajax_url' : url_base,
                'text' : sub.student_response,
                'location' : sub.location,
                'prompt' : sub.prompt,
                'rubric' : sub.rubric,
                'sub_id' : sub.id,
                'max_score' : sub.max_score,
                'type' : 'submission',
                'student_id' : student_id,
                })
            return HttpResponse(rendered)
        else:
            (success,data)=lms_interface.get_calibration_essay({'problem_id' : location,'student_id' : student_id})

            if not success:
                return HttpResponse("Error getting calibration essay.")

            rendered=render_to_string("instructor_grading.html", {
                'score_points': [i for i in xrange(0,data['max_score']+1)],
                'ajax_url' : url_base,
                'text' : data['student_response'],
                'location' : location,
                'prompt' : data['prompt'],
                'rubric' : data['rubric'],
                'sub_id' : data['submission_id'],
                'max_score' : data['max_score'],
                'type' : 'calibration',
                'student_id' : student_id,
            })

            return HttpResponse(rendered)


