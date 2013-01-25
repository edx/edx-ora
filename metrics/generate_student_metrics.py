from controller.models import Grader, Message, Submission, GraderStatus, SubmissionState
import numpy
from django.conf import settings
from __future__ import division

def read_one_student_data(student_id, course_id):
    subs = list(Submission.objects.filter(student_id=student_id, course_id=course_id, state = SubmissionState.finished).order_by("-date_modified"))
    sub_ids = [sub.id for sub in subs]
    graders = list(Grader.objects.filter(submission_id__in=sub_ids))
    completed_graders = list(Grader.objects.filter(grader_id=student_id, submission__course_id = course_id, grader_type = "PE"))

    average_submission_length = numpy.mean([len(sub.student_response) for sub in subs])
    average_ml_confidence = numpy.mean([float(grade.confidence) for grade in graders if grade.grader_type == "ML"])
    problems_attempted = len(subs)
    attempts_per_problem = len(set([sub.location for sub in subs]))/(problems_attempted+1)

    average_length_of_peer_feedback_given = numpy.mean([len(cg.feedback) for cg in completed_graders])
    completed_peer_grading = len(completed_graders)
    average_peer_grading_score_given = numpy.mean([cg.score for cg in completed_graders])

    problems_attempted_peer = len([sub for sub in subs if sub.preferred_grader_type == "PE"])
    attempts_per_problem_peer = len(set([sub.location for sub in subs if sub.preferred_grader_type == "PE"]))/(problems_attempted_peer+1)

    problems_attempted_ml = len([sub for sub in subs if sub.preferred_grader_type == "ML"])
    attempts_per_problem_ml = len(set([sub.location for sub in subs if sub.preferred_grader_type == "ML"]))/(problems_attempted+1)

    graders_per_attempt = len(graders)/(len(subs)+1)

    average_percent_score_list=[]
    average_percent_score_list_peer = []
    average_percent_score_list_ml = []

    for sub in subs:
        grader_set = graders.filter(submission_id=sub.id)
        successful_grader_set = grader_set.filter(status_code = GraderStatus.success)
        max_score = sub.max_score
        if len(successful_grader_set)>0:
            if sub.preferred_grader_type == "ML":
                final_grader = successful_grader_set.order_by("-date_modified")[0]
                final_score = final_grader.score
                average_percent_score_list_ml.append(final_score/max_score)
                average_percent_score_list.append(final_score/max_score)
            elif sub.preferred_grader_type == "PE":
                final_graders = successful_grader_set.filter(grader_type = "PE")
                if len(final_graders)>0:
                    final_score = numpy.mean([fg.score for fg in final_grader])
                    average_percent_score_list_peer.append(final_score/max_score)
                    average_percent_score_list.append(final_score/max_score)
