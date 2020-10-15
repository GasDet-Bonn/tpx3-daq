#!/usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
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
      

    # Step 4: Set TP DACs
    # Step 4a: Set VTP_coarse DAC (8-bit)
    print("Set VTP_coarse")
    chip.dacs["VTP_coarse"] = 0b1000000
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
   
    # Step 4b: Set VTP_fine DAC (9-bit)
    print("Set VTP_fine")
    chip.dacs["VTP_fine"] = 0b100000000
    print(chip.dacs["VTP_fine"])

    # after setting the DACs, write them
    chip.write_dacs()

    
    #chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
   
    # Step 5: Set general config
    print("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    # Step 6: Write to the test pulse registers
    # Step 6a: Write to period and phase tp registers
    print("Write TP_period and TP_phase")
    data = chip.write_tp_period(10, 0, write=False)
    chip.write(data, True)
    
    # Step 6b: Write to pulse number tp register
    print("Write TP_number")
    data = chip.write_tp_pulsenumber(4, write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    print("Read TP config")
    data = chip.read_tp_config(write=False)
    chip.write(data, True)


    # Step 7: Set CTPR
    print("Write CTPR")
    data = chip.write_ctpr(list(range(128)), write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print("\tGet EoC: ")
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print_cmp_commands("11001111", dout[0], dout[1])

    # Step 8: Send "read pixel matrix data driven" command
    print("Read pixel matrix data driven")
    data = chip.read_pixel_matrix_datadriven(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    # Step 9: Enable Shutter
    chip['CONTROL']['SHUTTER'] = 1
    chip['CONTROL'].write()

    # Step 10: Receive data
    """ ??? """
    print("Acquisition")
    time.sleep(1)
    # Get the data and do the FPGA decoding
    # dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    # for el in dout:
    #    print "Decoded: ", el

    # Step 11: Disable Shutter
    print("Receive 'TP_internalfinished' and 'End of Readout'")
    chip['CONTROL']['SHUTTER'] = 0
    chip['CONTROL'].write()
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoR (header: 0x71)
    dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    pixel_counter = 0
    EoR_counter = 0
    stop_readout_counter = 0
    reset_sequential_counter = 0
    unknown_counter = 0
    print("Get data:")
    for el in dout:
        if el[47:44].tovalue() is 0xB:
            ddout = chip.decode(el, 0xB0)
            print("\tX Pos:", chip.pixel_address_to_x(ddout[0]))
            print("\tY Pos:", chip.pixel_address_to_y(ddout[0]))
            print("\tiTOT:", chip.lfsr_14[BitLogic.tovalue(ddout[1])])
            print("\tEvent Counter:", chip.lfsr_10[BitLogic.tovalue(ddout[2])])
            print("\tHit Counter", chip.lfsr_4[BitLogic.tovalue(ddout[3])])
            pixel_counter += 1
        elif el[47:40].tovalue() is 0x71:
            print("\tEoC/EoR/TP_Finished:", chip.decode(el,0x71))
            EoR_counter +=1
        elif el[47:40].tovalue() is 0xF0:
            print("\tStop Matrix Readout:", el)
            stop_readout_counter +=1
        elif el[47:40].tovalue() is 0xE0:
            print("\tReset Sequential:", el)
            reset_sequential_counter +=1
        else: 
          print("\tUnknown Packet:", el)  
          unknown_counter +=1   
    print("Pixel counter:", pixel_counter)
    print("EoR counter:", EoR_counter)
    print("Stop Matrix Readout counter:", stop_readout_counter)
    print("Reset Sequential counter:", reset_sequential_counter)
    print("Unknown counter:", unknown_counter)
    


if __name__ == "__main__":
    run_test_pulses()
