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
     data_packets = UInt32Col()     # Unsigned short integer
     timestamp  = Float32Col()    # float  (single-precision)    

class ToTReadout(IsDescription):
     pixel_x   = Int8Col()   # 8-bit integer
     pixel_y   = Int8Col()   # 8-bit integer
     ToT_value = UInt16Col()     # Unsigned short integer
     timestamp  = Float32Col()    # float  (single-precision)


def data_taking():
    '''
    Data Taking run main loop
    '''
    chip = TPX3()
    chip.init()
    #Storing run values in an HDF5 file
    datafilename = "data_run-" + str(time.ctime()) + ".h5"
    datafile = open_file(datafilename, mode="w", title="run file")
        
    group_data_preprocessing = datafile.create_group("/", 'group_data_packets', 'raw data packets  run')
    table_raw = datafile.create_table(group_data_preprocessing, 'raw', raw_packets, "raw packets data run")

    group_data_postprocessing = datafile.create_group("/", 'group_readout', 'data taking run')
    table_process = datafile.create_table(group_data_postprocessing, 'readout', ToTReadout, "Readout for data run")
    logger.info(datafile)
    
    data_raw = table_raw.row
    data_process = table_process.row
    logger.info("Starting" +datafilename)
    
    #reading the PCR and masking settings from file
    pcr_file = open_file("pcr1.h5", mode="r+", title="Test file")
    threshold_pcr=pcr_file.root.group_threshold.pixel_threshold_pcr.read()
    pixel_mask=pcr_file.root.group_threshold.pixel_mask.read()
    
    
    #set pixel pcrs
    for x in range(256):
        for y in range(256):
          if pixel_mask[x][y]>0 or threshold_pcr[x][y]<0:
            chip.set_pixel_pcr(x, y, 0, 0, 1)
          else: 
            chip.set_pixel_pcr(x, y, 0, threshold_pcr[x][y], 0)
    # Write PCR to chip
    for i in range(256):
        data = chip.write_pcr([i], write=True)
    pcr_file.close()
    
   # Step 5: Set general config
    logger.info("Disable Testpulses")
    chip._configs["TP_en"] = 0
    
    logger.info("Opmode:ToA_ToT")
    chip._configs["Op_mode"] = 0
    logger.info("Set general config")
    data=chip.set_dac("Vthreshold_fine", 95, write=True)
    data=chip.set_dac("Vthreshold_coarse", 8, write=True)
    
    data = chip.write_general_config(write=False)
    chip.write(data, True)
    
    #counters to keep track of unexpected results. logged at end
    pixel_counter = 0
    EoR_counter = 0
    stop_readout_counter = 0
    reset_sequential_counter = 0
    unknown_counter = 0
        
    

    
    
# Step 8: Send "read pixel matrix data driven" command
    logger.info("Read pixel matrix data driven")

    #data = chip.read_pixel_matrix_datadriven(write=False)
    data = chip.read_pixel_matrix_datadriven(write=False)        
    chip.write(data, True)
  
    chip['CONTROL']['SHUTTER'] = 1
    chip['CONTROL'].write()
  
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
                            logger.info('X Pos:%s', (str(x)))
                            logger.info('Y Pos:%s', (str(y)))
                            try:
                              tot_val=chip.lfsr_10[BitLogic.tovalue(ddout[2])]
                              hit_cntr=chip.lfsr_4[BitLogic.tovalue(ddout[3])]
                              data_process['ToT_value']=tot_val
                              data_process['timestamp']=time.clock()
                              logger.info('ToT Value:%s', (str(tot_val)))
                              logger.info('Hit Counter:%s', (str(hit_cntr)))
                            
                            except KeyError:
                              logger.info('received invalid values, manually decipher:%s', (str(ddout[1],ddout[2],ddout[3])))
                              data_process['ToT_value']=65535
                              data_process['timestamp']=time.clock()
                              
                            pixel_counter += 1
                      elif el[47:40].tovalue() is 0x71:
                          logger.info('\tEoC/EoR/TP_Finished:%s', (str(chip.decode(el,0x71))))
                          EoR_counter +=1
                      elif el[47:40].tovalue() is 0xF0:
                          logger.info('\tStop Matrix Readout:%s', (str(el)))
                          stop_readout_counter +=1
                      elif el[47:40].tovalue() is 0xE0:
                          logger.info('\tReset Sequential:%s', (str(el)))
                          reset_sequential_counter +=1
                      else: 
                        #logger.info("\tUnknown Packet:", el, " with header ", hex(el[47:40].tovalue()))
                        #while chip['RX'].is_ready == False:
                        #    continue
                        unknown_counter +=1 
                except AssertionError:
                    logger.info("package size error")
                logger.info('\tNo. of hits received:%s', (str(pixel_counter)))
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info('\tNo. of EoRs received:%s', (str(EoR_counter)))
            logger.info('\tNo. of Stop Readouts received:%s', (str(stop_readout_counter)))
            logger.info('\tNo. of Reset Sequentials received:%s', (str(reset_sequential_counter)))                
            logger.info('Readout manually stopped at Time:%s', (str(time.ctime())))
            break


         
    chip['CONTROL']['SHUTTER'] = 0
    chip['CONTROL'].write()
    table_raw.flush()
    table_process.flush() 
    datafile.close()
    # plt.plot(pixel_counts,label="8,86")
    # plt.title("Global Threshold:8,86")
    # plt.xlabel('Pixel PCR value')
    
    # plt.ylabel('No. of noise packets received')
    # plt.show()
if __name__ == "__main__":
     data_taking()
    
