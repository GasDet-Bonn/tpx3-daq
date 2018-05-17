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
    print 'RX ready:', chip['RX'].is_ready
    print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()

    data = chip.getGlobalSyncHeader() + [0x10] + [0b10101010, 0x01] + [0x0]
    
    chip.write(data)

    print 'RX ready:', chip['RX'].is_ready

    if delay_scan is True:
        for i in range(32):
            chip['RX'].reset()
            chip['RX'].DATA_DELAY = i  # i
            chip['RX'].ENABLE = 1
            chip['FIFO'].reset()
            time.sleep(0.01)
            chip['FIFO'].get_data()
            # print '-', i, chip['RX'].get_decoder_error_counter(), chip['RX'].is_ready

            for _ in range(100):

                data = [0xAA, 0x00, 0x00, 0x00, 0x00] + [0x11] + [0x00 for _ in range(3)]  # [0b10101010, 0xFF] + [0x0]
                chip.write(data)
                #

            fdata = chip['FIFO'].get_data()
            print i, 'len', len(fdata), chip['RX'].get_decoder_error_counter(), chip['RX'].is_ready

        print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()
        print 'RX ready:', chip['RX'].is_ready

        for i in fdata[:10]:
            print hex(i), (i & 0x01000000) != 0, hex(i & 0xffffff)
            b = BitLogic(32)
            b[:] = int(i)
            print b[:]
            pretty_print(i)

    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 0
    chip['RX'].ENABLE = 1
    time.sleep(0.01)

    while(not chip['RX'].is_ready):
        pass
    print(chip.get_configuration())

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
   

 #    #Step 5: Send Read Pixel Matrix Sequential command
 #    x=2
 #    for i in range(4):
 #     	x=x * 4 + 2
	# chip.read_pixel_matrix_sequential(x,False)
 #    chip['FIFO'].reset()
 #    time.sleep(0.01)
 #    chip.write(data)
 #    time.sleep(0.01)

    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    for i, d in enumerate(fdata):
        print i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff)
        pretty_print(d)
    for el in dout:
        print "Decoded: ", el
    ddout=chip.decode(dout,0x71)
    print ddout

 #    #Step 6: Receive Data 
 #    for i in range(4):   
	#     fdata = chip['FIFO'].get_data()
	#     print fdata
	#     dout = chip.decode_fpga(fdata, True)
	#     print dout
	#     for i, d in enumerate(fdata):
	#         print i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff)
	#         pretty_print(d)
	#     for el in dout:
	#         print "Decoded: ", el
	#     ddout=chip.decode(dout,0x09)
	#     print ddout

	# fdata = chip['FIFO'].get_data()
 #    print fdata
 #    dout = chip.decode_fpga(fdata, True)
 #    print dout
 #    for i, d in enumerate(fdata):
 #        print i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff)
 #        pretty_print(d)
 #    for el in dout:
 #        print "Decoded: ", el
 #    ddout=chip.decode(dout,0x71)
 #    print ddout
if __name__ == "__main__":
    pass
