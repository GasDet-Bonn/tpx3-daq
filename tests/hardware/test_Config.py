#!/usr/bin/env python
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse
import logging
import unittest
import pytest
 

logger = logging.getLogger(__file__)

class grouptest(unittest.TestCase):
 
    def setUp(self):
        pass
 
    def test_Config(self):
        self.assertEqual(test_config(0,0,0)[0].tovalue(),72)
@pytest.fixture(scope='module')    
def test_config(value1, value2, value3):
    # Step 1: Initialize chip & hardware
    chip = TPX3()
    chip.init()
    
    
    # now set some random config bits to different values than default
    logger.info("Switch Polarity:",value1)
    chip._config["Polarity"] = value1
    logger.info("Enable Test pulses:",value2)
    chip._config["TP_en"] = value2
    logger.info("Operating Mode ToA/ToT:",value3)
    chip._config["Op_mode"] = value3
    # assert we wrote the value correctly to the dictionary
    data=chip.write_general_config(False)
    chip.write(data)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x30)
    logger.info(ddout)
    # now read them back
    # NOTE: this check needs to be done by eye for now
    # TODO: fix that!
    data=chip.read_general_config(False)
    chip.write(data)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x31)
    logger.info(ddout)
    return ddout
    
    
if __name__ == "__main__":
    #test_config(0,0,0)
    pass
