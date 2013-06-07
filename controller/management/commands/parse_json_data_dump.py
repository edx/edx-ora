from django.core.management.base import BaseCommand

#from http://jamesmckay.net/2009/03/django-custom-managepy-commands-not-committing-transactions/
#Fix issue where db data in manage.py commands is not refreshed at all once they start running
from django.db import transaction
transaction.commit_unless_managed()

import logging
import json
import re
import csv

log = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "<path>"
    help = "Parse the json output from dump_data in metrics."

    def handle(self, *args, **options):
        """
        Read from file
        """
        if len(args)!=1:
            raise Exception("Not enough input arguments!")
        filepath = args[0]

        file = json.load(open(filepath))
        res = json.loads(file['task']['result'])
        bad_keys = ["feedback", "location"]
        keys = [k for k in res[0].keys() if k not in bad_keys]

        csvname = re.sub("\.json", ".csv", filepath)

        with open(csvname, 'w+') as csvfile:
            csvwriter = csv.writer(csvfile)
            for i in xrange(0,len(res)):
                if i==0:
                    csvwriter.writerow(keys)

                data = [res[i][key] for key in keys]

                csvwriter.writerow(data)


