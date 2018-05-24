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

    chip['CONTROL']['EN_POWER_PULSING'] = 1
    chip['CONTROL'].write()

    data = chip.getGlobalSyncHeader() + [0x10] + [0b10101010, 0x01] + [0x00]

    chip.write(data)

    print 'RX ready:', chip['RX'].is_ready

    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 0
    chip['RX'].ENABLE = 1
    time.sleep(0.01)

    while(not chip['RX'].is_ready):
        pass
        
    
    
    # Step 4d: Reset and start Timer
    print "ReSet Timer"
    data = chip.resetTimer(write=False)
    chip.write(data, True)
    print "Start Timer"
    data = chip.startTimer(write=False)
    chip.write(data, True)
    
    # Step 5: Set general config
    print "Set general config"
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print dout


    # Step 2a: reset sequential / resets pixels?!
    data = chip.reset_sequential(False)
    chip.write(data)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0],0x71)
    print ddout
    
    # Step 3b: Write PCR to chip
    chip.write_pll_config(0,1,1,1,0,0,0,False)
    print "pll config sent"
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    print dout
    # only read column x == 1
    data = chip.read_pll_config( write=False)
    chip.write(data)
    print "read pll config command sent"
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    print dout
    ddout = chip.decode(dout[0], 0x21)
    print ddout
    ddout = chip.decode(dout[1], 0x71)
    print ddout

    

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 CTPR read/write checking script')
    args_dict = vars(parser.parse_args())
    main(args_dict)
