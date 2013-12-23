from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from controller import util
import metrics_util

import logging

from statsd import statsd

log=logging.getLogger(__name__)

_INTERFACE_VERSION=1

@csrf_exempt
@statsd.timed('open_ended_assessment.grading_controller.metrics.views.time',
    tags=['function:metrics_form'])
@login_required
def metrics_form(request):

    if request.method == "POST":

        tags=['metric_type']
        for tag in tags:
            if tag not in request.POST:
                return HttpResponse("Request missing needed tag metric type.")

        arguments,title=metrics_util.get_arguments(request)
        metric_type=request.POST.get('metric_type').lower()
        success,response = metrics_util.render_requested_metric(metric_type,arguments,title, type="jquery")

        return response

    elif request.method == "GET":
        available_metric_types = [k for k in metrics_util.AVAILABLE_METRICS]
        rendered=metrics_util.render_form("metrics/metrics/",available_metric_types)
        return HttpResponse(rendered)

@csrf_exempt
@statsd.timed('open_ended_assessment.grading_controller.metrics.views.time',
    tags=['function:data_dump_form'])
@login_required
def data_dump_form(request):
    return metrics_util.dump_form(request,"data_dump")

@csrf_exempt
@statsd.timed('open_ended_assessment.grading_controller.metrics.views.time',
    tags=['function:message_dump_form'])
@login_required
def message_dump_form(request):
    return metrics_util.dump_form(request,"message_dump")

@csrf_exempt
def student_data_dump_form(request):
    return metrics_util.dump_form(request,"student_data_dump")

@csrf_exempt
@login_required
def error_dashboard(request):
    """
    Display a dashboard with good debugging/error metrics
    """
    base_xsize=20
    base_ysize=10
    if request.method != "GET":
        return util._error_response("Must use Http get request")

    m_renderer=metrics_util.MetricsRenderer(base_xsize,base_ysize)
    success, msg = m_renderer.run_query({'grader_type' : "ML"},'currently_being_graded')
    if not success:
        return HttpResponse(msg)

    success, currently_being_graded=m_renderer.chart_image()

    return HttpResponse(currently_being_graded,"image/png")



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

    arguments,title=metrics_util.get_arguments(request)
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

    arguments,title=metrics_util.get_arguments(request)
    success, response=metrics_util.generate_performance_response(arguments,title)

    if not success:
        return util._error_response(str(response),_INTERFACE_VERSION)

    return util._success_response({'img' : response},_INTERFACE_VERSION)