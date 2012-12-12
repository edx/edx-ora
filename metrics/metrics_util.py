from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
import charting
from django.db.models import Count
from metrics.models import Timing
from controller.models import  Submission, SubmissionState, Grader, GraderStatus
import logging
import matplotlib.pyplot as plt
import StringIO
from matplotlib import numpy as np

log = logging.getLogger(__name__)

IMAGE_ERROR_MESSAGE = "Error processing image."

def render_requested_metric(metric_type,arguments,title):
    """
    Returns a graph for a custom input metric
    Input:
        Metric type, parameters
    Output:
        Boolean success/fail, error message or rendered image
    """
    available_metric_types=[k for k in AVAILABLE_METRICS]

    if metric_type not in available_metric_types:
        return False, "Could not find the requested type of metric: {0}".format(metric_type)

    success,response=AVAILABLE_METRICS[metric_type](arguments,title)

    return success,response

def generate_counts_per_problem(arguments, title, state):
    """
    Generate counts of number of attempted problems with a specific state.  Aggreggate by location.
    Input:
        Arguments to query on, title of graph, state to query on.
    Output:
        PNG image
    """
    try:
        pend_counts = Submission.objects.filter(state=state).values('location').annotate(pend_count=Count('location'))

        pend_counts_list = [i['pend_count'] for i in pend_counts]
        pend_names = [i['location'] for i in pend_counts]

        if len(pend_counts_list) == 0:
            return False, HttpResponse("Did not find anything matching that query.")

        pend_counts_list.sort()
        x_data = [i for i in xrange(0, len(pend_counts_list))]

        response = charting.render_bar(x_data, pend_counts_list, title, "Number", "Count", x_tick_labels=pend_names)

        return True, response
    except:
        log.exception(IMAGE_ERROR_MESSAGE)
        return False, IMAGE_ERROR_MESSAGE


def generate_grader_types_per_problem(arguments, title):
    """
    Generate counts of graders aggeggrated by grader type.
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    try:
        sub_arguments = {"submission__" + k: arguments[k] for k in arguments.keys() if k in ['course_id', 'location']}
        sub_arguments.update({'status_code': GraderStatus.success})

        if 'grader_type' in arguments:
            sub_arguments.update({'grader_type': arguments['grader_type']})

        grader_counts = Grader.objects.filter(**sub_arguments).values('grader_type').annotate(
            grader_count=Count('grader_type'))

        grader_counts_list = [i['grader_count'] for i in grader_counts]
        grader_names = [i['grader_type'] for i in grader_counts]

        if len(grader_counts_list) == 0:
            return False, HttpResponse("Did not find anything matching that query.")

        grader_counts_list.sort()
        x_data = [i for i in xrange(0, len(grader_counts_list))]

        response = charting.render_bar(x_data, grader_counts_list, title, "Number", "Count", x_tick_labels=grader_names)

        return True, response
    except:
        log.exception(IMAGE_ERROR_MESSAGE)
        return False, IMAGE_ERROR_MESSAGE


def generate_number_of_responses_per_problem(arguments, title):
    """
    Generate counts of number of attempted problems that have been finished grading.
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    return generate_counts_per_problem(arguments, title, SubmissionState.finished)


def generate_pending_counts_per_problem(arguments, title):
    """
    Generate counts of number of submissions that are pending aggreggated by location.
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    return generate_counts_per_problem(arguments, title, SubmissionState.waiting_to_be_graded)


def generate_currently_being_graded_counts_per_problem(arguments, title):
    """
    Generate counts of number of submissions that are currently being graded aggreggated by location.
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    return generate_counts_per_problem(arguments, title, SubmissionState.being_graded)


