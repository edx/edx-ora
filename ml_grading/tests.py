"""
Run me with:
    python manage.py test --settings=edx_ora.test_settings ml_grading
"""

import unittest
import os
import random
import logging
import json
from django.conf import settings
import test_util
from controller.grader_util import create_and_handle_grader_object
from django.test.client import Client
import project_urls
from controller.models import Submission
from ml_model_creation import handle_single_location
from ml_grader import handle_single_item
from models import CreatedModel

log = logging.getLogger(__name__)

CHARACTER_LIMIT = 1000
TRAINING_LIMIT = 5
SUB_LOCATION = "test_location"

RUBRIC_XML_TEMPLATE = """
<rubric>
    {rubric_categories}
</rubric>
            """

RUBRIC_CATEGORY_TEMPLATE = """
<category>
    <description>One</description>
    {rubric_options}
</category>
"""

RUBRIC_OPTION_TEMPLATE = """
    <option>{option_score}</option>
"""

SUBMIT_URL = project_urls.ControllerURLs.submit

def construct_rubric_xml(scores):
    rubric_category_count = len(scores[0])
    option_counts = []
    for i in xrange(0,len(scores[0])):
        column_vals = [s[i] for s in scores]
        column_max = max(column_vals)
        option_counts.append(column_max)

    category_xml =[]
    for i in xrange(0,rubric_category_count):
        option_xml = []
        for m in xrange(0,option_counts[i]):
            option_xml.append(RUBRIC_OPTION_TEMPLATE.format(option_score = m))
        category_xml.append(RUBRIC_CATEGORY_TEMPLATE.format(rubric_options = " ".join(option_xml)))
    return RUBRIC_XML_TEMPLATE.format(rubric_categories = " ".join(category_xml))

def reformat_scores(scores):
    unique_score_points = []
    for i in xrange(0,len(scores[0])):
        column_vals = list(set([s[i] for s in scores]))
        column_vals.sort()
        unique_score_points.append(column_vals)
    unique_score_dicts = []
    for i in xrange(0,len(unique_score_points)):
        unique_score_dicts.append({})
        for m in xrange(0,len(unique_score_points[i])):
            unique_score_dicts[i].update({unique_score_points[i][m] : m})
    for i in xrange(0,len(scores)):
        for m in xrange(0,len(scores[i])):
            scores[i][m] = unique_score_dicts[m][scores[i][m]]
    return scores


class DataLoader():
    def load_text_files(self, pathname):
        filenames = os.listdir(pathname)
        text = []
        for filename in filenames:
            data = open(os.path.join(pathname, filename)).read()
            text.append(data[:CHARACTER_LIMIT])
        return text

    def load_json_file(self, filename):
        datafile = open(os.path.join(filename))
        data = json.load(datafile)
        return data

    def load_data(self):
        """
        Override when inheriting
        """
        pass

class PolarityLoader(DataLoader):
    def __init__(self, pathname):
        self.pathname = pathname

    def load_data(self):
        filenames = os.listdir(self.pathname)
        directories = [os.path.abspath(os.path.join(self.pathname,f)) for f in filenames if not os.path.isfile(os.path.join(self.pathname,f)) and f in ["neg", "pos"]]

        #Sort so neg is first
        directories.sort()
        #We need to have both a postive and a negative folder to classify
        if len(directories)!=2:
            raise Exception("Need a pos and a neg directory in {0}".format(self.pathname))

        neg = self.load_text_files(directories[0])
        pos = self.load_text_files(directories[1])

        scores = [[0] for i in xrange(0,len(neg))] + [[1] for i in xrange(0,len(pos))]
        text = neg + pos
        return scores, text


class ModelCreator():
    def __init__(self, location):
        self.location = location

    def create_model(self):
        return handle_single_location(self.location)

class Grader():
    def __init__(self, session):
        self.session = session

    def grade(self):
        return handle_single_item(self.session)

