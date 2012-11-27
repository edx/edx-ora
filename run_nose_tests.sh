export DJANGO_SETTINGS_MODULE="grading_controller.settings"
nosetests --cover-erase --with-xunit --with-xcoverage --cover-html --cover-inclusive --cover-html-dir=cover --cover-package=grading_controller --cover-package=controller --cover-package=staff_grading --cover-package=peer_grading
