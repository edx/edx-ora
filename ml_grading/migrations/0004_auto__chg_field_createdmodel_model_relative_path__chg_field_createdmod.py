# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'CreatedModel.model_relative_path'
        db.alter_column('ml_grading_createdmodel', 'model_relative_path', self.gf('django.db.models.fields.CharField')(max_length=512))

        # Changing field 'CreatedModel.course_id'
        db.alter_column('ml_grading_createdmodel', 'course_id', self.gf('django.db.models.fields.CharField')(max_length=512))

        # Changing field 'CreatedModel.model_full_path'
        db.alter_column('ml_grading_createdmodel', 'model_full_path', self.gf('django.db.models.fields.CharField')(max_length=512))

        # Changing field 'CreatedModel.problem_id'
        db.alter_column('ml_grading_createdmodel', 'problem_id', self.gf('django.db.models.fields.CharField')(max_length=512))

        # Changing field 'CreatedModel.location'
        db.alter_column('ml_grading_createdmodel', 'location', self.gf('django.db.models.fields.CharField')(max_length=512))

    def backwards(self, orm):

        # Changing field 'CreatedModel.model_relative_path'
        db.alter_column('ml_grading_createdmodel', 'model_relative_path', self.gf('django.db.models.fields.CharField')(max_length=1024))

        # Changing field 'CreatedModel.course_id'
        db.alter_column('ml_grading_createdmodel', 'course_id', self.gf('django.db.models.fields.CharField')(max_length=1024))

        # Changing field 'CreatedModel.model_full_path'
        db.alter_column('ml_grading_createdmodel', 'model_full_path', self.gf('django.db.models.fields.CharField')(max_length=1024))

        # Changing field 'CreatedModel.problem_id'
        db.alter_column('ml_grading_createdmodel', 'problem_id', self.gf('django.db.models.fields.CharField')(max_length=1024))

        # Changing field 'CreatedModel.location'
        db.alter_column('ml_grading_createdmodel', 'location', self.gf('django.db.models.fields.CharField')(max_length=1024))

    models = {
        'ml_grading.createdmodel': {
            'Meta': {'object_name': 'CreatedModel'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'creation_succeeded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cv_kappa': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '9'}),
            'cv_mean_absolute_error': ('django.db.models.fields.DecimalField', [], {'max_digits': '15', 'decimal_places': '10'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {}),
            'model_full_path': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'model_relative_path': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'model_stored_in_s3': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'number_of_essays': ('django.db.models.fields.IntegerField', [], {}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'prompt': ('django.db.models.fields.TextField', [], {}),
            'rubric': ('django.db.models.fields.TextField', [], {}),
            's3_bucketname': ('django.db.models.fields.TextField', [], {'default': "''"}),
            's3_public_url': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'submission_ids_used': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['ml_grading']