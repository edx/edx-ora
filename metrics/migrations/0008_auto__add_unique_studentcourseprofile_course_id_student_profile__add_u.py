# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'StudentCourseProfile', fields ['course_id', 'student_profile']
        db.create_unique('metrics_studentcourseprofile', ['course_id', 'student_profile_id'])

        # Adding unique constraint on 'StudentProfile', fields ['student_id']
        db.create_unique('metrics_studentprofile', ['student_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'StudentProfile', fields ['student_id']
        db.delete_unique('metrics_studentprofile', ['student_id'])

        # Removing unique constraint on 'StudentCourseProfile', fields ['course_id', 'student_profile']
        db.delete_unique('metrics_studentcourseprofile', ['course_id', 'student_profile_id'])


    models = {
        'metrics.studentcourseprofile': {
            'Meta': {'unique_together': "(('student_profile', 'course_id'),)", 'object_name': 'StudentCourseProfile'},
            'attempts_per_problem': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'attempts_per_problem_ml': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'attempts_per_problem_peer': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_length_of_peer_feedback_given': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_ml_confidence': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_peer_grading_score_given': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score_last10': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score_last20': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score_ml': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score_peer': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_submission_length': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'completed_peer_grading': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'course_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'graders_per_attempt': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problems_attempted': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'problems_attempted_ml': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'problems_attempted_peer': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'stdev_length_of_peer_feedback_given': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'stdev_percent_score': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'stdev_submission_length': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'student_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128', 'db_index': 'True'}),
            'student_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['metrics.StudentProfile']"})
        },
        'metrics.studentprofile': {
            'Meta': {'object_name': 'StudentProfile'},
            'average_message_feedback_length': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'messages_received': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'messages_sent': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'student_cannot_submit_more_for_peer_grading': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'student_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128', 'db_index': 'True'}),
            'student_is_staff_banned': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'metrics.timing': {
            'Meta': {'object_name': 'Timing'},
            'confidence': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '9', 'blank': 'True'}),
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'finished_timing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'grader_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'grader_version': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_calibration': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'submission_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['metrics']