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

def read_pcr():
    # Step 1: Initialize chip & hardware
    chip = TPX3()
    chip.init()

    # Step 2: Reset the chip
    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()
    chip['CONTROL']['RESET'] = 0
    chip['CONTROL'].write()


    #Step 3: Check Matrix Configuration
    data = chip.read_general_config(write=False)

    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    for i, d in enumerate(fdata):
        print i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff)
        pretty_print(d)
    for el in dout:
        print "Decoded: ", el


    #Step 4: Send Read Pixel Configuration Register Command
    a=1
    for i in range(4):
     	a=a *16+12
    chip.read_pixel_config_reg(a,False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
   

    #Step 5: Send Read Pixel Matrix Sequential command
    x=2
    for i in range(4):
     	x=x * 4 + 2
	chip.read_pixel_matrix_sequential(x,False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)

    #Step 6: Receive Data 
    for i in range(4):   
	    fdata = chip['FIFO'].get_data()
	    print fdata
	    dout = chip.decode_fpga(fdata, True)
	    print dout
	    for i, d in enumerate(fdata):
	        print i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff)
	        pretty_print(d)
	    for el in dout:
	        print "Decoded: ", el
	    ddout=chip.decode(dout,1001)
	    print ddout


