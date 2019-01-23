#!/usr/bin/env python

from __future__ import absolute_import
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse

# Causes that the print statement in Python 2.7 is deactivated and
# only the print() function is available
from __future__ import print_function
from six.moves import map
from six.moves import range


def pretty_print(string_val, bits=32):
    val = int(string_val)
    bits = BitLogic(bits)
    bits[:] = val
    lst = bits.toByteList(True)
    lst_hex = list(map(hex, bits.toByteList(False)))
    print("Int ", lst)
    print("Hex ", lst_hex)
    print("Binary ", bits)


def main(args_dict):

    chip = TPX3()
    chip.init()

    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()

    chip['CONTROL']['RESET'] = 0
    chip['CONTROL'].write()

    # print('RX ready:', chip['RX'].is_ready)
    # print('get_decoder_error_counter', chip['RX'].get_decoder_error_counter())

    data = chip.write_outputBlock_config(write=False)
    chip.write(data)

    print('RX ready:', chip['RX'].is_ready)

    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 0
    chip['RX'].ENABLE = 1
    time.sleep(0.01)

    while(not chip['RX'].is_ready):
        pass
  
    print("Test write CTPR")
    data = chip.write_ctpr(list(range(128)), False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print("send ctpr command sent")
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    for el in dout:
        print("Decode_fpga: ", el)
    ddout = chip.decode(dout[0], 0x71)
    print(ddout)
    print("Test Read CTPR")
    data = chip.read_ctpr(False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print("read ctpr command sent")
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    for el in dout:
        print("Decode_fpga: ", el)
    for i in range(128):
        ddout=chip.decode(dout[i],0xD0)
        print(ddout)     
    

    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    time.sleep(0.01)
    
    
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    for el in dout:
        print("Decoded: ", el)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 CTPR read/write checking script')
    args_dict = vars(parser.parse_args())
    main(args_dict)
