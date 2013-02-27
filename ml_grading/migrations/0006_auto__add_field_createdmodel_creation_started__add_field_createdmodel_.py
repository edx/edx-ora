# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'CreatedModel.creation_started'
        db.add_column('ml_grading_createdmodel', 'creation_started',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'CreatedModel.created_finished'
        db.add_column('ml_grading_createdmodel', 'created_finished',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'CreatedModel.creation_started'
        db.delete_column('ml_grading_createdmodel', 'creation_started')

        # Deleting field 'CreatedModel.created_finished'
        db.delete_column('ml_grading_createdmodel', 'created_finished')


    models = {
        'ml_grading.createdmodel': {
            'Meta': {'object_name': 'CreatedModel'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'created_finished': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'creation_started': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'creation_succeeded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cv_kappa': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '10', 'decimal_places': '9'}),
            'cv_mean_absolute_error': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '15', 'decimal_places': '10'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {}),
            'model_full_path': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'model_relative_path': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'model_stored_in_s3': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'number_of_essays': ('django.db.models.fields.IntegerField', [], {}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'prompt': ('django.db.models.fields.TextField', [], {}),
            'rubric': ('django.db.models.fields.TextField', [], {}),
            's3_bucketname': ('django.db.models.fields.TextField', [], {'default': "''"}),
            's3_public_url': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'submission_ids_used': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['ml_grading']