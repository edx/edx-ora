# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Timing'
        db.create_table('metrics_timing', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start_time', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True)),
            ('end_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('finished_timing', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('student_id', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('problem_id', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('max_score', self.gf('django.db.models.fields.IntegerField')()),
            ('submission_id', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('grader_type', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('confidence', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=9)),
            ('is_calibration', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('grader_version', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('grader_id', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('metrics', ['Timing'])


    def backwards(self, orm):
        # Deleting model 'Timing'
        db.delete_table('metrics_timing')


    models = {
        'metrics.timing': {
            'Meta': {'object_name': 'Timing'},
            'confidence': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '9'}),
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {}),
            'finished_timing': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'grader_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'grader_version': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_calibration': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'start_time': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'submission_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['metrics']