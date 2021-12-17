#!/usr/bin/env python

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse
from six.moves import map
from six.moves import range
from tpx3.utils import toByteList, bitword_to_byte_list
import sys
import math
import numpy as np


def pretty_print(string_val, bits=32):
    val = int(string_val)
    bits = BitLogic(bits)
    bits[:] = val
    lst = bits.toByteList(True)
    lst_hex = list(map(hex, bits.toByteList(False)))
    print("Int ", lst)
    print("Hex ", lst_hex)
    print("Binary ", bits)

def gray_decrypt(value):
    """
    Decrypts a gray encoded 48 bit value according to Manual v1.9 page 19
    """
    encoded_value = BitLogic(48)
    encoded_value[47:0]=value
    gray_decrypt = BitLogic(48)
    gray_decrypt[47]=encoded_value[47]
    for i in range (46, -1, -1):
        gray_decrypt[i]=gray_decrypt[i+1]^encoded_value[i]

    return gray_decrypt

def main(args_dict):

    led_blink = args_dict["led_blink"]
    benchmark = args_dict["benchmark"]
    delay_scan = args_dict["delay_scan"]
    timestamp_request = args_dict["timestamp_request"]
    timestamp_hits = args_dict["timestamp_hits"]

    chip = TPX3()
    chip.init()

    chip.toggle_pin("RESET")

    print('RX ready:', chip['RX0'].is_ready)
    print('get_decoder_error_counter', chip['RX0'].get_decoder_error_counter())

    data = chip.write_pll_config(write=False)
    chip.write(data)

    data = chip.write_outputBlock_config(write=False)
    chip.write(data)
    
    print('RX ready:', chip['RX0'].is_ready)

    if delay_scan is True:
        for i in range(32):
            chip['RX0'].reset()            
            chip['RX0'].INVERT = 0
            chip['RX0'].SAMPLING_EDGE = 0                  
            chip['RX0'].DATA_DELAY = i  # i
            chip['RX0'].ENABLE = 1
            chip["FIFO"].RESET
            time.sleep(0.02)
            chip['FIFO'].get_data()

            for _ in range(100):
                data = [0xAA, 0x00, 0x00, 0x00, 0x00] + [0x11] + [0x00 for _ in range(3)]
                chip.write(data)

            time.sleep(0.01)
            fdata = chip['FIFO'].get_data()
            print('i =', i, '\tlen =', len(fdata), '\terror =', chip['RX0'].get_decoder_error_counter(), "\tready =", chip['RX0'].is_ready)

        print('get_decoder_error_counter', chip['RX0'].get_decoder_error_counter())
        print('RX ready:', chip['RX0'].is_ready)

        for i in fdata[:10]:
            print(hex(i), (i & 0x01000000) != 0, hex(i & 0xffffff))
            b = BitLogic(32)
            b[:] = int(i)
            print(b[:])
            pretty_print(i)

    chip['RX0'].reset()
    chip['RX0'].DATA_DELAY = 7
    chip['RX0'].ENABLE = 1
    time.sleep(0.01)
        
    while(not chip['RX0'].is_ready):
        pass
    print((chip.get_configuration()))

    print("Get ChipID")
    data = chip.read_periphery_template("EFuse_Read")
    data += [0x00]*4
    print(data)
    chip["FIFO"].RESET
    time.sleep(0.1)
    chip.write(data)
    time.sleep(0.1)
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)

    if len(dout) == 2:
        wafer_number = dout[1][19:8]
        y_position = dout[1][7:4]
        x_position = dout[1][3:0]
        print("W{}-{}{}".format(wafer_number.tovalue(), chr(ord('a') + x_position.tovalue() - 1).upper(), y_position.tovalue()))

    print("Test set DAC")
    data = chip.set_dac("Vfbk", 0b10101011, write=False)
    chip["FIFO"].RESET
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    data = chip.read_dac("Vfbk", write=False)
            
    chip["FIFO"].RESET
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    for i, d in enumerate(fdata):
        print(i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff))
        pretty_print(d)
    for el in dout:
        print("Decode_fpga: ", el)
    ddout = chip.decode(dout[0], 0x03)
    print("Decoded 'Read DAC':")
    for el in ddout:
        print("\tDecode: ", el)
    ddout = chip.decode(dout[1], 0x71)
    print("Decoded 'End of Command':")
    for el in ddout:
        print("\tDecode: ", el)

    print("Test set general config")
    data = chip.write_general_config(write=False)
    chip["FIFO"].RESET
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    data = chip.read_general_config(write=False)

    chip["FIFO"].RESET
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    for i, d in enumerate(fdata):
        print(i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff))
        pretty_print(d)
    for el in dout:
        print("Decode_fpga: ", el)
    ddout = chip.decode(dout[0], 0x31)
    print("Decoded 'Read GeneralConfig':")
    for el in ddout:
        print("\tDecode: ", el)
    ddout = chip.decode(dout[1], 0x71)
    print("Decoded 'End of Command':")
    for el in ddout:
        print("\tDecode: ", el)

    print("Test test pulse registers")
    data = chip.write_tp_period(100, 0, write=False)
    chip["FIFO"].RESET
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    data = chip.write_tp_pulsenumber(1000, write=False)
    chip["FIFO"].RESET
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    data = chip.read_tp_config(write=False)

    chip["FIFO"].RESET
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    for i, d in enumerate(fdata):
        print(i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff))
        pretty_print(d)
    for el in dout:
        print("Decode_fpga: ", el)
    ddout = chip.decode(dout[0], 0x0E)
    print("Decoded 'Read TestPulse Config':")
    for el in ddout:
        print("\tDecode: ", el)
    ddout = chip.decode(dout[1], 0x71)
    print("Decoded 'End of Command':")
    for el in ddout:
        print("\tDecode: ", el)

    if timestamp_request is True:
        print("Test Timestamp extension")
        chip['gpio'].reset()
        chip["FIFO"].RESET
        time.sleep(0.01)
        chip['FIFO'].get_data()

        chip['PULSE_GEN'].reset()
        chip['PULSE_GEN'].set_delay(40)
        chip['PULSE_GEN'].set_width(4056)
        chip['PULSE_GEN'].set_repeat(200)
        chip['PULSE_GEN'].set_en(True)
        print("\t Delay = ", chip['PULSE_GEN'].get_delay())
        print("\t Width = ", chip['PULSE_GEN'].get_width())
        print("\t Repeat = ", chip['PULSE_GEN'].get_repeat())

        for counter in range(1):
            chip.toggle_pin("TO_SYNC")

            for _ in range(20):
                chip.requestTimerLow()

            time.sleep(0.1)
            ret = chip['FIFO'].get_data()
            print("\t Length of FIFO data: ", len(ret))

            print("\t FIFO data: ")
            for i, r in enumerate(ret):
                if (r & 0xf0000000) >> 28 == 0b0101:
                    if (r & 0x0f000000) >> 24 == 0b0001:
                        print("FPGA", bin(r & 0x00ffffff), r & 0x00ffffff, (r & 0x00ffffff) * 25 / 1000000)
                else:
                    if (r & 0x0f000000) >> 24 != 0b0001:
                        dataout = BitLogic(48)

                        d1 = bitword_to_byte_list(ret[i-1])
                        d2 = bitword_to_byte_list(ret[i])

                        dataout[47:40] = d2[3]
                        dataout[39:32] = d2[2]
                        dataout[31:24] = d2[1]
                        dataout[23:16] = d1[3]
                        dataout[15:8] = d1[2]
                        dataout[7:0] = d1[1]
                        if (dataout.tovalue() & 0xff0000000000) >> 40 != 0x71:
                            print("CHIP", bin(dataout.tovalue() & 0xffffffff), dataout.tovalue() & 0xffffffff, (dataout.tovalue() & 0xffffffff) * 25 / 1000000)

            time.sleep(1)

    if timestamp_hits is True:
        with open('timestamp_test.txt', 'w') as f:
            sys.stdout = f
            print("Test Timestamp extension - Hit data")

            chip.toggle_pin("RESET")

            for rx in {'RX0', 'RX1', 'RX2', 'RX3', 'RX4', 'RX5', 'RX6', 'RX7'}:
                chip[rx].reset()
                chip[rx].DATA_DELAY = 0
                chip[rx].ENABLE = 1

            data = chip.reset_sequential(False)
            chip.write(data, True)

            chip['CONTROL']['EN_POWER_PULSING'] = 1
            chip['CONTROL'].write()

            # Set the output settings of the chip
            chip._outputBlocks["chan_mask"] = 0b11111111
            data = chip.write_outputBlock_config()

            data = chip.write_pll_config(write=False)
            chip.write(data)

            chip.write_general_config()

            data = chip.read_periphery_template("EFuse_Read")
            data += [0x00]*4
            chip["FIFO"].RESET
            time.sleep(0.1)
            chip.write(data)
            time.sleep(0.1)

            chip['gpio'].reset()
            chip["FIFO"].RESET 
            time.sleep(0.01)
            chip['FIFO'].get_data()

            chip['PULSE_GEN'].reset()
            chip['PULSE_GEN'].set_delay(40)
            chip['PULSE_GEN'].set_width(4056)
            chip['PULSE_GEN'].set_repeat(400)
            chip['PULSE_GEN'].set_en(True)

            chip.configs["Op_mode"] = 0
            chip.write_general_config()

            chip.reset_dac_attributes(to_default = False)
            chip.write_dacs()
            chip.set_dac("VTP_fine", 300)
            time.sleep(0.01)

            data = chip.write_tp_period(2, 0, write=False)
            chip["FIFO"].RESET
            time.sleep(0.01)
            chip.write(data)
            time.sleep(0.01)
            data = chip.write_tp_pulsenumber(20, write=False)
            chip["FIFO"].RESET
            time.sleep(0.01)
            chip.write(data)
            time.sleep(0.01)

            mask_step_cmd = []

            chip.test_matrix[:, :] = chip.TP_OFF
            chip.mask_matrix[:, :] = chip.MASK_OFF
            chip.test_matrix[0::64,0::64] = chip.TP_ON
            chip.mask_matrix[0::64,0::64] = chip.MASK_ON
            
            for i in range(256 // 4):
                mask_step_cmd.append(chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))
            mask_step_cmd.append(chip.read_pixel_matrix_datadriven())

            chip.toggle_pin("TO_SYNC")

            for counter in range(1):

                chip.write_ctpr(list(range(0, 256, 1)))
                chip.write(mask_step_cmd)
                chip['FIFO'].get_data()

                chip.toggle_pin("SHUTTER", 0.1)

                time.sleep(0.1)
                ret = chip['FIFO'].get_data()
                print("\t Length of FIFO data: ", len(ret))

                print("\t FIFO data: ")
                for i, r in enumerate(ret):
                    if (r & 0xf0000000) >> 28 == 0b0101:
                        if (r & 0x0f000000) >> 24 == 0b0001:
                            print("FPGA", bin(0x400000 | (r & 0x00ffffff)), r & 0x00ffffff, (r & 0x00ffffff) * 25 / 1000000)
                    else:
                        link = (r & 0x0e000000) >> 25

                        if ((r & 0x0f000000) >> 24 == 0b0001 or 
                            (r & 0x0f000000) >> 24 == 0b0011 or
                            (r & 0x0f000000) >> 24 == 0b0101 or
                            (r & 0x0f000000) >> 24 == 0b0111 or
                            (r & 0x0f000000) >> 24 == 0b1001 or 
                            (r & 0x0f000000) >> 24 == 0b1011 or
                            (r & 0x0f000000) >> 24 == 0b1101 or
                            (r & 0x0f000000) >> 24 == 0b1111):

                            d1 = bitword_to_byte_list(r)
                            for j in range(i, len(ret)):
                                if (ret[j] & 0x0f000000) >> 24 == ((r & 0x0f000000) >> 24) - 1:
                                    if (ret[j] & 0xf0000000) >> 28 != 0b0101:
                                        d2 = bitword_to_byte_list(ret[j])
                                        break

                            dataout = BitLogic(48)
                            dataout[47:40] = d2[3]
                            dataout[39:32] = d2[2]
                            dataout[31:24] = d2[1]
                            dataout[23:16] = d1[3]
                            dataout[15:8] = d1[2]
                            dataout[7:0] = d1[1]

                            if (dataout.tovalue() & 0xf00000000000) >> 44 == 0xB:
                                pixel = (dataout.tovalue() >> 28) & 0b111
                                super_pixel = (dataout.tovalue() >> 31) & 0x3f
                                right_col = pixel > 3
                                eoc = (dataout.tovalue() >> 37) & 0x7f

                                x = (super_pixel * 4) + (pixel - right_col * 4)
                                y = eoc * 2 + right_col * 1
                                toa = gray_decrypt((dataout.tovalue() >> 14) & 0x3fff).tovalue()
                                
                                print("CHIP", bin(0x400000 | toa), toa, toa * 25 / 1000000, x, y, link)
                            else:
                                print("Reply", hex((dataout.tovalue() & 0xffff00000000) >> 32), link)

        sys.stdout = sys.__stdout__

    chip.toggle_pin("RESET")

    if led_blink is True:
        # let LEDs blink!
        for i in range(8):
            chip['CONTROL']['LED'] = 0
            chip['CONTROL']['LED'][i] = 1

            chip['CONTROL'].write()
            time.sleep(0.1)

    if benchmark is True:
        chip['CONTROL']['CNT_FIFO_EN'] = 1
        chip['CONTROL'].write()
        count = 0
        stime = time.time()
        for _ in range(500):
            count += len(chip['FIFO'].get_data())
        etime = time.time()
        chip['CONTROL']['CNT_FIFO_EN'] = 0
        chip['CONTROL'].write()

        ttime = etime - stime
        bits = count * 4 * 8
        print(ttime, 's ', bits, 'b ', (float(bits) / ttime) / (1024 * 1024), 'Mb/s')

    print('Happy day!')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 hardware checking script')
    parser.add_argument('--led_blink',
                        action='store_true',
                        help="Toggle this, if you want to blink the LEDs")
    parser.add_argument('--benchmark',
                        action='store_true',
                        help="Toggle this, if you want to perform a benchmark")
    parser.add_argument('--delay_scan',
                        action='store_true',
                        help="Toggle this, if you want to perform a delay scan")
    parser.add_argument('--timestamp_request',
                        action='store_true',
                        help="Toggle this, if you want to test the timestamp extension with TPX3 Timer requests")
    parser.add_argument('--timestamp_hits',
                        action='store_true',
                        help="Toggle this, if you want to test the timestamp extension with TPX3 hit data")
    args_dict = vars(parser.parse_args())
    main(args_dict)
