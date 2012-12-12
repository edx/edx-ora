import json
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from controller.models import Submission, Grader
from ml_grading.models import CreatedModel
from controller import util
from django.core import management

class Command(BaseCommand):
    help = "Create users that are specified in auth.json"

    def handle(self, *args, **options):
        if settings.DATABASES['default']['NAME']=='test_essaydb':
            management.call_command('syncdb', interactive=False)
            management.call_command('migrate', interactive=False)
            for sub in Submission.objects.all():
                sub.delete()
            for grade in Grader.objects.all():
                grade.delete()
            for cm in CreatedModel.objects.all():
                cm.delete()

            util.update_users_from_file()

