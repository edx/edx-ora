# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Deleting model 'PeerGrader'
        db.delete_table('controller_peergrader')

        # Deleting model 'MLGrader'
        db.delete_table('controller_mlgrader')

        # Deleting model 'SelfAssessmentGrader'
        db.delete_table('controller_selfassessmentgrader')

        # Deleting model 'InstructorGrader'
        db.delete_table('controller_instructorgrader')

        # Adding model 'Grader'
        db.create_table('controller_grader', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('grader_type', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('confidence', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=9)),
            ))
        db.send_create_signal('controller', ['Grader'])

        # Deleting field 'Submission.final_grader'
        db.delete_column('controller_submission', 'final_grader')


    def backwards(self, orm):
        # Adding model 'PeerGrader'
        db.create_table('controller_peergrader', (
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ))
        db.send_create_signal('controller', ['PeerGrader'])

        # Adding model 'MLGrader'
        db.create_table('controller_mlgrader', (
            ('confidence', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=9)),
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ))
        db.send_create_signal('controller', ['MLGrader'])

        # Adding model 'SelfAssessmentGrader'
        db.create_table('controller_selfassessmentgrader', (
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ))
        db.send_create_signal('controller', ['SelfAssessmentGrader'])

        # Adding model 'InstructorGrader'
        db.create_table('controller_instructorgrader', (
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('feedback', self.gf('django.db.models.fields.TextField')()),
            ('grader_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('score', self.gf('django.db.models.fields.IntegerField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('submission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['controller.Submission'])),
            ))
        db.send_create_signal('controller', ['InstructorGrader'])

        # Deleting model 'Grader'
        db.delete_table('controller_grader')

        # Adding field 'Submission.final_grader'
        db.add_column('controller_submission', 'final_grader',
            self.gf('django.db.models.fields.CharField')(default='NA', max_length=2),
            keep_default=False)


    models = {
        'controller.grader': {
            'Meta': {'object_name': 'Grader'},
            'confidence': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '9'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'feedback': ('django.db.models.fields.TextField', [], {}),
            'grader_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'grader_type': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
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
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'next_grader': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'problem_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'prompt': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'student_response': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'student_submission_time': (
            'django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'xqueue_queue_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'xqueue_submission_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'xqueue_submission_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'})
        }
    }

    complete_apps = ['controller']