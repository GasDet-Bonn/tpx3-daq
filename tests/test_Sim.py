#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import unittest
import os
from basil.utils.sim.utils import cocotb_compile_and_run, cocotb_compile_clean
import sys
import yaml
import time

from tpx3.tpx3 import TPX3

# Causes that the print statement in Python 2.7 is deactivated and
# only the print() function is available
from __future__ import print_function


class TestSim(unittest.TestCase):

    def setUp(self):

        extra_defines = []

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ../
        print(root_dir)
        cocotb_compile_and_run(
            sim_files=[root_dir + '/tests/tpx3_tb.v'],
            extra_defines=extra_defines,
            # sim_bus = 'basil.utils.sim.SiLibUsbBusDriver',
            include_dirs=(root_dir, root_dir + "/firmware/src")
        )

        with open(root_dir + '/tpx3/tpx3.yaml', 'r') as f:
            cnfg = yaml.load(f)

        cnfg['transfer_layer'][0]['type'] = 'SiSim'
        cnfg['transfer_layer'][0]['init']['port'] = 12345
        cnfg['transfer_layer'][0]['init']['host'] = 'localhost'

        self.dut = TPX3(conf=cnfg)

    def test(self):
        self.dut.init()

        self.dut['CONTROL']['RESET'] = 1
        self.dut['CONTROL'].write()
        self.dut['CONTROL']['RESET'] = 0
        self.dut['CONTROL'].write()

        self.dut['SPI'].set_size(125)  # in bits

        self.dut['SPI'].set_data(range(64))
        self.dut['SPI'].start()
        while(not self.dut['SPI'].is_ready):
            pass

        self.dut['CONTROL']['CNT_FIFO_EN'] = 1
        self.dut['CONTROL'].write()

        self.dut['CONTROL']['CNT_FIFO_EN'] = 0
        self.dut['CONTROL'].write()

        fdata = self.dut['FIFO'].get_data()
        assert len(fdata) != 0

        for i in range(20):
            self.dut['RX'].READY

        fdata = self.dut['FIFO'].get_data()
        for i in fdata:
            print((i & 0x01000000) != 0, hex(i & 0xffffff))

    def tearDown(self):
        self.dut.close()
        time.sleep(1)
        cocotb_compile_clean()

if __name__ == '__main__':
    unittest.main()
