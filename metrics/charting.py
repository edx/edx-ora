from django.http import HttpResponse
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String

import StringIO
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab

__author__ = 'vik'

def render_image(chart_data,title):
    chart_data.sort()
    d = BarChartDrawing(title=title)
    d.chart.data = [chart_data]

    binary_char = d.asString("gif")
    response=HttpResponse(binary_char, 'image/gif')

    return response

def render_image2(chart_data,title):

    fig = plt.figure()
    ax = fig.add_subplot(111)

    # the histogram of the data
    n, bins, patches = ax.hist(chart_data, 50, normed=1, facecolor='green', alpha=0.75)

    ax.set_xlabel('Smarts')
    ax.set_ylabel('Probability')
    #ax.set_title(r'$\mathrm{Histogram\ of\ IQ:}\ \mu=100,\ \sigma=15$')
    ax.set_xlim(40, 160)
    ax.set_ylim(0, 0.03)
    ax.grid(True)

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