from django.conf import settings
import sys

sys.path.append(settings.ML_PATH)
import feature_extractor
import essay_set
import json

from controller.models import GraderStatus


def perform_spelling_and_grammar_checks(string):
    """
    Performs basic spelling and grammar checks on an input dictionary
    Input:
        Any string
    Output:
        Feedback dictionary and an essay set object
    """
    feature_ext=feature_extractor.FeatureExtractor()
    e_set=essay_set.EssaySet(type="test")
    e_set.add_essay(string,0)

    feedback=feature_ext.gen_feedback(e_set)[0]

    return feedback, e_set

def simple_quality_check(string):
    """
    Performs a simple sanity test on an input string
    Input:
        Any string
    Output:
        Boolean indicating success/failure and dictionary with sanity checks
    """
    quality_dict={'feedback' : {}, 'score' : 1, 'grader_type' : 'BC', 'status' : GraderStatus.success}
    try:
        basic_check, e_set=perform_spelling_and_grammar_checks(string)
        total_length=len(string)
        word_length_ratio=total_length/float(len(e_set._tokens[0]))
    except:
        quality_dict['status']=GraderStatus.failure
        return False, quality_dict

    quality_dict['feedback']=json.dumps(basic_check)
    if(total_length<10 or word_length_ratio<=3 or
       basic_check['grammar_per_char']>.1 or basic_check['spelling_per_char']>.3):
        quality_dict['score']=0

    return True, quality_dict







