from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^grading_controller/', include('controller.urls')),
    url(r'^peer_grading/', include('peer_grading.urls')),
    url(r'^staff_grading/', include('staff_grading.urls')),
    url(r'^metrics/', include('metrics.urls')),
)
