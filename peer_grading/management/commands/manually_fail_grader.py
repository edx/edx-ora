from django.core.management.base import BaseCommand
from optparse import make_option
from controller.models import Grader, GraderStatus


class Command(BaseCommand):

    help = "Usage: manually_fail_grader <grader_id>\n"

    option_list = BaseCommand.option_list + (
        make_option(
            '-n',
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help="Do everything except update of status to GraderStatus.failure."
        ),
    )

    def handle(self, *args, **options):
        """
        Change status of grader to GraderStatus.failure graded by instructor.
        This will make the submission not appear to students as a calibration essay.
        """

        dry_run = options['dry_run']
        if len(args) == 1:
            submission_id = args[0]
        else:
            print self.help
            return

        try:
            update_grader_to_manually_fail(submission_id, dry_run)
        except Exception as ex:
            print "Error: {0}".format(ex)


def update_grader_to_manually_fail(grader_id, dry_run=True):
    """
    Change status of grader to GraderStatus.failure graded by instructor.
    This will make the submission not appear to students as a calibration essay.
    """

    try:
        grader = Grader.objects.get(id=grader_id)
    except Grader.DoesNotExist:
        print "Grader {0} not found.".format(grader_id)
        return

    if dry_run:
        print "Skipping changing status for grader <{0}> <{1}>".format(
            grader.id,
            grader.grader_type
        )
    else:
        grader.status_code = GraderStatus.failure
        grader.save()

        print "Grader <{0}> <{1}> status has been set to GraderStatus.failure.".format(
            grader.id,
            grader.grader_type
        )
