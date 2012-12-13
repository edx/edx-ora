from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from controller import util
from metrics.charting import render_image
from metrics.metrics_util import render_form, get_arguments
import metrics_util
from django.template.loader import render_to_string

from models import Timing
import logging

log=logging.getLogger(__name__)

_INTERFACE_VERSION=1

@csrf_exempt
@login_required
def metrics_form(request):

    if request.method == "POST":

        arguments,title=get_arguments(request)

        tags=['metric_type']
        for tag in tags:
            if tag not in request.POST:
                return HttpResponse("Request missing needed tag metric type.")

        metric_type=request.POST.get('metric_type').lower()
        success,response = metrics_util.render_requested_metric(metric_type,arguments,title)

        if not success:
            return HttpResponse(response)

        return HttpResponse(response,"image/png")

    elif request.method == "GET":
        available_metric_types = [k for k in metrics_util.AVAILABLE_METRICS]
        rendered=render_form("metrics/metrics/",available_metric_types)
        return HttpResponse(rendered)

@csrf_exempt
@login_required
def error_dashboard(request):
    """
    Display a dashboard with good debugging/error metrics
    """
    base_xsize=5
    base_ysize=3
    if request.method != "GET":
        return util._error_response("Must use Http get request")

    m_renderer=metrics_util.MetricsRenderer(base_xsize,base_ysize)
    success, msg = m_renderer.run_query({},'currently_being_graded')
    success, currently_being_graded=m_renderer.chart_image()

    rendered = render_to_string('error_dashboard.html', {
        'metric_images' : [HttpResponse(currently_being_graded,"image/png")]
    })

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