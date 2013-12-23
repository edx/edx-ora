import datetime
import json
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Count
from create_grader import create_grader
import grader_util
import util
import logging
from models import GraderStatus, SubmissionState, Submission, Grader, Rubric, RubricItem
from staff_grading import staff_grading_util
from xqueue_interface import handle_submission
from ml_grading import ml_grading_util
from ml_grading.models import CreatedModel
import os
from control_util import SubmissionControl

from statsd import statsd

log = logging.getLogger(__name__)

def reset_ml_subs_to_in():
    """
    Reset submissions marked ML to instructor if there are not enough instructor submissions to grade
    This happens if the instructor skips too many submissions
    """
    counter=0
    unique_locations=[x['location'] for x in Submission.objects.all().values('location').distinct()]
    for location in unique_locations:
        sl = staff_grading_util.StaffLocation(location)
        subs_graded, subs_pending = sl.graded_count(), sl.pending_count()

        control = SubmissionControl(sl.latest_submission())

        subs_pending_total = Submission.objects.filter(
            location=location,
            state=SubmissionState.waiting_to_be_graded,
            preferred_grader_type="ML"
        ).order_by('-date_created')[:control.minimum_to_use_ai]

        if (subs_graded + subs_pending) < control.minimum_to_use_ai and subs_pending_total.count() > subs_pending:
            for sub in subs_pending_total:
                if sub.next_grader_type == "ML" and sub.get_unsuccessful_graders().count() == 0:
                    staff_grading_util.set_ml_grading_item_back_to_instructor(sub)
                    counter += 1
                if (counter + subs_graded + subs_pending) > control.minimum_to_use_ai:
                    break
    if counter>0:
        statsd.increment("open_ended_assessment.grading_controller.expire_submissions.reset_ml_subs_to_in",
            tags=["counter:{0}".format(counter)])
        log.debug("Reset {0} submission from ML to IN".format(counter))

def reset_in_subs_to_ml():
    count=0
    in_subs=Submission.objects.filter(
        state=SubmissionState.waiting_to_be_graded,
        next_grader_type="IN",
        preferred_grader_type="ML"
    )

    for sub in in_subs:
        #If an instructor checks out a submission after ML grading has started,
        # this resets it to ML if the instructor times out
        success= ml_grading_util.check_for_all_model_and_rubric_success(sub.location)
        if (sub.next_grader_type=="IN" and success):
            sub.next_grader_type="ML"
            sub.save()
            count+=1

    if count>0:
        statsd.increment("open_ended_assessment.grading_controller.expire_submissions.reset_in_subs_to_ml",
            tags=["counter:{0}".format(count)])
        log.debug("Reset {0} instructor subs to ML".format(count))

    return True

def reset_subs_in_basic_check():
    #Reset submissions that are stuck in basic check state
    subs_stuck_in_basic_check=Submission.objects.filter(
        next_grader_type="BC",
        state__in=[SubmissionState.waiting_to_be_graded, SubmissionState.being_graded]
    )

    count=0
    for sub in subs_stuck_in_basic_check:
        handle_submission(sub)
        count+=1

    if count>0:
        statsd.increment("open_ended_assessment.grading_controller.expire_submissions.reset_subs_in_basic_check",
            tags=["counter:{0}".format(count)])
        log.debug("Reset {0} basic check subs properly.".format(count))
    return True

def reset_failed_subs_in_basic_check():
    #Reset submissions that are stuck in basic check state
    subs_failed_basic_check=Submission.objects.filter(
        grader__grader_type="BC",
        grader__status_code= GraderStatus.failure,
        state=SubmissionState.waiting_to_be_graded,
    ).exclude(grader__status_code=GraderStatus.success)

    count=0
    for sub in subs_failed_basic_check:
        handle_submission(sub)
        count+=1

    if count>0:
        statsd.increment("open_ended_assessment.grading_controller.expire_submissions.reset_subs_failed_basic_check",
            tags=["counter:{0}".format(count)])
        log.debug("Reset {0} basic check failed subs properly.".format(count))
    return True

