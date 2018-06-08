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

def print_exp_recvd(name, exp_header, header, chipId = None):
    print "\tExpected {}: {}".format(name, exp_header)
    print "\tReceived {}: {}".format(name, header)
    if chipId != None:
        print "\tChipID:", chipId


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

def run_test_pulses():
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

    print 'RX ready:', chip['RX'].is_ready
    print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()

    data = chip.getGlobalSyncHeader() + [0x10] + [0b10101010, 0x01] + [0x0]
    chip.write(data)

    print 'RX ready:', chip['RX'].is_ready

    print(chip.get_configuration())

    # Step 2e: reset sequential / resets pixels?!
    # before setting PCR need to reset pixel matrix
    data = chip.reset_sequential(False)
    chip.write(data, True)
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    ddout = chip.decode(dout[0], 0x71)
    print ddout
    try:
        ddout = chip.decode(dout[1], 0x71)
        print ddout
    except IndexError:
        print("no EoR found")


    # Step 3: Set PCR
    # Step 3a: Produce needed PCR
    for x in range(255):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 0, 7, 1)
    for y in range(255):
        chip.set_pixel_pcr(255,y,0,7,1)
    chip.set_pixel_pcr(255,255,1,7,0)
    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)
      

    
    # Step 5: Set general config
    print "Set general config"
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)

    chip['FIFO'].reset()

    """
    Explanation for the determination of this chips ChipID:
    The idea is to send a valid command using a local chip header with a
    chip ID different from the one the chip has. According to the manual
    page 29 of manual v1.9, a chip will send the `OtherChipCommand` containing
    its own ChipID. So therefore we send the SenseDACsel command, which with
    a local chip ID of 0x01. The chip correctly answers with an OtherChipCommand,
    but containing the chip ID with all 0s...
    """
    
    data = chip.read_periphery_template("SenseDACsel", local_header = True)
    chip.write(data, False, printf = True)

    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    print("Fdata is ", fdata)
    print("dout is {} and its length {}".format(dout, len(dout)))
    
    ddout = chip.decode(dout[0], 0x72)
    #ddout1 = chip.decode(dout[1], 0x00)    
    
    print("ddout is ", ddout)
    #print("ddout1 is ", ddout1)    
   


if __name__ == "__main__":
    run_test_pulses()
