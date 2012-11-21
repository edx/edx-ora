# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CalibrationHistory'
        db.create_table('peer_grading_calibrationhistory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('problem_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('peer_grading', ['CalibrationHistory'])

        # Adding model 'CalibrationRecord'
        db.create_table('peer_grading_calibrationrecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('calibration_history', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['peer_grading.CalibrationHistory'])),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('actual_score', self.gf('django.db.models.fields.IntegerField')()),
            ('is_pre_calibration', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('peer_grading', ['CalibrationRecord'])


    def backwards(self, orm):
        # Deleting model 'CalibrationHistory'
        db.delete_table('peer_grading_calibrationhistory')

        # Deleting model 'CalibrationRecord'
        db.delete_table('peer_grading_calibrationrecord')


    models = {
        'peer_grading.calibrationhistory': {
            'Meta': {'object_name': 'CalibrationHistory'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'peer_grading.calibrationrecord': {
            'Meta': {'object_name': 'CalibrationRecord'},
            'actual_score': ('django.db.models.fields.IntegerField', [], {}),
            'calibration_history': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['peer_grading.CalibrationHistory']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_pre_calibration': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'score': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['peer_grading']