def reset_timed_out_submissions():
    """
    Check if submissions have timed out, and reset them to waiting to grade state if they have
    Input:
        subs - A QuerySet of submissions
    Output:
        status code indicating success
    """
    now = timezone.now()
    min_time = datetime.timedelta(seconds=settings.RESET_SUBMISSIONS_AFTER)

    # have to split into 2 queries now, because we are giving some finished submissions to peer graders when
    # there's nothing to grade

    reset_waiting_count = (Submission.objects
                           .filter(date_modified__lt=now-min_time,
                                   state=SubmissionState.being_graded,
                                   posted_results_back_to_queue=False)
                           .update(state=SubmissionState.waiting_to_be_graded))

    reset_finished_count = (Submission.objects
                            .filter(date_modified__lt=now-min_time,
                                    state=SubmissionState.being_graded,
                                    posted_results_back_to_queue=True)
                            .update(state=SubmissionState.finished))

    reset_count = reset_waiting_count + reset_finished_count
    if reset_count>0:
        statsd.increment("open_ended_assessment.grading_controller.expire_submissions.reset_timed_out_submissions",
            tags=["counter:{0}".format(reset_count)])
        log.debug("Reset {0} submissions that had timed out in their current grader.  {1}->W {2}->F"
                  .format(reset_count, reset_waiting_count, reset_finished_count))

    return True


def get_submissions_that_have_expired():
    """
    Check if submissions have expired, and return them if they have.
    Input:
        subs - A queryset of submissions
    """
    now = timezone.now()
    min_time = datetime.timedelta(seconds=settings.EXPIRE_SUBMISSIONS_AFTER)
    expired_subs=Submission.objects.filter(date_modified__lt=now-min_time, posted_results_back_to_queue=False, state=SubmissionState.waiting_to_be_graded)

    return expired_subs

def finalize_expired_submissions(timed_out_list):
    for sub in timed_out_list:
        grader_util.finalize_expired_submission(sub)

    log.debug("Reset {0} submissions that had timed out in their current grader.".format(len(timed_out_list)))

    return True

def check_if_grading_finished_for_duplicates():
    duplicate_submissions = Submission.objects.filter(
        preferred_grader_type = "PE",
        is_duplicate= True,
        posted_results_back_to_queue=False,
    )
    counter=0
    for sub in duplicate_submissions:
        if sub.duplicate_submission_id is not None:
            try:
                original_sub=Submission.objects.get(id=sub.duplicate_submission_id)
                if original_sub.state == SubmissionState.finished:
                    finalize_grade_for_duplicate_peer_grader_submissions(sub, original_sub)
                    counter+=1
                    log.debug("Finalized one duplicate submission: Original: {0} Duplicate: {1}".format(original_sub,sub))
            except Exception:
                log.exception("Could not finalize grade for submission with id {0}".format(sub.duplicate_submission_id))

    statsd.increment("open_ended_assessment.grading_controller.expire_submissions.check_if_duplicate_grading_finished",
        tags=[
            "counter:{0}".format(counter),
        ])
    log.info("Finalized {0} duplicate submissions".format(counter))
    return True

def finalize_grade_for_duplicate_peer_grader_submissions(sub, original_sub):
    transaction.commit()
    existing_grader_count = sub.grader_set.filter(grader_type__in=["PE", "IN", "ML"]).count() + 1

    # Get rid of extra "basic check" graders.
    for grader in sub.grader_set.filter(grader_type="BC")[1:]:
        grader.delete()

    if existing_grader_count < settings.MAX_GRADER_COUNT:
        original_grader_set = original_sub.grader_set.filter(grader_type__in=["PE", "IN", "ML"])[:(settings.MAX_GRADER_COUNT - existing_grader_count)]

        #Need to trickle through all layers to copy the info
        for i in xrange(0,len(original_grader_set)):
            grade = original_grader_set[i]
            rubric_set = list(grade.rubric_set.all())
            grade.pk = None
            grade.id = None
            grade.submission = sub
            grade.save()
            transaction.commit()
            for rubric in rubric_set:
                rubricitem_set = list(rubric.rubricitem_set.all())
                rubric.pk = None
                rubric.id = None
                rubric.grader = grade
                rubric.save()
                transaction.commit()
                for rubric_item in rubricitem_set:
                    rubricoption_set = list(rubric_item.rubricoption_set.all())
                    rubric_item.pk = None
                    rubric_item.id = None
                    rubric_item.rubric = rubric
                    rubric_item.save()
                    transaction.commit()
                    for rubric_option in rubricoption_set:
                        rubric_option.pk = None
                        rubric_option.id = None
                        rubric_option.rubric_item = rubric_item
                        rubric_option.save()
                        transaction.commit()

    sub.state = SubmissionState.finished
    sub.previous_grader_type = "PE"
    sub.save()

    return True

