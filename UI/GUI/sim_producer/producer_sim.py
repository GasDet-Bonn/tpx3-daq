#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# Based on: https://github.com/SiLab-Bonn/online_monitor
# ------------------------------------------------------------
#

import multiprocessing
import zmq
import logging
import signal
import time
from UI.GUI.converter import utils

class ProducerSim(multiprocessing.Process):
    ''' For testing we have to generate some random data to fake a DAQ. This is done with this Producer Simulation'''
    def __init__(self, backend, data_file, delay = 0.1, kind='Test', name='Undefined', loglevel='INFO'):
        multiprocessing.Process.__init__(self)

        self.backend_address = backend
        self.name = name  # name of the DAQ/device
        self.kind = kind
        self.delay = delay
        self.data_file = data_file

        self.loglevel = loglevel
        self.exit = multiprocessing.Event()  # exit signal
        utils.setup_logging(loglevel)

        logging.debug("Initialize %s producer %s at %s", self.kind, self.name, self.backend_address)

    def setup_producer_device(self):
        # ignore SIGTERM; signal shutdown() is used for controlled process termination
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        # Setup ZeroMQ connetions, has to be within run; otherwise ZMQ does not work
        self.context = zmq.Context()
        # Send socket facing services (e.g. online monitor)
        self.sender = self.context.socket(zmq.PUB)
        self.sender.bind(self.backend_address)

    def run(self):  # The receiver loop running in extra process; is called after start() method
        utils.setup_logging(self.loglevel)
        logging.debug("Start %s producer %s at %s", self.kind, self.name, self.backend_address)

        self.setup_producer_device()

        while not self.exit.wait(0.02):
            self.send_data()

        ## Close connections
        self.sender.close()
        self.context.term()
        logging.debug("Close %s producer %s at %s", self.kind, self.name, self.backend_address)

    def shutdown(self):
        self.exit.set()
