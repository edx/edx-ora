from settings import *
from logsettings import get_logger_config

import logging
south_logger=logging.getLogger('south')
south_logger.setLevel(logging.INFO)

log_dir = REPO_PATH / "log"

try:
    os.makedirs(log_dir)
except Exception:
    pass

LOGGING = get_logger_config(debug=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME' : 'test_essaydb',
        }
}

RESET_SUBMISSIONS_AFTER = 0 #seconds
EXPIRE_SUBMISSIONS_AFTER = 0 #seconds
MIN_TO_USE_PEER = 2
MIN_TO_USE_ML = 3

TEST_PATH = os.path.abspath(os.path.join(REPO_PATH, "tests"))

# Nose Test Runner
INSTALLED_APPS += ('django_nose',)
NOSE_ARGS = [ '--with-xunit', '--with-coverage',
              '--cover-html-dir', 'cover',
              '--cover-package', 'controller',
              '--cover-package', 'ml_grading',
              '--cover-package', 'staff_grading',
              '--cover-package', 'peer_grading',
              '--cover-package', 'basic_check',
              ]
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

CELERY_ALWAYS_EAGER = True