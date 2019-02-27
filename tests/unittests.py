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

dac_list = ["Ibias_Preamp_ON", "Ibias_Preamp_OFF", "VPreamp_NCAS", "Ibias_Ikrum", "Vfbk", "Vthreshold_fine", "Vthreshold_coarse", "Ibias_DiscS1_ON", "Ibias_DiscS1_OFF", "Ibias_DiscS2_ON", "Ibias_DiscS2_OFF", "Ibias_PixelDAC", "Ibias_TPbufferIn", "Ibias_TPbufferOut", "VTP_coarse", "VTP_fine", "Ibias_CP_PLL", "PLL_Vcntrl"]
dac_size_list = [256, 16, 256, 256, 256, 512, 16, 256, 16, 256, 16, 256, 256, 256, 256, 512, 256, 256]
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


    def test_set_DACs_Global(self):
        self.startUp()

        print("Test DAC errors")
        # Test KeyError
        with self.assertRaises(KeyError):
            chip.dacs["WrongDac"] = 1
        with self.assertRaises(KeyError):
            chip.read_dac("WrongDac")
        # Test ValueErrors
        for dac in range(18):
            with self.assertRaises(ValueError):
                chip.dacs[dac_list[dac]] = -1
            with self.assertRaises(ValueError):
                chip.dacs[dac_list[dac]] = dac_size_list[dac]

        # Test setting DAC values
        print("Test reading and writing DACs")
        pbar = tqdm(total=512*2*18)
        for value in range(512):
            for dac in range(18):
                if value < dac_size_list[dac]:
                    chip.dacs[dac_list[dac]] = value
                    self.assertEqual(value, chip.dacs[dac_list[dac]])
                pbar.update(1)
            chip.write_dacs()
            for dac in range(18):
                if value < dac_size_list[dac]:
                    chip.read_dac(dac_list[dac])
                    fdata = chip['FIFO'].get_data()
                    dout = chip.decode_fpga(fdata, True)
                    self.assertEqual(dac_list[dac], dac_list[dout[len(dout) - 2][4:0].tovalue() - 1])
                    self.assertEqual(value, dout[len(dout) - 2][13:5].tovalue())
                    self.assertEqual(chip.dacs[dac_list[dac]], dout[len(dout) - 2][13:5].tovalue())
                pbar.update(1)
           
        pbar.close()
                
        # Test defaults
        chip.reset_dac_attributes(to_default = True)
        chip.write_dacs()
        pbar = tqdm(total=18)
        for dac in range(18):
            chip.read_dac(dac_list[dac])
            fdata = chip['FIFO'].get_data()
            dout = chip.decode_fpga(fdata, True)
            self.assertEqual(dac_list[dac], dac_list[dout[len(dout) - 2][4:0].tovalue() - 1])
            self.assertEqual(chip.dacs[dac_list[dac]], dout[len(dout) - 2][13:5].tovalue())
            pbar.update(1)
        pbar.close()

if __name__ == "__main__":
    unittest.main()