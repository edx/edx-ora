Part of `edX code`__.

__ http://code.edx.org/

edx ORA (Open Response Assessor)
=======================

The ORA will take a submission from an xqueue installation, pass it through machine learning grading, peer grading, and staff grading as appropriate, and return a result to LMS.  This is to be used with the edx-platform and xqueue.  It allows for the assessment of open response problems on the edx platform.

Overview
------------------------

Each type of grader is a separate django application, with the controller having common logic, such as submission and returning the result to the LMS.

After installation, tests can be run by running ``sh run_tests.sh`` .

Documentation
-------------------------

You can find full documentation in the docs directory, and build it using ``make html``, or see `here`__ for built documentation.

__ http://edx-ora.readthedocs.org/en/latest/

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

Mailing List and IRC Channel
----------------------------

You can discuss this code on the `edx-code Google Group`__ or in the
``edx-code`` IRC channel on Freenode.

__ https://groups.google.com/forum/#!forum/edx-code
