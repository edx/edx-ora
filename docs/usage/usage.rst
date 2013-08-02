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


Automated execution using Supervisor
------------------------------------

In order to fully use edx-ora, you need to have many processes running:

* edx-ora 
* edx-ora Celery
* xqueue
* RabbitMQ
* MongoDB
* LMS
* CMS

Starting up all of these services manually can be tiresome, so we can use Supervisor_ to automatically handle the starting and stopping of these processes.

To start up all of the processes, you simply run this command::

    $ sudo supervisord -c supervisor.conf

You can then see that all the processes started up properly with::

    $ sudo supervisorctl
    celeryd                          RUNNING    pid 29669, uptime 1:00:37
    cms                              RUNNING    pid 29678, uptime 1:00:37
    edx-ora                          RUNNING    pid 29671, uptime 1:00:37
    lms                              RUNNING    pid 29672, uptime 1:00:37
    mongod                           RUNNING    pid 30013, uptime 0:59:08
    rabbitmq                         RUNNING    pid 3688, uptime 0:00:16
    xqueue                           RUNNING    pid 29675, uptime 1:00:37
    supervisor>

URLs for LMS and CMS (Studio)
-----------------------------

From your host machine, you now can access the LMS at:

    * http://192.168.20.40:8000

And the CMS (Studio) can be accessed at:

    * http://192.168.20.40:8001
    

Start/stop processes with web interface
---------------------------------------

Supervisor also runs a web interface that is accessible at: 

    * http://192.168.20.40:9001
    
.. image:: supervisor.png
   :width: 800px
   :alt: Supervisor screenshot


Start/stop processes with command line
--------------------------------------

You can start individual processes with::

    $ sudo supervisorctl start edx-ora

And stop individual processes with::

    $ sudo supervisorctl stop edx-ora

You can also restart all processes with::

    $ sudo supervisorctl restart all

All of the log files are stored in ``logs/supervisor``::

    $ ls supervisor/logs
    celeryd_stderr.log  cms_stderr.log  edx-ora_stderr.log  lms_stderr.log  mongod_stderr.log  rabbitmq_stderr.log  supervisord.log    xqueue_stdout.log
    celeryd_stdout.log  cms_stdout.log  edx-ora_stdout.log  lms_stdout.log  mongod_stdout.log  rabbitmq_stdout.log  xqueue_stderr.log


Virtualenvs and directory structure
-----------------------------------

Supervisor expects you to have created virtualenvs for each project in the ``/home/vagrant/.virtualenvs`` dir:

* /home/vagrant/.virtualenvs/edx-ora
* /home/vagrant/.virtualenvs/edx-platform
* /home/vagrant/.virtualenvs/xqueue

And the project directories are all located in ``/opt/edx``:

* /opt/edx/edx-ora
* /opt/edx/edx-platform
* /opt/edx/xqueue

.. _Supervisor: http://supervisord.org

Manual execution
----------------

If you want to run everything manually rather than using Supervisor, here are the instructions.

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
