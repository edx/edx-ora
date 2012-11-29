import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from controller.models import Submission
from controller import util
from controller import grader_util
from django.template.loader import render_to_string
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import HorizontalBarChart

from models import Timing

def query_metrics(request):
    """
    Request is an HTTP get request with the following keys:
        Course_id
        Grader_type
        Location
    """

    if request.method != "GET":
        raise Http404

    course_id = request.GET.get('course_id')
    grader_type = request.GET.get('grader_type')
    location = request.GET.get('location')

    query_dict = {
        'course_id' : course_id,
        'grader_type' : grader_type,
        'location' : location
    }
    arguments = {}
    for k, v in query_dict.items():
        if v:
            arguments[k] = v

    timing_set=Timing.objects.filter(**arguments)
    timing_set_values=timing_set.values("start_time", "end_time")
    timing_set_start=[i['start_time'] for i in timing_set_values]
    timing_set_end=[i['end_time'] for i in timing_set_values]
    timing_set_difference=[timing_set_end[i]-timing_set_start[i] for i in xrange(0,len(timing_set_end))]


    # Our query is ready to take off.
    film_results = Timing.objects.filter(
        director__name=request_params['director'],
        created_at__range=(fromdate, todate)
    )
    return render_to_response('search_results.html', {'results':film_results})


class MyBarChartDrawing(Drawing):
    def __init__(self, width=400, height=200, *args, **kw):
        Drawing.__init__(self,width,height,*args,**kw)
        self.add(HorizontalBarChart(), name='chart')

        self.add(String(200,180,'Hello World'), name='title')

        #set any shapes, fonts, colors you want here.  We'll just
        #set a title font and place the chart within the drawing
        self.chart.x = 20
        self.chart.y = 20
        self.chart.width = self.width - 20
        self.chart.height = self.height - 40

        self.title.fontName = 'Helvetica-Bold'
        self.title.fontSize = 12

        self.chart.data = [[100,150,200,235]]
