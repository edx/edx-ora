from django.core.management.base import BaseCommand
from optparse import make_option
from controller.models import Submission, GraderStatus


class Command(BaseCommand):

    help = "Usage: manually_fail_submission <submission_id>\n"

    option_list = BaseCommand.option_list + (
        make_option(
            '-n',
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help="Doing everything else failing."
        ),
    )

    def handle(self, *args, **options):
        """
        Manually fail submission to not appear in calibration essays.
        """

        dry_run = options['dry_run']
        if len(args) == 1:
            submission_id = args[0]
        else:
            print self.help
            return

        try:
            manually_fail_submission(submission_id, dry_run)
        except Exception as ex:
            print "Error: {0}".format(ex.message)


def manually_fail_submission(submission_id, dry_run=True):
    """
    Manually fail submission to not appear in calibration essays.
    """

    try:
        submission = Submission.objects.get(id=submission_id)
    except:
        print "{0} Submission not found.".format(submission_id)
        return

    if dry_run:
        print "Failing submission skipped."
    else:
        graders = submission.grader_set.all()
        graders.update(status_code=GraderStatus.failure)

        print "{0} Submission status is failed now.".format(submission_id)
