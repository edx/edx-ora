# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'CalibrationRecord.rubric_scores'
        db.add_column('peer_grading_calibrationrecord', 'rubric_scores',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'CalibrationRecord.rubric_scores_complete'
        db.add_column('peer_grading_calibrationrecord', 'rubric_scores_complete',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'CalibrationRecord.rubric_scores'
        db.delete_column('peer_grading_calibrationrecord', 'rubric_scores')

        # Deleting field 'CalibrationRecord.rubric_scores_complete'
        db.delete_column('peer_grading_calibrationrecord', 'rubric_scores_complete')


    models = {
        'controller.submission': {
            'Meta': {'object_name': 'Submission'},
            'answer': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'duplicate_submission_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'grader_settings': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initial_display': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'is_duplicate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_plagiarized': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'next_grader_type': ('django.db.models.fields.CharField', [], {'default': "'NA'", 'max_length': '2'}),
            'posted_results_back_to_queue': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'preferred_grader_type': ('django.db.models.fields.CharField', [], {'default': "'NA'", 'max_length': '2'}),
            'previous_grader_type': ('django.db.models.fields.CharField', [], {'default': "'NA'", 'max_length': '2'}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'rubric': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'student_response': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'student_submission_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'xqueue_queue_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024'}),
            'xqueue_submission_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024'}),
            'xqueue_submission_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024'})
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
            'calibration_history': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['peer_grading.CalibrationHistory']"}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_pre_calibration': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rubric_scores': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'rubric_scores_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['controller.Submission']"})
        }
    }

    complete_apps = ['peer_grading']