from models import Message, Grader, Submission
import logging

from statsd import statsd

log=logging.getLogger(__name__)

def create_message(message_dict):
    """
    Creates a message object.
    Input:
        Dictionary with keys specified below
    Output:
        Boolean true/false, message id or error message
    """

    for tag in ['grader_id', 'originator', 'submission_id', 'message', 'recipient', 'message_type', 'score']:
        if not message_dict.has_key(tag):
            return False, "Needed tag '{0}' missing".format(tag)

    grade=Grader.objects.get(id=message_dict['grader_id'])
    submission = Submission.objects.get(id = message_dict['submission_id'])


    msg=Message(
        grader=grade,
        message=message_dict['message'],
        originator=message_dict['originator'],
        recipient=message_dict['recipient'],
        message_type=message_dict['message_type'],
        score=message_dict['score']
    )

    try:
        msg.save()
    except Exception:
        error="Could not save the message"
        log.exception(error)
        return False, error

    statsd.increment("open_ended_assessment.grading_controller.create_message",
        tags=["course:{0}".format(submission.course_id),
              "location:{0}".format(submission.location),
              "grader_type:{0}".format(submission.previous_grader_type),
              "grade:{0}".format(grade.score),
              "message_type:{0}".format(message_dict['message_type']),
              "message_score:{0}".format(message_dict['score'])
              ]
    )
    return True, msg.id

