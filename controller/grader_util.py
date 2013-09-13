from __future__ import unicode_literals
import ConfigParser
from django.conf import settings
from create_grader import create_grader
from models import Submission
import logging
from models import GraderStatus, SubmissionState, STATE_CODES, NotificationTypes
from statsd import statsd
import json
import os
import util
from staff_grading import staff_grading_util
from ml_grading import ml_grading_util
from peer_grading import peer_grading_util
import rubric_functions
from metrics.models import StudentProfile
import re
import control_util

log = logging.getLogger(__name__)

error_template = u"""

<section>
    <div class="shortform">
        <div class="result-errors">
          There was an error with your submission.  Please contact the course staff.
        </div>
    </div>
    <div class="longform">
        <div class="result-errors">
          {errors}
        </div>
    </div>
</section>

"""

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
    except Exception:
        return False, "Error getting submission."

    try:
        grader_dict['feedback'] = json.loads(grader_dict['feedback'])
    except Exception:
        pass

    if not isinstance(grader_dict['feedback'], dict):
        grader_dict['feedback'] = {'feedback': grader_dict['feedback']}

    for k in grader_dict['feedback']:
        grader_dict['feedback'][k] = util.sanitize_html(grader_dict['feedback'][k])

    if grader_dict['status'] == GraderStatus.failure:
        grader_dict['feedback'] = ' '.join(grader_dict['errors'])

    grader_dict['feedback'] = json.dumps(grader_dict['feedback'])

    grade = create_grader(grader_dict, sub)

    #Check to see if rubric scores were passed to the function, and handle if so.
    if 'rubric_scores_complete' in grader_dict and 'rubric_scores' in grader_dict:
        try:
            grader_dict['rubric_scores']=json.loads(grader_dict['rubric_scores'])
        except Exception:
            pass

        if grader_dict['rubric_scores_complete'] in ['True', "TRUE", 'true', True]:
            grader_dict['rubric_scores']=[int(r) for r in grader_dict['rubric_scores']]
            try:
                rubric_functions.generate_rubric_object(grade,grader_dict['rubric_scores'], sub.rubric)
            except Exception:
                log.exception("Problem with getting rubric scores from dict : {0}".format(grader_dict))

    #TODO: Need some kind of logic somewhere else to handle setting next_grader

    sub.previous_grader_type = grade.grader_type
    sub.next_grader_type = grade.grader_type

    #check to see if submission is flagged.  If so, put it in a flagged state
    submission_is_flagged = grader_dict.get('is_submission_flagged', False)
    if submission_is_flagged:
        sub.state = SubmissionState.flagged
    else:
        #TODO: Some kind of logic to decide when sub is finished grading.

        control = control_util.SubmissionControl(sub)
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
            if successful_peer_grader_count >= control.peer_grader_count:
                sub.state = SubmissionState.finished
            else:
                sub.state = SubmissionState.waiting_to_be_graded
        #If something fails, immediately mark it for regrading
        #TODO: Get better logic for handling failure cases
        elif(grade.status_code == GraderStatus.failure and sub.state == SubmissionState.being_graded):
            number_of_failures = sub.get_unsuccessful_graders().count()
            #If it has failed too many times, just return an error
            if number_of_failures > settings.MAX_NUMBER_OF_TIMES_TO_RETRY_GRADING:
                finalize_expired_submission(sub)
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
    except Exception:
        return False, "No current problems for given location."

    eta = settings.DEFAULT_ESTIMATED_GRADING_TIME
    grader_type = sub_graders.preferred_grader_type

    if grader_type == "ML":
        #success= ml_grading_util.check_for_all_model_and_rubric_success(location)
        #if success:
        #    eta = settings.ML_ESTIMATED_GRADING_TIME
        pass
    elif grader_type == "PE":
        #Just use the default timing for now.
        pass
    elif grader_type=="IN":
        #Use default for now
        pass

    return True, eta

def find_close_match_for_string(string, text_list):
    SUB_CHARS = "[,\.;!?']"
    CLOSE_MATCH_THRESHOLD = .95
    CLOSE_MATCH_INVALIDATION_WORDS = ['not', 'isnt', 'cannot']
    LENGTH_MATCH_THRESHOLD = .05

    success = False
    close_match_found = False
    close_match_index = 0

    tokenized_string = re.sub(SUB_CHARS, '', string.lower()).split(" ")
    string_length = len(string)
    length_min = string_length * (1-LENGTH_MATCH_THRESHOLD)
    length_max = string_length * (1+LENGTH_MATCH_THRESHOLD)
    string_tokens_length = len(tokenized_string)

    success = True
    for i in xrange(0,len(text_list)):
        text_length = len(text_list[i])
        contains_invalidation_word = False
        if length_min < text_length < length_max:
            tokenized_text = re.sub(SUB_CHARS, '', text_list[i].lower()).split(" ")
            text_tokens_length = len(tokenized_text)
            for word in CLOSE_MATCH_INVALIDATION_WORDS:
                if word in tokenized_text:
                    contains_invalidation_word = True

            if not contains_invalidation_word:
                string_text_overlap = len([ts for ts in tokenized_string if ts in tokenized_text])
                text_string_overlap = len([tt for tt in tokenized_text if tt in tokenized_string])
                if (string_text_overlap + text_string_overlap) > float((string_tokens_length + text_tokens_length)*CLOSE_MATCH_THRESHOLD):
                    close_match_found = True
                    close_match_index = i
                    break

    return success, close_match_found, close_match_index


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
    location_ids = [sub['id'] for sub in sub_text_and_ids]

    if submission_text in location_text:
        sub_index=location_text.index(submission_text)
        is_duplicate=True
        duplicate_id=location_ids[sub_index]

    if not is_duplicate:
        success, close_match_found, close_match_index = find_close_match_for_string(submission_text, location_text)
        if success and close_match_found:
            duplicate_id = location_ids[close_match_index]
            is_duplicate = True

    return is_duplicate,duplicate_id

