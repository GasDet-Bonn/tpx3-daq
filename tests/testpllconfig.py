#!/usr/bin/env python

from __future__ import absolute_import

# Causes that the print statement in Python 2.7 is deactivated and
# only the print() function is available
from __future__ import print_function

from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse


def main(args_dict):

    chip = TPX3()
    chip.init()

    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()

    chip['CONTROL']['RESET'] = 0
    chip['CONTROL'].write()

    chip['CONTROL']['EN_POWER_PULSING'] = 1
    chip['CONTROL'].write()

    data = chip.write_outputBlock_config(write=False)
    chip.write(data)

    print('RX ready:', chip['RX'].is_ready)

    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 0
    chip['RX'].ENABLE = 1
    time.sleep(0.01)

    while(not chip['RX'].is_ready):
        pass
       
  # Step 2a: reset sequential / resets pixels?!
    data = chip.reset_sequential(False)
    chip.write(data)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0],0x71)
    print(ddout)
    
    # Step 5: Set general config
    print("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print(dout)

    # Step 3b: Write PLL to chip
    data=chip.write_pll_config(1,0,1,1,1,0,0,False)
    chip.write(data)
    print("pll config sent")
    fdata = chip['FIFO'].get_data()
    print(fdata)
    # only read column x == 1
    data = chip.read_pll_config( write=False)
    chip.write(data)
    print("read pll config command sent")
    fdata = chip['FIFO'].get_data()
    print(fdata)
    

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 CTPR read/write checking script')
    args_dict = vars(parser.parse_args())
    main(args_dict)
