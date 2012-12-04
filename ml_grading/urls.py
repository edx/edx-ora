from django.conf.urls import patterns, url
from django.contrib.auth.views import login

# Temporary stub view
urlpatterns = patterns('ml_grading.views',
    url(r'^request_latest_created_model/$', 'request_latest_created_model'),
)