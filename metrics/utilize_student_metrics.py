from __future__ import division
from controller.models import Grader, Message, Submission, GraderStatus, SubmissionState
import numpy
from django.conf import settings
from models import StudentCourseProfile, StudentProfile, DECIMAL_PLACES
from django.db import transaction
from django.forms.models import model_to_dict

import logging

log=logging.getLogger(__name__)

FIELDS_TO_EVALUATE = [
    "problems_attempted",
    "attempts_per_problem",
    "graders_per_attempt",
    "stdev_percent_score",
    "average_percent_score",
    "average_percent_score_last20",
    "average_percent_score_last10",
    "problems_attempted_peer",
    "completed_peer_grading",
    "average_length_of_peer_feedback_given",
    "stdev_length_of_peer_feedback_given",
    "average_peer_grading_score_given",
    "attempts_per_problem_peer",
    "average_percent_score_peer",
    "problems_attempted_ml",
    "attempts_per_problem_ml",
    "average_ml_confidence",
    "average_percent_score_ml",
    "average_submission_length",
    "stdev_submission_length",
]

def get_student_profile(student_id, course_id):
    success = False
    try:
        student_profile = StudentCourseProfile.objects.get(student_id = student_id, course_id = course_id)
        student_profile = model_to_dict(student_profile, FIELDS_TO_EVALUATE)
        success = True
    except:
        student_profile = None

    return success, student_profile


def get_similarity_score(base_student_dict, comparison_student_id, course_id):
    similarity_score = 5
    success = False
    try:
        comparison_student_profile = StudentCourseProfile.objects.get(student_id = comparison_student_id, course_id = course_id)
    except:
        return success, similarity_score

    comparison_student_dict = model_to_dict(comparison_student_profile, fields = FIELDS_TO_EVALUATE)
    log.debug(base_student_dict)
    log.debug(comparison_student_dict)
    difference_list=[]
    for field in FIELDS_TO_EVALUATE:
        if field in base_student_dict and field in comparison_student_dict:
            base_field = base_student_dict[field]
            comparison_field = comparison_student_dict[field]
            if base_field>0:
                field_diff = abs(base_field - comparison_field)/base_field
                difference_list.append(field_diff)

    log.debug("Difference List : {0}".format(difference_list))
    if len(difference_list)>0:
        similarity_score = numpy.mean(difference_list)

    success = True

    return success, round(similarity_score, DECIMAL_PLACES)

    
