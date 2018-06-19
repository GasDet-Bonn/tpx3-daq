#!/usr/bin/env python
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array
import argparse
import logging
from tables import *


class pcr_values(IsDescription):
    pix_x=Int8Col()
    pix_y=Int8Col()
    test_bit=Int8Col()   
    threshold=Int8Col()
    mask_bit=Int8Col()
    
    
logger = logging.getLogger(__file__)

def run_test_tables():
    # Step 1: Initialize chip & hardware
    chip = TPX3()
    chip.init()
    

    h5file = open_file("pcr1.h5", mode="w", title="Test file")
    group = h5file.create_group("/", 'pcr_group', 'PCR setup information')
    table = h5file.create_table(group, 'pcr_table', pcr_values, "PCR setup")
    test = table.row
    print "Step 3a: Produce needed PCR"
    for x in range(255):
        for y in range(256):
            chip.set_pixel_pcr(x, y, 0, 7, 1)
    for y in range(255):
        chip.set_pixel_pcr(255,y,0,7,1)
    chip.set_pixel_pcr(255,255,0,7,1)
    print " Step 3b: Write PCR to chip"
    for i in range(256):
        data = chip.write_pcr([i], write=False)
        chip.write(data, True)
      
    data = chip.read_pixel_config_reg([1], write=False)
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
        x = chip.pixel_address_to_x(ddout[0])
        y = chip.pixel_address_to_y(ddout[0])
        print("X pos {}".format(x))
        print("Y pos {}".format(y))
        test['pix_x']=x
        test['pix_y']=x
        xs.append(x)
        ys.append(y)
        print(ddout[1])
        print(ddout[1][5])
        print(ddout[1][4:1].tovalue())
        print(ddout[1][0])
        test['test_bit']=ddout[1][5]
        test['threshold']=ddout[1][4:1].tovalue()
        test['mask_bit']=ddout[1][0]
        test.append()
        
    print("Read {} packages".format(len(dout)))
    table.flush()
    return len(dout)
    
    
    


if __name__ == "__main__":
    run_test_tables()
