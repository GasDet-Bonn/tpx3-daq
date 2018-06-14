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
    def test_dacs(self):
        self.assertEqual(test_dacs(),18)
        
@pytest.fixture(scope='module')    
def test_dacs():
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

    logger.info('RX ready:', chip['RX'].is_ready)
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
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x71)
    logger.info("End of Command",ddout)
    try:
        ddout = chip.decode(dout[1], 0x71)
        logger.info("End of Command",ddout)
    except IndexError:
        logger.info("no EoR found")

    # now set some random DACS to different values than default
    chip.dacs["VTP_coarse"] = 11
    logger.info("Set VTP_coarse:11")
    chip.dacs["VTP_fine"] = 131
    logger.info("Set VTP_fine:131")
    
    # assert wrong values
    try:
        chip.dacs["WrongDac"] = 1
    except KeyError:
        logger.info("Wrong DAC check passed")
    try:
        chip.dacs["VTP_coarse"] = -1
    except ValueError:
        logger.info("Negative value check passed")
    try:
        chip.dacs["VTP_coarse"] = 1000000000000000000
    except ValueError:
        logger.info("Too large value check passed")

    # after setting them, write them
    chip.write_dacs()

    # now read them back
    # NOTE: this check needs to be done by eye for now
    # TODO: fix that!
    counter=chip.read_dacs()
    logger.info(chip.read_dacs())
    return counter

if __name__ == "__main__":
    test_dacs()
