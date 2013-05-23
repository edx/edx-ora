from django.core.management.base import BaseCommand

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction
transaction.commit_unless_managed()

import logging

from controller.models import Submission, SubmissionState

from controller.xqueue_interface import handle_submission
import random

log = logging.getLogger(__name__)

COUNT_MIN=1
COUNT_MAX=100
COPIED_STUDENT_ID = "copied_student"

GRADER_SETTINGS = {
    'ML' : "ml_grading.conf",
    'PE' : 'peer_grading.conf',
    'IN' : 'instructor_grading.conf'
}

class Command(BaseCommand):
    args = "<number> <location>"
    help = "Copy {count} student submissions.  Creates more submissions in the peer grading pool"

    def handle(self, *args, **options):
        """
        Read from file
        """
        if len(args)!=2:
            raise Exception("Not enough input arguments!")
        number, location= args

        number = int(number)

        valid_location_dicts = Submission.objects.all().values('location').distinct()
        valid_locations = [vld['location'] for vld in valid_location_dicts]

        if location not in valid_locations:
            raise Exception("Cannot find location in the available locations.  Available locations are: {0}".format(valid_locations))

        if number < COUNT_MIN or number> COUNT_MAX:
            raise Exception("Input number is too large or too small.  Must be over {0} and under {1}.".format(COUNT_MIN, COUNT_MAX))

        sub_count = Submission.objects.filter(location=location).count()

        if number >= sub_count:
            raise Exception("You specified too high a number of copies.  Only {0} submissions exist for location {1}.".format(sub_count, location))

        slice_start = random.randint(0, sub_count - number -1)

        subs = Submission.objects.filter(location=location)[slice_start:(slice_start+number)]

        last_sub = Submission.objects.filter(location=location).order_by('-date_modified')[0]
        preferred_grader_type = last_sub.preferred_grader_type

        log.info("Copying {0} submissions from location {1}.  Starting from number {2}.".format(number, location, slice_start))
        for sub in subs:
            #Set these to none to copy the submission
            sub.pk = None
            sub.id = None

            #Reset basic information
            sub.student_id = COPIED_STUDENT_ID
            sub.state = SubmissionState.waiting_to_be_graded
            if sub.preferred_grader_type == "NA":
                sub.preferred_grader_type = preferred_grader_type
            if sub.preferred_grader_type == "IN":
                sub.preferred_grader_type = preferred_grader_type
            if sub.grader_settings == "":
                sub.grader_settings = GRADER_SETTINGS[sub.preferred_grader_type]
            sub.previous_grader_type = "NA"
            sub.next_grader_type = "BC"
            sub.xqueue_submission_id = ""
            sub.xqueue_submission_key = ""
            sub.skip_basic_checks = False

            sub.save()
            #Run basic checks on the sub
            handle_submission(sub)

            #Ensure that submission is not marked as a duplicate
            sub.is_duplicate = False
            sub.is_plagiarized = False
            sub.duplicate_submission_id = None
            sub.save()

        log.info("Done copying submissions.")
        transaction.commit_unless_managed()


