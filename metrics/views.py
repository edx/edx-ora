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

@csrf_exempt
def query_metrics(request):
    """
    Request is an HTTP get request with the following keys:
        Course_id
        Grader_type
        Location
    """

    if request.method == "POST":
        course_id = request.POST.get('course_id')
        grader_type = request.POST.get('grader_type')
        location = request.POST.get('location')

        query_dict = {
            'course_id' : course_id,
            'grader_type' : grader_type,
            'location' : location
        }

        title= 'Timing Data for Request with params '
        arguments = {}
        for k, v in query_dict.items():
            if v:
                arguments[k] = v
                title+= " {0} : {1} ".format(k,v)

        timing_set=Timing.objects.filter(**arguments)
        if timing_set.count()==0:
            return HttpResponse("Did not find anything matching that query.")

        timing_set_values=timing_set.values("start_time", "end_time")
        timing_set_start=[i['start_time'] for i in timing_set_values]
        timing_set_end=[i['end_time'] for i in timing_set_values]
        timing_set_difference=[(timing_set_end[i]-timing_set_start[i]).total_seconds() for i in xrange(0,len(timing_set_end))]
        d = BarChartDrawing(title=title)

        d.chart.data = [timing_set_difference]
        binary_char = d.asString("gif")
        response=HttpResponse(binary_char, 'image/gif')
        #response['Content-Disposition'] = 'attachment; filename=output.gif'
        return response

    elif request.method == "GET":
        url_base = settings.GRADING_CONTROLLER_INTERFACE['url']
        if not url_base.endswith("/"):
            url_base += "/"
        rendered=render_to_string('metrics_display.html',
            {'ajax_url' : url_base})
        return HttpResponse(rendered)


class BarChartDrawing(Drawing):
    def __init__(self, width=1000, height=1000, title='Timing Data for Request ',*args, **kw):
        Drawing.__init__(self,width,height,*args,**kw)
        self.add(HorizontalBarChart(), name='chart')

        self.add(String(200,180,title), name='title')

        #set any shapes, fonts, colors you want here.  We'll just
        #set a title font and place the chart within the drawing
        self.chart.x = 20
        self.chart.y = 20
        self.chart.width = self.width - 20
        self.chart.height = self.height - 40

        self.title.fontName = 'Helvetica-Bold'
        self.title.fontSize = 12

        self.chart.data = [[100,150,200,235]]
