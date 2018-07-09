#!/usr/bin/env python
''' Entry point to simplify the usage from command line for
the online_monitor with bdaq53 plugins. Not really needed
start_online_monitor config.yaml would also work...
'''
import sys
import os
import subprocess
import logging

import psutil
from PyQt5 import Qt

from online_monitor.OnlineMonitor import OnlineMonitorApplication
from online_monitor.utils import utils


def run_script_in_shell(script, arguments, command=None):
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        creationflags = 0
    return subprocess.Popen("%s %s %s" % ('python' if not command else command, script, arguments),
                            shell=True, creationflags=creationflags)


def main():
    if sys.argv[1:]:
        args = utils.parse_arguments()
    else:  # no config yaml provided -> start online monitor with std. settings
        class Dummy(object):
            def __init__(self):
                folder = os.path.dirname(os.path.realpath(__file__))
                self.config_file = os.path.join(folder, r'tpx3_monitor.yaml')
                self.log = 'INFO'
        args = Dummy()
        logging.info('No configuration file provided! Use std. settings!')

    utils.setup_logging(args.log)

    # Start the converter
    run_script_in_shell('', args.config_file, 'start_online_monitor')


if __name__ == '__main__':
    main()
