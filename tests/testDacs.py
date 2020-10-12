#!/usr/bin/env python
from __future__ import print_function
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse

def print_exp_recvd(name, exp_header, header, chipId = None):
    print("\tExpected {}: {}".format(name, exp_header))
    print("\tReceived {}: {}".format(name, header))
    if chipId != None:
        print("\tChipID:", chipId)

def print_cmp_dacvals(exp_val, val):
    """
    Convenience printing function to compare expected and receive DAC values
    """
    print_exp_recvd("DAC value", exp_val, val, None)

def print_cmp_daccodes(exp_code, code):
    """
    Convenience printing function to compare expected and receive DAC codes
    """
    print_exp_recvd("DAC code", exp_code, code, None)

def test_dacs():
    # Step 1: Initialize chip & hardware
    chip = TPX3()
    chip.init()

    # Step 2: Chip start-up sequence
    # Step 2a: Reset the chip
    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()
    chip['CONTROL']['RESET'] = 0
    chip['CONTROL'].write()

    # Step 2b: Enable power pulsing
    chip['CONTROL']['EN_POWER_PULSING'] = 1
    chip['CONTROL'].write()

    # Step 2c: Reset the Timer
    data = chip.getGlobalSyncHeader() + [0x40] + [0x0]
    chip.write(data)
    
    # Step 2d: Start the Timer
    data = chip.getGlobalSyncHeader() + [0x4A] + [0x0]
    chip.write(data)

    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 0
    chip['RX'].ENABLE = 1
    time.sleep(0.01)

    print('RX ready:', chip['RX'].is_ready)
    print('get_decoder_error_counter', chip['RX'].get_decoder_error_counter())

    data = chip.write_outputBlock_config(write=False)
    chip.write(data)

    print('RX ready:', chip['RX'].is_ready)

    print(chip.get_configuration())

    # Step 2e: reset sequential / resets pixels?!
    # before setting PCR need to reset pixel matrix
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

    # now set some random DACS to different values than default
    print("Set VTP_coarse")
    chip.dacs["VTP_coarse"] = 11
    print("Set VTP_fine")
    chip.dacs["VTP_fine"] = 131
    # assert we wrote the value correctly to the dictionary
    assert(chip.dacs["VTP_fine"] == 131, "We wrote 131 but received {}".format(chip.dacs["VTP_fine"]))

    # assert wrong values
    try:
        chip.dacs["WrongDac"] = 1
    except KeyError:
        print("Wrong DAC check passed")
    try:
        chip.dacs["VTP_coarse"] = -1
    except ValueError:
        print("Negative value check passed")
    try:
        chip.dacs["VTP_coarse"] = 1000000000000000000
    except ValueError:
        print("Too large value check passed")

    # after setting them, write them
    chip.write_dacs()

    # now read them back
    # NOTE: this check needs to be done by eye for now
    # TODO: fix that!
    chip.read_dacs()

    # now reset the dacs to the default values
    print("Now reset the attributes, and write defaults\n\n")
    chip.reset_dac_attributes(to_default = True)
    # write them to the chip
    chip.write_dacs()

    # and read them back
    time.sleep(0.1)
    chip.read_dacs()

    
    

if __name__ == "__main__":
    test_dacs()
