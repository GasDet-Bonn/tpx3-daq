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
import logging

class TestSim(unittest.TestCase):
    def setUp(self):

        extra_defines = []

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ../

        tpx3_src = os.getenv("TPX3_SRC")
        if not tpx3_src:
            raise Exception("Set TPX3_SRC variable. Point to TPX3 source direcotry!")

        cocotb_compile_and_run(
            sim_files=[root_dir + "/tests/tpx3_tb.v"],
            extra_defines=extra_defines,
            # sim_bus = 'basil.utils.sim.SiLibUsbBusDriver',
            include_dirs=(root_dir, root_dir + "/firmware/src", tpx3_src),
            extra="\nVSIM_ARGS += -t 1ps -wlf /tmp/tpx3-daq.wlf\n",
        )

        with open(root_dir + "/tpx3/tpx3.yaml", "r") as f:
            cnfg = yaml.load(f)

        cnfg["transfer_layer"][0]["type"] = "SiSim"
        cnfg["transfer_layer"][0]["init"]["port"] = 12345
        cnfg["transfer_layer"][0]["init"]["host"] = "localhost"

        self.chip = TPX3(conf=cnfg)

    def wait_sim(self, how_long=10):
        for _ in range(how_long):
            self.chip["CONTROL"].write()

    def test(self):
        self.chip.init()

        self.chip["CONTROL"]["RESET"] = 1
        self.chip["CONTROL"].write()
        self.chip["CONTROL"]["RESET"] = 0
        self.chip["CONTROL"].write()

        self.chip.PLLConfigs["bypass"] = 0
        self.chip.PLLConfigs["dualedge"] = 0

        data = self.chip.write_pll_config(write=False)
        self.chip.write(data)

        self.chip.outputBlocks["clk_readout_src"] = 0b001
        self.chip.outputBlocks["ClkOut_frequency_src"] = 0b001
        data = self.chip.write_outputBlock_config(write=False)
        self.chip.write(data)

        self.wait_sim()

        self.chip["RX"].reset()
        self.chip["RX"].DATA_DELAY = 21
        self.chip["RX"].ENABLE = 1
        self.chip["RX"].INVERT = 0
        self.chip["RX"].SAMPLING_EDGE = 0
        time.sleep(0.01)

        fdata = self.chip["FIFO"].get_data()

        data = self.chip.reset_sequential(False)
        self.chip.write(data, True)
        self.wait_sim()
        fdata = self.chip["FIFO"].get_data()
        logging.info("fdata : %s" % (str(fdata)))
        dout = self.chip.decode_fpga(fdata, True)
        logging.info("dout : %s" % (str(dout)))
        ddout = self.chip.decode(dout[0], 0x71)
        logging.info("ddout : %s" % (str(ddout)))
        
        data = self.chip.read_dac("Vfbk")
        self.wait_sim()
        fdata = self.chip["FIFO"].get_data()
        dout = self.chip.decode_fpga(fdata, True)
        logging.info("Vfbk : %s" % (str(dout)))

        data = self.chip.read_periphery_template("EFuse_Read")
        data += [0x00] * 32
        self.chip.write(data)
        self.wait_sim()
        fdata = self.chip["FIFO"].get_data()
        dout = self.chip.decode_fpga(fdata, True)
        logging.info("EFuse_Read : %s" % (str(dout)))
        

    def tearDown(self):
        self.chip.close()
        time.sleep(2)
        cocotb_compile_clean()


if __name__ == "__main__":
    unittest.main()
