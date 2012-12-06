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
    available_metric_types=['timing', 'performance']
    if request.method == "POST":

        arguments,title=get_arguments(request)

        tags=['metric_type']
        for tag in tags:
            if tag not in request.POST:
                return HttpResponse("Request missing needed tag metric type.")

        metric_type=request.POST.get('metric_type').lower()

        if metric_type not in available_metric_types:
            return HttpResponse("Could not find the requested type of metric: {0}".format(metric_type))

        if metric_type=="timing":
            success,response=metrics_util.generate_timing_response(arguments,title)

        if metric_type=="performance":
            success,response=metrics_util.generate_performance_response(arguments,title)

        return response

    elif request.method == "GET":

        rendered=render_form("metrics/metrics/",available_metric_types)
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