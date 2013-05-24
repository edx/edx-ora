#!/usr/bin/env bash
set -e

# posix compliant sanity check
if [ -z $BASH ] || [  $BASH = "/bin/sh" ]; then
    echo "Please use the bash interpreter to run this script"
    exit 1
fi

trap "ouch" ERR

ouch() {
    printf '\E[31m'

    cat<<EOL

    !! ERROR !!

    The last command did not complete successfully,
    For more details or trying running the
    script again with the -v flag.

    Output of the script is recorded in $LOG

EOL
    printf '\E[0m'

}
error() {
      printf '\E[31m'; echo "$@"; printf '\E[0m'
}
output() {
      printf '\E[36m'; echo "$@"; printf '\E[0m'
}
usage() {
    cat<<EO

    Usage: $PROG [-c] [-h]

            -c        compile scipy and numpy
            -h        this

EO
    info
}

info() {

    cat<<EO
    MITx base dir : $BASE
    Python dir : $PYTHON_DIR

EO
}

clone_repos() {
    cd "$BASE"

    if [[ -d "$BASE/edx-ora/.git" ]]; then
        output "Pulling grading controller"
        cd "$BASE/edx-ora"
        git pull
    else
        output "Cloning grading controller"
        if [[ -d "$BASE/edx-ora" ]]; then
            mv "$BASE/edx-ora" "${BASE}/edx-ora.bak.$$"
        fi
        git clone git@github.com:edx/edx-ora.git
    fi

    # Also need machine learning repo for everything to work properly
    cd "$BASE"
    if [[ -d "$BASE/ease/.git" ]]; then
        output "Pulling ease"
        cd "$BASE/ease"
        git pull
    else
        output "Cloning machine learning"
        if [[ -d "$BASE/ease" ]]; then
            mv "$BASE/ease" "${BASE}/ease.bak.$$"
        fi
        git clone git@github.com:edx/ease.git
    fi

    # Also need xqueue for everything to work properly
    cd "$BASE"
    if [[ -d "$BASE/xqueue/.git" ]]; then
        output "Pulling xqueue"
        cd "$BASE/xqueue"
        git pull
    else
        output "Cloning xqueue"
        if [[ -d "$BASE/xqueue" ]]; then
            mv "$BASE/xqueue" "${BASE}/xqueue.bak.$$"
        fi
        git clone git@github.com:edx/xqueue.git
    fi
}

### START

PROG=${0##*/}
BASE="$HOME/mitx_all"
PYTHON_DIR="$BASE/python"
LOG="/var/tmp/install-controller-$(date +%Y%m%d-%H%M%S).log"

# Read arguments

if [[ $EUID -eq 0 ]]; then
    error "This script should not be run using sudo or as the root user"
    usage
    exit 1
fi
ARGS=$(getopt "cvhs" "$*")
if [[ $? != 0 ]]; then
    usage
    exit 1
fi
eval set -- "$ARGS"
while true; do
    case $1 in
        -c)
            compile=true
            shift
            ;;
        -h)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
    esac
done

cat<<EO

  This script will setup the grading controller.
  includes

       * Grading controller
       * Machine learning
       * Dependencies

  It will also attempt to install operating system dependencies
  with apt(debian) or brew(OSx).

  To compile scipy and numpy from source use the -c option

  !!! Do not run this script from an existing virtualenv !!!

  If you are in a ruby/python virtualenv please start a new
  shell.

EO
info
output "Press return to begin or control-C to abort"
read dummy


# Log all stdout and stderr

exec > >(tee $LOG)
exec 2>&1


# Install basic system requirements

mkdir -p $BASE
case `uname -s` in
    [Ll]inux)
        command -v lsb_release &>/dev/null || {
            error "Please install lsb-release."
            exit 1
        }

        distro=`lsb_release -cs`
        case $distro in
            maya|lisa|natty|oneiric|precise|quantal)
                sudo apt-get install git
                ;;
            *)
                error "Unsupported distribution - $distro"
                exit 1
               ;;
        esac
        ;;

    Darwin)
        if [[ ! -w /usr/local ]]; then
            cat<<EO

        You need to be able to write to /usr/local for
        the installation of brew and brew packages.

        Either make sure the group you are in (most likely 'staff')
        can write to that directory or simply execute the following
        and re-run the script:

        $ sudo chown -R $USER /usr/local
EO

            exit 1

        fi

        ;;
    *)
        error "Unsupported platform"
        exit 1
        ;;
esac


# Clone MITx repositories

clone_repos


# Install system-level dependencies
bash $BASE/edx-ora/install_system_req.sh
bash $BASE/ease/install_system_req.sh

