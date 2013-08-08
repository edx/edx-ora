import random
from django.conf import settings
from controller.models import Submission, GraderStatus
import logging
from peer_grading.models import CalibrationHistory, CalibrationRecord
import json

log = logging.getLogger(__name__)

def create_and_save_calibration_record(calibration_data):
    """
    This function will create and save a calibration record object.
    Input:
        Dictionary containing keys submission_id, score, feedback, student_id, location
    Output:
        Boolean indicating success and dictionary with calibration id
        Or boolean indicating failure and error message
    """

    for tag in ['submission_id', 'score', 'feedback', 'student_id', 'location', 'rubric_scores_complete', 'rubric_scores']:
        if not tag in calibration_data:
            error_msg = "Cannot find needed key {0} in request.".format(tag)
            log.error(error_msg)
            return False, (error_msg)

    try:
        calibration_history, success = CalibrationHistory.objects.get_or_create(
            student_id=calibration_data['student_id'],
            location=calibration_data['location'],
        )
    except DatabaseError:
        error_msg = "get_or_create failed with DatabaseError "
        "student id {0} and location {1}.".format(calibration_data['student_id'],
                                                  calibration_data['location'])
        log.exception(error_msg)
        return False, (error_msg)
        
    except Exception:
        error_msg = "Cannot get or create CalibrationRecord with "
        "student id {0} and location {1}.".format(calibration_data['student_id'],
                                                  calibration_data['location'])
        log.exception(error_msg)
        return False, (error_msg)
    try:
        submission = Submission.objects.get(
            id=calibration_data['submission_id']
        )
    except Exception:
        error_msg = "Invalid submission id {0}.".format(calibration_data['submission_id'])
        log.exception(error_msg)
        return False, (error_msg)

    try:
        last_grader = submission.get_last_successful_instructor_grader()
        actual_score = last_grader['score']
        actual_rubric = last_grader['rubric']
        actual_feedback = last_grader['feedback']
    except Exception:
        error_msg = "Error getting actual score for submission id {0}.".format(calibration_data['submission_id'])
        log.exception(error_msg)
        return False, (error_msg)

    if actual_score == -1:
        error_msg = "No instructor graded submission for submission id {0}.".format(calibration_data['submission_id'])
        log.error(error_msg)
        return False, (error_msg)

    cal_record = CalibrationRecord(
        submission=submission,
        calibration_history=calibration_history,
        score=calibration_data['score'],
        actual_score=actual_score,
        feedback=calibration_data['feedback'],
        rubric_scores_complete = calibration_data['rubric_scores_complete'],
        rubric_scores = json.dumps(calibration_data['rubric_scores']),
    )

    cal_record.save()

    return True, {'cal_id': cal_record.id, 'actual_score' : actual_score, 'actual_rubric' : actual_rubric, 'actual_feedback' : actual_feedback}


def get_calibration_essay_data(calibration_essay_id):
    """
    From a calibration essay id, lookup prompt, rubric, max score, prompt, essay text, and return
    Input:
        calibration essay id
    Output:
        Dict containing submission id, submission key, student response, prompt, rubric, max_score
        Or error string if submission cannot be found
    """

    try:
        sub = Submission.objects.get(id=int(calibration_essay_id))
    except Exception:
        return "Could not find submission!"

    response = {
        'submission_id': calibration_essay_id,
        'submission_key': sub.xqueue_submission_key,
        'student_response': sub.student_response,
        'prompt': sub.prompt,
        'rubric': sub.rubric,
        'max_score': sub.max_score,
    }

    return response


