"""
Ensure that the right users exist:

- read USERS dictionary from auth.json
- if they don't exist, create them.
- if they do, update the passwords to match

"""
import json
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from controller import util

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create users that are specified in auth.json"

    def handle(self, *args, **options):

        log.info("root is : " + settings.ENV_ROOT)
        util.update_users_from_file()
