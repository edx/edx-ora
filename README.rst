edx ORA (Open Response Assessor)
=======================

The ORA will take a submission from an xqueue installation, pass it through machine learning grading, peer grading, and staff grading as appropriate, and return a result to LMS.  This is to be used with the edx-platform and xqueue.  It allows for the assessment of open response problems on the edx platform.

Overview
------------------------

Each type of grader is a separate django application, with the controller having common logic, such as submission and returning the result to the LMS.

Tests can be run by running `sh run_tests.sh` .

Getting Started
-------------------------------

In order to get started, you may run the setup_controller.sh shell script.  Depending on your system, it may or may not work.

If it does not work:

- git clone git@github.com:edx/edx-ora
- cd edx-ora
- xargs -a apt-packages.txt apt-get install -y
- Now, either create a virtualenv and activate it, or use the global python env.  This will assume you made a virtualenv.
- apt-get install python-pip
- pip install virtualenv
- virtualenv /opt/edx
- source /opt/edx/bin/activate
- pip install -r pre-requirements.txt
- pip install -r requirements.txt
- python manage.py syncdb --settings=edx_ora.settings --noinput --pythonpath=.
- python manage.py migrate --settings=edx_ora.settings --noinput --pythonpath=.

You will also need to install the ease repo from https://github.com/edx/ease and follow the install instructions there in order to get AI scoring.

License
-------

The code in this repository is licensed under version 3 of the AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.

How to Contribute
-----------------

Contributions are very welcome. The easiest way is to fork this repo, and then
make a pull request from your fork. The first time you make a pull request, you
may be asked to sign a Contributor Agreement.

Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@edx.org

Please see http://code.edx.org/security/ for details.

Mailing List and IRC Channel
----------------------------

You can discuss this code on the `edx-code Google Group`__ or in the
``edx-code`` IRC channel on Freenode.

__ https://groups.google.com/forum/#!forum/edx-code
