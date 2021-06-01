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

def main():
    chip = TPX3()
    chip.init()

    chip.toggle_pin("RESET")

    data = chip.write_pll_config(write=False)
    chip.write(data)

    data = chip.write_outputBlock_config(write=False)
    chip.write(data)

    time.sleep(0.01)

    print((chip.get_configuration()))

    print("Test TLU")
    print(chip['TLU'].VERSION)
    #chip['PULSE_GEN'].set_delay(40)
    #chip['PULSE_GEN'].set_width(4056)
    #chip['PULSE_GEN'].set_repeat(0)
    #chip['PULSE_GEN'].set_en(True)
    #chip.toggle_pin("TO_SYNC", 0.0001)
    #for i in range(256):
    chip['TLU'].TRIGGER_MODE = 3
    chip['TLU'].USE_EXT_TIMESTAMP = 0
    chip['TLU'].TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES = 5
    chip['TLU'].TRIGGER_SELECT = 0
    chip['TLU'].DATA_FORMAT = 2
    chip['TLU'].TRIGGER_LOW_TIMEOUT = 0
    chip['TLU'].TRIGGER_DATA_DELAY = 6
    time.sleep(0.1)
    chip['TLU'].TRIGGER_ENABLE = True
        #print(i, chip['TLU'].TRIGGER_LOW_TIMEOUT_ERROR_COUNTER, chip['TLU'].TLU_TRIGGER_ACCEPT_ERROR_COUNTER, chip['TLU'].LOST_DATA_COUNTER, chip['TLU'].TRIGGER_COUNTER)
        #chip['TLU'].TRIGGER_ENABLE = False
    

    time.sleep(0.5)
    chip['PULSE_GEN'].set_delay(40)
    chip['PULSE_GEN'].set_width(4056)
    chip['PULSE_GEN'].set_repeat(0)
    chip['PULSE_GEN'].set_en(True)
    chip.toggle_pin("TO_SYNC", 0.0001)

    while True:
        #chip.toggle_pin("TO_SYNC", 0.0001)
        fdata = chip['FIFO'].get_data()
        fdata = fdata[fdata > 2147483648]
        print("Timeout: \t{} | Accept Error: \t{} | Lost Data: \t{} | Current Trigger: \t{} | Trigger Counter: \t{} | Fifo length: \t{}".format(chip['TLU'].TRIGGER_LOW_TIMEOUT_ERROR_COUNTER, chip['TLU'].TLU_TRIGGER_ACCEPT_ERROR_COUNTER, chip['TLU'].LOST_DATA_COUNTER, chip['TLU'].CURRENT_TLU_TRIGGER_NUMBER, chip['TLU'].TRIGGER_COUNTER, len(fdata)))
        if len(fdata) != 0:
            print("Last TLU word: \t {} | \t{}".format(bin(fdata[len(fdata)-1]), fdata[len(fdata)-1] - 2147483648))
            #for data in fdata:
            #    print(bin(data))
        time.sleep(0.25)

    chip.toggle_pin("RESET")

    print('Happy day!')


if __name__ == "__main__":
    main()
