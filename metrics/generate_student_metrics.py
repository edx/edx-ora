from __future__ import division
from controller.models import Grader, Message, Submission, GraderStatus, SubmissionState
import numpy
from django.conf import settings
from models import StudentCourseProfile, StudentProfile, DECIMAL_PLACES, FIELDS_TO_EVALUATE
from django.db import transaction
import gc

import logging

log=logging.getLogger(__name__)

MIN_NEW_ATTEMPTS_TO_REGENERATE = 5

MIN_DIFF_TO_PEER_GRADE = 2

def regenerate_student_data():
    transaction.commit()
    unique_courses = [s['course_id'] for s in Submission.objects.all().values('course_id').distinct()]

    for course in unique_courses:
        transaction.commit()
        unique_students = [s['student_id'] for s in Submission.objects.filter(course_id = course).values('student_id').distinct()]
        success_count = 0
        change_count = 0
        for student in unique_students:
            try:
                success, changed = read_one_student_data(student, course)
                if success:
                    success_count+=1
                if changed:
                    change_count+=1
            except Exception:
                error_message = "Could not generate student course profile for student "
                log.exception(error_message)
        log.debug("{0} students successfully scanned, {1} updated.".format(success_count, change_count))
        gc.collect()

def read_one_student_data(student_id, course_id):
    transaction.commit()
    success = False
    changed = False
    try:
        student_profile, created = StudentProfile.objects.get_or_create(student_id = student_id)
        student_course_profile, created = StudentCourseProfile.objects.get_or_create(student_id = student_id, course_id = course_id, student_profile = student_profile)
    except Exception:
        log.exception("Could not find student_profile or student_course_profile.")
        return success, changed

    sub_count = Submission.objects.filter(student_id=student_id, course_id=course_id, state = SubmissionState.finished).count()
    if sub_count < (student_course_profile.problems_attempted + MIN_NEW_ATTEMPTS_TO_REGENERATE):
        success = True
        return success, changed

    subs = list(Submission.objects.filter(student_id=student_id, course_id=course_id, state = SubmissionState.finished).order_by("-date_modified"))
    sub_ids = [sub.id for sub in subs]
    graders = list(Grader.objects.filter(submission_id__in=sub_ids))
    completed_graders = list(Grader.objects.filter(grader_id=student_id, submission__course_id = course_id, grader_type = "PE"))

    submission_length_list = [len(sub.student_response) for sub in subs]
    average_submission_length = numpy.mean(submission_length_list)
    stdev_submission_length = numpy.std(submission_length_list)

    average_ml_confidence = numpy.mean([float(grade.confidence) for grade in graders if grade.grader_type == "ML"])
    problems_attempted = len(subs)
    attempts_per_problem = problems_attempted / (len(set([sub.location for sub in subs]))+1)

    peer_feedback_list = [len(cg.feedback) for cg in completed_graders]
    average_length_of_peer_feedback_given = numpy.mean(peer_feedback_list)
    stdev_length_of_peer_feedback_given = numpy.std(peer_feedback_list)

    completed_peer_grading = len(completed_graders)
    average_peer_grading_score_given = numpy.mean([cg.score for cg in completed_graders])

    problems_attempted_peer = len([sub for sub in subs if sub.preferred_grader_type == "PE"])
    attempts_per_problem_peer = problems_attempted_peer / (len(set([sub.location for sub in subs if sub.preferred_grader_type == "PE"]))+1)

    problems_attempted_ml = len([sub for sub in subs if sub.preferred_grader_type == "ML"])
    attempts_per_problem_ml = problems_attempted / (len(set([sub.location for sub in subs if sub.preferred_grader_type == "ML"]))+1)

    graders_per_attempt = len(graders)/(len(subs)+1)

    average_percent_score_list=[]
    average_percent_score_list_peer = []
    average_percent_score_list_ml = []

    for sub in subs:
        grader_set = [g for g in graders if g.submission_id == sub.id]
        successful_grader_set = [sg for sg in grader_set if sg.status_code == GraderStatus.success]
        max_score = sub.max_score
        if len(successful_grader_set)>0:
            if sub.preferred_grader_type == "ML":
                successful_grader_set.sort(key=lambda x: x.date_modified, reverse=True)
                first_grader = successful_grader_set[0]
                final_score = first_grader.score
                average_percent_score_list_ml.append(final_score/max_score)
                average_percent_score_list.append(final_score/max_score)
            elif sub.preferred_grader_type == "PE":
                final_graders = [sg for sg in successful_grader_set if sg.grader_type=="PE"]
                if len(final_graders)>0:
                    final_score = numpy.mean([fg.score for fg in final_graders])
                    average_percent_score_list_peer.append(final_score/max_score)
                    average_percent_score_list.append(final_score/max_score)

    stdev_percent_score = numpy.std(average_percent_score_list)
    average_percent_score = numpy.mean(average_percent_score_list)
    average_percent_score_last20 = numpy.mean(average_percent_score_list[:20])
    average_percent_score_last10 = numpy.mean(average_percent_score_list[:10])
    average_percent_score_peer = numpy.mean(average_percent_score_list_peer)
    average_percent_score_ml = numpy.mean(average_percent_score_list_ml)

    value_dict = {
        "problems_attempted" : problems_attempted,
        "attempts_per_problem" : attempts_per_problem,
        "graders_per_attempt" : graders_per_attempt,
        "stdev_percent_score" : stdev_percent_score,
        "average_percent_score" : average_percent_score,
        "average_percent_score_last20" : average_percent_score_last20,
        "average_percent_score_last10" : average_percent_score_last10,
        "problems_attempted_peer" : problems_attempted_peer,
        "completed_peer_grading" : completed_peer_grading,
        "average_length_of_peer_feedback_given" : average_length_of_peer_feedback_given,
        "stdev_length_of_peer_feedback_given" : stdev_length_of_peer_feedback_given,
        "average_peer_grading_score_given" : average_peer_grading_score_given,
        "attempts_per_problem_peer" : attempts_per_problem_peer,
        "average_percent_score_peer" : average_percent_score_peer,
        "problems_attempted_ml" : problems_attempted_ml,
        "attempts_per_problem_ml" : attempts_per_problem_ml,
        "average_ml_confidence" : average_ml_confidence,
        "average_percent_score_ml" : average_percent_score_ml,
        "stdev_submission_length" : stdev_submission_length,
    }

    value_dict = fix_value_dict(value_dict)

    StudentCourseProfile.objects.filter(id = student_course_profile.id).update(**value_dict)

    student_cannot_submit_more_for_peer_grading = (problems_attempted_peer - completed_peer_grading)>MIN_DIFF_TO_PEER_GRADE
    value_dict_2 = {
        'student_cannot_submit_more_for_peer_grading' : student_cannot_submit_more_for_peer_grading
    }

    value_dict_2 = fix_value_dict(value_dict_2)

    StudentProfile.objects.filter(id = student_profile.id).update(**value_dict_2)

    success = True
    changed = True
    return success, changed

def fix_value_dict(value_dict):
    for k in value_dict:
        value_dict[k] = round(value_dict[k], DECIMAL_PLACES)
        if numpy.isnan(value_dict[k]):
            value_dict[k]=0
    return value_dict