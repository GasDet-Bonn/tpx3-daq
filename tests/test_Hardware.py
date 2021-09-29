#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
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
config_list = ["Polarity", "Op_mode", "Gray_count_en", "AckCommand_en", "TP_en", "Fast_Io_en", "TimerOverflowControl", "SelectTP_Dig_Analog", "SelectTP_Ext_Int", "SelectTP_ToA_Clk"]
config_size_list = [2, 4, 2, 2, 2, 2, 2, 2, 2, 2]
config_bit_list = [0, 1, 3, 4, 5, 6, 7, 9, 10, 11]

bypass_pll = 0
reset_pll = 1

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

        chip['RX0'].reset()
        chip['RX0'].DATA_DELAY = 21
        chip['RX0'].ENABLE = 1
        chip['RX0'].INVERT = 0
        chip['RX0'].SAMPLING_EDGE = 0
        time.sleep(0.01)

        data = chip.write_pll_config(write=False)
        chip.write(data)
        data = chip.write_outputBlock_config(write=False)
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

        # Test setting DAC values
        print("Test reading and writing DACs")
        if chip.PLLConfigs["bypass"] == 0 and chip.PLLConfigs["reset"] == 1:
            dac_number_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15]
        else:
            dac_number_list = range(18)
        pbar = tqdm(total=512*2*len(dac_number_list))
        for value in range(512):
            for dac in dac_number_list:
                if value < dac_size_list[dac]:
                    chip.dacs[dac_list[dac]] = value
                    self.assertEqual(value, chip.dacs[dac_list[dac]])
                pbar.update(1)
            chip.write_dacs()
            for dac in dac_number_list:
                if value < dac_size_list[dac]:
                    chip.read_dac(dac_list[dac])
                    fdata = chip['FIFO'].get_data()
                    dout = chip.decode_fpga(fdata, True)
                    self.assertEqual(dac_list[dac], dac_list[dout[len(dout) - 2][4:0].tovalue() - 1])
                    self.assertEqual(value, dout[len(dout) - 2][13:5].tovalue())
                    self.assertEqual(chip.dacs[dac_list[dac]], dout[len(dout) - 2][13:5].tovalue())
                pbar.update(1)
           
        pbar.close()


    def test_pixel_address_functions(self):
        self.startUp()
        print("Test pixel address function errors")
        # Test for errors
        with self.assertRaises(ValueError):
            chip.xy_to_pixel_address(256, 0)
        with self.assertRaises(ValueError):
            chip.xy_to_pixel_address(0, 256)
        with self.assertRaises(ValueError):
            chip.pixel_address_to_x(BitLogic.from_value(0b10000000000000000))
        with self.assertRaises(ValueError):
            chip.pixel_address_to_y(BitLogic.from_value(0b10000000000000000))
        
        print("Test pixel address functions")
        # Test for valid addresses
        pbar = tqdm(total=256*256)
        for x in range(256):
            for y in range(256):
                address = chip.xy_to_pixel_address(x, y)
                self.assertEqual(x, chip.pixel_address_to_x(address))
                self.assertEqual(y, chip.pixel_address_to_y(address))
                pbar.update(1)
        pbar.close()


    def test_set_matrix(self):
        self.startUp()

        print("Test PCR function errors")
        # Test for errors
        with self.assertRaises(ValueError):
            chip.set_pixel_pcr(256, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            chip.set_pixel_pcr(0, 256, 0, 0, 0)
        with self.assertRaises(ValueError):
            chip.matrices_to_pcr(256, 0)
        with self.assertRaises(ValueError):
            chip.matrices_to_pcr(0, 256)
        with self.assertRaises(ValueError):
            chip.set_pixel_pcr(0, 0, 2, 0, 0)
        with self.assertRaises(ValueError):
            chip.set_pixel_pcr(0, 0, 0, 16, 0)
        with self.assertRaises(ValueError):
            chip.set_pixel_pcr(0, 0, 0, 0, 2)

        # Test writing PCR columnwise
        print("Test reading and writing PCRs")
        iterations = 5
        pbar = tqdm(total = iterations * (2 * 256 * 256 + 2 * 256))
        test = np.zeros((256, 256), dtype=int)
        thr = np.zeros((256, 256), dtype=int)
        mask = np.zeros((256, 256), dtype=int)
        broken_pixels = []
        for i in range(iterations):
            for x in range(256):
                for y in range(256):
                    test[x, y] = random.randint(0, 1)
                    thr[x, y] = random.randint(0, 15)
                    mask[x, y] = random.randint(0, 1)
                    chip.set_pixel_pcr(x, y, test[x, y], thr[x, y], mask[x, y])
                    pbar.update(1)
            for x in range(256):
                for y in range(256):
                    pcr = chip.matrices_to_pcr(x, y)
                    self.assertEqual(test[x, y], int(pcr[5]))
                    self.assertEqual(thr[x, y], pcr[4:1].tovalue())
                    self.assertEqual(mask[x, y], int(pcr[0]))
                    pbar.update(1)
            for i in range(256):
                data = chip.write_pcr([i], write=False)
                chip.write(data, True)
                pbar.update(1)
            for i in range(256):
                data = chip.read_pixel_config_reg([i], write=False)
                chip.write(data, True)
                data = chip.read_pixel_matrix_sequential(i, False)
                chip.write(data, True)
                fdata = chip['FIFO'].get_data()
                dout = chip.decode_fpga(fdata, True)
                pbar.update(1)
                for j in range(len(dout)):
                    if(dout[j][47:44].tovalue() == 0x9):
                        x = chip.pixel_address_to_x(dout[j][43:28])
                        y = chip.pixel_address_to_y(dout[j][43:28])
                        pcr_read = dout[j][19:14]
                        if test[x, y] != int(pcr_read[5]):
                            if dout[j][43:28] not in broken_pixels:
                                broken_pixels.append(dout[j][43:28])
                            continue
                        if thr[x, y] != pcr_read[4] + pcr_read[3] * 2 + pcr_read[2] * 4 + pcr_read[1] * 8:
                            if dout[j][43:28] not in broken_pixels:
                                broken_pixels.append(dout[j][43:28])
                            continue
                        if mask[x, y] != int(pcr_read[0]):
                            if dout[j][43:28] not in broken_pixels:
                                broken_pixels.append(dout[j][43:28])
                            continue

                        self.assertEqual(test[x, y], int(pcr_read[5]))
                        self.assertEqual(thr[x, y], pcr_read[4] + pcr_read[3] * 2 + pcr_read[2] * 4 + pcr_read[1] * 8)
                        self.assertEqual(mask[x, y], int(pcr_read[0]))
        pbar.close()

        for i in range(len(broken_pixels)):
            print("Pixel %i/%i is broken" % (chip.pixel_address_to_x(broken_pixels[i]), chip.pixel_address_to_y(broken_pixels[i])))


    def test_set_ctpr(self):
        self.startUp()
        print("Test CTPR errors")
        # Test for errors
        with self.assertRaises(ValueError):
            chip.write_ctpr(list(range(257)), False)
        with self.assertRaises(ValueError):
            chip.write_ctpr(list(range(257, 256, -1)), False)
        
        # Test values
        print("Test reading and writing CTPR")
        pbar = tqdm(total = 256)
        for column in range(256):
            data = chip.write_ctpr([column], False)
            chip.write(data, True)
            fdata = chip['FIFO'].get_data()
            dout = chip.decode_fpga(fdata, True)
            data = chip.read_ctpr(False)
            chip.write(data, True)
            fdata = chip['FIFO'].get_data()
            dout = chip.decode_fpga(fdata, True)
            pbar.update(1)
            for j in range(len(dout)):
                if(dout[j][47:44].tovalue() == 0xD):
                    if dout[j][1:0].tovalue() != 0:
                        self.assertEqual(column, dout[j][43:37].tovalue() * 2 + int(dout[j][1]))
        pbar.close()

    
    def test_general_config(self):
        self.startUp()

        print("Test general config")
        # Test errors
        with self.assertRaises(KeyError):
            chip.configs["WrongConfig"] = 1
        # Test ValueErrors
        for config in range(10):
            with self.assertRaises(ValueError):
                chip.configs[config_list[config]] = -1
            with self.assertRaises(ValueError):
                chip.configs[config_list[config]] = config_size_list[config]

        # Test values
        pbar = tqdm(total = 4 * 10)
        for value in range(4):
            for config in range(10):
                if value < config_size_list[config]:
                    chip.configs[config_list[config]] = value
            data = chip.write_general_config(False)
            chip.write(data)
            data = chip.read_general_config(False)
            chip.write(data)
            fdata = chip['FIFO'].get_data()
            dout = chip.decode_fpga(fdata, True)
            for config in range(10):
                if value < config_size_list[config]:
                    self.assertEqual(value, chip.configs[config_list[config]])
                if config == 1:
                    self.assertEqual(chip.configs[config_list[config]], dout[len(dout) - 2][2:1].tovalue())
                else:
                    self.assertEqual(chip.configs[config_list[config]], int(dout[len(dout) - 2][config_bit_list[config]]))
                pbar.update(1)
        pbar.close()

        # Test defaults
        chip.reset_config_attributes(to_default = True)
        data = chip.write_general_config(False)
        chip.write(data)
        data = chip.read_general_config(False)
        chip.write(data)
        fdata = chip['FIFO'].get_data()
        dout = chip.decode_fpga(fdata, True)
        pbar = tqdm(total=10)
        for config in range(10):
            if config == 1:
                self.assertEqual(chip.configs[config_list[config]], dout[len(dout) - 2][2:1].tovalue())
            else:
                self.assertEqual(chip.configs[config_list[config]], int(dout[len(dout) - 2][config_bit_list[config]]))
            pbar.update(1)
        pbar.close()

    
    def test_testpulse(self):
        self.startUp()

        print("Test testpulse config")
        # Test errors
        with self.assertRaises(ValueError):
            chip.write_tp_pulsenumber(65536, False)
        with self.assertRaises(ValueError):
            chip.write_tp_period(256, 0, False)
        with self.assertRaises(ValueError):
            chip.write_tp_period(0, 16, False)

        # Test default (@reset)
        data = chip.read_tp_config(False)
        chip.write(data)
        fdata = chip['FIFO'].get_data()
        dout = chip.decode_fpga(fdata, True)
        self.assertEqual(0, dout[len(dout) - 2][27:0].tovalue())

        # Test values
        pbar = tqdm(total = 65536 + 256 + 16)
        for i in range(65536):
            data = chip.write_tp_pulsenumber(i, False)
            chip.write(data)
            data = chip.read_tp_config(False)
            chip.write(data)
            fdata = chip['FIFO'].get_data()
            dout = chip.decode_fpga(fdata, True)
            self.assertEqual(i, dout[len(dout) - 2][15:0].tovalue())
            pbar.update(1)
        for i in range(256):
            data = chip.write_tp_period(i, 0, False)
            chip.write(data)
            data = chip.read_tp_config(False)
            chip.write(data)
            fdata = chip['FIFO'].get_data()
            dout = chip.decode_fpga(fdata, True)
            self.assertEqual(i, dout[len(dout) - 2][23:16].tovalue())
            pbar.update(1)
        for i in range(16):
            data = chip.write_tp_period(0, i, False)
            chip.write(data)
            data = chip.read_tp_config(False)
            chip.write(data)
            fdata = chip['FIFO'].get_data()
            dout = chip.decode_fpga(fdata, True)
            self.assertEqual(i, dout[len(dout) - 2][27:24].tovalue())
            pbar.update(1)
        pbar.close()

if __name__ == "__main__":
    unittest.main()
