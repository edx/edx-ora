from django.conf.urls import patterns, url
from django.conf import settings

# LMS Interface
urlpatterns = patterns('peer_grading.lms_interface',
    url(r'^get_next_submission/$', 'get_next_submission'),
    url(r'^save_grade/$', 'save_grade'),
    url(r'^is_student_calibrated/$', 'is_student_calibrated'),
    url(r'^show_calibration_essay/$', 'show_calibration_essay'),
    url(r'^save_calibration_essay/$', 'save_calibration_essay'),
)

# Temporary stub view
urlpatterns += patterns('peer_grading.views',
    url(r'^peer_grading/$', 'peer_grading'),
)