#!/usr/bin/env python
import os
import time
import logging
from basil.utils.BitLogic import BitLogic
import unittest

from testConfig import test_config
from testDacs import test_dacs
from testiToTEventCtr import run_test_iToTEventCtr

logger = logging.getLogger(__file__)
bits = BitLogic(40)
bits[39:0]=0

# TODO: what is this file about?

class grouptest(unittest.TestCase):
 
    def setUp(self):
        pass
 
    def test_Config(self):
        self.assertEqual(test_config(0,0,0)[0].tovalue(),72)
    def test_iToTEventCtr(self):
        self.assertEqual(run_test_iToTEventCtr(),1)
    def test_dacs(self):
        self.assertEqual(test_dacs(),18)
 

 
if __name__ == '__main__':
    unittest.main()
