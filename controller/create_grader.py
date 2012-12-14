from models import Grader
import logging

log=logging.getLogger(__name__)

def create_grader(grader_dict, sub):
    log.debug("Creating grader with feedback: {0} and type {1}".format(grader_dict['feedback'], grader_dict['grader_type']))
    grade = Grader(
        score=grader_dict['score'],
        feedback=grader_dict['feedback'],
        status_code=grader_dict['status'],
        grader_id=grader_dict['grader_id'],
        grader_type=grader_dict['grader_type'],
        confidence=grader_dict['confidence'],
        submission=sub,
    )

    grade.save()

    return grade