def remove_old_model_files():
    transaction.commit()
    locations = [cm['location'] for cm in CreatedModel.objects.all().values('location').distinct()]
    path_whitelist = []
    for loc in locations:
        success, latest_model = ml_grading_util.get_latest_created_model(loc)
        if success:
            grader_path = latest_model.model_relative_path
            path_whitelist.append(str(grader_path))
    onlyfiles = [ f for f in os.listdir(settings.ML_MODEL_PATH) if os.path.isfile(os.path.join(settings.ML_MODEL_PATH,f)) ]
    files_to_delete = [f for f in onlyfiles if f not in path_whitelist and not f.startswith(".")]
    could_not_delete_list=[]
    for i in xrange(0,len(files_to_delete)):
        mfile = files_to_delete[i]
        try:
            os.remove(str(os.path.join(settings.ML_MODEL_PATH, mfile)))
        except Exception:
            could_not_delete_list.append(i)

    log.debug("Deleted {0} old ML models.  Could not delete {1}".format((
        len(files_to_delete)-len(could_not_delete_list)), len(could_not_delete_list)))

def mark_student_duplicate_submissions():
    transaction.commit()
    unique_students = [s['student_id'] for s in Submission.objects.filter(is_duplicate=False, has_been_duplicate_checked = False).values('student_id').distinct()]
    total_dup_count=0
    for student in unique_students:
        student_dup_count=0
        responses, locations = zip(*Submission.objects.filter(student_id=student, is_duplicate=False, has_been_duplicate_checked = False).values_list('student_response', 'location').distinct())
        for resp, loc in zip(responses, locations):
            try:
                original = Submission.objects.filter(student_id=student, student_response=resp, location=loc, is_duplicate=False, has_been_duplicate_checked = True).values_list('id', 'student_response', 'location', 'date_created').order_by('date_created')[0]
                duplicates = Submission.objects.filter(student_id=student, student_response=resp, location=loc, is_duplicate=False, has_been_duplicate_checked = False).values_list('id', 'student_response', 'location', 'date_created').order_by('date_created')
                duplicate_data = zip(*duplicates)
                if len(duplicates)>0:
                    student_dup_count+=len(duplicates)
                    Submission.objects.filter(id__in=duplicate_data[0]).update(is_duplicate=True, duplicate_submission_id=original[0], has_been_duplicate_checked = True)
                    transaction.commit()
            except Exception:
                log.exception("Could not mark duplicates for student {0} location {1}".format(student,loc))
        if student_dup_count>0:
            log.info("Marked {0} duplicate subs from student {1}".format(student_dup_count,student))
            total_dup_count+=student_dup_count
    log.info("Marked duplicate subs for {0} students total.".format(total_dup_count))

def add_in_duplicate_ids():
    transaction.commit()
    total_dup_count=0
    unique_students = [s['student_id'] for s in Submission.objects.filter(is_duplicate=True, is_plagiarized=False, duplicate_submission_id = None).values('student_id').distinct()]
    for student in unique_students:
        student_dup_count=0
        duplicate_without_id = Submission.objects.filter(student_id=student, is_duplicate=True, is_plagiarized=False, duplicate_submission_id = None)
        for sub in duplicate_without_id:
            matching_sub = Submission.objects.filter(student_id=student, location=sub.location, is_duplicate=False, has_been_duplicate_checked = True)
            student_dup_count+=1
            if matching_sub.count()>0:
                matching_sub_id = matching_sub[0].id
                sub.duplicate_submission_id = matching_sub_id
            else:
                sub.is_duplicate = False
            sub.save()
        if student_dup_count>0:
            log.info("Added ids for {0} duplicates for student {1}".format(student_dup_count, student))
        total_dup_count+=student_dup_count
    log.info("Added ids for {0} duplicates total".format(total_dup_count))
    transaction.commit()


