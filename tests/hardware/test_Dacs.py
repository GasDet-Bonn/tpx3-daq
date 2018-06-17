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
    #chip.startup()
    
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
