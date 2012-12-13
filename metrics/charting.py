from django.http import HttpResponse
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
import logging

import StringIO
import numpy as np
import matplotlib

__author__ = 'vik'

log=logging.getLogger(__name__)

def render_image(chart_data,title):
    chart_data.sort()
    d = BarChartDrawing(title=title)
    d.chart.data = [chart_data]

    binary_char = d.asString("gif")
    response=HttpResponse(binary_char, 'image/gif')

    return response

def render_bar(x_data,y_data,title,x_label,y_label,x_tick_labels=None,xsize=20,ysize=10):
    matplotlib.rcParams.update({'font.size': min(12,xsize)})
    epsilon = .01
    y_data=[i+epsilon for i in y_data]
    fig = matplotlib.pyplot.figure(figsize=(xsize,ysize))
    ax = fig.add_subplot(111)

    # the bar chart of the data
    ax.bar(x_data, y_data, align='center')

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)

    if x_tick_labels:
        ax.set_xticks(x_data)
        ax.set_xticklabels(x_tick_labels)

    imgdata = StringIO.StringIO()
    fig.savefig(imgdata, format='png')
    imgdata.seek(0)
    svg_dta = imgdata.buf

    return svg_dta


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