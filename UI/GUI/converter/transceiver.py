#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# Based on: https://github.com/SiLab-Bonn/online_monitor
# ------------------------------------------------------------
#

import multiprocessing
import threading
import zmq
import logging
import signal
import psutil
import queue as queue
from UI.GUI.converter import utils

class Transceiver(multiprocessing.Process):

    '''Every converter is a transceiver.
    The transceiver connects a data source / multiple data sources
    (e.g. DAQ systems, other converter, ...) and interprets the data according
    to the specified data type.
    Usage:
    To specify a converter for a certain data type, inherit from this base
    class and define these methods accordingly:
        - setup_interpretation()
        - deserialize_data()
        - interpret_data()
        - serialize_data()
    New methods/objects that are not called/created within these function will
    not work! Since a new process is created that only knows the objects
    (and functions) defined there.
    Parameter
    ----------
    frontend_address : str
        Address where the converter publishes the converted data
    kind : str
        String describing the kind of converter (e.g. forwarder)
    max_buffer : number
        Maximum messages buffered for interpretation, if exceeded
        data is discarded. If None no limit is applied.
    loglevel : str
        The verbosity level for the logging (e.g. INFO, WARNING)
    '''

    def __init__(self, frontend, kind, data_queue, symbol_pipe, chip_links, name='Undefined',
                 max_buffer=None, loglevel='INFO', **kwarg):
        multiprocessing.Process.__init__(self)

        self.kind = kind  # kind of transeiver (e.g. forwarder)
        self.frontend_address = frontend  # socket facing a data publisher
        # Maximum number of input messages buffered, otherwise data omitted
        self.max_buffer = max_buffer
        self.name = name  # name of the DAQ/device
        # Std. setting is unidirectional frondend communication
        self.frontend_socket_type = zmq.SUB

        self.data_queue = data_queue
        self.symbol_pipe = symbol_pipe
        self.run_data_queue_symbol = True

        self.chip_links = chip_links

        if 'max_cpu_load' in kwarg:
            logging.warning('The parameter max_cpu_load is deprecated! Use max_buffer!')

        self.config = kwarg

        # Determine how many frontends the converter has
        # just one frontend socket given
        if not isinstance(self.frontend_address, list):
            self.frontend_address = [self.frontend_address]
            self.n_frontends = 1
        else:
            self.n_frontends = len(self.frontend_address)

        self.exit = multiprocessing.Event()  # exit signal

        self.loglevel = loglevel
        utils.setup_logging(self.loglevel)

        logging.debug("Initialize %s converter %s with frontends %s ",
                      self.kind, self.name, self.frontend_address)

    def _setup_frontend(self):
        ''' Receiver sockets facing clients (DAQ systems)
        '''
        self.frontends = []
        self.fe_poller = zmq.Poller()
        for actual_frontend_address in self.frontend_address:
            # Subscriber or server socket
            actual_frontend = (actual_frontend_address,
                               self.context.socket(self.frontend_socket_type))
            # Wait 0.5 s before termating socket
            actual_frontend[1].setsockopt(zmq.LINGER, 500)
            # Buffer only 10 meassages, then throw data away
            actual_frontend[1].set_hwm(10)
            # A suscriber has to set to not filter any data
            if self.frontend_socket_type == zmq.SUB:
                actual_frontend[1].setsockopt_string(zmq.SUBSCRIBE, u'')
            actual_frontend[1].connect(actual_frontend_address)
            self.frontends.append(actual_frontend)
            self.fe_poller.register(actual_frontend[1], zmq.POLLIN)
        self.raw_data = queue.Queue()
        self.fe_stop = threading.Event()

    def _setup_transceiver(self):
        # ignore SIGTERM; signal shutdown() is used for controlled proc. term.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        # Setup ZeroMQ connections, has to be within run;
        # otherwise ZMQ does not work
        self.context = zmq.Context()

        self._setup_frontend()

    def recv_data(self):
        while not self.fe_stop.is_set():
            self.fe_poller.poll(1)  # max block 1 ms
            raw_data = []
            # Loop over all frontends
            for actual_frontend in self.frontends:
                try:
                    actual_raw_data = actual_frontend[1].recv(flags=zmq.NOBLOCK)
                    raw_data.append((actual_frontend[0],
                                     self.deserialize_data(actual_raw_data)))
                except zmq.Again:  # no data
                    pass
            if raw_data:
                self.raw_data.put_nowait(raw_data)

    def run(self):  # the Receiver loop run in extra process
        utils.setup_logging(self.loglevel)
        self._setup_transceiver()
        self.setup_interpretation()

        process = psutil.Process(self.ident)  # access this process info
        self.cpu_load = 0.

        fe_thread = threading.Thread(target=self.recv_data)
        fe_thread.start()

        logging.debug("Start %s transceiver %s", self.kind, self.name)
        while not self.exit.wait(0.01):
            if self.raw_data.empty():
                continue
            else:
                raw_data = self.raw_data.get_nowait()

            actual_cpu_load = process.cpu_percent()
            # Filter cpu load by running mean since it changes rapidly;
            # cpu load spikes can be filtered away since data queues up
            # through ZMQ
            self.cpu_load = 0.90 * self.cpu_load + 0.1 * actual_cpu_load
            # Check if already too many messages queued up then omit data
            if not self.max_buffer or self.max_buffer > self.raw_data.qsize():
                self.interpret_data(raw_data)
            else:
                logging.warning('Converter cannot keep up, omitting data for interpretation!')

        self.fe_stop.set()
        fe_thread.join()
        # Close connections
        for actual_frontend in self.frontends:
            actual_frontend[1].close()
        self.context.term()

        logging.debug("Close %s transceiver %s", self.kind, self.name)

    def shutdown(self):
        self.exit.set()
