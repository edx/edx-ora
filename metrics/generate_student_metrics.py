from controller.models import Grader, Message, Submission, GraderStatus, SubmissionState
import numpy
from django.conf import settings
from __future__ import division
from models import StudentCourseProfile, StudentProfile
from django.db import transaction

MIN_NEW_ATTEMPTS_TO_REGENERATE = 5

def regenerate_student_data():
    transaction.commit_unless_managed()
    unique_courses = Submission.objects.all().values('course_id').distinct()

    for course in unique_courses:
        transaction.commit_unless_managed()
        unique_students = Submission.objects.filter(course_id = course).values('student_id').distinct()
        log.debug("Regenerating data for course {0} with {1} students.".format(course, unique_students.count()))
        success_count = 0
        change_count = 0
        for student in unique_students:
            try:
                success, changed = read_one_student_data(student, course)
                if success:
                    success_count+=1
                if changed:
                    change_count+=1
            except:
                error_message = "Could not generate student course profile for student "
        log.debug("{0} students successfully scanned, {1} updated.".format(success_count, change_count))

def read_one_student_data(student_id, course_id):
    transaction.commit_unless_managed()
    success = False
    changed = False
    try:
        student_profile = StudentProfile.objects.get_or_create(student_id = student_id)
        student_course_profile = StudentCourseProfile.objects.get_or_create(student_id = student_id, course_id = course_id)
    except:
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
                    final_score = numpy.mean([fg.score for fg in final_grader])
                    average_percent_score_list_peer.append(final_score/max_score)
                    average_percent_score_list.append(final_score/max_score)

    stdev_percent_score = numpy.std(average_percent_score_list)
    average_percent_score = numpy.mean(average_percent_score_list)
    average_percent_score_last20 = numpy.mean(average_percent_score_list[:20])
    average_percent_score_last10 = numpy.mean(average_percent_score_list[:10])
    average_percent_score_peer = numpy.mean(average_percent_score_list_peer)
    average_percent_score_ml = numpy.mean(average_percent_score_list_ml)

    student_course_profile = StudentCourseProfile(
        student_profile = student_profile,
        course_id = course_id,
        student_id = student_id,
        problems_attempted = problems_attempted,
        attempts_per_problem = attempts_per_problem,
        graders_per_attempt = graders_per_attempt,
        stdev_percent_score = stdev_percent_score,
        average_percent_score = average_percent_score,
        average_percent_score_last20 = average_percent_score_last20,
        average_percent_score_last10 = average_percent_score_last10,
        problems_attempted_peer = problems_attempted_peer,
        completed_peer_grading = completed_peer_grading,
        average_length_of_peer_feedback_given = average_length_of_peer_feedback_given,
        stdev_length_of_peer_feedback_given = stdev_length_of_peer_feedback_given,
        average_peer_grading_score_given = average_peer_grading_score_given,
        attempts_per_problem_peer = attempts_per_problem_peer,
        average_percent_score_peer = average_percent_score_peer,
        problems_attempted_ml = problems_attempted_ml,
        attempts_per_problem_ml = attempts_per_problem_ml,
        average_ml_confidence = average_ml_confidence,
        average_percent_score_ml = average_percent_score_ml,
        average_submission_length = average_submission_length,
        stdev_submission_length = stdev_submission_length,
    )

    student_course_profile.save()

    success = True
    changed = True
    return success, changed