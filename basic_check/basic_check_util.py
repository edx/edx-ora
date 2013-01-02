from django.conf import settings
import sys

sys.path.append(settings.ML_PATH)
import feature_extractor
import essay_set
import json
import logging
log=logging.getLogger(__name__)

from controller.models import GraderStatus


def perform_spelling_and_grammar_checks(string):
    """
    Performs basic spelling and grammar checks on an input dictionary
    Input:
        Any string
    Output:
        Feedback dictionary and an essay set object
    """
    feature_ext = feature_extractor.FeatureExtractor()
    e_set = essay_set.EssaySet(type="test")
    e_set.add_essay(string, 0)

    feedback = feature_ext.gen_feedback(e_set)[0]

    return feedback, e_set


def simple_quality_check(string):
    """
    Performs a simple sanity test on an input string
    Input:
        Any string
    Output:
        Boolean indicating success/failure and dictionary with sanity checks
        Dictionary contains keys feedback, score, grader_type, and status
        Dictionary key feedback contains further keys markup_text, spelling, and grammar
    """

    #Maximum proportion of characters in a string that can be badly spelled or grammatically incorrect
    #before it is rejected
    SPELLING_MAXIMUM = .3
    GRAMMAR_MAXIMUM = .1

    #Minimum number of characters needed in a string before it is ok
    LENGTH_MINIMUM = 25

    #Minimum characters per word needed in a response (below is rejected)
    CHARS_PER_WORD_MINIMUM = 3

    quality_dict = {'feedback': {}, 'score': 1, 'grader_type': 'BC', 'status': GraderStatus.success}
    try:
        basic_check, e_set = perform_spelling_and_grammar_checks(string)
        total_length = len(string)
        word_length_ratio = total_length / float(len(e_set._tokens[0])+.1)
    except:
        log.exception("could not run basic checks.")
        quality_dict['status'] = GraderStatus.failure
        return False, quality_dict

    quality_dict['feedback'] = json.dumps({k: basic_check[k] for k in ['markup_text', 'spelling', 'grammar']})
    if(total_length < LENGTH_MINIMUM or word_length_ratio <= CHARS_PER_WORD_MINIMUM or
       basic_check['grammar_per_char'] > GRAMMAR_MAXIMUM or basic_check['spelling_per_char'] > SPELLING_MAXIMUM):
        quality_dict['score'] = 0

    return True, quality_dict







