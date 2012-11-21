from django.conf.urls import patterns, url
from django.conf import settings

urlpatterns = patterns('staff_grading.views',
    url(r'^get_next_submission/$', 'get_next_submission'),
    url(r'^save_grade/$', 'save_grade'),
)
