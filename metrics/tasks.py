from controller.models import Submission, SubmissionState, Message
from django.http import HttpResponse
import re
import csv
from .models import StudentCourseProfile, FIELDS_TO_EVALUATE
import numpy
from django.forms.models import model_to_dict
from celery.task import periodic_task, task
import StringIO
import json
import logging
from django.db import transaction
from django.conf import settings
import os
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from datetime import timedelta
from controller.single_instance_task import single_instance_task
from tempfile import TemporaryFile

log = logging.getLogger(__name__)


def get_course_data_filename(course):
    """
    Return the name of the file used to store course data.
    """
    return re.sub("[/:]", "_", course) + "_student_information.csv"

def sub_commas(text):
    fixed_text=re.sub(","," ",text)
    return fixed_text

def encode_ascii(text):
    return text.encode('ascii', 'ignore')

def set_up_data_dump(locations,name):
    fixed_name=re.sub("[/:]","_",name)

    if isinstance(locations, basestring):
        locations=[locations]

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{0}.csv"'.format(fixed_name)
    string_write = StringIO.StringIO()
    writer = csv.writer(string_write)

    return writer, locations, string_write

def join_if_list(text):
    if isinstance(text,list):
        text=" ".join(text)
    return text

@task()
def get_message_in_csv_format(locations, name):
    writer, locations, response = set_up_data_dump(locations, name)
    headers = ["Message Text", "Score", "Location"]
    values = []

    for z in xrange(0,len(locations)):
        location=locations[z]
        fixed_location=re.sub("[/:]","_",location)

        messages=Message.objects.filter(grader__submission__location=location)
        message_score=[message.score for message in messages]
        message_text=[sub_commas(encode_ascii(message.message)) for message in messages]

        for i in xrange(0,len(message_score)):
            values.append([message_text[i], message_score[i], location])

    return write_to_json(headers,values)

def write_to_json(headers, values):
    json_data = []
    for val in values:
        loop_dict = {}
        for i in xrange(0,len(headers)):
            try:
                loop_dict.update({headers[i] : val[i]})
            except IndexError:
                continue
        json_data.append(loop_dict)
    return json.dumps(json_data)

@task()
def get_data_in_csv_format(locations, name):
    writer, locations, response = set_up_data_dump(locations, name)
    values = []

    for z in xrange(0,len(locations)):
        location=locations[z]
        fixed_location=re.sub("[/:]","_",location)

        subs=Submission.objects.filter(location=location,state=SubmissionState.finished)
        grader_info=[sub.get_all_successful_scores_and_feedback() for sub in subs]
        bad_list = []
        additional_list = []
        additional_text = []
        submission_text=[sub_commas(encode_ascii(sub.student_response)) for sub in subs]

        for i in xrange(0,len(grader_info)):
            if isinstance(grader_info[i]['score'], list):
                bad_list.append(i)
                for j in xrange(0,len(grader_info[i]['score'])):
                    new_grader_info = {}
                    for key in grader_info[i]:
                        if isinstance(grader_info[i][key], list):
                            new_grader_info.update({key : grader_info[i][key][j]})
                        else:
                            new_grader_info.update({key : grader_info[i][key]})
                    additional_list.append(new_grader_info)
                    additional_text.append(submission_text[i])

        grader_info = [grader_info[i] for i in xrange(0,len(grader_info)) if i not in bad_list]
        grader_info += additional_list

        submission_text = [submission_text[i] for i in xrange(0,len(submission_text)) if i not in bad_list]
        submission_text += additional_text

        grader_type=[grade['grader_type'] for grade in grader_info]
        score=[numpy.median(grade['score']) for grade in grader_info]
        feedback=[sub_commas(encode_ascii(grade['feedback'])) for grade in grader_info]
        success=[grade['success'] for grade in grader_info]

        student_ids = [grade['student_id'] for grade in grader_info]

        for i in xrange(0,len(grader_info)):
            value_dict = {
                'student_id': student_ids[i],
                'score': score[i],
                'grader_type': grader_type[i],
                'success': success[i],
                'submission_text': submission_text[i],
                'location': location,
                'feedback': feedback[i]
            }
            for m in xrange(0,len(grader_info[i]['rubric_scores'])):
                value_dict.update({"rubric_{0}".format(grader_info[i]['rubric_headers'][m]) : grader_info[i]['rubric_scores'][m]})
            values.append(value_dict)
    return json.dumps(values)

