# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CreatedModel'
        db.create_table('ml_grading_createdmodel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('max_score', self.gf('django.db.models.fields.IntegerField')()),
            ('prompt', self.gf('django.db.models.fields.TextField')()),
            ('rubric', self.gf('django.db.models.fields.TextField')()),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('submission_ids_used', self.gf('django.db.models.fields.TextField')()),
            ('problem_id', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('model_relative_path', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('model_full_path', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('number_of_essays', self.gf('django.db.models.fields.IntegerField')()),
            ('cv_kappa', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=9)),
            ('cv_mean_absolute_error', self.gf('django.db.models.fields.DecimalField')(max_digits=15, decimal_places=10)),
            ('creation_succeeded', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('ml_grading', ['CreatedModel'])


    def backwards(self, orm):
        # Deleting model 'CreatedModel'
        db.delete_table('ml_grading_createdmodel')


    models = {
        'ml_grading.createdmodel': {
            'Meta': {'object_name': 'CreatedModel'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'creation_succeeded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cv_kappa': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '9'}),
            'cv_mean_absolute_error': ('django.db.models.fields.DecimalField', [], {'max_digits': '15', 'decimal_places': '10'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {}),
            'model_full_path': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'model_relative_path': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'number_of_essays': ('django.db.models.fields.IntegerField', [], {}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'prompt': ('django.db.models.fields.TextField', [], {}),
            'rubric': ('django.db.models.fields.TextField', [], {}),
            'submission_ids_used': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['ml_grading']