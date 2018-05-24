#!/usr/bin/env python
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse


def threshold_scan():
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
    for x in range(256):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 0, 7, 0)

    # Step 3b: Write PCR to chip
    print "Write PCR"
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)

    print "Start threshold scan"
    for coarse in range(16):
        for fine in range(160):
            # Step 4: Set TP DACs
            # Step 4a: Set VTP_coarse DAC (8-bit)
            data = chip.set_dac("Vthreshold_coarse", 0b1000000, write=False)
            chip.write(data, True)

            # Step 4b: Set VTP_fine DAC (9-bit)
            data = chip.set_dac("Vthreshold_fine", 0b100000000, write=False)
            chip.write(data, True)

            # Step 5: Set general config
            data = chip.write_general_config(write=False)
            chip.write(data, True)

            # Step 8: Send "read pixel matrix data driven" command
            data = chip.read_pixel_matrix_datadriven(write=False)
            chip.write(data, True)

            # Step 9: Enable Shutter
            chip['CONTROL']['SHUTTER'] = 1
            chip['CONTROL'].write()

            # Step 10: Receive data
            # Leave the shutter opened for 1 ms
            time.sleep(0.001)

            # Step 11: Disable Shutter
            chip['CONTROL']['SHUTTER'] = 0
            chip['CONTROL'].write()
            # Get the data, do the FPGA decode and do the decode ot the 0th element
            # which should be EoR (header: 0x71)
            dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
            pixel_counter = 0
            for el in dout:
                if el[47:44].tovalue() is 0xB:
                    pixel_counter += 1
            threshold_voltage = fine * 0.5 + coarse * 80
            print "Pixel counter for", threshold_voltage, "mV threshold:", pixel_counter


if __name__ == "__main__":
    threshold_scan()
