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

    # Step 2: Chip start-up sequence
    # Step 2a: Reset the chip
    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()
    chip['CONTROL']['RESET'] = 0
    chip['CONTROL'].write()

    # Step 2b: Enable power pulsing
    chip['CONTROL']['EN_POWER_PULSING'] = 1
    chip['CONTROL'].write()

    # Step 2c: Reset the Timer
    data = chip.getGlobalSyncHeader() + [0x40] + [0x0]
    chip.write(data)
    
    # Step 2d: Start the Timer
    data = chip.getGlobalSyncHeader() + [0x4A] + [0x0]
    chip.write(data)

    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 0
    chip['RX'].ENABLE = 1
    time.sleep(0.01)

    logger.info(chip['RX'].is_ready,":Receiver Ready")
    logger.info('get_decoder_error_counter', chip['RX'].get_decoder_error_counter())

    data = chip.getGlobalSyncHeader() + [0x10] + [0b10101010, 0x01] + [0x0]
    chip.write(data)

    logger.info('RX ready:', chip['RX'].is_ready)

    logger.info(chip.get_configuration())

    # Step 2e: reset sequential / resets pixels?!
    # before setting PCR need to reset pixel matrix
    data = chip.reset_sequential(False)
    chip.write(data, True)
    fdata = chip['FIFO'].get_data()
    #print fdata
    dout = chip.decode_fpga(fdata, True)
    #print dout
    ddout = chip.decode(dout[0], 0x71)
    logger.info(ddout)
    #try:
        #ddout = chip.decode(dout[1], 0x71)
        #print ddout
    #except IndexError:
        #print("no EoR found")
    chip.reset_config_attributes()
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
