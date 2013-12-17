#To check how many students do not have a Submission row.
import csv
from django.core.management.base import BaseCommand
from controller.models import Submission


class Command(BaseCommand):
    """Admin command for students do not have a Submission row."""

    help = "Usage: submission_stats <path_to_csv> <location> \n"

    def handle(self, *args, **options):

        if len(args) != 2:
            print help

        path_to_csv, location = args

        student_ids = self.create_list_from_csv(path_to_csv)
        submissions = Submission.objects.filter(student_id__in=student_ids, location=location)
        for submission in submissions:
            if submission.id in student_ids:
                student_ids.pop(submission.id)

        print "Student not have rows in submission: {0}".format(len(student_ids))
        print "Student ids: {0}".format(student_ids)

    def create_list_from_csv(self, path_to_csv):
        """Read a csv and return items in a list."""

        items = []
        with open(path_to_csv) as csv_file:
            csv_reader = csv.reader(csv_file)
            items = [row[0] for row in csv_reader]

        return items
