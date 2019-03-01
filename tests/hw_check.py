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


def main(args_dict):

    led_blink = args_dict["led_blink"]
    benchmark = args_dict["benchmark"]
    delay_scan = args_dict["delay_scan"]

    chip = TPX3()
    chip.init()

    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()

    chip['CONTROL']['RESET'] = 0
    chip['CONTROL'].write()

    print 'RX ready:', chip['RX'].is_ready
    print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()

    data = chip.write_pll_config(bypass=0, reset=1, selectVctl=1, dualedge=1, clkphasediv=1, clkphasenum=0, PLLOutConfig=0, write=False)
    chip.write(data)

    data = chip.write_outputBlock_config(write=False)
    # data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0b10101100, 0x01]
    # data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0xAD, 0x01] #org
    # data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0x0, 0x0] + [0x0]
    # write some value to the register
    # data = chip.set_dac("Vfbk", 128, write = False)

    # chip['SPI'].set_size(len(data)*8) #in bits
    # chip['SPI'].set_data(data)
    # chip['SPI'].start()

    # print(chip.get_configuration())
    # while(not chip['SPI'].is_ready):
    #     pass
    chip.write(data)
    
    print 'RX ready:', chip['RX'].is_ready

    if delay_scan is True:
        for i in range(32):
            chip['RX'].reset()            
            chip['RX'].INVERT = 0
            chip['RX'].SAMPLING_EDGE = 0                   
            chip['RX'].DATA_DELAY = i  # i
            chip['RX'].ENABLE = 1
            chip['FIFO'].reset()
            time.sleep(0.01)
            chip['FIFO'].get_data()
            # print '-', i, chip['RX'].get_decoder_error_counter(), chip['RX'].is_ready

            for _ in range(100):

                data = [0xAA, 0x00, 0x00, 0x00, 0x00] + [0x11] + [0x00 for _ in range(3)]  # [0b10101010, 0xFF] + [0x0]
                chip.write(data)
                # read back the value we just wrote
                # data = chip.set_dac("Vfbk", 128, write = False)
                # chip['SPI'].set_size(len(data)*8) #in bits
                # chip['SPI'].set_data(data)
                # chip['SPI'].start()
                # while(not chip['SPI'].is_ready):
                #     pass

                # print 'FIFO_SIZE', chip['FIFO'].FIFO_SIZE

            fdata = chip['FIFO'].get_data()
            print 'i =', i, '\tlen =', len(fdata), '\terror =', chip['RX'].get_decoder_error_counter(), "\tready =", chip['RX'].is_ready



        print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()
        print 'RX ready:', chip['RX'].is_ready

        for i in fdata[:10]:
            print hex(i), (i & 0x01000000) != 0, hex(i & 0xffffff)
            b = BitLogic(32)
            b[:] = int(i)
            print b[:]
            pretty_print(i)

    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 20
    chip['RX'].ENABLE = 1
    time.sleep(0.01)
        
    while(not chip['RX'].is_ready):
        pass
    print(chip.get_configuration())

    # data = chip.getGlobalSyncHeader() + [0x02] + [0b11111111, 0x00000001] + [0x0]
    # data = chip.set_dac("Ibias_Preamp_ON", 0x00, write = False)
    # chip['FIFO'].reset()
    # chip.write(data)

    print "Test set DAC"
    data = chip.set_dac("Vfbk", 0b10101011, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    data = chip.read_dac("Vfbk", write=False)

    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    dout = chip.decode_fpga(fdata, True)
    for i, d in enumerate(fdata):
        print i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff)
        pretty_print(d)
    for el in dout:
        print "Decode_fpga: ", el
    ddout = chip.decode(dout[0], 0x03)
    print "Decoded 'Read DAC':"
    for el in ddout:
        print "\tDecode: ", el
    ddout = chip.decode(dout[1], 0x71)
    print "Decoded 'End of Command':"
    for el in ddout:
        print "\tDecode: ", el

    print "Test set general config"
    data = chip.write_general_config(write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    data = chip.read_general_config(write=False)

    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    for i, d in enumerate(fdata):
        print i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff)
        pretty_print(d)
    for el in dout:
        print "Decode_fpga: ", el
    ddout = chip.decode(dout[0], 0x31)
    print "Decoded 'Read GeneralConfig':"
    for el in ddout:
        print "\tDecode: ", el
    ddout = chip.decode(dout[1], 0x71)
    print "Decoded 'End of Command':"
    for el in ddout:
        print "\tDecode: ", el

    print "Test test pulse registers"
    data = chip.write_tp_period(100, 0, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    data = chip.write_tp_pulsenumber(1000, write=False)
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    data = chip.read_tp_config(write=False)

    chip['FIFO'].reset()
    time.sleep(0.01)
    chip.write(data)
    time.sleep(0.01)
    fdata = chip['FIFO'].get_data()
    print fdata
    dout = chip.decode_fpga(fdata, True)
    print dout
    for i, d in enumerate(fdata):
        print i, hex(d), (d & 0x01000000) != 0, bin(d & 0xffffff), hex(d & 0xffffff)
        pretty_print(d)
    for el in dout:
        print "Decode_fpga: ", el
    ddout = chip.decode(dout[0], 0x0E)
    print "Decoded 'Read TestPulse Config':"
    for el in ddout:
        print "\tDecode: ", el
    ddout = chip.decode(dout[1], 0x71)
    print "Decoded 'End of Command':"
    for el in ddout:
        print "\tDecode: ", el

    # data = chip.set_dac("Ibias_Preamp_ON", 0b1101, write = False)
    # chip['FIFO'].reset()
    # chip.write(data)
    # data = chip.read_dac("Ibias_Preamp_ON", write = False)
    # chip['FIFO'].reset()

    # chip.write(data)
    # fdata = chip['FIFO'].get_data()
    # print "decimal ", fdata[-1], " and length ", len(fdata)
    # pretty_print(fdata[-1])
    # pretty_print(fdata[0])
    # #for i in range(len(fdata)):
    # #    pretty_print(fdata[i])

    # print 'FIFO_SIZE', chip['FIFO'].FIFO_SIZE

    if led_blink is True:
        # let LEDs blink!
        for i in range(8):
            chip['CONTROL']['LED'] = 0
            chip['CONTROL']['LED'][i] = 1

            chip['CONTROL'].write()
            time.sleep(0.1)

    if benchmark is True:
        chip['CONTROL']['CNT_FIFO_EN'] = 1
        chip['CONTROL'].write()
        count = 0
        stime = time.time()
        for _ in range(500):
            count += len(chip['FIFO'].get_data())
        etime = time.time()
        chip['CONTROL']['CNT_FIFO_EN'] = 0
        chip['CONTROL'].write()

        ttime = etime - stime
        bits = count * 4 * 8
        print ttime, 's ', bits, 'b ', (float(bits) / ttime) / (1024 * 1024), 'Mb/s'

    print('Happy day!')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Timepix3 hardware checking script')
    parser.add_argument('--led_blink',
                        action='store_true',
                        help="Toggle this, if you want to blink the LEDs")
    parser.add_argument('--benchmark',
                        action='store_true',
                        help="Toggle this, if you want to perform a benchmark")
    parser.add_argument('--delay_scan',
                        action='store_true',
                        help="Toggle this, if you want to perform a delay scan")
    args_dict = vars(parser.parse_args())
    main(args_dict)
