#To check how many students do not have a Submission row.
import csv
import json
from django.core.management.base import BaseCommand
from controller.models import Submission


class Command(BaseCommand):
    """Admin command for students do not have a Submission row."""

    help = "Usage: submission_stats <path_to_json> <location> \n"

    missing_student_ids = []

    def handle(self, *args, **options):

        if len(args) != 2:
            print self.help

        path_to_json, location = args

        assessing_student_ids, post_assessment_student_ids = self.create_dict_from_json(path_to_json)

        print "----------Stats for Assessing----------"
        self.get_student_stats(assessing_student_ids, location)

        print "\n----------Stats for Post Assessment----------"
        self.get_student_stats(post_assessment_student_ids, location)

        self.create_csv_from_list(self.missing_student_ids)

    def get_student_stats(self, student_ids, location):
        """Generate student stats."""

        submissions = Submission.objects.filter(student_id__in=student_ids, location=location)
        sub_stats = []
        print "Total Students: {0}".format(len(student_ids))
        print "Total Submissions For These Students: {0}".format(submissions.count())
        for submission in submissions:
            graders = submission.get_all_graders()
            sub_stats.append({"submission_id": submission.id,
                              "state": submission.state,
                              "grader_count": graders.count(),
                              "status": [grader.status_code for grader in graders]
            })
            if submission.student_id in student_ids:
                student_ids.remove(submission.student_id)

        for num in range(max([stat.get("grader_count", 0) for stat in sub_stats])+1):
            count = 0
            for stat in sub_stats:
                if stat.get("grader_count", 0) == num:
                    count += 1

            print "Submissions with {0} graders: {1}".format(num, count)

        self.missing_student_ids.extend(student_ids)
        print "Student not have rows in submission: {0}".format(len(student_ids))

    def create_dict_from_json(self, path_to_json):
        """Read a json and return items lists."""

        json_file = open(path_to_json)
        json_file_loaded = json.loads(json_file.read())
        assessing_student_ids = self.create_list(json_file_loaded.get("assessing", []))
        post_assessment_student_ids = self.create_list(json_file_loaded.get("post_assessment", []))

        return assessing_student_ids, post_assessment_student_ids

    def create_list(self, stats):
        """Creates a list of anonymous ids"""

        items_list = []
        for stat in stats:
            items_list.append(stat["anonymous_id"])

        return items_list

    def create_csv_from_list(self, student_ids):
        """Create csv of student anonymous ids"""

        csv_file = open("missing_student_ids_in_ora.csv", "wb")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerows([[sid] for sid in student_ids])
        csv_file.close()