from django.conf.urls import patterns, url
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

# LMS Interface
urlpatterns = patterns('peer_grading.lms_interface',
    url(r'^get_next_submission/$', 'get_next_submission'),
    url(r'^save_grade/$', 'save_grade'),
    url(r'^is_calibrated/$', 'is_student_calibrated'),
    url(r'^show_calibration_essay/$', 'show_calibration_essay'),
    url(r'^save_calibration_essay/$', 'save_calibration'),
)

# Temporary stub view
urlpatterns = patterns('peer_grading.views',
    url(r'^peer_grading/$', 'peer_grading'),
)