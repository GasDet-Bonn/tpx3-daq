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
import os
import yaml

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

        # set up chip_links dictionary, TODO: maybe replace later with values from data_logger

        # Get link configuration
        working_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        file_name   = os.path.join(working_dir, 'tpx3' + os.sep + 'links.yml')
        '''
        with open(file_name, 'r') as file:
            links_dict  = yaml.load(file, Loader = yaml.FullLoader)

        chip_IDs = [register['chip-id'] for register in links_dict['registers']]

        # Create dictionary of Chips and the links they are connected to
        self.chip_links = {}
    
        for link, ID in enumerate(chip_IDs):
            if ID not in self.chip_links:
                self.chip_links[ID] = [link]
            else:
                self.chip_links[ID].append(link)
        '''
        #self.chip_links = {'W12-K7': [0,1,2,3], 'W13-K8': [4,5,6,7]}
        #self.chip_links = {'W12-K7': [0,1], 'W13-K8': [2,3], 'W14-K9': [4,5], 'W15-K6': [6,7]}
        self.chip_links = {'W12-K7': [0], 'W13-K8': [2], 'W14-K9': [4], 'W15-K6': [6],
                            'W11-K1': [1], 'W16-K2': [3], 'W17-K3': [5], 'W18-K4': [7]}

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
            converter = Tpx3(data_queue = self.data_queue, symbol_pipe = self.symbol_pipe, chip_links = self.chip_links, *(), **converter_settings)
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