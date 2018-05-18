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
    #print(chip.get_configuration())

    # data = chip.getGlobalSyncHeader() + [0x02] + [0b11111111, 0x00000001] + [0x0]
    # data = chip.set_dac("Ibias_Preamp_ON", 0x00, write = False)
    # chip['FIFO'].reset()
    # chip.write(data)
    print "Test write CTPR"
    data = chip.write_ctpr(range(128), False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "send ctpr command sent"
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    for el in dout:
        print "Decode_fpga: ", el
    ddout=chip.decode(dout[0],0x71)
    print ddout  
    print "Test Read CTPR"
    data = chip.read_ctpr(False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "read ctpr command sent"
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    for el in dout:
        print "Decode_fpga: ", el
    for i in range(128):
        ddout=chip.decode(dout[i],0xD0)
        print ddout     
    
    print "Shutter Enabled"
    #chip['CONTROL']['SHUTTER'] = 1
    #chip['CONTROL'].write()
    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    time.sleep(0.01)
    #chip['CONTROL']['SHUTTER'] = 0
    #chip['CONTROL'].write()
    print "Shutter Disabled"
    
    
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    for el in dout:
        print "Decoded: ", el

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 CTPR read/write checking script')
    args_dict = vars(parser.parse_args())
    main(args_dict)
