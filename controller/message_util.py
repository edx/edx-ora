from controller.models import Message, Grader, Submission

def create_message(message_dict):
    """
    Creates a message object.
    Input:
        Dictionary with keys specified below
    Output:
        Boolean true/false, message id or error message
    """

    for tag in ['grader_id', 'originator', 'submission_id', 'message', 'recipient', 'message_type']:
        if not message_dict.has_key(tag):
            return False, "Needed tag '{0}' missing".format(tag)

    grade=Grader.objects.get(id=message_dict['grader_id'])
    submission = Submission.objects.get(id = message_dict['submission_id'])

    msg=Message(
        grader=grade,
        message=message_dict['message'],
        originator=message_dict['originator'],
        recipient=message_dict['recipient'],
        message_type=message_dict['message_type']
    )

    try:
        msg.save()
    except:
        error="Could not save the message"
        log.exception(error)
        return False, error

    return True, msg.id

