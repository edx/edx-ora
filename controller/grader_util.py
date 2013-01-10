import ConfigParser
from django.conf import settings
from create_grader import create_grader
from metrics.timing_functions import finalize_timing
from models import Submission
import logging
from models import GraderStatus, SubmissionState
import expire_submissions
from statsd import statsd
import json
import os
from staff_grading import staff_grading_util
from ml_grading import ml_grading_util
import rubric

log = logging.getLogger(__name__)

def add_additional_tags_to_dict(grader_dict, sub_id):
    """
    This adds additional tags to an input dictionary in order to allow it to be used as input into
    the create_and_handle_grader_object function.  This is used because basic check does not support/add
    all of these tags by default.
    Submission id is handled separately because it is the only tag here that is required to be correct for the
    create_and_handle_grader_object to handle the grader dictionary properly.  Basic check is not aware of the submission
    id, so it must be specially inserted here.
    Input:
        A partial grader dictionary and the associated submission id
    Output:
        A full grader dictionary
    """

    default_grader_dict={
        'feedback' : 'Errors with your submission.  Please try again or contact course staff.',
        'status' : GraderStatus.success,
        'grader_id' : 1,
        'grader_type' : "BC",
        'confidence' : 1,
        'score' : 0,
        'submission_id' : 1,
        'errors' : ""
    }
    grader_dict.update({'submission_id' : sub_id})
    default_grader_dict.update(grader_dict)

    return default_grader_dict


def create_and_handle_grader_object(grader_dict):
    """
    Creates a Grader object and associates it with a given submission
    Input is grader dictionary with keys:
     feedback, status, grader_id, grader_type, confidence, score,submission_id, errors
        Feedback should be a dictionary with as many keys as needed.
        Errors is a string containing errors.
    """

    for tag in ["feedback", "status", "grader_id", "grader_type", "confidence", "score", "submission_id", "errors"]:
        if tag not in grader_dict:
            return False, "{0} tag not in input dictionary.".format(tag)

    try:
        sub = Submission.objects.get(id=int(grader_dict['submission_id']))
    except:
        return False, "Error getting submission."

    log.debug(grader_dict['feedback'])

    try:
        grader_dict['feedback'] = json.loads(grader_dict['feedback'])
    except:
        pass

    if not isinstance(grader_dict['feedback'], dict):
        grader_dict['feedback'] = {'feedback': grader_dict['feedback']}

    if grader_dict['status'] == GraderStatus.failure:
        grader_dict['feedback'] = ' '.join(grader_dict['errors'])

    grader_dict['feedback'] = json.dumps(grader_dict['feedback'])

    grade = create_grader(grader_dict, sub)

    #Check to see if rubric scores were passed to the function, and handle if so.
    if 'rubric_scores_complete' in grader_dict and 'rubric_scores' in grader_dict:
        if grader_dict['rubric_scores_complete']==True:
            rubric.generate_rubric_object(grade,grader_dict['rubric_scores'], sub.rubric)

    #TODO: Need some kind of logic somewhere else to handle setting next_grader

    sub.previous_grader_type = grade.grader_type
    sub.next_grader_type = grade.grader_type

    #TODO: Some kind of logic to decide when sub is finished grading.

    #If we are calling this after a basic check and the score is 0, that means that the submission is bad, so mark as finished
    if(grade.status_code == GraderStatus.success and grade.grader_type in ["BC"] and grade.score==0):
        sub.state = SubmissionState.finished
    #If submission is ML or IN graded, and was successful, state is finished
    elif(grade.status_code == GraderStatus.success and grade.grader_type in ["IN", "ML"]):
        sub.state = SubmissionState.finished
    elif(grade.status_code == GraderStatus.success and grade.grader_type in ["PE"]):
        #If grading type is Peer, and was successful, check to see how many other times peer grading has succeeded.
        successful_peer_grader_count = sub.get_successful_peer_graders().count()
        #If number of successful peer graders equals the needed count, finalize submission.
        if successful_peer_grader_count >= settings.PEER_GRADER_COUNT:
            sub.state = SubmissionState.finished
        else:
            sub.state = SubmissionState.waiting_to_be_graded
    #If something fails, immediately mark it for regrading
    #TODO: Get better logic for handling failure cases
    elif(grade.status_code == GraderStatus.failure and sub.state == SubmissionState.being_graded):
        number_of_failures = sub.get_unsuccessful_graders().count()
        #If it has failed too many times, just return an error
        if number_of_failures > settings.MAX_NUMBER_OF_TIMES_TO_RETRY_GRADING:
            expire_submissions.finalize_expired_submission(sub)
        else:
            sub.state = SubmissionState.waiting_to_be_graded

    #Increment statsd whenever a grader object is saved.
    statsd.increment("open_ended_assessment.grading_controller.controller.create_grader_object",
        tags=["submission_state:{0}".format(sub.state),
              "grader_type:{0}".format(grade.grader_type),
              "grader_status:{0}".format(grade.status_code),
              "location:{0}".format(sub.location),
              "course_id:{0}".format(sub.course_id),
              "next_grader_type:{0}".format(sub.next_grader_type),
              "score:{0}".format(grade.score),
        ]
    )

    sub.save()

    #Insert timing finalization code
    finalize_timing(sub, grade)

    return True, {'submission_id': sub.xqueue_submission_id, 'submission_key': sub.xqueue_submission_key}


