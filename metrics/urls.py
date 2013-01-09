from django.conf.urls import patterns, url
from django.contrib.auth.views import login

# Temporary stub view
urlpatterns = patterns('metrics.views',
    url(r'^timing/$', 'timing_metrics'),
    url(r'^student_performance/$', 'student_performance_metrics'),
    url(r'^metrics/$', 'metrics_form'),
    url(r'^error_dash/$', 'error_dashboard'),
    url(r'^data_dump/$', 'data_dump_form'),
    url(r'^message_dump/$', 'message_dump_form'),
)