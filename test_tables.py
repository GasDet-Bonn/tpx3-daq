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

def run_test_tables():
    # Step 1: Initialize chip & hardware
    chip = TPX3()
    chip.init()
    h5file = open_file("pcr1.h5", mode="w", title="Test file")
    group_threshold = h5file.create_group("/", 'group_threshold', 'PCR Threshold Matrix')
    group_test = h5file.create_group("/", 'group_test', 'PCR Test bit Matrix')
    group_mask = h5file.create_group("/", 'group_mask', 'PCR Mask Matrix')
    
    test_bit=np.zeros((256, 256),dtype=int)
    mask_bit=np.zeros((256, 256), dtype=int)
    threshold_pcr=np.zeros((256, 256), dtype=int)

    
 
    
    print "Step 3a: Produce needed PCR"
    for x in range(255):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 0, 7, 1)
    for y in range(255):
        chip.set_pixel_pcr(255,y,0,7,1)
    chip.set_pixel_pcr(255,255,1,7,0)
    print " Step 3b: Write PCR to chip"
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)
    for i in range(0,256,4):
      data = chip.read_pixel_config_reg(range(i,i+4), write=False)
      chip.write(data, True)
      print("read pixel config command sent")
      fdata = chip['FIFO'].get_data()
      dout = chip.decode_fpga(fdata, True)
      ddout = chip.decode(dout[0], 0x71)
      
      data = chip.read_pixel_matrix_sequential(0x02, False)
      print("read matrix sequential command sent")
      chip.write(data, True)
      print("waiting for packets received")
      fdata = chip['FIFO'].get_data()
      dout = chip.decode_fpga(fdata, True)
      
      counts = []
      count = 0
      xs = []
      ys = []
      for i in range(len(dout)):
          #print("decoding now ", dout[i])
          try:
              ddout = chip.decode(dout[i], 0x90)
              count += 1
              x = chip.pixel_address_to_x(ddout[0])
              y = chip.pixel_address_to_y(ddout[0])
              print("X pos {}".format(x))
              print("Y pos {}".format(y))
              xs.append(x)
              ys.append(y)
              print(ddout[1].reverse())
              test_bit[x][y]=ddout[1][0]
              threshold_pcr[x][y]=ddout[1][4:1].tovalue()
              mask_bit[x][y]=ddout[1][5]
              if ddout[0] == "EoC":
                  continue
          except ValueError:
              try:
                  ddout = chip.decode(dout[i], 0xF0)
                  print("Found a stop matrix readout?")
                  counts.append(count)
                  count = 0
                  continue
              except ValueError:
                  print("Got value error in decode for data ", dout[i])
                  raise
   
      
        
    print("Read {} packages".format(len(dout)))
    print threshold_pcr
    h5file.create_array(group_threshold, 'threshold_pcr', threshold_pcr, "PCR Threshold Matrix")
    h5file.create_array(group_test, 'test_bit', test_bit, "PCR Test Bit Matrix")
    h5file.create_array(group_mask, 'mask_bit', mask_bit, "PCR Mask Matrix")
 
    
    return len(dout)
    
    
    


if __name__ == "__main__":
    run_test_tables()
