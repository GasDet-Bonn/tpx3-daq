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
 
    def test_ChipID(self):
        self.assertEqual(test_chipID()[0].tovalue(),0)

@pytest.fixture(scope='module')    
def test_chipID():
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
    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 0
    chip['RX'].ENABLE = 1
    time.sleep(0.01)

    logger.info (chip['RX'].is_ready,":Receiver Ready")

    
    #print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()

    data = chip.getGlobalSyncHeader() + [0x10] + [0b10101010, 0x01] + [0x0]
    chip.write(data)

    #assertTrue(chip['RX'].is_ready," Receiver Ready")
    logger.info(chip.get_configuration())

    # Step 2e: reset sequential / resets pixels?!
    # before setting PCR need to reset pixel matrix
    data = chip.reset_sequential(False)
    chip.write(data, True)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x71)
    logger.info("Received EoR:",ddout)
    try:
        ddout = chip.decode(dout[1], 0x71)
        logger.info("Received EoR:",ddout)
    except IndexError:
        logger.warning("no EoR found")

    # Step 3: Set PCR
    # Step 3a: Produce needed PCR
    for x in range(256):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 0, 7, 1)
    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)

    # Step 4: Set general config
    logger.info("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)

    chip['FIFO'].reset()

    """
    Explanation for the determination of this chips ChipID:
    The idea is to send a valid command using a local chip header with a
    chip ID different from the one the chip has. According to the manual
    page 29 of manual v1.9, a chip will send the `OtherChipCommand` containing
    its own ChipID. So therefore we send the SenseDACsel command, which with
    a local chip ID of 0x01. The chip correctly answers with an OtherChipCommand,
    but containing the chip ID with all 0s...
    """

    data = chip.read_periphery_template("SenseDACsel", local_header = True)
    chip.write(data, False)

    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    logger.info("Fdata is ", fdata)
    logger.info("dout is {} and its length {}".format(dout, len(dout)))

    ddout = chip.decode(dout[0], 0x72)
    # ddout1 = chip.decode(dout[1], 0x00)
    logger.info("Output is:",ddout)
    return ddout
    #print("ddout is ", ddout)
    # print("ddout1 is ", ddout1)



if __name__ == "__main__":
    test_chipID()
