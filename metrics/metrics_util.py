from models import Timing
from django.utils import timezone
from controller.models import Submission, Grader
import logging

log=logging.getLogger(__name__)

def initialize_timing(sub_id):
    success, timing_dict=generate_initial_timing_dict(sub_id)
    if not success:
        log.warning("Initial timing dict generation failed with error: {0}".format(timing_dict))
        return False

    success, timing_id = instantiate_timing_object(timing_dict)

    if not success:
        log.warning("Timing object instantiation failed with error: {0}".format(timing_dict))
        return False

    return True

def finalize_timing(sub_id, grade_id):
    success, timing_dict=generate_final_timing_dict(sub_id,grade_id)
    if not success:
        log.warning("Final timing dict generation failed with error: {0}".format(timing_dict))
        return False

    success, timing_id=save_grader_data_in_timing_object(timing_dict)

    if not success:
        log.warning("Timing object finalization failed with error: {0}".format(timing_id))
        return False

    return True

def generate_initial_timing_dict(submission_id):
    """
    Generate a timing dictionary from a submission object id.
    Input:
        integer submission id or Submission object
    Output:
        boolean success, timing dictionary or error message
    """

    if not isinstance(submission_id,int) and not isinstance(submission_id, Submission):
        return False, "Invalid input!  Needs to be int (submission id) or Submission object."

    if isinstance(submission_id,int):
        try:
            submission_id=Submission.objects.get(id=submission_id)
        except:
            return False, "Could not generate submission object from input id."

    timing_dict={
        'student_id' : submission_id.student_id,
        'location' : submission_id.location,
        'problem_id' : submission_id.problem_id,
        'course_id' : submission_id.course_id,
        'max_score' : submission_id.max_score,
        'submission_id' : submission_id.id,
    }

    return True, timing_dict

def generate_final_timing_dict(submission_id,grader_id):
    """
    Generate a final timing dictionary from a submission object id and grader id.
    Input:
        integer submission id or Submission object and grader id or grader object
    Output:
        boolean success, timing dictionary or error message
    """
    success, timing_dict=generate_initial_timing_dict(submission_id)

    if not success:
        return False, "Invalid submission id."

    if not isinstance(grader_id,int) and not isinstance(grader_id, Grader):
        return False, "Invalid input!  Needs to be int (submission id) or Submission object."

    if isinstance(grader_id,int):
        try:
            grader_id=Grader.objects.get(id=grader_id)
        except:
            return False, "Could not generate grader object from input id."

    timing_dict.update({
        'grader_type' : grader_id.grader_type,
        'status_code' : grader_id.status_code,
        'confidence' : grader_id.confidence,
        'is_calibration' : grader_id.is_calibration,
        'score' : grader_id.score,
        'grader_version' : grader_id.grader_id,
        'grader_id' : grader_id.id,
    })

    return True, timing_dict


def instantiate_timing_object(timing_dict):
    """
    Input is dictionary with tags specified below in tags variable
    Output is boolean success/fail, and then either timing id or error message
    """

    tags=['student_id', 'location', 'problem_id', 'course_id', 'max_score', 'submission_id']

    for tag in tags:
        if tag not in timing_dict:
            return False, "Could not find needed tag : {0}".format(tag)

    timing=Timing(
        start_time=timezone.now(),
        student_id=timing_dict['student_id'],
        location=timing_dict['location'],
        problem_id=timing_dict['problem_id'],
        course_id=timing_dict['course_id'],
        max_score=timing_dict['max_score'],
        submission_id=timing_dict['submission_id'],
    )

    timing.save()

    return True, timing.id

def save_grader_data_in_timing_object(timing_dict):
    """
    Looks up a timing object that was instantiated, and then adds in final data to it.
    Input: Dictionary with below tags in timing_lookup_tags and to_save_tags
    Output: Boolean true/false, and then timing id or error message
    """

    timing_lookup_tags=['student_id', 'location', 'problem_id', 'course_id', 'max_score', 'submission_id']
    to_save_tags=['grader_type', 'status_code', 'confidence', 'is_calibration', 'score', 'grader_version', 'grader_id']

    tags= timing_lookup_tags + to_save_tags
    for tag in tags:
        if tag not in timing_dict:
            return False, "Could not find needed tag : {0}".format(tag)

    timing_list=Timing.objects.filter(
        student_id=timing_dict['student_id'],
        location=timing_dict['location'],
        problem_id=timing_dict['problem_id'],
        course_id=timing_dict['course_id'],
        max_score=timing_dict['max_score'],
        submission_id=timing_dict['submission_id'],
    )[:1]

    if timing_list.count()==0:
        return False, "Could not find a matching timing object."

    timing=timing_list[0]

    timing.grader_type=timing_dict['grader_type']
    timing.status_code=timing_dict['status_code']
    timing.confidence=timing_dict['confidence']
    timing.is_calibration=timing_dict['is_calibration']
    timing.score=timing_dict['score']
    timing.grader_version=timing_dict['grader_version']
    timing.grader_id=timing_dict['grader_id']

    timing.end_time=timezone.now()
    timing.finished_timing=True

    timing.save()

    return True, timing.id

