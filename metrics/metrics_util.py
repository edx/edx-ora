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
import re
import csv

log = logging.getLogger(__name__)

IMAGE_ERROR_MESSAGE = "Error processing image."

def get_data_in_csv(location):
    fixed_location=re.sub("[/:]","_",location)
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{0}.csv"'.format(fixed_location)
    writer = csv.writer(response)
    subs=Submission.objects.filter(location=location,state=SubmissionState.finished)
    grader_info=[sub.get_all_successful_scores_and_feedback() for sub in subs]
    grader_type=[grade['grader_type'] for grade in grader_info]
    

def render_requested_metric(metric_type,arguments,title,xsize=20,ysize=10):
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

    m_renderer=MetricsRenderer(xsize,ysize)
    success, msg = m_renderer.run_query(arguments,metric_type)
    success, currently_being_graded=m_renderer.chart_image()

    return success,currently_being_graded

class MetricsRenderer(object):
   def __init__(self,xsize,ysize):
       self.xsize=xsize
       self.ysize=ysize
       self.x_title="Number"
       self.y_title="Count"
       self.x_labels=""
       self.title=""
       self.success=False

   def run_query(self,arguments,metric_type):
       try:
           self.title=get_title(arguments,metric_type)
           log.debug(AVAILABLE_METRICS[metric_type](arguments))
           (self.x_data, self.y_data, self.x_labels, self.x_title, self.y_title) = AVAILABLE_METRICS[metric_type](arguments)
           self.success=True
       except:
           log.exception(IMAGE_ERROR_MESSAGE)
           return False, IMAGE_ERROR_MESSAGE
       return True, "Success."

   def chart_image(self):
       if self.success:
           response = charting.render_bar(self.x_data, self.y_data, self.title, self.x_title, self.y_title, x_tick_labels=self.x_labels, xsize=self.xsize, ysize=self.ysize)
       else:
           return False, IMAGE_ERROR_MESSAGE

       return True, response


def generate_counts_per_problem(arguments, state):
    """
    Generate counts of number of attempted problems with a specific state.  Aggreggate by location.
    Input:
        Arguments to query on, title of graph, state to query on.
    Output:
        PNG image
    """
    pend_counts = Submission.objects.filter(state=state).values('location').annotate(pend_count=Count('location'))

    pend_counts_list = [i['pend_count'] for i in pend_counts]
    pend_names = [i['location'] for i in pend_counts]

    if len(pend_counts_list) == 0:
        return False, "Did not find anything matching that query."

    pend_counts_list.sort()
    x_data = [i for i in xrange(0, len(pend_counts_list))]

    return x_data, pend_counts_list, pend_names, "Number", "Count"

def generate_grader_types_per_problem(arguments):
    """
    Generate counts of graders aggeggrated by grader type.
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
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

    return x_data, grader_counts_list, grader_names, "Number", "Count"

def generate_number_of_responses_per_problem(arguments):
    """
    Generate counts of number of attempted problems that have been finished grading.
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    return generate_counts_per_problem(arguments, SubmissionState.finished)


def generate_pending_counts_per_problem(arguments):
    """
    Generate counts of number of submissions that are pending aggreggated by location.
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    return generate_counts_per_problem(arguments, SubmissionState.waiting_to_be_graded)


def generate_currently_being_graded_counts_per_problem(arguments):
    """
    Generate counts of number of submissions that are currently being graded aggreggated by location.
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
    return generate_counts_per_problem(arguments, SubmissionState.being_graded)


def generate_student_attempt_count_response(arguments):
    """
    Generate counts of number of attempts per student with given criteria
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
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

    return x_data, attempt_count_list, None, "Number", "Attempt Count"

def generate_timing_response(arguments):
    """
    Generate data on number of seconds each submission has taken
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
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

    return x_data, timing_set_difference, None, "Number", "Time taken"

def generate_student_performance_response(arguments):
    """
    Generate data on student performance on specific problems/across the course
    Input:
        Arguments to query on, title of graph
    Output:
        PNG image
    """
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

    return x_data, grader_scores, None, "Number", "Score"


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

def render_data_dump_form(post_url, unique_locations):
    url_base = settings.GRADING_CONTROLLER_INTERFACE['url']
    if not url_base.endswith("/"):
        url_base += "/"
    rendered = render_to_string('data_dump_display.html',
        {'ajax_url': url_base,
         'post_url': post_url,
         'unique_locations': unique_locations,
         })

    return rendered


def get_title(query_dict,metric_type):
    title = 'Data for metric {0} request with params '.format(metric_type)
    arguments = {}
    for k, v in query_dict.items():
        if v:
            arguments[k] = v
            title += " {0} : {1} ".format(k, v)

    return title

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

    title=get_title(query_dict,metric_type)

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