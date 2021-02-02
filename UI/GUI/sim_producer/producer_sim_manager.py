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
from UI.GUI.sim_producer.producer_sim import ProducerSim
from UI.GUI.converter import utils
from UI.GUI.sim_producer.tpx3_sim import Tpx3Sim

class ProducerSimManager(object):
    def __init__(self, configuration, path, loglevel='INFO', delay = 0.1, kind='Test', name='Undefined'):
        utils.setup_logging(loglevel)
        logging.info("Initialize producer simulation mananager")
        self.configuration = utils.parse_config_file(configuration)
        self.data_file = path
        self.loglevel = loglevel
        self.delay = delay
        self.kind = kind
        self.name = name

    def start(self):
        try:
            self.configuration['converter']
        except KeyError:
            logging.info('Backend not defined in config file')
            logging.info('Close producer simulation manager')
            return
        backend = self.configuration['converter']['TPX3Converter']['frontend']
        logging.info('Starting %d producer simulations', 1)

        producer_sim = Tpx3Sim(backend = backend, data_file = self.data_file, delay = self.delay, kind = self.kind, name = self.name, loglevel = self.loglevel)
        producer_sim.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info('CRTL-C pressed, shutting down %d producer simulations', 1)
            producer_sim.shutdown()
        except SystemExit:
            logging.info('System exit, shutting down %d producer simulations', 1)
            producer_sim.shutdown()

        producer_sim.join()
        logging.info('Close producer simulation manager')