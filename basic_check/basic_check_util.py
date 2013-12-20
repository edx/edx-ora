from django.conf import settings
import sys

import json
import logging
log = logging.getLogger(__name__)

from controller.models import GraderStatus
from metrics.models import StudentProfile


def simple_quality_check(string, initial_display, student_id, skip_basic_checks):
    """
    Performs a simple sanity test on an input string
    Input:
        Any string
    Output:
        Boolean indicating success/failure and dictionary with sanity checks
        Dictionary contains keys feedback, score, grader_type, and status
        Dictionary key feedback contains further keys markup_text, spelling, and grammar
    """
    quality_dict = {
        'feedback': json.dumps({
            'spelling': "Ok.",
            'grammar': "Ok.",
            'markup_text': "NA"
        }),
        'score': 1,
        'grader_type': 'BC',
        'status': GraderStatus.success
    }

    if string == initial_display or len(string.strip()) == 0:
        quality_dict['score'] = 0

    #If student is banned by staff from peer grading, then they will not get any feedback here.
    success, quality_dict = handle_banned_students(student_id, quality_dict)

    return True, quality_dict


def handle_banned_students(student_id, quality_dict):
    success, student_banned = is_student_banned(student_id)
    if success and student_banned:
        quality_dict['score'] = 0

    return success, quality_dict


def is_student_banned(student_id):
    success = False
    student_banned = False
    try:
        student_profile = StudentProfile.objects.get(student_id=student_id)
        student_banned = student_profile.student_is_staff_banned
        success = True
    except Exception:
        pass

    return success, student_banned
