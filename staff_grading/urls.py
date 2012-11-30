from django.conf.urls import patterns, url
from django.conf import settings

urlpatterns = patterns('staff_grading.views',
    url(r'^get_next_submission/$', 'get_next_submission'),
    url(r'^save_grade/$', 'save_grade'))


# Also have proxies for the login and logout views--this allows
# clients to view staff grading as a self-contained interface.
urlpatterns += patterns('controller.views',
    url(r'^login/$', 'log_in'),
    url(r'^logout/$', 'log_out'),
)
