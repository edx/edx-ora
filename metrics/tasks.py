from controller.models import Submission, SubmissionState, Message
from django.http import HttpResponse
import re
import csv
from metrics.models import StudentCourseProfile, FIELDS_TO_EVALUATE
import numpy
from django.forms.models import model_to_dict
from celery import task

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
    writer = csv.writer(response)

    return writer, locations, response

def join_if_list(text):
    if isinstance(text,list):
        text=" ".join(text)
    return text

@task
def get_message_in_csv_format(locations, name):
    writer, locations, response = set_up_data_dump(locations, name)

    for z in xrange(0,len(locations)):
        location=locations[z]
        fixed_location=re.sub("[/:]","_",location)

        messages=Message.objects.filter(grader__submission__location=location)
        message_score=[message.score for message in messages]
        message_text=[sub_commas(encode_ascii(message.message)) for message in messages]

        if z==0:
            writer.writerow(["Message Text", "Score", "Location"])
        for i in xrange(0,len(message_score)):
            writer.writerow([message_text[i], message_score[i], location])

    return True, response

@task
def get_data_in_csv_format(locations, name):
    writer, locations, response = set_up_data_dump(locations, name)

    for z in xrange(0,len(locations)):
        location=locations[z]
        fixed_location=re.sub("[/:]","_",location)

        subs=Submission.objects.filter(location=location,state=SubmissionState.finished)
        grader_info=[sub.get_all_successful_scores_and_feedback() for sub in subs]
        grader_type=[grade['grader_type'] for grade in grader_info]
        score=[numpy.median(grade['score']) for grade in grader_info]
        feedback=[sub_commas(encode_ascii(join_if_list(grade['feedback']))) for grade in grader_info]
        success=[grade['success'] for grade in grader_info]
        submission_text=[sub_commas(encode_ascii(sub.student_response)) for sub in subs]
        max_score=[sub.max_score for sub in subs]

        if z==0:
            writer.writerow(["Score", "Max Score","Grader Type", "Success", "Submission Text", "Location"])
        for i in xrange(0,len(grader_info)):
            writer.writerow([score[i], max_score[i], grader_type[i], success[i], submission_text[i], location])

    return True, response

@task
def get_student_data_in_csv_format(locations, name):
    writer, locations, response = set_up_data_dump(locations, name)

    for z in xrange(0,len(locations)):
        location=locations[z]
        fixed_location=re.sub("[/:]","_",location)

        student_course_profiles=StudentCourseProfile.objects.filter(course_id=location)
        student_course_profiles_count = student_course_profiles.count()

        if z==0:
            writer.writerow(FIELDS_TO_EVALUATE)
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
                writer.writerow(field_values)

    return True, response