from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

import requests
import urlparse
import time
import json
import logging
import sys
from ConfigParser import SafeConfigParser
from datetime import datetime

from controller.models import Submission,Grader

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

        location = parser.get('ImportData', 'location')
        course_id = parser.get('ImportData', 'course_id')
        problem_id = parser.get('ImportData', 'problem_id')
        prompt = parser.get('ImportData', 'prompt')
        essay_file = parser.get('ImportData', 'essay_file')
        essay_limit = parser.get('ImportData', 'essay_limit')

        score,text=[],[]
        combined_raw=open(essay_file).read()
        raw_lines=combined_raw.splitlines()
        for row in xrange(1,len(raw_lines)):
            score1,text1 = raw_lines[row].strip().split("\t")
            text.append(text1)
            score.append(int(score1))

        for i in range(0,min(essay_limit,len(text))):
            sub=Submission(
                prompt=prompt,
                student_id="",
                problem_id=problem_id,
                state="W",
                student_response=text[i],
                student_submission_time= datetime.now(),
                xqueue_submission_id= "",
                xqueue_submission_key= "",
                xqueue_queue_name= "",
                location=location,
                course_id=course_id,
            )

            sub.save()

            grade=Grader(
                score=score[i],
                feedback = "",
                status_code = "S",
                grader_id= "",
                grader_type= "IN",
                confidence= 1,
            )

            grade.submission=sub
            grade.save()

        print ("Successfully imported {0} essays using configuration in file {!}.".format(
            min(essay_limit,len(text)),
            args[0],
        ))