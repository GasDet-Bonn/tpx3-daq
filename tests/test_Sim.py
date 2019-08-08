#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#
from __future__ import absolute_import
from __future__ import print_function
from six.moves import range
import unittest
import os
from basil.utils.sim.utils import cocotb_compile_and_run, cocotb_compile_clean
from basil.utils.BitLogic import BitLogic
from tqdm import tqdm
import sys
import yaml
import time
import random
import numpy as np

from tpx3.tpx3 import TPX3
import logging

dac_list = ["Ibias_Preamp_ON", "Ibias_Preamp_OFF", "VPreamp_NCAS", "Ibias_Ikrum", "Vfbk", "Vthreshold_fine", "Vthreshold_coarse", "Ibias_DiscS1_ON", "Ibias_DiscS1_OFF", "Ibias_DiscS2_ON", "Ibias_DiscS2_OFF", "Ibias_PixelDAC", "Ibias_TPbufferIn", "Ibias_TPbufferOut", "VTP_coarse", "VTP_fine", "Ibias_CP_PLL", "PLL_Vcntrl"]
dac_size_list = [256, 16, 256, 256, 256, 512, 16, 256, 16, 256, 16, 256, 256, 256, 256, 512, 256, 256]
config_list = ["Polarity", "Op_mode", "Gray_count_en", "AckCommand_en", "TP_en", "Fast_Io_en", "TimerOverflowControl", "SelectTP_Dig_Analog", "SelectTP_Ext_Int", "SelectTP_ToA_Clk"]
config_size_list = [2, 4, 2, 2, 2, 2, 2, 2, 2, 2]
config_bit_list = [0, 1, 3, 4, 5, 6, 7, 9, 10, 11]

