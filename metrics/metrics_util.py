from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from metrics.charting import render_image
from metrics.models import Timing
from controller.models import  Grader, GraderStatus
import logging

log=logging.getLogger(__name__)

def generate_timing_response(arguments,title):
    try:
        timing_set=Timing.objects.filter(**arguments)
        if timing_set.count()==0:
            return HttpResponse("Did not find anything matching that query.")

        timing_set_values=timing_set.values("start_time", "end_time")
        timing_set_start=[i['start_time'] for i in timing_set_values]
        timing_set_end=[i['end_time'] for i in timing_set_values]
        timing_set_difference=[(timing_set_end[i]-timing_set_start[i]).total_seconds() for i in xrange(0,len(timing_set_end))]

        response=render_image(timing_set_difference,title)

        return True,response
    except:
        return False, "Unexpected error processing image."


def generate_performance_response(arguments,title):
    try:
        sub_arguments={}
        for tag in ['course_id', 'location']:
            if arguments[tag]:
                sub_arguments["submission__" + tag]=arguments[tag]

        grader_set=Grader.objects.filter(**sub_arguments).filter(status_code=GraderStatus.success)

        if arguments['grader_type']:
            grader_set=grader_set.filter(grader_type="ML")

        if grader_set.count()==0:
            return False, "Did not find anything matching that query."

        grader_scores=[x['score'] for x in grader_set.values("score")]


        response=render_image(grader_scores,title)

        return True, response
    except:
        return False, "Unexpected error processing image."


def render_form(post_url):
    url_base = settings.GRADING_CONTROLLER_INTERFACE['url']
    if not url_base.endswith("/"):
        url_base += "/"
    rendered=render_to_string('metrics_display.html',
        {'ajax_url' : url_base,
         'post_url' : post_url
        })

    return rendered


def get_arguments(request):
    course_id = request.POST.get('course_id')
    grader_type = request.POST.get('grader_type')
    location = request.POST.get('location')
    metric_type=request.POST.get('metric_type')

    query_dict = {
        'course_id' : course_id,
        'grader_type' : grader_type,
        'location' : location
    }

    title= 'Data for metric {0} request with params '.format(metric_type)
    arguments = {}
    for k, v in query_dict.items():
        if v:
            arguments[k] = v
            title+= " {0} : {1} ".format(k,v)

    return arguments, title