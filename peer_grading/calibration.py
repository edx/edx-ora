import random
from django.conf import settings
from controller.models import Submission
import logging
from peer_grading.models import CalibrationHistory, CalibrationRecord

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

    for tag in ['submission_id', 'score', 'feedback', 'student_id', 'location']:
        if not tag in calibration_data:
            return False, ("Cannot find needed key {0} in request.".format(tag))

    try:
        calibration_history, success = CalibrationHistory.objects.get_or_create(
            student_id=calibration_data['student_id'],
            location=calibration_data['location'],
        )
    except:
        return False, ("Cannot get or create CalibrationRecord with "
                       "student id {0} and location {1}.".format(calibration_data['student_id'],
            calibration_data['location']))
    try:
        submission = Submission.objects.get(
            id=calibration_data['submission_id']
        )
    except:
        return False, ("Invalid submission id {0}.".format(calibration_data['submission_id']))

    try:
        actual_score = submission.get_last_successful_instructor_grader()['score']
    except:
        return False, ("Error getting actual score for submission id {0}.".format(calibration_data['submission_id']))

    if actual_score == -1:
        return False, (
        "No instructor graded submission for submission id {0}.".format(calibration_data['submission_id']))

    cal_record = CalibrationRecord(
        submission=submission,
        calibration_history=calibration_history,
        score=calibration_data['score'],
        actual_score=actual_score,
        feedback=calibration_data['feedback'],
    )

    cal_record.save()

    return True, {'cal_id': cal_record.id}


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
        sub = Submission.objects.get(id=calibration_essay_id)
    except:
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

    calibration_submissions = Submission.objects.filter(
        location=location,
        grader__grader_type="IN",
        grader__is_calibration=True,
    )

    calibration_submission_count = calibration_submissions.count()
    if calibration_submission_count < settings.PEER_GRADER_MINIMUM_TO_CALIBRATE:
        return False, "Not enough calibration essays."

    student_calibration_history = CalibrationHistory.objects.get(student_id=student_id, location=location)
    student_calibration_records = student_calibration_history.get_all_calibration_records()

    student_calibration_ids = [cr.submission.id for cr in list(student_calibration_records)]
    calibration_essay_ids = [cr.id for cr in list(calibration_submissions)]

    for i in xrange(0, len(calibration_essay_ids)):
        if calibration_essay_ids[i] not in student_calibration_ids:
            calibration_data = get_calibration_essay_data(calibration_essay_ids[i])
            return True, calibration_data

    if len(student_calibration_ids) > len(calibration_essay_ids):
        random_calibration_essay_id = random.sample(calibration_essay_ids, 1)[0]
        calibration_data = get_calibration_essay_data(random_calibration_essay_id)
        return True, calibration_data

    return False, "Unexpected error."


def check_calibration_status(problem_id,student_id):
    """
    Checks if a given student has calibrated for a given problem or not
    Input:
        dict containing problem_id, student_id
    Output:
        success, data
          success is a boolean
          data is a dict containing key 'calibrated', which is a boolean showing whether or not student is calibrated.
    """

    matching_submissions = Submission.objects.filter(location=problem_id)

    if matching_submissions.count() < 1:
        return False, "Invalid problem id specified: {0}".format(problem_id)

    calibration_history, created = CalibrationHistory.objects.get_or_create(student_id=student_id, location=problem_id)
    max_score = matching_submissions[0].max_score
    calibration_record_count = calibration_history.get_calibration_record_count()
    log.debug("Calibration record count: {0}".format(calibration_record_count))
    if (calibration_record_count >= settings.PEER_GRADER_MINIMUM_TO_CALIBRATE and
        calibration_record_count < settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE):
        calibration_error = calibration_history.get_average_calibration_error()
        normalized_calibration_error = calibration_error / float(max_score)
        if normalized_calibration_error >= settings.PEER_GRADER_MIN_NORMALIZED_CALIBRATION_ERROR:
            return True, {'calibrated': False}
        else:
            return True, {'calibrated': True}
    elif calibration_record_count >= settings.PEER_GRADER_MAXIMUM_TO_CALIBRATE:
        return True, {'calibrated': True}
    else:
        return True, {'calibrated': False}