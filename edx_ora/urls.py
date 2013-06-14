from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^grading_controller/', include('controller.urls')),
    url(r'^peer_grading/', include('peer_grading.urls')),
    url(r'^staff_grading/', include('staff_grading.urls')),
    url(r'^metrics/', include('metrics.urls')),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url('^tasks/', include('djcelery.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
