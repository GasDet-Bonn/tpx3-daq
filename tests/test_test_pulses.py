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
        print "\tGet EoC: "
        dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
        print "\tExpected command header: 10001111"
        print "\tReceived command header:", dout[0]
        print "\tChipID:", dout[1]

    # Step 4: Set TP DACs
    # Step 4a: Set VTP_coarse DAC (8-bit)
    print "Set VTP_coarse"
    data = chip.set_dac("VTP_coarse", 0b1000000, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print "\tGet EoC: "
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print "\tExpected command header: 00000010"
    print "\tReceived command header:", dout[0]
    print "\tChipID:", dout[1]
    print "Read VTP_coarse"
    data = chip.read_dac("VTP_coarse", write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "\tGet DAC value, DAC code and EoC:"
    dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    ddout = chip.decode(dout[0], 0x03)
    print "\tExpected DAC value: 01000000"
    print "\tReceived DAC value:", ddout[0][13:5]
    print "\tExpected DAC code: 01111"
    print "\tReceived DAC code:", ddout[0][4:0]
    ddout = chip.decode(dout[1], 0x71)
    print "\tExpected command header: 00000011"
    print "\tReceived command header:", ddout[0]
    print "\tChipID:", ddout[1]

    # Step 4b: Set VTP_fine DAC (9-bit)
    print "Set VTP_fine"
    data = chip.set_dac("VTP_fine", 0b100000000, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print "\tGet EoC: "
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print "\tExpected command header: 00000010"
    print "\tReceived command header:", dout[0]
    print "\tChipID:", dout[1]
    print "Read VTP_fine"
    data = chip.read_dac("VTP_fine", write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "\tGet DAC value, DAC code and EoC:"
    dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    ddout = chip.decode(dout[0], 0x03)
    print "\tExpected DAC value: 100000000"
    print "\tReceived DAC value:", ddout[0][13:5]
    print "\tExpected DAC code: 10000"
    print "\tReceived DAC code:", ddout[0][4:0]
    ddout = chip.decode(dout[1], 0x71)
    print "\tExpected command header: 00000011"
    print "\tReceived command header:", ddout[0]
    print "\tChipID:", ddout[1]

    # Step 5: Set general config
    print "Set general config"
    data = chip.write_general_config(write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print "\tGet EoC: "
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print "\tExpected command header: 00110000"
    print "\tReceived command header:", dout[0]
    print "\tChipID:", dout[1]
    print "Read general config"
    data = chip.read_general_config(write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "\tGet General config and EoC:"
    dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    ddout = chip.decode(dout[0], 0x31)
    print "\tExpected general config: 000000100001"
    print "\tReceived general config:", ddout[0][11:0]
    ddout = chip.decode(dout[1], 0x71)
    print "\tExpected command header: 00110001"
    print "\tReceived command header:", ddout[0]
    print "\tChipID:", ddout[1]

    # Step 6: Write to the test pulse registers
    # Step 6a: Write to period and phase tp registers
    print "Write TP_period and TP_phase"
    data = chip.write_tp_period(10, 0, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print "\tGet EoC: "
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print "\tExpected command header: 00001100"
    print "\tReceived command header:", dout[0]
    print "\tChipID:", dout[1]

    # Step 6b: Write to pulse number tp register
    print "Write TP_number"
    data = chip.write_tp_pulsenumber(10, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print "\tGet EoC: "
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print "\tExpected command header: 00001101"
    print "\tReceived command header:", dout[0]
    print "\tChipID:", dout[1]
    
    print "Read TP config"
    data = chip.read_tp_config(write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    print "\tGet TP config and EoC:"
    dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    ddout = chip.decode(dout[0], 0x0E)
    print "\tExpected TP_number: 0000000000001010"
    print "\tReceived TP_number:", ddout[0][15:0]
    print "\tExpected TP_phase: 0000"
    print "\tReceived TP_phase:", ddout[0][27:24]
    print "\tExpected TP_period: 00001010"
    print "\tReceived TP_period:", ddout[0][23:16]
    ddout = chip.decode(dout[1], 0x71)
    print "\tExpected command header: 00001110"
    print "\tReceived command header:", ddout[0]
    print "\tChipID:", ddout[1]

    # Step 7: Set CTPR
    print "Write CTPR"
    data = chip.write_ctpr(range(128), write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print "\tGet EoC: "
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print "\tExpected command header: 11001111"
    print "\tReceived command header:", dout[0]
    print "\tChipID:", dout[1]

    # Step 8: Send "read pixel matrix data driven" command
    print "Read pixel matrix data driven"
    data = chip.read_matrix_data_driven(write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print "\tGet EoC: "
    dout = chip.decode(chip.decode_fpga(chip['FIFO'].get_data(), True)[0], 0x71)
    print "\tExpected command header: 10111111"
    print "\tReceived command header:", dout[0]
    print "\tChipID:", dout[1]

    # Step 9: Enable Shutter
    chip['CONTROL']['SHUTTER'] = 1
    chip['CONTROL'].write()

    # Step 10: Receive data
    """ ??? """
    print "Acquisition"
    time.sleep(5)
    # Get the data and do the FPGA decoding
    # dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    # for el in dout:
    #    print "Decoded: ", el

    # Step 11: Disable Shutter
    print "Receive 'TP_internalfinished' and 'End of Readout'"
    chip['CONTROL']['SHUTTER'] = 0
    chip['CONTROL'].write()
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoR (header: 0x71)
    print "\tGet TP_internalfinished: "
    dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
    ddout = chip.decode(dout[0], 0x71)
    print "\tExpected command header: 00001111"
    print "\tReceived command header:", ddout[0]
    print "\tChipID:", ddout[1]
    print "\tGet EoR: "
    ddout = chip.decode(dout[1], 0x71)
    print "\tExpected command header: 10110000"
    print "\tReceived command header:", ddout[0]
    print "\tChipID:", ddout[1]

    print dout


if __name__ == "__main__":
    run_test_pulses()
