#!/usr/bin/env python
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import numpy as np
import argparse
import logging
import matplotlib.pyplot as plt
from tables import *
 
logger = logging.getLogger(__file__)
class raw_packets(IsDescription):
...     data_packets = UInt32Col()     # Unsigned short integer
...     timestamp  = Float32Col()    # float  (single-precision)    
>>>
class ToTReadout(IsDescription):
...     pixel_x   = Int8Col()   # 8-bit integer
...     pixel_y   = Int8Col()   # 8-bit integer
...     ToT_value = UInt16Col()     # Unsigned short integer
...     timestamp  = Float32Col()    # float  (single-precision)
>>>


def data_taking():
    '''
    Threshold scan main loop
    '''
    chip = TPX3()
    chip.init()
    h5file = open_file("pcr1.h5", mode="r+", title="Test file")
    threshold_pcr=h5file.root.group_threshold.pixel_threshold_pcr.read()
    #logger.info("threshold_pcr is an object of type:", type(threshold_pcr))
    #logger.info threshold_pcr
    pixel_mask=h5file.root.group_threshold.pixel_mask.read()
    logger.info(h5file)
    
    datafile = open_file("data_taking_run.h5", mode="w", title="run file")
        
    group_data_preprocessing = datafile.create_group("/", 'group_data_packets', 'raw data packets  run')
    table_raw = datafile.create_table(group_data_preprocessing, 'raw', raw_packets, "raw packets data run")

    group_data_postprocessing = datafile.create_group("/", 'group_readout', 'data taking run')
    table_process = datafile.create_table(group_data_postprocessing 'readout', ToTReadout, "Readout for data run")
    logger.info(datafile)
    
    data_raw = table_raw.row
    data_process = table_process.row
    for x in range(256):
        for y in range(256):
          if pixel_mask[x][y]>0 or threshold_pcr[x][y]<0:
            chip.set_pixel_pcr(x, y, 0, 0, 1)
          else 
            chip.set_pixel_pcr(x, y, 0, threshold_pcr[x][y], 0)
    # Step 3b: Write PCR to chip

    chip.set_pixel_pcr(40,38, 0, 0, 1)
    chip.set_pixel_pcr(38,40, 0, 0, 1)
    data = chip.write_pcr([38,40], write=True)
    
    for i in range(256):
        data = chip.write_pcr([i], write=True)
    h5file.close()
    
   # Step 5: Set general config
    logger.info("Disable Testpulses")
    chip._configs["TP_en"] = 0
    
    logger.info("Opmode:ToA_ToT")
    chip._configs["Op_mode"] = 0
    logger.info("Set general config")
    data=chip.set_dac("Vthreshold_fine", 85, write=True)
    data=chip.set_dac("Vthreshold_coarse", 8, write=True)
    
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    pixel_counter = 0
    EoR_counter = 0
    stop_readout_counter = 0
    reset_sequential_counter = 0
    unknown_counter = 0
        
    pixel_counter=0

    
    
# Step 8: Send "read pixel matrix data driven" command
    logger.info("Read pixel matrix data driven")

    #data = chip.read_pixel_matrix_datadriven(write=False)
    data = chip.read_pixel_matrix_datadriven(write=False)        
    chip.write(data, True)
  
    chip['CONTROL']['SHUTTER'] = 1
    chip['CONTROL'].write()
  
    # Step 10: Receive data
    """ ??? """
    
   
    
    # Get the data, do the FPGA decode and do the decode ot the 0th element
    # which should be EoR (header: 0x71)
    while 1:
        try:
            while chip['RX'].is_ready == False:
                continue        
            fdata=chip['FIFO'].get_data()

            for i in range(len(fdata)):
                data_raw['data_packets']=fdata[i]
                data_raw['timestamp']=time.clock()
                data_raw.append()
            if len(fdata)>0:    
                try:
                    dout = chip.decode_fpga(fdata, True)
                    for el in dout:
                      if el[47:44].tovalue() is 0xB:
                          ddout = chip.decode(el, 0xB0)
                          x = chip.pixel_address_to_x(ddout[0])
                          y = chip.pixel_address_to_y(ddout[0])
                          if not(((x==40) and (y==38))or((x==35) and (y==255))):
                            data_process['pixel_x']=x
                            data_process['pixel_y']=y
                            logger.info("X Pos:", x)
                            logger.info("Y Pos:", y)
                            try:
                              tot_val=chip.lfsr_10[BitLogic.tovalue(ddout[2])]
                              hit_cntr=chip.lfsr_4[BitLogic.tovalue(ddout[3])]
                              data_process['ToT_value']=tot_val
                              data_process['timestamp']=time.clock()
                              logger.info("ToT Value:", tot_val)
                              logger.info("Hit Counter", hit_cntr)
                            except KeyError:
                              logger.info ("received invalid values, manually decipher:",ddout[1]," ",ddout[2]," ",ddout[3])
                            
                            pixel_counter += 1
                      elif el[47:40].tovalue() is 0x71:
                          logger.info("\tEoC/EoR/TP_Finished:", chip.decode(el,0x71))
                          EoR_counter +=1
                      elif el[47:40].tovalue() is 0xF0:
                          logger.info("\tStop Matrix Readout:", el)
                          stop_readout_counter +=1
                      elif el[47:40].tovalue() is 0xE0:
                          logger.info("\tReset Sequential:", el)
                          reset_sequential_counter +=1
                      else: 
                        #logger.info("\tUnknown Packet:", el, " with header ", hex(el[47:40].tovalue()))
                        #while chip['RX'].is_ready == False:
                        #    continue
                        unknown_counter +=1 
                except AssertionError:
                    logger.info("package size error")
                logger.info(pixel_counter)
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Readout manually stopped")
            logger.infor(time.time())
            break


 
          
    chip['CONTROL']['SHUTTER'] = 0
    chip['CONTROL'].write()

    # plt.plot(pixel_counts,label="8,86")
    # plt.title("Global Threshold:8,86")
    # plt.xlabel('Pixel PCR value')
    
    # plt.ylabel('No. of noise packets received')
    # plt.show()
if __name__ == "__main__":
     data_taking()
    
