from logsettings import get_logger_config
from path import path
import os


# Django settings for grading_controller project.
ROOT_PATH = path(__file__).dirname()
REPO_PATH = ROOT_PATH.dirname()
ENV_ROOT = REPO_PATH.dirname()

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
# ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

REQUESTS_TIMEOUT = 5    # seconds
TIME_BETWEEN_XQUEUE_PULLS = 5 #seconds
TIME_BETWEEN_EXPIRED_CHECKS = 30 * 60 #seconds
GRADER_SETTINGS_DIRECTORY = "grader_settings/"
MAX_NUMBER_OF_TIMES_TO_RETRY_GRADING=10

#Config for specific graders
#ML
MIN_TO_USE_ML = 100
ML_PATH = os.path.join(ENV_ROOT, "machine_learning/")
ML_MODEL_PATH=os.path.join(ENV_ROOT,"ml_models/")

#Peer
MIN_TO_USE_PEER=20
PEER_GRADER_COUNT = 3
PEER_GRADER_MINIMUM_TO_CALIBRATE = 3
PEER_GRADER_MAXIMUM_TO_CALIBRATE = 6

#Error units are defined as the absolute value of student calibration score minus actual score divided by maximum score
#abs(student_score-actual_score)/max_score
PEER_GRADER_MIN_NORMALIZED_CALIBRATION_ERROR = .5

EXPIRE_SUBMISSIONS_AFTER = 5 * 24 * 60 * 60  #Seconds
RESET_SUBMISSIONS_AFTER = 5 * 60 #Seconds

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'essaydb', # Or path to database file if using sqlite3.
        'USER': '', # Not used with sqlite3.
        'PASSWORD': '', # Not used with sqlite3.
        'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '', # Set to empty string for default. Not used with sqlite3.
    }
}

XQUEUE_INTERFACE = {
    "url": "http://127.0.0.1:3032",
    "django_auth": {
        "username": "lms",
        "password": "abcd"
    },
    "basic_auth": ('anant', 'agarwal'),
}

GRADING_CONTROLLER_INTERFACE = {
    "url": "http://127.0.0.1:3033",
    "django_auth": {
        "username": "xqueue_pull",
        "password": "abcd",
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    str(os.path.join(REPO_PATH, "static/")),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    )

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
    )

# Make this unique, and don't share it with anybody.
SECRET_KEY = '7q%=)6+vz$1zy!-vm4-k-^tj5q)hbgukoud%%$6edcxn^i^u)a'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #     'django.template.loaders.eggs.Loader',
    )

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    )

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    )

ROOT_URLCONF = 'grading_controller.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'grading_controller.wsgi.application'

TEMPLATE_DIRS = (
    str(os.path.join(REPO_PATH, "templates/"))
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    )

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'controller',
    'staff_grading',
    'south',
    'peer_grading',
    'ml_grading',
    )

LOGGING = get_logger_config(ENV_ROOT / "log",
    logging_env="dev",
    dev_env=True,
    debug=True,
    local_loglevel="DEBUG")
