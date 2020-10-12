#!/usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse

import matplotlib
matplotlib.use('TKagg')
import matplotlib.pyplot as plt


MASK_ON = 0
MASK_OFF = 1
TP_ON = 1
TP_OFF = 0


def pretty_print(string_val, bits=32):
    val = int(string_val)
    bits = BitLogic(bits)
    bits[:] = val
    lst = bits.toByteList(True)
    lst_hex = map(hex, bits.toByteList(False))
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

    print((chip.get_configuration()))

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
            chip.set_pixel_pcr(x, y, TP_OFF, 7, MASK_OFF)
    # choose the pixel for which to do an SCurve
    x_pixel = 128
    y_pixel = 128
    chip.set_pixel_pcr(x_pixel, y_pixel, TP_ON, 7, MASK_ON)
    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)
      

    # Step 5: Set general config
    print("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    # Step 6: Write to the test pulse registers
    # Step 6a: Write to period and phase tp registers
    print("Write TP_period and TP_phase")
    data = chip.write_tp_period(1, 0, write=False)
    chip.write(data, True)
    
    # Step 6b: Write to pulse number tp register
    print("Write TP_number")
    data = chip.write_tp_pulsenumber(104, write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    print("Read TP config")
    data = chip.read_tp_config(write=False)
    chip.write(data, True)

    
    print("Set Vthreshold_coarse")
    data = chip.set_dac("Vthreshold_coarse", 8, write=False)
    chip.write(data, True)

    # Step 7: Set CTPR
    print("Write CTPR")
    data = chip.write_ctpr([128], write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print("\tGet EoC: ")
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print_cmp_commands("11001111", dout[0], dout[1])


    tp_fine = 2.5 # 9 bit
    tp_coarse = 5 # 8 bit
    tpvals = []
    evCounters = []
    wrongCommands = 0
    thrs = []

    try:
        #for tpc in range(2 ** 7, 2 ** 8):
        # Step 4: Set TP DACs
        # Step 4a: Set VTP_coarse DAC (8-bit)
        tpc = 0b00100000
        print("Set VTP_coarse")
        data = chip.set_dac("VTP_coarse", tpc, write=False)
        chip.write(data, True)

        # Step 4b: Set VTP_fine DAC (9-bit)
        #print "Set VTP_fine"
        tpf = 48
        data = chip.set_dac("VTP_fine", tpf, write=False)
        chip.write(data, True)
        tpval = tpf * tp_fine + tpc * tp_coarse        
        # Get the data, do the FPGA decode and do the decode ot the 0th element
        # which should be EoC (header: 0x71)        
        for thr in range(2 ** 8):
            print("Starting to work on tp val {} mV at thr {}".format(tpval, thr))
            print("Set Vthreshold_fine")
            data = chip.set_dac("Vthreshold_fine", thr, write=False)
            chip.write(data, True)
            # Step 8: Send "read pixel matrix data driven" command
            #print "Read pixel matrix data driven"
            data = chip.read_pixel_matrix_datadriven(write=False)
            chip.write(data, True)    
            # Get the data, do the FPGA decode and do the decode ot the 0th element
            # which should be EoC (header: 0x71)
            
            # Step 9: Enable Shutter
            chip['CONTROL']['SHUTTER'] = 1
            chip['CONTROL'].write()

            # Step 10: Receive data
            """ ??? """
            #print "Acquisition"
            time.sleep(0.05)
            # Get the data and do the FPGA decoding
            # dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
            # for el in dout:
            #    print "Decoded: ", el

            # Step 11: Disable Shutter
            #print "Receive 'TP_internalfinished' and 'End of Readout'"
            chip['CONTROL']['SHUTTER'] = 0
            chip['CONTROL'].write()
            

            # Get the data, do the FPGA decode and do the decode ot the 0th element
            # which should be EoR (header: 0x71)
            dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
            print(dout)
            for i in range(len(dout)):
                try:
                    ddout = chip.decode(dout[i], 0xB0)
                    if ddout[0] != "EoC":
                        x = chip.pixel_address_to_x(ddout[0])
                        y = chip.pixel_address_to_y(ddout[0])
                        if x == 128 and y == 128:
                            iTot = chip.lfsr_14[BitLogic.tovalue(ddout[1])]
                            evCount = chip.lfsr_10[BitLogic.tovalue(ddout[2])]
                            hitCount = chip.lfsr_4[BitLogic.tovalue(ddout[3])]
                            evCounters.append(evCount)
                            #tpvals.append(tpval)
                            thrs.append(thr)
                            print("TP {} mV, iToT {}, evCount {}, hitCount {}".format(tpval, iTot, evCount, hitCount))
                except ValueError:
                    wrongCommands += 1
                    continue
    except KeyboardInterrupt:
        print("Current wrong command counter is {}".format(wrongCommands))
        import sys
        sys.exit()

        
    print("We found {} wrong commands during SCurve".format(wrongCommands))

    plt.plot(thrs, evCounters)
    plt.title("SCurve scan 1 pixel ({} / {})".format(x_pixel, y_pixel))
    plt.xlabel("Threshold fine")
    plt.ylabel("Count / #")
    plt.show()            

if __name__ == "__main__":
    run_test_pulses()
