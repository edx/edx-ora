# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Timing.student_id'
        db.alter_column('metrics_timing', 'student_id', self.gf('django.db.models.fields.CharField')(max_length=128))

        # Changing field 'Timing.location'
        db.alter_column('metrics_timing', 'location', self.gf('django.db.models.fields.CharField')(max_length=128))

        # Changing field 'Timing.course_id'
        db.alter_column('metrics_timing', 'course_id', self.gf('django.db.models.fields.CharField')(max_length=128))

    def backwards(self, orm):

        # Changing field 'Timing.student_id'
        db.alter_column('metrics_timing', 'student_id', self.gf('django.db.models.fields.CharField')(max_length=1024))

        # Changing field 'Timing.location'
        db.alter_column('metrics_timing', 'location', self.gf('django.db.models.fields.CharField')(max_length=1024))

        # Changing field 'Timing.course_id'
        db.alter_column('metrics_timing', 'course_id', self.gf('django.db.models.fields.CharField')(max_length=1024))

    models = {
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
            'location': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
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