def get_grader_settings(settings_file):
    """
    Reads grader settings from a given file
    Output:
        Dictionary containing all grader settings
    """
    config = ConfigParser.RawConfigParser()
    config.read(settings_file)
    grader_type = config.get("grading", "grader_type")

    grader_settings = {
        'grader_type': grader_type,
    }

    return grader_settings


def get_eta_for_submission(location):
    """
    Gets an eta for a given location
    Input:
        Problem location
    Output:
        Boolean success, and an error message or eta
    """
    try:
        sub_graders = Submission.objects.filter(location=location)[0]
    except:
        return False, "No current problems for given location."

    eta = settings.DEFAULT_ESTIMATED_GRADING_TIME
    grader_settings_path = os.path.join(settings.GRADER_SETTINGS_DIRECTORY, sub_graders.grader_settings)
    grader_settings = get_grader_settings(grader_settings_path)

    if grader_settings['grader_type'] in ["ML", "IN"]:
        success, model = ml_grading_util.get_latest_created_model(location)
        if success:
            eta = settings.ML_ESTIMATED_GRADING_TIME
    elif grader_settings['grader_type'] in "PE":
        #Just use the default timing for now.
        pass

    return True, eta

def check_is_duplicate(submission_text,location, student_id, preferred_grader_type, check_plagiarized=False):
    is_duplicate=False
    duplicate_id=0

    if not check_plagiarized:
        sub_text_and_ids=Submission.objects.filter(
            location=location,
            is_duplicate=False,
            is_plagiarized=False,
            preferred_grader_type = preferred_grader_type,
        ).values('student_response', 'id')
    else:
        sub_text_and_ids=Submission.objects.filter(
            location=location,
            is_duplicate=False,
            is_plagiarized=False
        ).exclude(student_id=student_id).values('student_response', 'id')

    location_text=[sub['student_response'] for sub in sub_text_and_ids]
    if submission_text in location_text:
        location_ids = [sub['id'] for sub in sub_text_and_ids]
        sub_index=location_text.index(submission_text)
        is_duplicate=True
        duplicate_id=location_ids[sub_index]

    return is_duplicate,duplicate_id

def check_is_duplicate_and_plagiarized(submission_text,location, student_id, preferred_grader_type):
    is_duplicate, duplicate_submission_id = check_is_duplicate(submission_text, location, student_id, preferred_grader_type)
    is_plagiarized, plagiarized_submission_id = check_is_duplicate(submission_text, location, student_id, preferred_grader_type, check_plagiarized=True)
    if is_plagiarized:
        duplicate_submission_id=plagiarized_submission_id

    return is_duplicate, is_plagiarized, duplicate_submission_id