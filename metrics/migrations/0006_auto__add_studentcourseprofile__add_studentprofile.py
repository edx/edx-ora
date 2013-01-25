# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'StudentCourseProfile'
        db.create_table('metrics_studentcourseprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student_profile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['metrics.StudentProfile'])),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('course_id', self.gf('django.db.models.fields.CharField')(default='', max_length=128)),
            ('student_id', self.gf('django.db.models.fields.CharField')(default='', max_length=128, db_index=True)),
            ('problems_attempted', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('attempts_per_problem', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('graders_per_attempt', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('stdev_percent_score', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_percent_score', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_percent_score_last20', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_percent_score_last10', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('problems_attempted_peer', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('completed_peer_grading', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_length_of_peer_feedback_given', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('stdev_length_of_peer_feedback_given', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_peer_grading_score_given', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('attempts_per_problem_peer', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_percent_score_peer', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('problems_attempted_ml', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('attempts_per_problem_ml', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_ml_confidence', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_percent_score_ml', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_submission_length', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('stdev_submission_length', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
        ))
        db.send_create_signal('metrics', ['StudentCourseProfile'])

        # Adding model 'StudentProfile'
        db.create_table('metrics_studentprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('student_id', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('messages_sent', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('messages_received', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
            ('average_message_feedback_length', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=10, decimal_places=5)),
        ))
        db.send_create_signal('metrics', ['StudentProfile'])


    def backwards(self, orm):
        # Deleting model 'StudentCourseProfile'
        db.delete_table('metrics_studentcourseprofile')

        # Deleting model 'StudentProfile'
        db.delete_table('metrics_studentprofile')


    models = {
        'metrics.studentcourseprofile': {
            'Meta': {'object_name': 'StudentCourseProfile'},
            'attempts_per_problem': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'attempts_per_problem_ml': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'attempts_per_problem_peer': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_length_of_peer_feedback_given': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_ml_confidence': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_peer_grading_score_given': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score_last10': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score_last20': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score_ml': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_percent_score_peer': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'average_submission_length': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'completed_peer_grading': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'course_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'graders_per_attempt': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'problems_attempted': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'problems_attempted_ml': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'problems_attempted_peer': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'stdev_length_of_peer_feedback_given': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'stdev_percent_score': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'stdev_submission_length': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'student_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128', 'db_index': 'True'}),
            'student_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['metrics.StudentProfile']"})
        },
        'metrics.studentprofile': {
            'Meta': {'object_name': 'StudentProfile'},
            'average_message_feedback_length': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'messages_received': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'messages_sent': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '10', 'decimal_places': '5'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'})
        },
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
            'location': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
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