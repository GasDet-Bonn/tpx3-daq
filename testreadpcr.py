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


    # Step 2a: reset sequential / resets pixels?!
    data = chip.reset_sequential(False)
    chip.write(data, True)
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    ddout = chip.decode(dout[0],0x71)
    print ddout
    try:
        ddout = chip.decode(dout[1],0x71)
        print ddout
    except IndexError:
        print("no EoR found")

    # Step 3: Set PCR
    #Step 3a: Produce needed PCR
    for x in range(256):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 1, 7, 1)

    # Step 3b: Write PCR to chip
    for i in range(256):
      data = chip.write_pcr([i], write=False)
      chip.write(data, True)
    print "pixel config sent"
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    ddout=chip.decode(dout[0],0x71)
    print ddout

    data = chip.read_pixel_config_reg(0x33, write=False)
    chip.write(data, True)
    print "read pixel config command sent"
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    ddout = chip.decode(dout[0], 0x71)
    print ddout

    data = chip.read_pixel_matrix_sequential(0x02, False)
    print "read matrix sequential command sent"
    chip.write(data, True)
    print "waiting for packets received"
    fdata = chip['FIFO'].get_data()
    print type(fdata)
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print len(dout)
    for i in range(len(dout) - 1):
        print("decoding now ", dout[i])
        try:
            ddout = chip.decode(dout[i], 0x90)
            if ddout[0] == "EoC":
                continue
        except ValueError:
            try:
                ddout = chip.decode(dout[i], 0xFB)
                print("Found a stop matrix readout?")
            except ValueError:
                print("Got value error in decode for data ", dout[i])
                raise
        print("X pos {}".format(chip.pixel_address_to_x(ddout[0])))
        print("Y pos {}".format(chip.pixel_address_to_y(ddout[0])))
        print(ddout[0].tovalue())


    print ddout
    ddout = chip.decode(dout[-1], 0x71)
    print ddout


    # Step 2a: reset sequential / resets pixels?!
    data = chip.reset_sequential(False)
    chip.write(data, True)
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    ddout = chip.decode(dout[0],0x71)
    try:
        ddout = chip.decode(dout[1],0x71)
        print ddout
    except IndexError:
        print("no EoR found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 CTPR read/write checking script')
    args_dict = vars(parser.parse_args())
    main(args_dict)
