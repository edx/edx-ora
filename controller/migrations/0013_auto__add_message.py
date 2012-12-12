# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Message'
        db.create_table('controller_message', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('grader', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Grader'])),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('originator', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('recipient', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('message_type', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('controller', ['Message'])


    def backwards(self, orm):
        # Deleting model 'Message'
        db.delete_table('controller_message')


    models = {
        'controller.grader': {
            'Meta': {'object_name': 'Grader'},
            'confidence': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '9'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_calibration': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['controller.Submission']"})
        },
        'controller.message': {
            'Meta': {'object_name': 'Message'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'grader': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['controller.Grader']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'message_type': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'originator': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'recipient': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        },
        'controller.submission': {
            'Meta': {'object_name': 'Submission'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'grader_settings': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024'}),
            'max_score': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'next_grader_type': ('django.db.models.fields.CharField', [], {'default': "'NA'", 'max_length': '2'}),
            'posted_results_back_to_queue': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
        }
    }

    complete_apps = ['controller']