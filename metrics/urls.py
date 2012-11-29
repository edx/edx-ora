from django.conf.urls import patterns, url
from django.contrib.auth.views import login

# Temporary stub view
urlpatterns = patterns('metrics.views',
    url(r'^timing/$', 'timing_metrics'),
    url(r'^student_performance/$', 'student_performance_metrics'),
)