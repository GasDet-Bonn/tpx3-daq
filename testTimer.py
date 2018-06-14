#!/usr/bin/env python
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse







def run_test_timer(val):
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
    chip.set_pixel_pcr(255,255,0,7,1)
    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)
      

    
    # Step 5: Set general config
    print "Enable Test pulses"
    chip._config["TP_en"] = 0
    print "Set general config"
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    print "Write TP_period and TP_phase"
    data = chip.write_tp_period(10, 0, write=False)
    chip.write(data, True)
    fdata=chip['FIFO'].get_data()
    
    # Step 6b: Write to pulse number tp register
    print "Write TP_number"
    data = chip.write_tp_pulsenumber(4, write=False)
    chip.write(data, True)
    fdata=chip['FIFO'].get_data()
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    print "Read TP config"
    data = chip.read_tp_config(write=False)
    chip.write(data, True)
    fdata=chip['FIFO'].get_data()
   
    
# Step 2c: Reset the Timer
    print "Set Timer Low"
    chip['CONTROL']['TO_SYNC'] = 0
    chip['CONTROL'].write()
    data = chip.resetTimer(False)
    chip.write(data)
    chip['CONTROL']['TO_SYNC'] = 1
    chip['CONTROL'].write()
    
    # Step 2d: Start the Timer
    chip['CONTROL']['TO_SYNC'] = 0
    chip['CONTROL'].write()
    data = chip.startTimer(False)
    chip.write(data)
    # Step 7: Set CTPR
   
    print "Write CTPR"
    data = chip.write_ctpr(range(255), write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
     
   # Step 8: Send "read pixel matrix data driven" command
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    # Step 9: Enable Shutter
    print "Shutter Open"
    chip['CONTROL']['SHUTTER'] = 1
    chip['CONTROL'].write()
    

    # Step 10: Receive data
   
    data = chip.requestTimerLow(False)
    chip.write(data)
    fdata=chip['FIFO'].get_data()
    dout=chip.decode_fpga(fdata,True)
    ddout = chip.decode(dout[1],0x44)
    print "Timer Check",BitLogic.tovalue(ddout[0])
    
    time.sleep(val)
  
    # Step 11: Disable Shutter
    print "Shutter Closed'"
    chip['CONTROL']['SHUTTER'] = 0
    chip['CONTROL'].write()
    
    
    data = chip.requestTimerRisingShutterLow(False)
    chip.write(data)
    ftdata=chip['FIFO'].get_data()
    dtout=chip.decode_fpga(ftdata,True)
    ddout = chip.decode(dtout[0],0x46)
    print "Timer Check Rising Low:", BitLogic.tovalue(ddout[0])
    t1=BitLogic.tovalue(ddout[0])
    data = chip.requestTimerRisingShutterHigh(False)
    chip.write(data)
    fdata=chip['FIFO'].get_data()
    dout=chip.decode_fpga(fdata,True)
    ddout = chip.decode(dout[0],0x47)
    print "Timer Check Rising High:", BitLogic.tovalue(ddout[0])
    data = chip.requestTimerFallingShutterLow(False)
    chip.write(data)
    ftdata=chip['FIFO'].get_data()
    dtout=chip.decode_fpga(ftdata,True)
    ddout = chip.decode(dtout[0],0x48)
    print "Timer Check Falling Low:",BitLogic.tovalue(ddout[0])
    t2=BitLogic.tovalue(ddout[0])
    data = chip.requestTimerFallingShutterHigh(False)
    chip.write(data)
    ftdata=chip['FIFO'].get_data()
    dtout=chip.decode_fpga(ftdata,True)
    ddout = chip.decode(dtout[0],0x49)
    print "Timer Check Falling Low:",BitLogic.tovalue(ddout[0])
    
    return (t2-t1)*25.0/(10**9)
    
    


if __name__ == "__main__":
    run_test_timer(0.2)
