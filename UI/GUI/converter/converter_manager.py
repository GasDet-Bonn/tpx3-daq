#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# Based on: https://github.com/SiLab-Bonn/online_monitor
# ------------------------------------------------------------
#

import logging
import time
import psutil
import sys

from UI.GUI.converter.transceiver import Transceiver
from UI.GUI.converter import utils
from UI.GUI.converter.tpx3_inter import Tpx3

class ConverterManager(object):
    def __init__(self, configuration, data_queue, symbol_pipe, loglevel='INFO'):
        self.data_queue = data_queue
        self.symbol_pipe = symbol_pipe
        utils.setup_logging(loglevel)
        logging.info("Initialize converter mananager with configuration in %s", configuration)
        self.configuration = utils.parse_config_file(configuration)

    def start(self):
        try:
            self.configuration['converter']
        except KeyError:
            logging.info('No converters defined in config file')
            logging.info('Close converter manager')
            return
        logging.info('Starting %d converters', len(self.configuration['converter']))
        converters, process_infos = [], []

        for (converter_name, converter_settings) in self.configuration['converter'].items():
            converter_settings['name'] = converter_name
            converter = Tpx3(data_queue = self.data_queue, symbol_pipe = self.symbol_pipe, *(), **converter_settings)
            converter.start()
            process_infos.append((converter_name, psutil.Process(converter.ident)))
            converters.append(converter)
        try:
            while True:
                time.sleep(2)
        except:
            logging.info('Shutting down %d converters', len(self.configuration['converter']))
            for converter in converters:
                converter.shutdown()

        for converter in converters:
            converter.join()
        logging.info('Close converter manager')