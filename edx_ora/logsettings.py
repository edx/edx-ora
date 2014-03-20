import os
import platform
import sys
from logging.handlers import SysLogHandler

LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

def get_logger_config(log_dir, debug=False, dev_env=False, local_loglevel='INFO'):
    """

    Return the appropriate logging config dictionary. You should assign the
    result of this to the LOGGING var in your settings. The reason it's done
    this way instead of registering directly is because I didn't want to worry
    about resetting the logging state if this is called multiple times when
    settings are extended.

    If dev_env is set to true logging will not be done via local rsyslogd,
    instead, application logs will be dropped in log_dir.

    "edx_filename" is ignored unless dev_env is set to true since otherwise logging is handled by rsyslogd.

    """

    # Revert to INFO if an invalid string is passed in
    if local_loglevel not in LOG_LEVELS:
        local_loglevel = 'INFO'

    edx_filename = "edx.log"

    handlers = ['console', 'local'] if debug else [
        'console', 'syslogger-remote', 'local'
    ]

    logger_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s %(levelname)s %(process)d '
                          '[%(name)s] %(filename)s:%(lineno)d - %(message)s',
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG' if debug else 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': sys.stdout,
            },
        },
        'loggers': {
            'django': {
                'handlers': handlers,
                'propagate': True,
                'level': 'INFO'
            },
            '': {
                'handlers': handlers,
                'level': 'DEBUG',
                'propagate': False
            },
            'ease': {
                'handlers': handlers,
                'level': 'DEBUG',
                'propagate': False
            },
            'edx-ora': {
                'handlers': handlers,
                'level': 'DEBUG',
                'propagate': False
            },
        }
    }

    if dev_env:
        edx_file_loc = os.path.join(log_dir, edx_filename)
        logger_config['handlers'].update({
            'local': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filename': edx_file_loc,
                'maxBytes': 1024 * 1024 * 2,
                'backupCount': 5,
            },
        })
    else:
        logger_config['handlers'].update({
            'local': {
                'level': local_loglevel,
                'class': 'logging.handlers.SysLogHandler',
                'address': '/dev/log',
                'formatter': 'syslog_format',
                'facility': SysLogHandler.LOG_LOCAL0,
            },
        })

    return logger_config
