from django.core.management.base import BaseCommand
from controller.models import Submission, SubmissionState, GraderStatus
from optparse import make_option
import logging

log = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Usage: divert_specific_location_subs_to_instructor_grading <course_id> <location> --dry-run \n" \
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

        if len(args) == 2:
            course_id = args[0]
            location = args[1]
        else:
            print self.help
            return
        try:
            reset_and_divert_submissions_for_location(course_id,
                                                      location,
                                                      dry_run=dry_run)
        except Exception as ex:
            print "ERROR: {0}".format(ex.message)


def reset_and_divert_submissions_for_location(course_id, location, dry_run=True):
    """
    Update submissions for given location and course_id.
    """

    submissions = Submission.objects.filter(
        location=location,
        course_id=course_id,
        state=SubmissionState.waiting_to_be_graded,
        next_grader_type="PE",
        is_duplicate=False,
        grader__status_code=GraderStatus.success,
        grader__grader_type__in=["PE", "BC"],
    )

    sub_count = submissions.count()
    print "Found Submissions: {0}".format(sub_count)

    if dry_run:
        print "Skipped updating failed basic check submissions."
    else:
        submissions.update(next_grader_type="IN")

        print "Updated Submissions: {0}".format(sub_count)
