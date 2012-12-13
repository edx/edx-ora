from lxml import etree
from models import Rubric, RubricItem

RUBRIC_VERSION=1

sample_rubric="""
<table>
<tr><td>Rubric item 1</td><td>0</td><td>2</td></tr>
<tr><td>Rubric item 2</td><td>0</td><td>2</td></tr>
</table>
"""

def generate_rubric_object(submission):
    rubric=Rubric(
        submission= submission,
        rubric_version=RUBRIC_VERSION,
    )
    try:
        parsed_rubric=etree.fromstring(submission.rubric)
    except:
        log.exception("Could not parse rubric properly.")
        return False, rubric

    try:
        rubric.save()
        rubric_items=[c for c in parsed_rubric]
        rubric_item_set=[]

        for i in xrange(0,len(rubric_items)):
            rubric_row=[c.text for c in rubric_items[i]]
            text=rubric_row[0]
            score=rubric_row[1]
            max_score=rubric_row[2]
            rubric_item=RubricItem(
                rubric=rubric,
                text=text,
                score=score,
                item_number=i,
                max_score=max_score,
                finished_scoring=False,
            )
            rubric_item.save()
    except:
        log.exception("Could not save and/or parse rubric properly")
        return False, rubric

    return True, rubric





