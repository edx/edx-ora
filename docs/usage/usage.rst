==================================
Usage
==================================

This page will walk you through setting up ORA and getting it working locally.

Configuration
--------------------------------------------------

You will first need to setup edx-platform properly:

In /path/to/edx/platform/lms/envs/dev.py , change OPEN_ENDED_GRADING_INTERFACE to point to your server::

    OPEN_ENDED_GRADING_INTERFACE = {
        'url' : 'http://127.0.0.1:3033/',
        'username' : 'lms',
        'password' : 'abcd',
        'staff_grading' : 'staff_grading',
        'peer_grading' : 'peer_grading',
        'grading_controller' : 'grading_controller'
    }

Also, change the XQUEUE_INTERFACE to have the right password and point to the right place::

    XQUEUE_INTERFACE = {
        "url": "http://127.0.0.1:3032",
        "django_auth": {
            "username": "lms",
            "password": "abcd"
        },
        "basic_auth": ('anant', 'agarwal'),
    }

Create an auth.json file one level above your xqueue installation directory (so if xqueue is at /opt/edx/xqueue, you need /opt/edx/auth.json).
It must contain the following::

    {
      "USERS": {"lms": "abcd", "xqueue_pull" : "abcd"}
    }

If edx-ora is not in the same directory as xqueue, do the same for edx-ora.

Update the xqueue users::

    $ cd path/to/xqueue
    $ python manage.py update_users --settings=xqueue.settings --pythonpath=`pwd`

Update the edx-ora users::

    $ cd path/to/edx-ora
    $ python manage.py update_users --settings=edx_ora.settings --pythonpath=`pwd`


Execution
---------------------------------------------------------

Run the edx-platform::

    $ cd /path/to/edx-platform
    $ rake lms

If you want to run edX studio, you can do rake cms and rake lms[cms.dev] in two separate terminal windows.

All of the following commands must be run in separate terminal windows.

Run the xqueue::

    $ cd /path/to/xqueue
    $ python manage.py runserver 127.0.0.1:3032 --settings=xqueue.settings --pythonpath=.

Run edx-ora::

    $ cd /path/to/edx-ora
    $ python manage.py runserver 127.0.0.1:3033 --settings=edx_ora.settings --pythonpath=.

Run the edx-ora celery tasks::

    $ cd /path/to/ora
    $ python manage.py celeryd -B --settings=edx_ora.settings --pythonpath=.

The LMS/CMS will now be able to interact with edX-ORA.
