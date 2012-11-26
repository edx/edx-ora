# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Adding field 'CalibrationRecord.submission'
        db.add_column('peer_grading_calibrationrecord', 'submission',
            self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['controller.Submission']),
            keep_default=False)


    def backwards(self, orm):
        # Deleting field 'CalibrationRecord.submission'
        db.delete_column('peer_grading_calibrationrecord', 'submission_id')


    models = {
        'controller.submission': {
            'Meta': {'object_name': 'Submission'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'grader_settings': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'next_grader_type': ('django.db.models.fields.CharField', [], {'default': "'NA'", 'max_length': '2'}),
            'posted_results_back_to_queue': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'previous_grader_type': ('django.db.models.fields.CharField', [], {'default': "'NA'", 'max_length': '2'}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'rubric': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'student_response': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'student_submission_time': (
            'django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'xqueue_queue_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'xqueue_submission_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'xqueue_submission_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'})
        },
        'peer_grading.calibrationhistory': {
            'Meta': {'object_name': 'CalibrationHistory'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'problem_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'peer_grading.calibrationrecord': {
            'Meta': {'object_name': 'CalibrationRecord'},
            'actual_score': ('django.db.models.fields.IntegerField', [], {}),
            'calibration_history': (
            'django.db.models.fields.related.ForeignKey', [], {'to': "orm['peer_grading.CalibrationHistory']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_pre_calibration': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['controller.Submission']"})
        }
    }

    complete_apps = ['peer_grading']