"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import unittest
import csv
import test_util
from metrics.tasks import regenerate_course_data_in_csv_format, get_course_data_filename
import os
from django.conf import settings
import logging
log = logging.getLogger(__name__)

COURSE = "test"
LOCATION = "test/test"
STUDENT_ID = "1"

class TestCourseDataGeneration(unittest.TestCase):
    """
    Test course data generation.
    """

    def setUp(self):
        test_util.create_user()

    def tearDown(self):
        test_util.delete_all()

    def get_course_data_file(self, course):
        """
        Given a course, generate a data file and return the filename.
        course - A string course name.
        returns - A string filename.
        """
        regenerate_course_data_in_csv_format(course)
        filename = get_course_data_filename(course)

        data_filename = os.path.abspath(os.path.join(settings.COURSE_DATA_PATH, filename))
        return data_filename

    def test_generate_course_data_empty(self):
        """
        Test to ensure that generating data for an empty course results in an empty file.
        """
        data_filename = self.get_course_data_file(COURSE)

        # There should not be any data in the file.
        with open(data_filename, 'rb') as data_file:
            data = data_file.read()
            self.assertEqual(len(data), 0)

    def test_course_data_real(self):
        """
        Test to ensure that generating data for a course results in proper csv output.
        """

        submission_count = 100

        # Generate our submissions and grade them.
        for i in xrange(0, submission_count):
            sub = test_util.get_sub("IN", STUDENT_ID, LOCATION, course_id=COURSE)
            sub.save()

            grade = test_util.get_grader("IN")
            grade.submission = sub
            grade.save()

        # Generate the data file and get the filename.
        data_filename = self.get_course_data_file(COURSE)

        with open(data_filename, 'rb') as data_file:
            # Ensure that we have data.
            data = data_file.read()
            self.assertGreater(len(data), 0)

            data_file.seek(0)
            reader = csv.reader(data_file, delimiter=',', doublequote=True, quoting=csv.QUOTE_MINIMAL)
            rows = []
            for row in reader:
                rows.append(row)

            # The number of rows should equal the number of submissions plus one for the header row.
            self.assertEqual(len(rows), submission_count + 1)
