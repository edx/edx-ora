from django.core.management.base import BaseCommand
from controller.models import Submission, SubmissionState
from optparse import make_option
import logging

log = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Usage: force_pass_basic_check <course_id> --dry-run \n" \
           "       Passes basic check for all problems in course."

    option_list = BaseCommand.option_list + (
        make_option('-n', '--dry-run',
                    action='store_true', dest='dry_run', default=False,
                    help="Do everything except updating failed basic "
                         "check submissions."),
    )

    def handle(self, *args, **options):

        dry_run = options['dry_run']
        print "args = ", args

        if len(args) == 1:
            course_id = args[0]
        else:
            print self.help
            return
        try:
            reset_failed_basic_check_submissions(course_id, dry_run=dry_run)
        except Exception as ex:
            print "ERROR: {0}".format(ex.message)


def reset_failed_basic_check_submissions(course_id, dry_run=True):
    """
    Update affected submissions.
    """

    submissions = Submission.objects.filter(
        course_id=course_id,
        state=SubmissionState.finished,
        previous_grader_type=u'BC',
        next_grader_type=u'BC',
        posted_results_back_to_queue=True,
    )

    sub_count = submissions.count()
    print "Found Submissions: {0}".format(sub_count)

    if dry_run:
        print "Skipped updating failed basic check submissions."
    else:
        submissions.update(
            state=SubmissionState.waiting_to_be_graded,
            posted_results_back_to_queue=False,
            skip_basic_checks=True
        )

        print "Updated Submissions: {0}".format(sub_count)
