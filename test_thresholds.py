#!/usr/bin/env python
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import numpy as np
import argparse
import logging
from tables import *
 
logger = logging.getLogger(__file__)


def scan():
    '''
    Threshold scan main loop
    '''
    chip = TPX3()
    chip.init()
    pixel_counts=np.zeros((256),dtype=int)
    pixel_threshold_coarse=np.zeros((256,256),dtype=int)
    pixel_threshold_fine=np.zeros((256,256),dtype=int)
    
    for x in range(256):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 0, 15, 0)
    #for x in range(180,256,1):
     #   for y in range(256):
      #      chip.set_pixel_pcr(x, y, 0, 15, 0)
    # Step 3b: Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)
   # Step 5: Set general config
    print("Disable Testpulses")
    chip._configs["TP_en"] = 0
    
    print("Enable Opmode")
    chip._configs["Op_mode"] = 2
    print("Set general config")
    data = chip.write_general_config(write=False)
    chip.write(data, True)
     # Step 3: Set PCR
    # Step 3a: Produce needed PCR
    pixel_counter = 0
    EoR_counter = 0
    stop_readout_counter = 0
    reset_sequential_counter = 0
    unknown_counter = 0
        
    print("Acquisition for 0.2 s")
    #for vtc in range(16):
    for vtc in range(15,-1,-1):
      if pixel_counter>60:
        break
      for vtf in range(180,0,-1):
    #TODO: Should be loaded from configuration and saved in rn_config
        print vtc," ",vtf
        data=chip.set_dac("Vthreshold_fine", vtf, write=True)
        #chip.write(data, True)
        data=chip.set_dac("Vthreshold_coarse", vtc, write=True)
        #chip.write(data, True)
      
        # Step 8: Send "read pixel matrix data driven" command
        print("Read pixel matrix data driven")
        data = chip.read_pixel_matrix_datadriven(write=False)
        chip.write(data, True)
      
        print("Enable Shutter")
        chip['CONTROL']['SHUTTER'] = 1
        chip['CONTROL'].write()
      
        # Step 10: Receive data
        """ ??? """
        time.sleep(0.002)
        # Get the data and do the FPGA decoding
        # dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
        # for el in dout:
        #    print "Decoded: ", el
      
        print("Disable Shutter")
        chip['CONTROL']['SHUTTER'] = 0
        chip['CONTROL'].write()
        # Get the data, do the FPGA decode and do the decode ot the 0th element
        # which should be EoR (header: 0x71)
        dout = chip.decode_fpga(chip['FIFO'].get_data(), True)
        for el in dout:
            if el[47:44].tovalue() is 0xB:
                ddout = chip.decode(el, 0xB0)
                print("X Pos:", chip.pixel_address_to_x(ddout[0]))
                print("Y Pos:", chip.pixel_address_to_y(ddout[0]))
                print("iTOT:", chip.lfsr_14[BitLogic.tovalue(ddout[1])])
                print("Event Counter:", chip.lfsr_10[BitLogic.tovalue(ddout[2])])
                print("Hit Counter", chip.lfsr_4[BitLogic.tovalue(ddout[3])])
                chip.set_pixel_pcr(chip.pixel_address_to_x(ddout[0]), chip.pixel_address_to_y(ddout[0]), 0, 15, 1)
                pixel_threshold_coarse[chip.pixel_address_to_x(ddout[0])][chip.pixel_address_to_y(ddout[0])]=vtc
                pixel_threshold_fine[chip.pixel_address_to_x(ddout[0])][chip.pixel_address_to_y(ddout[0])]=vtf
                data = chip.write_pcr([chip.pixel_address_to_x(ddout[0])], write=False)
                chip.write(data, True)
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
        print pixel_counter
        if pixel_counter>60:
          print "Final Thresholds:"," ",vtc," ",vtf
          break
      
        #pixel_counter=0
  

if __name__ == "__main__":
     scan()
    
