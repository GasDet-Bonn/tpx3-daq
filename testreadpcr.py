#!/usr/bin/env python

from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse


def pretty_print(string_val, bits=32):
    val = int(string_val)
    bits = BitLogic(bits)
    bits[:] = val
    lst = bits.toByteList(True)
    lst_hex = map(hex, bits.toByteList(False))
    print "Int ", lst
    print "Hex ", lst_hex
    print "Binary ", bits


def main(args_dict):

    chip = TPX3()
    chip.init()

    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()

    chip['CONTROL']['RESET'] = 0
    chip['CONTROL'].write()

    # print 'RX ready:', chip['RX'].is_ready
    # print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()

    data = chip.getGlobalSyncHeader() + [0x10] + [0b10101010, 0x01] + [0x00]

    chip.write(data)

    print 'RX ready:', chip['RX'].is_ready

    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 0
    chip['RX'].ENABLE = 1
    time.sleep(0.01)

    while(not chip['RX'].is_ready):
        pass
  
    print "Test write PLL Config"
    data = chip.write_pll_config(0, 1, 1, 0, 0, 0, 0, False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "write PLL Config command sent"
    fdata = chip['FIFO'].get_data()
    print fdata

    print "Test Read PLL Config"
    data = chip.read_pll_config(False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "read pll config command sent"
    fdata = chip['FIFO'].get_data()
    print fdata
   
     
    



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 CTPR read/write checking script')
    args_dict = vars(parser.parse_args())
    main(args_dict)
