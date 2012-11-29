# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Timing.confidence'
        db.alter_column('metrics_timing', 'confidence', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=9))

        # Changing field 'Timing.status_code'
        db.alter_column('metrics_timing', 'status_code', self.gf('django.db.models.fields.CharField')(max_length=1, null=True))

        # Changing field 'Timing.score'
        db.alter_column('metrics_timing', 'score', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'Timing.grader_type'
        db.alter_column('metrics_timing', 'grader_type', self.gf('django.db.models.fields.CharField')(max_length=2, null=True))

        # Changing field 'Timing.grader_version'
        db.alter_column('metrics_timing', 'grader_version', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True))

        # Changing field 'Timing.end_time'
        db.alter_column('metrics_timing', 'end_time', self.gf('django.db.models.fields.DateTimeField')(null=True))

    def backwards(self, orm):

        # Changing field 'Timing.confidence'
        db.alter_column('metrics_timing', 'confidence', self.gf('django.db.models.fields.DecimalField')(default=1, max_digits=10, decimal_places=9))

        # Changing field 'Timing.status_code'
        db.alter_column('metrics_timing', 'status_code', self.gf('django.db.models.fields.CharField')(default='S', max_length=1))

        # Changing field 'Timing.score'
        db.alter_column('metrics_timing', 'score', self.gf('django.db.models.fields.IntegerField')(default=1))

        # Changing field 'Timing.grader_type'
        db.alter_column('metrics_timing', 'grader_type', self.gf('django.db.models.fields.CharField')(default='ML', max_length=2))

        # Changing field 'Timing.grader_version'
        db.alter_column('metrics_timing', 'grader_version', self.gf('django.db.models.fields.CharField')(default='1', max_length=1024))

        # Changing field 'Timing.end_time'
        db.alter_column('metrics_timing', 'end_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2012, 11, 28, 0, 0)))

    models = {
        'metrics.timing': {
            'Meta': {'object_name': 'Timing'},
            'confidence': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '9', 'blank': 'True'}),
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'finished_timing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'grader_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'grader_version': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_calibration': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'submission_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['metrics']