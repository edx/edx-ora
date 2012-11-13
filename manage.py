#!/usr/bin/env python
import os
import sys
from django.core.management import execute_manager

if __name__ == "__main__":

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grading_controller.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
