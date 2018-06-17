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
    def test_readpcr(self):
        self.assertEqual(test_readpcr(),258)
    

@pytest.fixture(scope='module')    
def test_readpcr():

    chip = TPX3()
    chip.init()
    # Step 5: Set general config
    logger.info("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    

    # Step 2a: reset sequential / resets pixels?!
    data = chip.reset_sequential(False)
    chip.write(data, True)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x71)
    logger.info(ddout)
    try:
        ddout = chip.decode(dout[1], 0x71)
        logger.info(ddout)
    except IndexError:
        logger.info("no EoR found")

    # Step 3: Set PCR
    # Step 3a: Produce needed PCR
    for x in range(256):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 1, 7, 1)

    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)
    logger.info("pixel config sent")
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x71)
    
    # only read column x == 1
    data = chip.read_pixel_config_reg([1], write=False)
    chip.write(data, True)
    logger.info("read pixel config command sent")
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x71)
    
    data = chip.read_pixel_matrix_sequential(0x02, False)
    logger.info("read matrix sequential command sent")
    chip.write(data, True)
    logger.info("waiting for packets received")
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    
    counts = []
    count = 0
    xs = []
    ys = []
    for i in range(len(dout)):
        print("decoding now ", dout[i])
        try:
            ddout = chip.decode(dout[i], 0x90)
            count += 1
            if ddout[0] == "EoC":
                continue
        except ValueError:
            try:
                ddout = chip.decode(dout[i], 0xF0)
                logger.info("Found a stop matrix readout?")
                counts.append(count)
                count = 0
                continue
            except ValueError:
                logger.info("Got value error in decode for data ", dout[i])
                raise
        x = chip.pixel_address_to_x(ddout[0])
        y = chip.pixel_address_to_y(ddout[0])
        # print("X pos {}".format(x))
        # print("Y pos {}".format(y))
        xs.append(x)
        ys.append(y)
        # print(ddout[0].tovalue())

    logger.info("Read {} packages".format(len(dout)))
    logger.info("Found the following counts: ", counts)
    return len(dout)

if __name__ == "__main__":
    test_readpcr()