class GenericTest(object):
    loader = DataLoader
    data_path = ""

    def load_data(self):
        data_loader = self.loader(os.path.join(settings.TEST_PATH, self.data_path))
        scores, text = data_loader.load_data()
        scores = reformat_scores(scores)
        rubric_xml = construct_rubric_xml(scores)
        return rubric_xml, scores, text

    def generic_setup(self, rubric_xml, scores, text):
        test_util.create_user()

        self.c = Client()
        self.c.login(username='test', password='CambridgeMA')

        #Shuffle to mix up the classes, set seed to make it repeatable
        random.seed(1)
        shuffled_scores = []
        shuffled_text = []
        indices = [i for i in xrange(0,len(scores))]
        random.shuffle(indices)
        for i in indices:
            shuffled_scores.append(scores[i])
            shuffled_text.append(text[i])

        text = shuffled_text[:TRAINING_LIMIT]
        scores = shuffled_scores[:TRAINING_LIMIT]
        self.scores = scores
        self.text = text
        self.rubric_xml = rubric_xml

    def create_grader_and_rubric(self, sub, scores):
        grader_dict = {
            "feedback" : "",
            "status" : "S",
            "grader_id" : "1",
            "grader_type" : "IN",
            "confidence" : 1,
            "score" : sum(scores),
            "submission_id" : sub.id,
            "errors" : [],
            'rubric_scores_complete' : True,
            'rubric_scores' : scores
        }
        create_and_handle_grader_object(grader_dict)

    def create_models(self, rubric_xml, scores, text):
        self.location = SUB_LOCATION
        for i in xrange(0,len(text)):
            sub = self.add_ungraded_sub(rubric_xml, text[i])
            self.create_grader_and_rubric(sub, scores[i])

    def add_ungraded_sub(self, rubric_xml, text):
        grader_payload = {
            'location': self.location,
            'course_id': u'MITx/6.002x',
            'problem_id': u'6.002x/Welcome/OETest',
            'grader': "temp",
            'prompt' : 'This is a prompt',
            'rubric' : rubric_xml,
            'grader_settings' : "ml_grading.conf",
            'skip_basic_checks': False
        }
        xqueue_body = {
            'grader_payload': json.dumps(grader_payload),
            'student_info': test_util.get_student_info('test_student'),
            'student_response': text,
            'max_score': 1,
            }
        content = {
            'xqueue_header': test_util.get_xqueue_header(),
            'xqueue_body': json.dumps(xqueue_body),
            }

        self.c.post(
            SUBMIT_URL,
            content,
            )

        sub = Submission.objects.filter(location=self.location).order_by("-date_created")[0]
        return sub

    def model_creation_and_grading(self):
        random.seed(1)
        self.create_models(self.rubric_xml, self.scores, self.text)
        model_creator = ModelCreator(self.location)
        model_creator.create_model()
        assert CreatedModel.objects.filter(location=self.location).order_by("-date_created")[0].creation_succeeded==True

        sub = self.add_ungraded_sub(self.rubric_xml, self.text[0])
        grader = Grader(self.c)
        grader.grade()
        assert sub.grader_set.count()>1

    def model_creation(self):
        self.create_models(self.rubric_xml, self.scores, self.text)
        random.seed(1)
        model_creator = ModelCreator(self.location)
        model_creator.create_model()
        assert CreatedModel.objects.filter(location=self.location).order_by("-date_created")[0].creation_succeeded==True

class PolarityTest(unittest.TestCase,GenericTest):
    loader = PolarityLoader
    data_path = "data/polarity"

    #These will increase if we allow more data in.
    #I am setting the amount of data low to allow tests to finish quickly (40 training essays, 1000 character max for each)
    expected_kappa_min = -.2
    expected_mae_max = 1

    def setUp(self):
        rubric_xml, scores, text = self.load_data()
        self.generic_setup(rubric_xml, scores, text)

    def test_model_creation_and_grading(self):
        self.model_creation_and_grading()

    def test_model_creation(self):
        self.model_creation()