def get_calibration_essay(location, student_id):
    """
    Gets a calibration essay for a particular student and location (problem id).
    Input:
        student id, location
    Output:
        dict containing text of calibration essay, prompt, rubric, max score, calibration essay id
    """

    #Get all possible calibration essays for problem
    calibration_submissions = Submission.objects.filter(
        location=location,
        grader__grader_type="IN",
        grader__is_calibration=True,
        grader__status_code=GraderStatus.success,
    )

    #Check to ensure sufficient calibration essays exists
    calibration_submission_count = calibration_submissions.count()
    if calibration_submission_count < settings.PEER_GRADER_MINIMUM_TO_CALIBRATE:
        calibration_submissions = Submission.objects.filter(
            location=location,
            grader__grader_type="IN",
            grader__status_code=GraderStatus.success,
        )
        calibration_submission_count = calibration_submissions.count()

    if calibration_submission_count < settings.PEER_GRADER_MINIMUM_TO_CALIBRATE:
        # return False, "Not enough calibration essays."
        return False, "The course staff has not graded enough calibration essays yet, please check back later."

    #Get all student calibration done on current problem
    try:
        student_calibration_history, success = CalibrationHistory.objects.get_or_create(student_id=student_id, location=location)
    except DatabaseError:
        error_msg = "get_or_create failed with DatabaseError "
        "student id {0} and location {1}.".format(student_id,
                                                  location)
        log.exception(error_msg)
        return False, (error_msg)
        
    student_calibration_records = student_calibration_history.get_all_calibration_records()
    student_calibration_ids = [cr.submission.id for cr in list(student_calibration_records)]
    calibration_essay_ids = [cr.id for cr in list(calibration_submissions)]

    #Ensure that student only gets calibration essays that they have not seen before
    for i in xrange(0, len(calibration_essay_ids)):
        if calibration_essay_ids[i] not in student_calibration_ids:
            calibration_data = get_calibration_essay_data(calibration_essay_ids[i])
            return True, calibration_data

    #If student has already seen all the calibration essays, give them a random one.
    if len(student_calibration_ids) > len(calibration_essay_ids):
        random_calibration_essay_id = random.choice(calibration_essay_ids)
        calibration_data = get_calibration_essay_data(random_calibration_essay_id)
        return True, calibration_data

    return False, "Unexpected error."


def check_calibration_status(location,student_id):
    """
    Checks if a given student has calibrated for a given problem or not
    Input:
        dict containing problem_id, student_id
    Output:
        success, data
          success is a boolean
          data is a dict containing key 'calibrated', which is a boolean showing whether or not student is calibrated.
    """

    matching_submissions = Submission.objects.filter(location=location)

    if matching_submissions.count() < 1:
        return False, "Invalid problem id specified: {0}".format(location)

    #Get student calibration history and count number of records associated with it
    try:
        calibration_history, created = CalibrationHistory.objects.get_or_create(student_id=student_id, location=location)
    except DatabaseError:
        error_msg = "get_or_create failed with DatabaseError "
        "student id {0} and location {1}.".format(student_id,
                                                  location)
        log.exception(error_msg)
        return False, (error_msg)
    
    max_score = matching_submissions[0].max_score
    calibration_record_count = calibration_history.get_calibration_record_count()

    calibration_dict={'total_calibrated_on_so_far' : calibration_record_count}
    #If student has calibrated more than the minimum and less than the max, check if error is higher than specified
    #Threshold.  Send another calibration essay if so.
    if (calibration_record_count >= settings.PEER_GRADER_MINIMUM_TO_CALIBRATE and
        calibration_record_count < settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE):
        #Get average student error on the calibration records.
        calibration_error = calibration_history.get_average_calibration_error()
        if max_score>0:
            normalized_calibration_error = calibration_error / float(max_score)
        else:
            normalized_calibration_error=0
        #If error is too high, student not calibrated, otherwise they are.
        if normalized_calibration_error >= settings.PEER_GRADER_MIN_NORMALIZED_CALIBRATION_ERROR:
            calibration_dict.update({'calibrated': False})
            return True, calibration_dict
        else:
            calibration_dict.update({'calibrated': True})
            return True, calibration_dict     #If student has seen too many calibration essays, just say that they are calibrated.
    elif calibration_record_count >= settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE:
        calibration_dict.update({'calibrated': True})
        return True, calibration_dict 
    #If they have not already calibrated the minimum number of essays, they are not calibrated
    else:
        calibration_dict.update({'calibrated': False})
        return True, calibration_dict 