@task()
def get_student_data_in_csv_format(locations, name):
    writer, locations, response = set_up_data_dump(locations, name)
    headers = FIELDS_TO_EVALUATE
    values = []

    for z in xrange(0,len(locations)):
        location=locations[z]
        fixed_location=re.sub("[/:]","_",location)

        student_course_profiles=StudentCourseProfile.objects.filter(course_id=location)
        student_course_profiles_count = student_course_profiles.count()

        for i in xrange(0,student_course_profiles_count):
            field_values = []
            all_zeros = True
            scp_dict = model_to_dict(student_course_profiles[i])
            for m in xrange(0,len(FIELDS_TO_EVALUATE)):
                scp_val = scp_dict.get(FIELDS_TO_EVALUATE[m], 0)
                field_values.append(scp_val)
                if scp_val!=0:
                    all_zeros = False
            if not all_zeros:
                values.append(field_values)

    return write_to_json(headers,values)


@periodic_task(run_every=timedelta(seconds=settings.GENERATE_COURSE_DATA_EVERY))
def regenerate_course_data():
    """
    Periodically regenerate course data dumps.  Course data dumps contain
    information on student submissions and grades.
    """
    # Loop through all courses and fire a delayed event to get course data.
    courses = [c['course_id'] for c in Submission.objects.values('course_id').distinct()]
    for course in courses:
        regenerate_course_data_in_csv_format.delay(course=course)

@task()
def regenerate_course_data_in_csv_format(course):
    """
    Get all data the ORA has for a course in CSV format, and upload it to S3.
    course - A course id string.
    """
    # Set up an output for our csv file.
    tempfile_write = TemporaryFile()

    # Get all locations in the course.
    locations = [l['location'] for l in Submission.objects.filter(course_id=course).values('location').distinct()]

    # Set up our csv writer.
    csv.register_dialect('ora', delimiter=',', quoting=csv.QUOTE_MINIMAL, doublequote=True)

    keys = None

    # Loop through all of the locations in the course to generate data.
    for (i, location) in enumerate(locations):
        subs = Submission.objects.filter(location=location)

        for sub in subs:
            values = []

            # Get all the scores and feedback for each submission.
            grader_info = sub.get_all_successful_scores_and_feedback()
            submission_text = sub_commas(encode_ascii(sub.student_response))

            # Some submissions have multiple graders, in which case score is a list.
            # Handle these cases by breaking them down into separate rows.
            if isinstance(grader_info['score'], list):
                for j in xrange(0, len(grader_info['score'])):
                    new_grader_info = {'submission_text': submission_text}
                    # Any key that is a list should be broken down, any other key should
                    # be passed into the row like normal.
                    for key in grader_info:
                        if isinstance(grader_info[key], list):
                            new_grader_info.update({key: grader_info[key][j]})
                        else:
                            new_grader_info.update({key: grader_info[key]})
                    values.append(new_grader_info)
            else:
                grader_info['submission_text'] = submission_text
                values.append(grader_info)

            for val in values:
                val['feedback'] = sub_commas(encode_ascii(val['feedback']))

            # Set up the header keys, csv writer, and header row.
            if keys is None:
                keys = [k for k in values[0]]
                writer = csv.DictWriter(tempfile_write, keys, dialect='ora')
                writer.writeheader()

            # Write the rows to csv.
            for v in values:
                writer.writerow(v)

    # Go back to the beginning of the string.
    tempfile_write.seek(0)
    filename = get_course_data_filename(course)

    # If we have an S3 account setup, upload, otherwise write to a local file.
    if settings.AWS_ACCESS_KEY_ID != "":
        # Upload the csv file to S3 and close the StringIO object.
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        bucket = conn.create_bucket(settings.S3_BUCKETNAME.lower())
        k = Key(bucket)
        k.key = filename
        k.set_contents_from_file(tempfile_write)
        tempfile_write.close()
    else:
        with open(os.path.abspath(os.path.join(settings.COURSE_DATA_PATH, filename)), "w") as f:
            f.write(tempfile_write.read())
