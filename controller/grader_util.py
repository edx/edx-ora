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
from peer_grading import peer_grading_util
import rubric_functions

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
        try:
            grader_dict['rubric_scores']=json.loads(grader_dict['rubric_scores'])
        except:
            pass

        if grader_dict['rubric_scores_complete']=='True':
            grader_dict['rubric_scores']=[int(r) for r in grader_dict['rubric_scores']]
            try:
                rubric_functions.generate_rubric_object(grade,grader_dict['rubric_scores'], sub.rubric)
            except:
                log.exception("Problem with getting rubric scores from dict : {0}".format(grader_dict))

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
        success= ml_grading_util.check_for_all_model_and_rubric_success(location)
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

def validate_rubric_scores(rubric_scores, rubric_scores_complete, sub):
    success=False
    if rubric_scores_complete!="True":
        return success, "Rubric scores complete is not true: {0}".format(rubric_scores_complete)

    success, targets=rubric_functions.generate_targets_from_rubric(sub.rubric)
    if not success:
        return success, "Cannot generate targets from rubric xml: {0}".format(sub.rubric)

    if not isinstance(rubric_scores,list):
        return success, "Rubric Scores is not a list: {0}".format(rubric_scores)

    if len(rubric_scores)!=len(targets):
        return success, "Number of scores saved does not equal number of targets.  Targets: {0} Rubric Scores: {1}".format(targets, rubric_scores)

    for i in xrange(0,len(rubric_scores)):
        try:
            rubric_scores[i]=int(rubric_scores[i])
        except:
            return success, "Cannot parse score into int".format(rubric_scores[i])

        if rubric_scores[i] < 0 or rubric_scores[i] > targets[i]:
            return success, "Score {0} under 0 or over max score {1}".format(rubric_scores[i], targets[i])
    success = True
    return success , ""

def check_name_uniqueness(problem_id, location, course_id):

    problem_name_pairs = Submission.objects.filter(course_id=course_id).values('problem_id', 'location').distinct()
    locations = [p['location'] for p in problem_name_pairs]
    problem_names = [p['problem_id'] for p in problem_name_pairs]

    equal_locations=[p for p in locations if p==location]
    equal_problem_id = [p for p in problem_names if p==problem_id]
    name_unique=True
    success=True

    if len(equal_problem_id)>1:
        name_unique=False
    elif len(equal_problem_id)==1:
        equal_id_index=problem_names.index(problem_id)
        matching_location=locations[equal_id_index]
        if matching_location!=location:
            name_unique=False

    return success, name_unique

def check_for_student_grading_notifications(student_id, course_id, last_time_viewed):
    success = True
    new_student_grading = False
    subs = Submission.objects.filter(state=SubmissionState.finished, date_modified__gte=last_time_viewed, course_id = course_id)
    if subs.count()>0:
        new_student_grading=True
    return success, new_student_grading

def check_for_combined_notifications(notification_dict):
    overall_success = True
    for tag in ['location', 'course_id', 'user_is_staff', 'last_viewed_time']:
        if tag not in notification_dict:
            return False, "Missing required key {0}".format(tag)

    location = notification_dict['location']
    course_id = notification_dict['course_id']
    user_is_staff = notification_dict['user_is_staff']
    last_time_viewed = notification_dict['last_time_viewed']

    combined_notifications = {}
    success, student_needs_to_peer_grade = peer_grading_util.get_peer_grading_notifications(course_id, student_id)
    if success:
        combined_notifications.update({'student_needs_to_peer_grade' : student_needs_to_peer_grade})

    if user_is_staff==True:
        success, staff_needs_to_grade = staff_grading_util.get_staff_grading_notifications(course_id)
        if success:
            combined_notifications.update({'staff_needs_to_grade' : staff_needs_to_grade})

    success, new_student_grading = check_for_student_grading_notifications(student_id, course_id, last_time_viewed)
    if success:
        combined_notifications.update({'new_student_grading_to_view' : new_student_grading})

    return overall_success, combined_notifications


