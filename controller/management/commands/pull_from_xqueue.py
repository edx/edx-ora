import json
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import requests
import urlparse


log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<queue_name>"
    help = "Pull items from given queues and send to grading controller"

    def handle(self, *args, **options):
        """
        Constant loop that pulls from queue and posts to grading controller
        """
        log.info(' [*] Pulling from xqueues...')

        flag=True
        error = self.login()

        while flag:
            for queue_name in args:
                queue_item=self.get_from_queue(queue_name)
                log.debug(queue_item)

    def login():
        '''
        Login to xqueue to pull submissions
        '''
        full_login_url = urlparse.join(settings.XQUEUE_INTERFACE['url'],'/xqueue/login/')

        response = requests.post(login_url,params= {'username': settings.XQUEUE_INTERFACE['django_auth']['username'],
                                            'password':XQUEUE_INTERFACE['django_auth']['password']})
        (error,_) = parse_xreply(response.content)

        log.debug(error)

        return error

    def get_from_queue(queue_name):
        """
        Get a single submission from xqueue
        """
        try:
            response = self._http_get(urlparse.join(settings.XQUEUE_INTERFACE['url'],'/xqueue/get_submissions/'),
                {'queue_name' : queue_name})
        except:
            return "Error getting response."

        return response

    def _http_get(self, url, data):
        try:
            r = requests.get(url, params=data)
        except requests.exceptions.ConnectionError, err:
            log.error(err)
            return (1, 'cannot connect to server')

        if r.status_code not in [200]:
            return (1, 'unexpected HTTP status code [%d]' % r.status_code)

        return parse_xreply(r.text)


    def push_orphaned_submissions(self, orphaned_submissions):
        for orphaned_submission in orphaned_submissions:
            current_time = timezone.now()
            time_difference = (current_time - orphaned_submission.arrival_time).total_seconds()
            if time_difference > settings.ORPHANED_SUBMISSION_TIMEOUT:

                log.info("Found orphaned submission: queue_name: {0}, lms_header: {1}".format(
                    orphaned_submission.queue_name, orphaned_submission.xqueue_header))
                orphaned_submission.num_failures += 1

                payload = {'xqueue_body': orphaned_submission.xqueue_body,
                           'xqueue_files': orphaned_submission.s3_urls}

                orphaned_submission.grader_id = settings.XQUEUES[orphaned_submission.queue_name]
                orphaned_submission.push_time = timezone.now()
                (grading_success, grader_reply) = _http_post(orphaned_submission.grader_id, json.dumps(payload), settings.GRADING_TIMEOUT)
                orphaned_submission.return_time = timezone.now()

                if grading_success:
                    orphaned_submission.grader_reply = grader_reply
                    orphaned_submission.lms_ack = post_grade_to_lms(orphaned_submission.xqueue_header, grader_reply)
                else:
                    log.error("Submission {} to grader {} failure: Reply: {}, ".format(orphaned_submission.id, orphaned_submission.grader_id, grader_reply))
                    orphaned_submission.num_failures += 1
                    orphaned_submission.lms_ack = post_failure_to_lms(orphaned_submission.xqueue_header)

                orphaned_submission.retired = True # NOTE: Retiring pushed submissions after one shot regardless of grading_success
                orphaned_submission.save()