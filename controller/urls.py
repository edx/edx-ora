from django.conf.urls import patterns, url
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone


# General
#------------------------------------------------------------
urlpatterns = patterns('controller.views',
    url(r'^login/$', 'log_in'),
    url(r'^logout/$', 'log_out'),
    url(r'^status/$', 'status'),
)

# Xqueue submission interface (xqueue pull script uses this)
#------------------------------------------------------------
urlpatterns += patterns('controller.xqueue_interface',
    url(r'^submit/$', 'submit'),
)

# Grader pull interface
#------------------------------------------------------------
urlpatterns += patterns('controller.grader_interface',
    url(r'^get_submission/$', 'get_submission'),
    url(r'^put_result/$', 'put_result'),
)