# Activate Python virtualenv
source $PYTHON_DIR/bin/activate

# compile numpy and scipy if requested

NUMPY_VER="1.6.2"
SCIPY_VER="0.10.1"

if [[ -n $compile ]]; then
    output "Downloading numpy and scipy"
    curl -sL -o numpy.tar.gz http://downloads.sourceforge.net/project/numpy/NumPy/${NUMPY_VER}/numpy-${NUMPY_VER}.tar.gz
    curl -sL -o scipy.tar.gz http://downloads.sourceforge.net/project/scipy/scipy/${SCIPY_VER}/scipy-${SCIPY_VER}.tar.gz
    tar xf numpy.tar.gz
    tar xf scipy.tar.gz
    rm -f numpy.tar.gz scipy.tar.gz
    output "Compiling numpy"
    cd "$BASE/numpy-${NUMPY_VER}"
    python setup.py install
    output "Compiling scipy"
    cd "$BASE/scipy-${SCIPY_VER}"
    python setup.py install
    cd "$BASE"
    rm -rf numpy-${NUMPY_VER} scipy-${SCIPY_VER}
fi

case `uname -s` in
    Darwin)
        # on mac os x get the latest distribute and pip
        curl http://python-distribute.org/distribute_setup.py | python
        pip install -U pip
        # need latest pytz before compiling numpy and scipy
        pip install -U pytz
        pip install numpy
        # fixes problem with scipy on 10.8
        pip install -e git+https://github.com/scipy/scipy#egg=scipy-dev
        ;;
esac

output "Installing Controller pre-requirements"
pip install -r $BASE/edx-ora/pre-requirements.txt

output "Installing ML pre-requirements"
pip install -r $BASE/ease/pre-requirements.txt

output "Installing Controller requirements"
# Need to be in the mitx dir to get the paths to local modules right
cd $BASE/edx-ora
pip install -r requirements.txt

output "Installing ml requirements"
# Need to be in the mitx dir to get the paths to local modules right
cd $BASE/ease
pip install -r requirements.txt

output "Installing xqueue requirements"
# Need to be in the mitx dir to get the paths to local modules right
cd $BASE/xqueue
pip install -r requirements.txt


mkdir "$BASE/log" || true
mkdir "$BASE/edx-ora/log" || true
mkdir "$BASE/ease/log" || true
mkdir "$BASE/xqueue/log" || true
touch "$BASE/edx-ora/log/edx.log" || true
touch "$BASE/ease/log/edx.log" || true
touch "$BASE/xqueue/log/edx.log" || true

#Sync controller db
cd $BASE/edx-ora
yes | django-admin.py syncdb --settings=edx_ora.settings --pythonpath=.
yes | django-admin.py migrate --settings=edx_ora.settings --pythonpath=.

#sync xquque db
cd $BASE/xqueue
yes | django-admin.py syncdb --settings=xqueue.settings --pythonpath=.
yes | django-admin.py migrate --settings=xqueue.settings --pythonpath=.

touch "$BASE/auth.json"
echo '{ "USERS": {"lms": "abcd", "xqueue_pull": "abcd"} }' > "$BASE/auth.json"

#Update controller users
cd $BASE/edx-ora
django-admin.py update_users --pythonpath=$BASE/edx-ora --settings=edx_ora.settings

#Update xqueue users
cd $BASE/xqueue
django-admin.py update_users --pythonpath=$BASE/xqueue --settings=xqueue.settings

#Install machine learning nltk stuff
python -m nltk.downloader maxent_treebank_pos_tagger wordnet

### DONE

cat<<END
   Success!!

   See full instructions below if you run into trouble:
   https://edx-wiki.atlassian.net/wiki/display/ENG/Setting+up+Grading+Controller+and+XQueue

   Next steps are to point the LMS to the xqueue and grading controller (lms/envs/dev.py),
   then run the xqueue and the grading controller on the correct ports:

   To start the controller:

        $ django-admin.py runserver 127.0.0.1:3033 --settings=edx_ora.settings --pythonpath=$BASE/edx-ora

   To start the xqueue:
        $ django-admin.py runserver 127.0.0.1:3032 --settings=xqueue.settings --pythonpath=. --pythonpath=$BASE/xqueue

   Then start the celery processes associated with the grading controller:
        python manage.py celeryd -B --settings = edx_ora.settings --pythonpath=$BASE/edx-ora

  If the  Django development server starts properly you
  should see:

      Development server is running at http://127.0.0.1:<port#>/
      Quit the server with CONTROL-C.

  Connect your browser to http://127.0.0.1:<port#> to
  view the Django site.


END
exit 0