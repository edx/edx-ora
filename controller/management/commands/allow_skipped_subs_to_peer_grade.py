from django.core.management.base import BaseCommand
from optparse import make_option
from controller.models import Submission


class Command(BaseCommand):

    help = "Usage: allow_skipped_subs_to_peer_grade <course_id>\n"

    option_list = BaseCommand.option_list + (
        make_option(
            '-n',
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help="Doing everything else updating."
        ),
    )

    def handle(self, *args, **options):
        """
        Update submissions skipped by instructor to allow peer grading.
        """

        dry_run = options['dry_run']
        if len(args) == 1:
            course_id = args[0]
        else:
            print self.help
            return

        try:
            update_subs_skipped_by_instructor(course_id, dry_run)
        except Exception as ex:
            print "Error: {0}".format(ex.message)


def update_subs_skipped_by_instructor(course_id, dry_run=True):
    """
    Update submissions skipped by instructor to allow peer grading.
    """

    submissions = Submission.objects.filter(
        course_id=course_id,
        preferred_grader_type="PE",
        next_grader_type="ML"
    )

    sub_count = submissions.count()
    print "Found Submissions: {0}".format(sub_count)

    if dry_run:
        print "Updating submissions skipped."
    else:
        submissions.update(next_grader_type="PE")

        print "Updated Submissions: {0}".format(sub_count)