def check_is_duplicate_and_plagiarized(submission_text,location, student_id, preferred_grader_type):
    is_duplicate, duplicate_submission_id = check_is_duplicate(submission_text, location, student_id, preferred_grader_type)
    is_plagiarized, plagiarized_submission_id = check_is_duplicate(submission_text, location, student_id, preferred_grader_type, check_plagiarized=True)
    if is_plagiarized:
        duplicate_submission_id=plagiarized_submission_id

    return is_duplicate, is_plagiarized, duplicate_submission_id

def validate_rubric_scores(rubric_scores, rubric_scores_complete, sub):
    success=False
    if rubric_scores_complete not in ["True", True, "true"]:
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
        except Exception:
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
    subs = Submission.objects.filter(state=SubmissionState.finished, date_modified__gte=last_time_viewed, course_id = course_id, student_id = student_id)
    if subs.count()>0:
        new_student_grading=True
    return success, new_student_grading

def get_problems_student_has_tried(student_id, course_id):
    success = True
    subs = Submission.objects.filter(student_id=student_id, course_id = course_id)
    sub_list = []
    if subs.count()>0:
        sub_locations = [s['location'] for s in subs.values('location').distinct()]
        for location in sub_locations:
            last_sub = subs.filter(location=location).order_by('-date_modified')[0]
            problem_name = last_sub.problem_id
            sub_state = last_sub.state
            sub_codes = [s[0] for s in STATE_CODES]
            state_index = sub_codes.index(sub_state)
            sub_human_state = STATE_CODES[state_index][1]
            eta = 0
            eta_available = False
            if sub_state in ["W","C"]:
                success, eta = get_eta_for_submission(location)
                eta_available = success
            sub_dict={
                'state' : sub_human_state,
                'location' : location,
                'grader_type' : last_sub.previous_grader_type,
                'problem_name' : last_sub.problem_id,
                'eta' : eta,
                'eta_available' : eta_available,
            }
            sub_list.append(sub_dict)
    return success, sub_list

def check_for_combined_notifications(notification_dict):
    overall_success = True
    for tag in ['course_id', 'user_is_staff', 'last_time_viewed', 'student_id']:
        if tag not in notification_dict:
            return False, "Missing required key {0}".format(tag)

    course_id = notification_dict['course_id']
    user_is_staff = notification_dict['user_is_staff']
    if isinstance(user_is_staff, basestring):
        user_is_staff = (user_is_staff == "True")
    last_time_viewed = notification_dict['last_time_viewed']
    student_id = notification_dict['student_id']
    overall_need_to_check=False

    combined_notifications = {}
    pc = peer_grading_util.PeerCourse(course_id, student_id)
    success, student_needs_to_peer_grade = pc.notifications()
    if success:
        combined_notifications.update({NotificationTypes.peer_grading : student_needs_to_peer_grade})
        if student_needs_to_peer_grade==True:
            overall_need_to_check=True

    if user_is_staff==True:
        sc = staff_grading_util.StaffCourse(course_id)
        success, staff_needs_to_grade = sc.notifications()
        if success:
            combined_notifications.update({NotificationTypes.staff_grading : staff_needs_to_grade})
            if staff_needs_to_grade==True:
                overall_need_to_check=True

        success, flagged_submissions_exist = peer_grading_util.get_flagged_submission_notifications(course_id)
        if success:
            combined_notifications.update({NotificationTypes.flagged_submissions : flagged_submissions_exist})
            if flagged_submissions_exist==True:
                overall_need_to_check=True

    success, new_student_grading = check_for_student_grading_notifications(student_id, course_id, last_time_viewed)
    if success:
        combined_notifications.update({
            NotificationTypes.new_grading_to_view : new_student_grading
        })
        if new_student_grading==True:
            overall_need_to_check=True

    combined_notifications.update({NotificationTypes.overall : overall_need_to_check})
    return overall_success, combined_notifications


def finalize_expired_submission(sub):
    """
    Expire submissions by posting back to LMS with error message.
    Input:
        timed_out_list from check_if_expired method
    Output:
        Success code.
    """

    grader_dict = {
        'score': 0,
        'feedback': error_template.format(errors="Error scoring submission."),
        'status': GraderStatus.failure,
        'grader_id': "0",
        'grader_type': sub.next_grader_type,
        'confidence': 1,
        'submission_id' : sub.id,
        }

    sub.state = SubmissionState.finished
    sub.save()

    grade = create_grader(grader_dict,sub)

    statsd.increment("open_ended_assessment.grading_controller.expire_submissions.finalize_expired_submission",
                     tags=[
                         "course:{0}".format(sub.course_id),
                         "location:{0}".format(sub.location),
                         'grader_type:{0}'.format(sub.next_grader_type)
                     ])

    return True


