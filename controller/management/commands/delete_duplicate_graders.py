from django.core.management.base import BaseCommand
import logging
from controller.models import Submission, Message
from metrics.models import StudentProfile, StudentCourseProfile
from peer_grading.models import CalibrationHistory
from optparse import make_option
from itertools import chain
from collections import namedtuple
from django.conf import settings
from django.db.models import Count

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ""
    help = "Delete any graders over and above the maximum."
    option_list = BaseCommand.option_list + (
        make_option(
            "--delete",
            action = "store_true",
            help="Delete excess graders."
        ),
    )

    def handle(self, delete, *args, **options):
        """
        Find how many duplicates exist in the tables and optionally delete them.
        """

        # Find submissions with more than the maximum number of graders.
        # This happens due to bad duplication logic.
        high_grader_subs = Submission.objects.annotate(grader_count=Count('grader')).filter(grader_count__gt=settings.MAX_GRADER_COUNT)

        log.info("{0} submissions found with more than {1} graders.".format(high_grader_subs.count(), settings.MAX_GRADER_COUNT))

        # Optionally delete all graders over the limit.
        if delete:
            log.info("Starting to delete excess graders....")
            for sub in high_grader_subs:
                # Basic check was most affected by duplication issues, so ensure that the submission
                # only has one basic check record.
                duplicate_bc = sub.grader_set.filter(grader_type="BC")[1:]
                for grader in duplicate_bc:
                    grader.delete()

                duplicate_graders = sub.grader_set.filter(grader_type__in=["PE", "ML", "IN"])[(settings.MAX_GRADER_COUNT-1):]
                for grader in duplicate_graders:
                    grader.delete()
            log.info("...Delete complete.")

