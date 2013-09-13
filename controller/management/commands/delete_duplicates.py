from django.core.management.base import BaseCommand
import logging
from controller.models import Submission, Message
from metrics.models import StudentProfile, StudentCourseProfile
from peer_grading.models import CalibrationHistory
from optparse import make_option
from itertools import chain
from collections import namedtuple

log = logging.getLogger(__name__)

# Unique model represents a model instance that we would like to make unique over certain fields.
# cls is the class of the model that we would like to make unique.  For example, Submission.
# name is the human readable name of the model, used in log messages.  For example, "submission".
# fields is a list of fields over which the model should be unique.  For example, ["id", "student_response"]
UniqueModel = namedtuple('UniqueModel', ['cls', 'name', 'fields'])

# Make a list of models and fields that we would like to make unique.
UNIQUE_MODELS = [
    UniqueModel(Submission, "submission", ("xqueue_submission_id",)),
    UniqueModel(StudentProfile, "student_profile", ("student_id",)),
    UniqueModel(StudentCourseProfile, "student_course_profile", ("student_profile", "course_id")),
    UniqueModel(CalibrationHistory, "calibration_history", ("student_id", "location")),
]

class DuplicateDeleter(object):
    """
    Gets and deletes duplicates for a given django model.
    """
    def __init__(self, unique_model):
        """
        unique_model - instance of the UniqueModel namedtuple.
        """
        self.model_cls = unique_model.cls
        self.model_count = self.model_cls.objects.all().count()
        self.fields = unique_model.fields
        self.name = unique_model.name

    def get_unique(self):
        """
        Retrieves the unique values for self.model_cls.  Logs the count of duplicates.
        """
        self.unique = self.model_cls.objects.values(*self.fields).distinct()
        self.duplicate_count = self.model_count - len(self.unique)
        log.info("{0} duplicate {1} found on fields {2}.".format(self.duplicate_count, self.name, self.fields))

    def delete_duplicates(self):
        """
        Deletes all duplicates for a given model.  Must be called after get_unique.
        """
        # Ensure that get_unique has been called.
        if getattr(self, "unique") is None:
            error_msg = "delete_duplicates must be called after get_unique."
            log.error(error_msg)
            raise ValueError(error_msg)

        log.info("Deleting the duplicate submissions....")

        # Get all duplicates.
        duplicates = []
        for val in self.unique:
            duplicate = self.model_cls.objects.filter(**val)[1:]
            duplicates.append(duplicate)
        duplicates = list(chain.from_iterable(duplicates))

        # If the number of duplicates does not equal the duplicate count calculated in get_unique,
        # something is wrong.  This is not an expected case, but better to be cautious with deleting
        # records.
        if len(duplicates) != self.duplicate_count:
            error_msg = ("Number of duplicates {0} differs from the count that should exist {1} for {2}.  "
                         "Please delete manually.").format(len(duplicates), self.duplicate_count, self.name)
            log.error(error_msg)
            raise ValueError(error_msg)

        # Delete the duplicates.
        for dup in duplicates:
            dup.delete()
        log.info("...Finished.")

class Command(BaseCommand):
    args = ""
    help = "Shows you how many duplicates exist in each table.  Optionally can delete them."
    option_list = BaseCommand.option_list + (
        make_option(
            "--delete",
            action = "store_true",
            help="Delete duplicate data."
        ),
    )

    def handle(self, delete, *args, **options):
        """
        Find how many duplicates exist in the tables and optionally delete them.
        """

        for unique_model in UNIQUE_MODELS:
            deleter = DuplicateDeleter(unique_model)
            deleter.get_unique()
            if delete:
                deleter.delete_duplicates()




