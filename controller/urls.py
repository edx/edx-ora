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
    url(r'^get_submission_eta/$', 'request_eta_for_submission'),
    url(r'^is_name_unique/$', 'verify_name_uniqueness'),
    url(r'^combined_notifications/$', 'check_for_notifications'),
    url(r'^get_grading_status_list/$', 'get_grading_status_list'),
)

# Xqueue submission interface (xqueue pull script uses this)
#------------------------------------------------------------
urlpatterns += patterns('controller.xqueue_interface',
    url(r'^submit/$', 'submit'),
    url(r'^submit_message/$', 'submit_message'),
)

# Grader pull interface
#------------------------------------------------------------
urlpatterns += patterns('controller.grader_interface',
    url(r'^get_submission_ml/$', 'get_submission_ml'),
    url(r'^get_submission_instructor/$', 'get_submission_instructor'),
    url(r'^put_result/$', 'put_result'),
    url(r'^get_pending_count/$', 'get_pending_count'),
)

# Peer grading flagging interface
#------------------------------------------------------------
urlpatterns += patterns('controller.views',
    url(r'^get_flagged_problem_list/$', 'get_flagged_problem_list'),
    url(r'^take_action_on_flags/$', 'take_action_on_flags'),
)

# Course staff data download
#------------------------------------------------------------
urlpatterns += patterns('controller.views',
    url(r'^get_course_data/$', 'get_course_data')
)

