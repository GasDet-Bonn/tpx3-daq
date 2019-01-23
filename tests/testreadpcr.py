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

    # Step 4d: Reset and start Timer
    print("ReSet Timer")
    data = chip.resetTimer(write=False)
    chip.write(data, True)
    print("Start Timer")
    data = chip.startTimer(write=False)
    chip.write(data, True)

    # Step 5: Set general config
    print("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print("\tGet EoC: ")
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print(dout)

    # Step 2a: reset sequential / resets pixels?!
    data = chip.reset_sequential(False)
    chip.write(data, True)
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    ddout = chip.decode(dout[0], 0x71)
    print(ddout)
    try:
        ddout = chip.decode(dout[1], 0x71)
        print(ddout)
    except IndexError:
        print("no EoR found")

    # Step 3: Set PCR
    # Step 3a: Produce needed PCR
    for x in range(256):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 1, 7, 1)

    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)
    print("pixel config sent")
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    ddout = chip.decode(dout[0], 0x71)
    print(ddout)

    # only read column x == 1
    data = chip.read_pixel_config_reg([1], write=False)
    chip.write(data, True)
    print("read pixel config command sent")
    fdata = chip['FIFO'].get_data()
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(dout)
    ddout = chip.decode(dout[0], 0x71)
    print(ddout)

    data = chip.read_pixel_matrix_sequential(0x02, False)
    print("read matrix sequential command sent")
    chip.write(data, True)
    print("waiting for packets received")
    fdata = chip['FIFO'].get_data()
    print(type(fdata))
    print(fdata)
    dout = chip.decode_fpga(fdata, True)
    print(len(dout))

    counts = []
    count = 0
    xs = []
    ys = []
    for i in range(len(dout)):
        print("decoding now ", dout[i])
        try:
            ddout = chip.decode(dout[i], 0x90)
            count += 1
            if ddout[0] == "EoC":
                continue
        except ValueError:
            try:
                ddout = chip.decode(dout[i], 0xF0)
                print("Found a stop matrix readout?")
                counts.append(count)
                count = 0
                continue
            except ValueError:
                print("Got value error in decode for data ", dout[i])
                raise
        x = chip.pixel_address_to_x(ddout[0])
        y = chip.pixel_address_to_y(ddout[0])
        # print("X pos {}".format(x))
        # print("Y pos {}".format(y))
        xs.append(x)
        ys.append(y)
        # print(ddout[0].tovalue())

    print("Read {} packages".format(len(dout)))
    # print("Read x: {} \nRead y: {}".format(xs, ys))
    # print("#x: {}\n#y: {}".format(len(xs), len(ys)))
    # print("{} / {}".format(xs[183], ys[183]))
    # print("{} / {}".format(xs[184], ys[184]))
    # print("{} / {}".format(xs[185], ys[185]))
    ddout = chip.decode(dout[-1], 0x90)
    print(ddout)

    print("Found the following counts: ", counts)

    # # Step 2a: reset sequential / resets pixels?!
    # data = chip.reset_sequential(False)
    # chip.write(data, True)
    # fdata = chip['FIFO'].get_data()
    # print(fdata)
    # dout = chip.decode_fpga(fdata, True)
    # print(dout)
    # ddout = chip.decode(dout[0],0x71)
    # try:
    #     ddout = chip.decode(dout[1],0x71)
    #     print(ddout)
    # except IndexError:
    #     print("no EoR found")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 CTPR read/write checking script')
    args_dict = vars(parser.parse_args())
    main(args_dict)
