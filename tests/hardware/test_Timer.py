#!/usr/bin/env python
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse
import logging
import unittest
import pytest
 

logger = logging.getLogger(__file__)
class grouptest(unittest.TestCase):
 
    def setUp(self):
        pass
    def test_Timer(self):
        self.assertTrue(0.2<=run_test_timer(0.2)<=0.21)
    

@pytest.fixture(scope='module')    
def run_test_timer(val):
    # Step 1: Initialize chip & hardware
    chip = TPX3()
    chip.init()
    
    # Step 5: Set general config
    logger.info("Enable Test pulses")
    chip._configa["TP_en"] = 0
    logger.info("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    data = chip.write_tp_period(10, 0, write=False)
    logger.info("Write TP_period and TP_phase",data)
    chip.write(data, True)
    fdata=chip['FIFO'].get_data()
    
    # Step 6b: Write to pulse number tp register
    data = chip.write_tp_pulsenumber(4, write=False)
    logger.info("Write TP_number",data)
    chip.write(data, True)
    fdata=chip['FIFO'].get_data()
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    # Step 2c: Reset the Timer
    logger.info("Set Timer Low")
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
   
    logger.info("Write CTPR")
    data = chip.write_ctpr(range(255), write=False)
    chip.write(data, True)
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    # Step 8: Send "read pixel matrix data driven" command
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoC (header: 0x71)
    
    # Step 9: Enable Shutter
    logger.info("Shutter Open")
    chip['CONTROL']['SHUTTER'] = 1
    chip['CONTROL'].write()
    

    # Step 10: Receive data
   
    data = chip.requestTimerLow(False)
    chip.write(data)
    fdata=chip['FIFO'].get_data()
    dout=chip.decode_fpga(fdata,True)
    ddout = chip.decode(dout[1],0x44)
    logger.info("Timer Check",BitLogic.tovalue(ddout[0]))
    
    time.sleep(val)
  
    # Step 11: Disable Shutter
    logger.info("Shutter Closed'")
    chip['CONTROL']['SHUTTER'] = 0
    chip['CONTROL'].write()
    
    
    data = chip.requestTimerRisingShutterLow(False)
    chip.write(data)
    ftdata=chip['FIFO'].get_data()
    dtout=chip.decode_fpga(ftdata,True)
    ddout = chip.decode(dtout[0],0x46)
    logger.info("Timer Check Rising Low:", BitLogic.tovalue(ddout[0]))
    t1=BitLogic.tovalue(ddout[0])
    data = chip.requestTimerRisingShutterHigh(False)
    chip.write(data)
    fdata=chip['FIFO'].get_data()
    dout=chip.decode_fpga(fdata,True)
    ddout = chip.decode(dout[0],0x47)
    logger.info("Timer Check Rising High:", BitLogic.tovalue(ddout[0]))
    data = chip.requestTimerFallingShutterLow(False)
    chip.write(data)
    ftdata=chip['FIFO'].get_data()
    dtout=chip.decode_fpga(ftdata,True)
    ddout = chip.decode(dtout[0],0x48)
    logger.info("Timer Check Falling Low:",BitLogic.tovalue(ddout[0]))
    t2=BitLogic.tovalue(ddout[0])
    data = chip.requestTimerFallingShutterHigh(False)
    chip.write(data)
    ftdata=chip['FIFO'].get_data()
    dtout=chip.decode_fpga(ftdata,True)
    ddout = chip.decode(dtout[0],0x49)
    logger.info("Timer Check Falling Low:",BitLogic.tovalue(ddout[0]))
    
    return (t2-t1)*25.0/(10**9)
    
    


if __name__ == "__main__":
    run_test_timer(0.2)
