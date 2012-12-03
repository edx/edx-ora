from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from controller import util
from metrics.charting import render_image
from metrics.metrics_util import render_form, get_arguments
import metrics_util

from models import Timing

_INTERFACE_VERSION=1

@csrf_exempt
@login_required
def metrics_form(request):
    if request.method == "POST":

        arguments,title=get_arguments(request)

        tags=['metric_type']
        for tag in tags:
            if tag not in arguments:
                return HttpResponse("Request missing needed tag metric type.")

        metric_type=arguments.get('metric_type').lower()

        available_metric_types=['timing', 'performance']

        if metric_type not in available_metric_types:
            return HttpResponse("Could not find the requested type of metric: {0}".format(metric_type))

        if metric_type=="timing":
            arguments,title=get_arguments(request)
            success,response=generate_timing_response(arguments,title)

        timing_set=Timing.objects.filter(**arguments)
        if timing_set.count()==0:
            return HttpResponse("Did not find anything matching that query.")

        timing_set_values=timing_set.values("start_time", "end_time")
        timing_set_start=[i['start_time'] for i in timing_set_values]
        timing_set_end=[i['end_time'] for i in timing_set_values]
        timing_set_difference=[(timing_set_end[i]-timing_set_start[i]).total_seconds() for i in xrange(0,len(timing_set_end))]

        response=render_image(timing_set_difference,title)

        return response

    elif request.method == "GET":

        rendered=render_form("metrics/timing/")
        return HttpResponse(rendered)

@csrf_exempt
@login_required
def timing_metrics(request):
    """
    Request is an HTTP get request with the following keys:
        Course_id
        Grader_type
        Location
    """

    if request.method != "POST":
        return util._error_response("Must make a POST request.", _INTERFACE_VERSION)

    arguments,title=get_arguments(request)
    success, response=metrics_util.generate_timing_response(arguments,title)

    if not success:
        return util._error_response(str(response),_INTERFACE_VERSION)

    return util._success_response({'img' : response}, _INTERFACE_VERSION)


@csrf_exempt
@login_required
def student_performance_metrics(request):
    """
    Request is an HTTP get request with the following keys:
        Course_id
        Grader_type
        Location
    """

    if request.method != "POST":
        return util._error_response("Request type must be POST", _INTERFACE_VERSION)

    arguments,title=get_arguments(request)
    success, response=metrics_util.generate_performance_response(arguments,title)

    if not success:
        return util._error_response(str(response),_INTERFACE_VERSION)

    return util._success_response({'img' : response},_INTERFACE_VERSION)