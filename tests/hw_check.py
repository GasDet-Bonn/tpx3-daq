
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array

chip = TPX3()
chip.init()

chip['CONTROL']['DATA_MUX_SEL'] = 1

chip['CONTROL']['RESET'] = 1
chip['CONTROL'].write()
chip['CONTROL']['RESET'] = 0
chip['CONTROL'].write()

print 'RX ready:', chip['RX'].is_ready
print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()


data = [0xAA,0x00,0x00,0x00,0x00] + [0x10] + [0b10101010, 0x01] + [0x0]
#data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0b10101100, 0x01]
#data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0xAD, 0x01] #org
#data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0x0, 0x0] + [0x0] 

chip['SPI'].set_size(len(data)*8) #in bits
chip['SPI'].set_data(data)
chip['SPI'].start()
while(not chip['SPI'].is_ready):
    pass

print 'RX ready:', chip['RX'].is_ready
for i in range(32):
    chip['RX'].reset()
    chip['RX'].DATA_DELAY = i #i
    chip['RX'].ENABLE = 1
    chip['FIFO'].reset()
    time.sleep(0.01)
    chip['FIFO'].get_data()
    #print '-', i, chip['RX'].get_decoder_error_counter(), chip['RX'].is_ready
     
    for _ in range(100):

        data = [0xAA,0x00,0x00,0x00,0x00] + [0x11] + [0b10101010, 0x01] + [0x0]
        chip['SPI'].set_size(len(data)*8) #in bits
        chip['SPI'].set_data(data)
        chip['SPI'].start()
        while(not chip['SPI'].is_ready):
            pass
        
        #print 'FIFO_SIZE', chip['FIFO'].FIFO_SIZE

    fdata = chip['FIFO'].get_data()
    print i, 'len', len(fdata), chip['RX'].get_decoder_error_counter(), chip['RX'].is_ready

    
print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()
print 'RX ready:', chip['RX'].is_ready

for i in fdata[:10]:
    print hex(i), (i & 0x01000000)!=0, hex(i & 0xffffff)

print 'FIFO_SIZE', chip['FIFO'].FIFO_SIZE  
   
    
     
for i in range(8):     
    chip['CONTROL']['LED'] = 0
    chip['CONTROL']['LED'][i] = 1
    
    chip['CONTROL'].write()
    time.sleep(0.1)

    
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
bits = count*4*8
print ttime, 's ', bits, 'b ', (float(bits)/ttime)/(1024*1024), 'Mb/s'

print('Happy day!')