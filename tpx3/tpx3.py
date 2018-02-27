#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import zlib # workaround
import yaml
import logging
import os
import time
import struct
import numpy as np
import tables as tb

import basil

from basil.dut import Dut
from basil.utils.BitLogic import BitLogic


import pkg_resources
VERSION = pkg_resources.get_distribution("tpx3-daq").version

loglevel = logging.INFO

''' Set up main logger '''
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
#logging.getLogger('basil.HL.RegisterHardwareLayer').setLevel(logging.WARNING)

logging.basicConfig(format="%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s")
    
logger = logging.getLogger('tpx3')
logger.setLevel(loglevel)


class TPX3(Dut):
    
    #'' Map hardware IDs for board identification '''
    #hw_map = {
    #    0: 'SIMULATION',
    #    1: 'MIO2',
    #}

    def __init__(self, conf=None, **kwargs):
        
        self.proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if not conf:
            conf = os.path.join(self.proj_dir, 'tpx3' + os.sep + 'tpx3.yaml')

        logger.info("Loading configuration file from %s" % conf)

        super(TPX3, self).__init__(conf)


    def init(self):
        super(TPX3, self).init()

        #self.fw_version, self.board_version = self.get_daq_version()
        #logger.info('Found board %s running firmware version %s' % (self.hw_map[self.board_version], self.fw_version))
        #
        #if self.fw_version != VERSION[:3]:     #Compare only the first two digits
        #    raise Exception("Firmware version %s does not satisfy version requirements %s!)" % ( self.fw_version, VERSION))

        #self['CONF_SR'].set_size(3924)
        

if __name__ == '__main__':
    chip = TPX3()
    chip.init()
    
    for i in range(8):     
        chip['CONTROL']['LED'] = 0
        chip['CONTROL']['LED'][i] = 1
        
        chip['CONTROL'].write()
        time.sleep(0.2)
    
    print('Happy day!')
    
