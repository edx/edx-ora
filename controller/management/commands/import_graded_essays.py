from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction
transaction.commit_unless_managed()

import requests
import urlparse
import time
import json
import logging
import sys
from ConfigParser import SafeConfigParser
from datetime import datetime

from controller.models import Submission, Grader
from controller.models import GraderStatus, SubmissionState

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "<filename>"
    help = "Poll grading controller and send items to be graded to ml"


    def handle(self, *args, **options):
        """
        Read from file
        """

        parser = SafeConfigParser()
        parser.read(args[0])

        print("Starting import...")
        print("Reading config from file {0}".format(args[0]))

        header_name = "importdata"
        location = parser.get(header_name, 'location')
        course_id = parser.get(header_name, 'course_id')
        problem_id = parser.get(header_name, 'problem_id')
        prompt = parser.get(header_name, 'prompt')
        essay_file = parser.get(header_name, 'essay_file')
        essay_limit = int(parser.get(header_name, 'essay_limit'))
        state = parser.get(header_name, "state")
        next_grader_type = parser.get(header_name, "next_grader")
        add_grader = parser.get(header_name, "add_grader_object") == "True"
        set_as_calibration = parser.get(header_name, "set_as_calibration") == "True"
        max_score= parser.get(header_name,"max_score")
        student_id = parser.get(header_name,student_id)

        score, text = [], []
        combined_raw = open(settings.REPO_PATH / essay_file).read()
        raw_lines = combined_raw.splitlines()
        for row in xrange(1, len(raw_lines)):
            score1, text1 = raw_lines[row].strip().split("\t")
            text.append(text1)
            score.append(int(score1))

        for i in range(0, min(essay_limit, len(text))):
            sub = Submission(
                prompt=prompt,
                student_id=student_id,
                problem_id=problem_id,
                state=state,
                student_response=text[i],
                student_submission_time=timezone.now(),
                xqueue_submission_id="",
                xqueue_submission_key="",
                xqueue_queue_name="",
                location=location,
                course_id=course_id,
                next_grader_type=next_grader_type,
                posted_results_back_to_queue=True,
                sub.previous_grader_type="BC",
                max_score=max_score,
            )

            sub.save()
            if add_grader:
                sub.previous_grader_type="IN"
                sub.save()
                grade = Grader(
                    score=score[i],
                    feedback="",
                    status_code=GraderStatus.success,
                    grader_id="",
                    grader_type="IN",
                    confidence=1,
                    is_calibration=set_as_calibration,
                )

                grade.submission = sub
                grade.save()

        print ("Successfully imported {0} essays using configuration in file {1}.".format(
            min(essay_limit, len(text)),
            args[0],
        ))
