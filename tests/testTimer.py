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


def print_exp_recvd(name, exp_header, header, chipId = None):
    print("\tExpected {}: {}".format(name, exp_header))
    print("\tReceived {}: {}".format(name, header))
    if chipId != None:
        print("\tChipID:", chipId)


def print_cmp_commands(exp_header, header, chipId = None):
    """
    Convenience printing function to compare expected and receive command headers
    """
    print_exp_recvd("command header", exp_header, header, chipId)


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


def test_timer():
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

    # Step 3: Set PCR
    # Step 3a: Produce needed PCR
    for x in range(255):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 0, 7, 1)
    for y in range(255):
        chip.set_pixel_pcr(255, y, 0, 7, 1)
    chip.set_pixel_pcr(255, 255, 1, 7, 0)
    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)

    # Step 4: Set general config
    print("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)

    # Step 5: Reset the Timer
    print("Set Timer Low")
    chip['CONTROL']['TO_SYNC'] = 0
    chip['CONTROL'].write()
    data = chip.resetTimer(False)
    chip.write(data)
    chip['CONTROL']['TO_SYNC'] = 1
    chip['CONTROL'].write()
    data = chip.requestTimerLow(False)
    chip.write(data)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x44)
    print(ddout[0])

    # Step 6: Start the Timer
    chip['CONTROL']['TO_SYNC'] = 0
    chip['CONTROL'].write()
    data = chip.startTimer(False)
    chip.write(data)

    # Step 7: Set CTPR
    print("Write CTPR")
    data = chip.write_ctpr(list(range(255)), write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    data = chip.requestTimerLow(False)
    chip.write(data)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[1], 0x44)
    print("Timer Check:", BitLogic.tovalue(ddout[0]))

    # Step 8: Send "read pixel matrix data driven" command
    print("Read pixel matrix data driven")
    data = chip.read_pixel_matrix_datadriven(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)

    # Step 9: Enable Shutter
    print("Shutter Open")
    chip['CONTROL']['SHUTTER'] = 1
    chip['CONTROL'].write()

    # Step 10: Receive data
    dout = chip.decode_fpga(chip['FIFO'].get_data(), True)

    # Step11: Request the low 32 bits of the timer multiple times
    data = chip.requestTimerLow(False)
    for i in range(15):
        chip.write(data)
    # fdata1=chip['FIFO'].get_data()
    fdata2 = chip['FIFO'].get_data()
    d1out1 = chip.decode_fpga(fdata2, True)
    for i in range(15):
        dd1out1 = chip.decode(d1out1[2 * i], 0x44)
        print("Timer Check:", BitLogic.tovalue(dd1out1[0]))

    # Step 11: Disable Shutter
    print("Shutter Closed'")
    chip['CONTROL']['SHUTTER'] = 0
    chip['CONTROL'].write()

    # Step 12: Request the low 32 bit and the high 16 bit of the timer
    #          for the shutter start (Rising) and the shutter end (Falling)
    data = chip.requestTimerRisingShutterLow(False)
    chip.write(data)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[1], 0x46)
    print("Timer Check Rising Low:", BitLogic.tovalue(ddout[0]))
    data = chip.requestTimerRisingShutterHigh(False)
    chip.write(data)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    ddout = chip.decode(dout[0], 0x47)
    print("Timer Check Rising High:", BitLogic.tovalue(ddout[0]))
    data = chip.requestTimerFallingShutterLow(False)
    chip.write(data)
    ftdata = chip['FIFO'].get_data()
    dtout = chip.decode_fpga(ftdata, True)
    ddout = chip.decode(dtout[0], 0x48)
    print("Timer Check Falling Low:", BitLogic.tovalue(ddout[0]))
    data = chip.requestTimerFallingShutterHigh(False)
    chip.write(data)
    ftdata = chip['FIFO'].get_data()
    dtout = chip.decode_fpga(ftdata, True)
    ddout = chip.decode(dtout[0], 0x49)
    print("Timer Check Falling Low:", BitLogic.tovalue(ddout[0]))


if __name__ == "__main__":
    test_timer()
