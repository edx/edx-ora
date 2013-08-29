from lxml import etree
from models import Rubric, RubricItem, RubricOption, GraderStatus
import logging
from itertools import chain

log=logging.getLogger(__name__)

RUBRIC_VERSION=1

sample_rubric="""
<rubric>
    <category>
        <description>Grammar and Spelling</description>
        <option>Many grammatical and spelling errors</option>
        <option>This is also a text option</option>
    </category>
    <category>
        <description>Another topic to grade on</description>
        <option points="0">This is an option</option>
        <option points="1">This is another option</option>
    </category>
</rubric>
"""

class RubricParsingError(Exception):
    pass

class RubricParser(object):
    def __init__(self, rubric_xml):
        self.rubric_xml = rubric_xml

    def parse(self):
        try:
            self.parse_xml()
        except RubricParsingError:
            return ""
        parsed_items=[self.parse_item(pc) for pc in self.categories]
        return parsed_items

    def parse_xml(self):
        try:
            parsed_rubric=etree.fromstring(self.rubric_xml)
        except Exception:
            log.info("Could not parse rubric properly. {0}".format(self.rubric_xml))
            raise RubricParsingError

        try:
            self.categories = self.parse_task('category', parsed_rubric)
        except Exception:
            error_message="Cannot properly parse the category from rubric {0}".format(parsed_rubric)
            log.error(error_message)
            raise RubricParsingError

    def parse_item(self, rubric_item):
        try:
            description=self.stringify_children(self.parse_tag('description', rubric_item))
            options=[self.stringify_children(node) for node in self.parse_task('option', rubric_item)]
        except Exception:
            error_message="Cannot find the proper tags in rubric item {0}".format(rubric_item)
            log.error(error_message)
            raise RubricParsingError

        return {'description' : description, 'options' : options}

    def parse_task(self, k, xml_object):
        """Assumes that xml_object has child k"""
        return [xml_object.xpath(k)[i] for i in xrange(0,len(xml_object.xpath(k)))]

    def parse_tag(self, k, xml_object):
        """Assumes that xml_object has child k"""
        return xml_object.xpath(k)[0]

    def stringify_children(self, node):
        '''
        Return all contents of an xml tree, without the outside tags.
        e.g. if node is parse of
            "<html a="b" foo="bar">Hi <div>there <span>Bruce</span><b>!</b></div><html>"
        should return
            "Hi <div>there <span>Bruce</span><b>!</b></div>"

        fixed from
        http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml
        '''
        # Useful things to know:

        # node.tostring() -- generates xml for the node, including start
        #                 and end tags.  We'll use this for the children.
        # node.text -- the text after the end of a start tag to the start
        #                 of the first child
        # node.tail -- the text after the end this tag to the start of the
        #                 next element.
        parts = [node.text]
        for c in node.getchildren():
            parts.append(etree.tostring(c, with_tail=True, encoding='unicode'))

        # filter removes possible Nones in texts and tails
        return u''.join(filter(None, parts))

    def generate_targets(self):
        try:
            parsed_rubric = self.parse()
        except RubricParsingError:
            return []
        max_scores=[]
        for category in parsed_rubric:
            max_score=len(category['options'])-1
            if max_score<1:
                max_score=1
            max_scores.append(max_score)
        return max_scores

def generate_rubric_object(grader, scores, rubric_xml):
    parser = RubricParser(rubric_xml)
    max_scores= parser.generate_targets()

    for i in xrange(0,len(scores)):
        score=scores[i]
        try:
            score=int(score)
        except ValueError:
            error_message = "Scores must be numeric."
            log.exception(error_message)
            raise RubricParsingError
        if score<0:
            error_message = "Scores cannot be below zero. : {0}".format(score)
            log.error(error_message)
            raise RubricParsingError
        if score>max_scores[i]:
            error_message = "Score: {0} is greater than max score for this item: {1}".format(score, max_scores[i])
            log.error(error_message)
            raise RubricParsingError

    try:
        rubric=Rubric(
            grader=grader,
            rubric_version=RUBRIC_VERSION,
            finished_scoring=True,
        )
        rubric.save()
        parser = RubricParser(rubric_xml)
        rubric_items = parser.parse()

        if len(scores)!=len(rubric_items):
            error_message = "Length of passed in scores: {0} does not match number of rubric items: {1}".format(len(scores), len(rubric_items))
            log.error(error_message)
            raise RubricParsingError

        for i in xrange(0,len(rubric_items)):
            rubric_item=rubric_items[i]
            description = rubric_item['description']
            options = rubric_item['options']

            text=description
            score=scores[i]
            max_score=len(options)

            rubric_item=RubricItem(
                rubric=rubric,
                text=text,
                score=score,
                item_number=i,
                max_score=max_score,
                finished_scoring=True,
            )
            rubric_item.save()
            for z in xrange(0,len(options)):
                option=options[z]
                rubric_option=RubricOption(
                    points=z,
                    text = option,
                    item_number=z,
                    rubric_item=rubric_item,
                )
                rubric_option.save()
        return True, rubric
    except Exception:
        error_message="Could not save and/or parse rubric properly"
        log.error(error_message)
        return False, error_message

def get_submission_rubric_instructor_scores(sub):
    grader_set=sub.grader_set.filter(status_code=GraderStatus.success, grader_type="IN")
    if grader_set.count()>0:
        rubrics=grader_set[0].rubric_set.filter(finished_scoring=True)
        if rubrics.count()>0:
            rubric = rubrics[0]
            rubric_items=rubric.rubricitem_set.all()
            scores=[int(rubric_item.score) for rubric_item in rubric_items]
            return True, scores
    return False, []




