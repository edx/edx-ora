# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Adding model 'Submission'
        db.create_table('controller_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('next_grader', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('prompt', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('student_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('problem_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('course_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ))
        db.send_create_signal('controller', ['Submission'])

        # Adding model 'PeerGrader'
        db.create_table('controller_peergrader', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ))
        db.send_create_signal('controller', ['PeerGrader'])

        # Adding model 'MLGrader'
        db.create_table('controller_mlgrader', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('confidence', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=9)),
            ))
        db.send_create_signal('controller', ['MLGrader'])

        # Adding model 'InstructorGrader'
        db.create_table('controller_instructorgrader', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ))
        db.send_create_signal('controller', ['InstructorGrader'])

        # Adding model 'SelfAssessmentGrader'
        db.create_table('controller_selfassessmentgrader', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ))
        db.send_create_signal('controller', ['SelfAssessmentGrader'])


    def backwards(self, orm):
        # Deleting model 'Submission'
        db.delete_table('controller_submission')

        # Deleting model 'PeerGrader'
        db.delete_table('controller_peergrader')

        # Deleting model 'MLGrader'
        db.delete_table('controller_mlgrader')

        # Deleting model 'InstructorGrader'
        db.delete_table('controller_instructorgrader')

        # Deleting model 'SelfAssessmentGrader'
        db.delete_table('controller_selfassessmentgrader')


    models = {
        'controller.instructorgrader': {
            'Meta': {'object_name': 'InstructorGrader'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['controller.Submission']"})
        },
        'controller.mlgrader': {
            'Meta': {'object_name': 'MLGrader'},
            'confidence': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '9'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['controller.Submission']"})
        },
        'controller.peergrader': {
            'Meta': {'object_name': 'PeerGrader'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['controller.Submission']"})
        },
        'controller.selfassessmentgrader': {
            'Meta': {'object_name': 'SelfAssessmentGrader'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'submission': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['controller.Submission']"})
        },
        'controller.submission': {
            'Meta': {'object_name': 'Submission'},
            'course_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'next_grader': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'prompt': ('django.db.models.fields.TextField', [], {}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['controller']