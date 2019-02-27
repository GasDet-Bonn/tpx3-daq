#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function
from six.moves import range
from tpx3.tpx3 import TPX3
from basil.utils.BitLogic import BitLogic
from tqdm import tqdm
import time
import unittest
import random
import numpy as np

chip = TPX3()
chip.init()

class Test(unittest.TestCase):
    def startUp(self):
        chip['CONTROL']['RESET'] = 1
        chip['CONTROL'].write()
        chip['CONTROL']['RESET'] = 0
        chip['CONTROL'].write()

        chip['CONTROL']['EN_POWER_PULSING'] = 1
        chip['CONTROL'].write()

        data = chip.getGlobalSyncHeader() + [0x40] + [0x0]
        chip.write(data)

        data = chip.getGlobalSyncHeader() + [0x4A] + [0x0]
        chip.write(data)

        chip['RX'].reset()
        chip['RX'].DATA_DELAY = 0
        chip['RX'].ENABLE = 1
        time.sleep(0.01)

        data = chip.write_outputBlock_config(write=False)
        chip.write(data)
        data = chip.write_pll_config(bypass=0, reset=1, selectVctl=1, dualedge=1, clkphasediv=1, clkphasenum=0, PLLOutConfig=0, write=False)
        chip.write(data)

        data = chip.reset_sequential(False)
        chip.write(data, True)
        fdata = chip['FIFO'].get_data()

if __name__ == "__main__":
    unittest.main()