bypass_pll = 0
reset_pll = 1

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
        self.chip.init()

    def wait_sim(self, how_long=10):
        for _ in range(how_long):
            self.chip["CONTROL"].write()

    def startUp(self):
        self.chip["CONTROL"]["RESET"] = 1
        self.chip["CONTROL"].write()
        self.chip["CONTROL"]["RESET"] = 0
        self.chip["CONTROL"].write()

        self.chip['CONTROL']['EN_POWER_PULSING'] = 1
        self.chip['CONTROL'].write()

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

        data = self.chip.reset_sequential(False)
        self.chip.write(data, True)

    def test_set_DACs_Global(self):
        self.startUp()

        logging.info("Test DAC errors")
        # Test KeyError
        with self.assertRaises(KeyError):
            self.chip.dacs["WrongDac"] = 1
        with self.assertRaises(KeyError):
            self.chip.read_dac("WrongDac")
        # Test ValueErrors
        for dac in range(18):
            with self.assertRaises(ValueError):
                self.chip.dacs[dac_list[dac]] = -1
            with self.assertRaises(ValueError):
                self.chip.dacs[dac_list[dac]] = dac_size_list[dac]

        # Test defaults
        self.chip.reset_dac_attributes(to_default = True)
        self.chip.write_dacs()
        pbar = tqdm(total=18)
        for dac in range(18):
            self.chip.read_dac(dac_list[dac])
            self.wait_sim()
            fdata = self.chip['FIFO'].get_data()
            dout = self.chip.decode_fpga(fdata, True)
            self.assertEqual(dac_list[dac], dac_list[dout[len(dout) - 2][4:0].tovalue() - 1])
            self.assertEqual(self.chip.dacs[dac_list[dac]], dout[len(dout) - 2][13:5].tovalue())
            pbar.update(1)
        pbar.close()

        # Test setting DAC values
        logging.info("Test reading and writing DACs")
        if self.chip.PLLConfigs["bypass"] == 0 and self.chip.PLLConfigs["reset"] == 1:
            dac_number_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15]
        else:
            dac_number_list = range(18)
        pbar = tqdm(total=512/2*len(dac_number_list))
        for value in range(0, 512, 4):
            for dac in dac_number_list:
                if value < dac_size_list[dac]:
                    self.chip.dacs[dac_list[dac]] = value
                    self.assertEqual(value, self.chip.dacs[dac_list[dac]])
                pbar.update(1)
            self.chip.write_dacs()
            for dac in dac_number_list:
                if value < dac_size_list[dac]:
                    self.chip.read_dac(dac_list[dac])
                    self.wait_sim()
                    fdata = self.chip['FIFO'].get_data()
                    dout = self.chip.decode_fpga(fdata, True)
                    self.assertEqual(dac_list[dac], dac_list[dout[len(dout) - 2][4:0].tovalue() - 1])
                    self.assertEqual(value, dout[len(dout) - 2][13:5].tovalue())
                    self.assertEqual(self.chip.dacs[dac_list[dac]], dout[len(dout) - 2][13:5].tovalue())
                pbar.update(1)
           
        pbar.close()
    
    def test_pixel_address_functions(self):
        self.startUp()
        logging.info("Test pixel address function errors")
        # Test for errors
        with self.assertRaises(ValueError):
            self.chip.xy_to_pixel_address(256, 0)
        with self.assertRaises(ValueError):
            self.chip.xy_to_pixel_address(0, 256)
        with self.assertRaises(ValueError):
            self.chip.pixel_address_to_x(BitLogic.from_value(0b10000000000000000))
        with self.assertRaises(ValueError):
            self.chip.pixel_address_to_y(BitLogic.from_value(0b10000000000000000))
        
        logging.info("Test pixel address functions")
        # Test for valid addresses
        pbar = tqdm(total=256*256)
        for x in range(256):
            for y in range(256):
                address = self.chip.xy_to_pixel_address(x, y)
                self.assertEquals(x, self.chip.pixel_address_to_x(address))
                self.assertEquals(y, self.chip.pixel_address_to_y(address))
                pbar.update(1)
        pbar.close()

    def test_set_matrix(self):
        self.startUp()

        logging.info("Test PCR function errors")
        # Test for errors
        with self.assertRaises(ValueError):
            self.chip.set_pixel_pcr(256, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            self.chip.set_pixel_pcr(0, 256, 0, 0, 0)
        with self.assertRaises(ValueError):
            self.chip.matrices_to_pcr(256, 0)
        with self.assertRaises(ValueError):
            self.chip.matrices_to_pcr(0, 256)
        with self.assertRaises(ValueError):
            self.chip.set_pixel_pcr(0, 0, 2, 0, 0)
        with self.assertRaises(ValueError):
            self.chip.set_pixel_pcr(0, 0, 0, 16, 0)
        with self.assertRaises(ValueError):
            self.chip.set_pixel_pcr(0, 0, 0, 0, 2)

        # Test writing PCR columnwise
        logging.info("Test reading and writing PCRs")
        iterations = 1
        pbar = tqdm(total = iterations * (2 * 256 * 256 + 2 * 256))
        test = np.zeros((256, 256), dtype=int)
        thr = np.zeros((256, 256), dtype=int)
        mask = np.zeros((256, 256), dtype=int)
        for i in range(iterations):
            for x in range(256):
                for y in range(256):
                    test[x, y] = random.randint(0, 1)
                    thr[x, y] = random.randint(0, 15)
                    mask[x, y] = random.randint(0, 1)
                    self.chip.set_pixel_pcr(x, y, test[x, y], thr[x, y], mask[x, y])
                    pbar.update(1)
            for x in range(256):
                for y in range(256):
                    pcr = self.chip.matrices_to_pcr(x, y)
                    self.assertEquals(test[x, y], int(pcr[5]))
                    self.assertEquals(thr[x, y], pcr[4:1].tovalue())
                    self.assertEquals(mask[x, y], int(pcr[0]))
                    pbar.update(1)
            for i in range(256):
                data = self.chip.write_pcr([i], write=False)
                self.chip.write(data, True)
                pbar.update(1)
            for i in range(256):
                data = self.chip.read_pixel_config_reg([i], write=False)
                self.chip.write(data, True)
                data = self.chip.read_pixel_matrix_sequential(i, False)
                self.chip.write(data, True)
                self.wait_sim()
                fdata = self.chip['FIFO'].get_data()
                dout = self.chip.decode_fpga(fdata, True)
                pbar.update(1)
                for j in range(len(dout)):
                    if(dout[j][47:44].tovalue() == 0x9):
                        x = self.chip.pixel_address_to_x(dout[j][43:28])
                        y = self.chip.pixel_address_to_y(dout[j][43:28])
                        pcr_read = dout[j][19:14]
                        self.assertEquals(test[x, y], int(pcr_read[5]))
                        self.assertEquals(thr[x, y], pcr_read[4] + pcr_read[3] * 2 + pcr_read[2] * 4 + pcr_read[1] * 8)
                        self.assertEquals(mask[x, y], int(pcr_read[0]))
        pbar.close()

    def test_set_ctpr(self):
        self.startUp()
        logging.info("Test CTPR errors")
        # Test for errors
        with self.assertRaises(ValueError):
            self.chip.write_ctpr(list(range(257)), False)
        with self.assertRaises(ValueError):
            self.chip.write_ctpr(list(range(257, 256, -1)), False)
        
        # Test values
        logging.info("Test reading and writing CTPR")
        pbar = tqdm(total = 256)
        for column in range(256):
            data = self.chip.write_ctpr([column], False)
            self.chip.write(data, True)
            self.wait_sim(10)
            fdata = self.chip['FIFO'].get_data()
            dout = self.chip.decode_fpga(fdata, True)
            data = self.chip.read_ctpr(False)
            self.chip.write(data, True)
            self.wait_sim(10)
            fdata = self.chip['FIFO'].get_data()
            dout = self.chip.decode_fpga(fdata, True)
            pbar.update(1)
            for j in range(len(dout)):
                if(dout[j][47:44].tovalue() == 0xD):
                    if dout[j][1:0].tovalue() != 0:
                        self.assertEquals(column, dout[j][43:37].tovalue() * 2 + int(dout[j][1]))
        pbar.close()

    def test_general_config(self):
        self.startUp()

        logging.info("Test general config")
        # Test errors
        with self.assertRaises(KeyError):
            self.chip.configs["WrongConfig"] = 1
        # Test ValueErrors
        for config in range(10):
            with self.assertRaises(ValueError):
                self.chip.configs[config_list[config]] = -1
            with self.assertRaises(ValueError):
                self.chip.configs[config_list[config]] = config_size_list[config]

        # Test values
        pbar = tqdm(total = 4 * 10)
        for value in range(4):
            for config in range(10):
                if value < config_size_list[config]:
                    self.chip.configs[config_list[config]] = value
            data = self.chip.write_general_config(False)
            self.chip.write(data)
            self.wait_sim(10)
            data = self.chip.read_general_config(False)
            self.chip.write(data)
            self.wait_sim(10)
            fdata = self.chip['FIFO'].get_data()
            dout = self.chip.decode_fpga(fdata, True)
            for config in range(10):
                if value < config_size_list[config]:
                    self.assertEquals(value, self.chip.configs[config_list[config]])
                if config == 1:
                    self.assertEquals(self.chip.configs[config_list[config]], dout[len(dout) - 2][2:1].tovalue())
                else:
                    self.assertEquals(self.chip.configs[config_list[config]], int(dout[len(dout) - 2][config_bit_list[config]]))
                pbar.update(1)
        pbar.close()

        # Test defaults
        self.chip.reset_config_attributes(to_default = True)
        data = self.chip.write_general_config(False)
        self.chip.write(data)
        self.wait_sim(10)
        data = self.chip.read_general_config(False)
        self.chip.write(data)
        self.wait_sim(10)
        fdata = self.chip['FIFO'].get_data()
        dout = self.chip.decode_fpga(fdata, True)
        pbar = tqdm(total=10)
        for config in range(10):
            if config == 1:
                self.assertEquals(self.chip.configs[config_list[config]], dout[len(dout) - 2][2:1].tovalue())
            else:
                self.assertEquals(self.chip.configs[config_list[config]], int(dout[len(dout) - 2][config_bit_list[config]]))
            pbar.update(1)
        pbar.close()

    def test_testpulse(self):
        self.startUp()

        logging.info("Test testpulse config")
        # Test errors
        with self.assertRaises(ValueError):
            self.chip.write_tp_pulsenumber(65536, False)
        with self.assertRaises(ValueError):
            self.chip.write_tp_period(256, 0, False)
        with self.assertRaises(ValueError):
            self.chip.write_tp_period(0, 16, False)

        # Test default (@reset)
        data = self.chip.read_tp_config(False)
        self.chip.write(data)
        self.wait_sim()
        fdata = self.chip['FIFO'].get_data()
        dout = self.chip.decode_fpga(fdata, True)
        self.assertEquals(0, dout[len(dout) - 2][27:0].tovalue())

        # Test values
        pbar = tqdm(total = 65536/64 + 256 + 16)
        for i in range(0, 65536, 64):
            data = self.chip.write_tp_pulsenumber(i, False)
            self.chip.write(data)
            self.wait_sim()
            data = self.chip.read_tp_config(False)
            self.chip.write(data)
            self.wait_sim()
            fdata = self.chip['FIFO'].get_data()
            dout = self.chip.decode_fpga(fdata, True)
            self.assertEquals(i, dout[len(dout) - 2][15:0].tovalue())
            pbar.update(1)
        for i in range(256):
            data = self.chip.write_tp_period(i, 0, False)
            self.chip.write(data)
            self.wait_sim()
            data = self.chip.read_tp_config(False)
            self.chip.write(data)
            self.wait_sim()
            fdata = self.chip['FIFO'].get_data()
            dout = self.chip.decode_fpga(fdata, True)
            self.assertEquals(i, dout[len(dout) - 2][23:16].tovalue())
            pbar.update(1)
        for i in range(16):
            data = self.chip.write_tp_period(0, i, False)
            self.chip.write(data)
            self.wait_sim()
            data = self.chip.read_tp_config(False)
            self.chip.write(data)
            self.wait_sim()
            fdata = self.chip['FIFO'].get_data()
            dout = self.chip.decode_fpga(fdata, True)
            self.assertEquals(i, dout[len(dout) - 2][27:24].tovalue())
            pbar.update(1)
        pbar.close()
        

    def tearDown(self):
        self.chip.close()
        time.sleep(2)
        cocotb_compile_clean()


if __name__ == "__main__":
    unittest.main()
