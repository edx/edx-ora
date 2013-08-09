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

Install XQueue
--------------

Follow similar steps to how you installed edx-ora::

    $ virtualenv /opt/edx/xqueue
    $ source /opt/edx/xqueue/bin/activate
    $ pip install -r pre-requirements.txt
    $ pip install -r requirements.txt
    $ python manage.py syncdb --settings=xqueue.settings --noinput --pythonpath=.
    $ python manage.py migrate --settings=xqueue.settings --noinput --pythonpath=.


NLTK data
---------

Install NLTK data with this command::

    $ python -m nltk.downloader maxent_treebank_pos_tagger wordnet

Special instructions for MacOSX 10.8
------------------------------------

Install Homebrew_. and then install these packages::

    $ brew install libpng
    $ brew install freetype
    $ brew install pkg-config
    $ brew install gfortran
    $ brew install redis

And to install RabbitMQ::

    $ brew install rabbitmq
    $ ln -sfv /usr/local/opt/rabbitmq/*.plist ~/Library/LaunchAgents
    $ launchctl load ~/Library/LaunchAgents/homebrew.mxcl.rabbitmq.plist

Instead of using ``requirements.txt`` use the special ``requirements_osx_10_8.txt`` to install newer versions of SciPy and Matplotlib::

    $ pip install -r requirements-osx-10_8.txt


TODO: check out ScipySuperpack (http://fonnesbeck.github.io/ScipySuperpack/
)

.. _Homebrew: http://brew.sh/