def generate_student_attempt_count_response(arguments, title):
    """
    Generate counts of number of attempts per student with given criteria
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    try:
        sub_arguments = {k: arguments[k] for k in arguments.keys() if k in ['course_id', 'location']}
        sub_arguments.update({'grader__status_code': GraderStatus.success})

        if 'grader_type' in arguments:
            sub_arguments.update({'grader__grader_type': arguments['grader_type']})

        attempt_counts = (Submission.objects.filter(**sub_arguments).filter(state=SubmissionState.finished).
                          values('student_id').annotate(student_count=Count('student_id')))

        attempt_count_list = [i['student_count'] for i in attempt_counts]

        if len(attempt_count_list) == 0:
            return False, HttpResponse("Did not find anything matching that query.")

        attempt_count_list.sort()
        x_data = [i for i in xrange(0, len(attempt_count_list))]

        response = charting.render_bar(x_data, attempt_count_list, title, "Number", "Attempt Count")

        return True, response
    except:
        log.exception(IMAGE_ERROR_MESSAGE)
        return False, IMAGE_ERROR_MESSAGE


def generate_timing_response(arguments, title):
    """
    Generate data on number of seconds each submission has taken
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    try:
        timing_set = Timing.objects.filter(**arguments)
        if timing_set.count() == 0:
            return False, HttpResponse("Did not find anything matching that query.")

        timing_set_values = timing_set.values("start_time", "end_time")
        timing_set_start = [i['start_time'] for i in timing_set_values]
        timing_set_end = [i['end_time'] for i in timing_set_values]
        timing_set_difference = [(timing_set_end[i] - timing_set_start[i]).total_seconds() for i in
                                 xrange(0, len(timing_set_end))]
        timing_set_difference.sort()
        x_data = [i for i in xrange(0, len(timing_set_difference))]

        response = charting.render_bar(x_data, timing_set_difference, title, "Number", "Time taken")

        return True, response
    except:
        log.exception(IMAGE_ERROR_MESSAGE)
        return False, IMAGE_ERROR_MESSAGE


def generate_student_performance_response(arguments, title):
    """
    Generate data on student performance on specific problems/across the course
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    try:
        sub_arguments = {}
        for tag in ['course_id', 'location']:
            if tag in arguments:
                sub_arguments["submission__" + tag] = arguments[tag]

        grader_set = Grader.objects.filter(**sub_arguments).filter(status_code=GraderStatus.success)

        if 'grader_type' in arguments:
            grader_set = grader_set.filter(grader_type=arguments['grader_type'])

        if grader_set.count() == 0:
            return False, HttpResponse("Did not find anything matching that query.")

        grader_scores = [x['score'] for x in grader_set.values("score")]
        grader_scores.sort()
        x_data = [i for i in xrange(0, len(grader_scores))]

        response = charting.render_bar(x_data, grader_scores, title, "Number", "Score")

        return True, response
    except:
        log.exception(IMAGE_ERROR_MESSAGE)
        return False, IMAGE_ERROR_MESSAGE


def render_form(post_url, available_metric_types):
    url_base = settings.GRADING_CONTROLLER_INTERFACE['url']
    if not url_base.endswith("/"):
        url_base += "/"
    rendered = render_to_string('metrics_display.html',
        {'ajax_url': url_base,
         'post_url': post_url,
         'available_metric_types': available_metric_types,

        })

    return rendered


def get_arguments(request):
    course_id = request.POST.get('course_id')
    grader_type = request.POST.get('grader_type')
    location = request.POST.get('location')
    metric_type = request.POST.get('metric_type')

    query_dict = {
        'course_id': course_id,
        'grader_type': grader_type,
        'location': location
    }

    title = 'Data for metric {0} request with params '.format(metric_type)
    arguments = {}
    for k, v in query_dict.items():
        if v:
            arguments[k] = v
            title += " {0} : {1} ".format(k, v)

    return arguments, title

AVAILABLE_METRICS={
    'timing' : generate_timing_response,
    'student_performance' : generate_student_performance_response,
    'attempt_counts' : generate_student_attempt_count_response,
    'response_counts' : generate_number_of_responses_per_problem,
    'grader_counts' : generate_grader_types_per_problem,
    'pending_counts' : generate_pending_counts_per_problem,
    'currently_being_graded' : generate_currently_being_graded_counts_per_problem,
    }