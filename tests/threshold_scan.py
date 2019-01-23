#!/usr/bin/env python
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse

# Causes that the print statement in Python 2.7 is deactivated and
# only the print() function is available
from __future__ import print_function
from six.moves import range


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
    for x in range(256):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 0, 7, 0)

    # Step 3b: Write PCR to chip
    print("Write PCR")
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)

    # Step 4: Set general config
    data = chip.write_general_config(write=False)
    chip.write(data, True)

    # Workaround: Set TP_number register
    # TODO: Even if all other test pulse related commands are missing
    # (CTPR, TP_phase, TP_period, ...) or set to 0 (or disabled) it is
    # somehow needed to set the pulsenumber. Without there is no data
    # and no 'End of Readout' after closing the shutter.
    data = chip.write_tp_pulsenumber(10, write=False)
    chip.write(data, True)

    print("Start threshold scan")
    # TODO: Full threshold scan is not possible yet because for low
    # thresholds 32 bit words keep missing. Maybe some problem with
    # the FIFO? A longer sleep before reading the fifo extends the
    # range of threshold a bit for lower thresholds but sleeps up to
    # 1 second do not solve the problem.
    for coarse in range(8, 16):
        for fine in range(115, 275, 5):
            # Step 5: Set Vthreshold DACs
            # Step 5a: Set Vthreshold_coarse DAC (4-bit)
            data = chip.set_dac("Vthreshold_coarse", coarse, write=False)
            chip.write(data, True)

            # Step 5b: Set Vthreshold_fine DAC (9-bit)
            data = chip.set_dac("Vthreshold_fine", fine, write=False)
            chip.write(data, True)

            # Step 6: Send "read pixel matrix data driven" command
            data = chip.read_pixel_matrix_datadriven(write=False)
            chip.write(data, True)

            # Step 7: Enable Shutter
            chip['CONTROL']['SHUTTER'] = 1
            chip['CONTROL'].write()

            # Step 8: Receive data
            # Leave the shutter opened for 1 ms
            time.sleep(0.001)

            # Step 9: Disable Shutter
            chip['CONTROL']['SHUTTER'] = 0
            chip['CONTROL'].write()

            # Some time is needed to fill the FIFO before it is read
            time.sleep(0.25)

            # Get the data, do the FPGA decode and do the decode ot the 0th element
            # which should be EoR (header: 0x71)
            dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
            pixel_counter = 0
            for el in dout:
                if el[47:44].tovalue() is 0xB:
                    pixel_counter += 1
            threshold_voltage = fine * 0.5 + coarse * 80
            print("Pixel counter for", threshold_voltage, "mV threshold:", pixel_counter)


if __name__ == "__main__":
    threshold_scan()
