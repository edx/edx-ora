==========
Supervisor
==========

If you're not using Vagrant, then this supervisor.conf file might be more appropriate::

	[program:celeryd]
	command=%(ENV_HOME)s/mitx_all/edx-ora-venv/bin/python manage.py celeryd -B --settings=edx_ora.settings --pythonpath=.
	directory=%(ENV_HOME)s/mitx_all/edx-ora       
	stdout_logfile=%(here)s/logs/supervisor/celeryd_stdout.log
	stderr_logfile=%(here)s/logs/supervisor/celeryd_stderr.log
	user=marco
	 
	[program:xqueue]
	command=%(ENV_HOME)s/mitx_all/xqueue-venv/bin/python manage.py runserver 127.0.0.1:3032 --settings=xqueue.settings --pythonpath=.
	directory=%(ENV_HOME)s/mitx_all/xqueue       
	stdout_logfile=%(here)s/logs/supervisor/xqueue_stdout.log
	stderr_logfile=%(here)s/logs/supervisor/xqueue_stderr.log
	user=marco
	 
	[program:edx-ora]
	command=%(ENV_HOME)s/mitx_all/edx-ora-venv/bin/python manage.py runserver 127.0.0.1:3033 --settings=edx_ora.settings --pythonpath=.
	directory=%(ENV_HOME)s/mitx_all/edx-ora       
	stdout_logfile=%(here)s/logs/supervisor/edx-ora_stdout.log
	stderr_logfile=%(here)s/logs/supervisor/edx-ora_stderr.log
	user=marco
	 
	[program:lms]
	command=%(ENV_HOME)s/mitx_all/edx-platform-venv/bin/django-admin.py runserver 127.0.0.1:8000 --traceback --settings=lms.envs.cms.dev --pythonpath=. 
	directory=%(ENV_HOME)s/mitx_all/edx-platform       
	stdout_logfile=%(here)s/logs/supervisor/lms_stdout.log
	stderr_logfile=%(here)s/logs/supervisor/lms_stderr.log
	user=marco
	 
	[program:cms]
	command=%(ENV_HOME)s/mitx_all/edx-platform-venv/bin/django-admin.py runserver 127.0.0.1:8001 --traceback --settings=cms.envs.dev --pythonpath=. 
	directory=%(ENV_HOME)s/mitx_all/edx-platform       
	stdout_logfile=%(here)s/logs/supervisor/cms_stdout.log
	stderr_logfile=%(here)s/logs/supervisor/cms_stderr.log
	user=marco

NOTE: Replace ``marco`` with your username.