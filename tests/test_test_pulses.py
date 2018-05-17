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


def run_test_pulses():
    # Step 1: Initialize chip & hardware
    chip = TPX3()
    chip.init()

    # Step 2: Reset the chip
    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()
    chip['CONTROL']['RESET'] = 0
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

    # Step 3: Set PCR
    # Step 3a: Produce needed PCR
    for x in range(256):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 1, 7, 1)

    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip['FIFO'].reset()
        time.sleep(0.01)
        chip.write(data)
        time.sleep(0.01)
        print "Write PCR for column ", i
        # Get the data, do the FPGA decode and do the decode ot the 0th element
        # which should be EoC (header: 0x71)
        dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
        for el in dout:
            print "Decoded: ", el

    # Step 4: Set TP DACs
    # Step 4a: Set VTP_coarse DAC (8-bit)
    data = chip.set_dac("VTP_coarse", 0b1000000, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "Set VTP_coarse"
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    for el in dout:
        print "Decoded: ", el

    # Step 4b: Set VTP_fine DAC (9-bit)
    data = chip.set_dac("VTP_fine", 0b10000000, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "Set VTP_fine"
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    for el in dout:
        print "Decoded: ", el

    # Step 5: Set general config
    data = chip.write_general_config(write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "Set general config"
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    for el in dout:
        print "Decoded: ", el

    # Step 6: Write to the test pulse registers
    # Step 6a: Write to period and phase tp registers
    data = chip.write_tp_period(10, 0, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "Write TP_period and TP_phase"
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    for el in dout:
        print "Decoded: ", el

    # Step 6b: Write to pulse number tp register
    data = chip.write_tp_pulsenumber(10, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "Write TP_number"
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    for el in dout:
        print "Decoded: ", el

    # Step 7: Set CTPR
    data = chip.write_ctpr(range(128), write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "Write CTPR"
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    for el in dout:
        print "Decoded: ", el

    # Step 8: Send "read pixel matrix data driven" command
    data = chip.read_matrix_data_driven(write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "Read pixel matrix data driven"
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    for el in dout:
        print "Decoded: ", el

    # Step 9: Enable Shutter
    chip['CONTROL']['SHUTTER'] = 1
    chip['CONTROL'].write()

    # Step 10: Receive data
    """ ??? """
    print "Acquisition"
    # Get the data and do the FPGA decoding
    dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    for el in dout:
        print "Decoded: ", el

    # Step 11: Disable Shutter
    chip['CONTROL']['SHUTTER'] = 0
    chip['CONTROL'].write()
    print "Receive 'End of Readout'"
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoR (header: 0x71)
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    for el in dout:
        print "Decoded: ", el


if __name__ == "__main__":
    run_test_pulses()
