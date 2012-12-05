from django.http import HttpResponse
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
import logging

import StringIO
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab

__author__ = 'vik'

log=logging.getLogger(__name__)

def render_image(chart_data,title):
    chart_data.sort()
    d = BarChartDrawing(title=title)
    d.chart.data = [chart_data]

    binary_char = d.asString("gif")
    response=HttpResponse(binary_char, 'image/gif')

    return response

def render_image2(chart_data,title,x_label,y_label):
    chart_data.sort()
    fig = plt.figure()
    ax = fig.add_subplot(111)

    # the bar chart of the data
    log.debug(chart_data)
    ax.bar([i for i in xrange(0,len(chart_data))], chart_data, width=1)

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)

    imgdata = StringIO.StringIO()
    fig.savefig(imgdata, format='png')
    imgdata.seek(0)
    svg_dta = imgdata.buf

    return HttpResponse(svg_dta,"image/png")


class BarChartDrawing(Drawing):
    def __init__(self, width=1000, height=1000, title='Timing Data for Request ',*args, **kw):
        Drawing.__init__(self,width,height,*args,**kw)
        self.add(VerticalBarChart(), name='chart')

        self.add(String(int(width/10),height-20,title), name='title')

        #set any shapes, fonts, colors you want here.  We'll just
        #set a title font and place the chart within the drawing
        self.chart.x = 20
        self.chart.y = 20
        self.chart.width = self.width - 20
        self.chart.height = self.height - 40

        self.title.fontName = 'Helvetica-Bold'
        self.title.fontSize = 12

        self.chart.data = [[100,150,200,235]]