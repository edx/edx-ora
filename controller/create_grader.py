from models import Grader

def create_grader(grader_dict, sub):
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