=================================
Installation Overview
=================================

In order to install edX-ORA, one must first have edX-platform, xqueue, and ease installed.  Please see https://github.com/edx/edx-platform, https://github.com/edx/xqueue, and https://github.com/edx/ease for installation instructions for those repositories.

This assumes that you already have git installed on your computer. The main steps are::

	$ git clone git://github.com/edx/edx-ora.git
	$ cd edx-ora
	$ xargs -a apt-packages.txt apt-get install -y
    $ apt-get install python-pip
    $ pip install virtualenv
	$ virtualenv /path/to/edx
	$ source /path/to/edx/bin/activate
	$ pip install -r pre-requirements.txt
	$ pip install -r requirements.txt
    $ python manage.py syncdb --settings=edx_ora.settings --noinput --pythonpath=.
    $ python manage.py migrate --settings=edx_ora.settings --noinput --pythonpath=.

See :doc:`usage` for how to run this.  You will both need to run the server and the celery tasks.