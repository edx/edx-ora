from __future__ import division
from controller.models import Grader, Message, Submission, GraderStatus, SubmissionState
import numpy
from django.conf import settings
from models import StudentCourseProfile, StudentProfile, DECIMAL_PLACES, FIELDS_TO_EVALUATE
from django.db import transaction
from django.forms.models import model_to_dict

import logging

log=logging.getLogger(__name__)


def get_student_profile(student_id, course_id):
    success = False
    try:
        student_profile = StudentCourseProfile.objects.get(student_id = student_id, course_id = course_id)
        student_profile = model_to_dict(student_profile, FIELDS_TO_EVALUATE)
        success = True
    except Exception:
        student_profile = None

    return success, student_profile


def get_similarity_score(base_student_dict, comparison_student_id, course_id):
    similarity_score = 5
    success = False
    try:
        comparison_student_profile = StudentCourseProfile.objects.get(student_id = comparison_student_id, course_id = course_id)
    except Exception:
        return success, similarity_score

    comparison_student_dict = model_to_dict(comparison_student_profile, fields = FIELDS_TO_EVALUATE)
    difference_list=[]
    for field in FIELDS_TO_EVALUATE:
        if field in base_student_dict and field in comparison_student_dict:
            base_field = base_student_dict[field]
            comparison_field = comparison_student_dict[field]
            if base_field>0:
                field_diff = abs(base_field - comparison_field)/base_field
                difference_list.append(field_diff)

    if len(difference_list)>0:
        difference_list = [float(i) for i in difference_list]
        similarity_score = numpy.mean(difference_list)

    success = True

    return success, round(similarity_score, DECIMAL_PLACES)

    
