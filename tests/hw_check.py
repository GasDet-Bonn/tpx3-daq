
from tpx3.tpx3 import TPX3
import time


chip = TPX3()
chip.init()

chip['SPI'].set_data(range(256)*4)
chip['SPI'].start()
while(not chip['SPI'].is_ready):
        pass

print chip['SPI'].get_data()


print 'FIFO_SIZE', chip['FIFO'].FIFO_SIZE
print 'len', len(chip['FIFO'].get_data())

chip['CONTROL']['CNT_FIFO_EN'] = 1
chip['CONTROL'].write()

chip['CONTROL']['CNT_FIFO_EN'] = 0
chip['CONTROL'].write()

print 'FIFO_SIZE', chip['FIFO'].FIFO_SIZE  
   

fdata = chip['FIFO'].get_data()
print 'Data FIFO_SIZE',len(fdata)

for i in fdata[:10]:
    print i, hex(i) #print (i & 0x01000000)!=0, hex(i & 0xffffff)
            
for i in fdata[-10:]:
    print i, hex(i) #print (i & 0x01000000)!=0, hex(i & 0xffffff)
    

print 'RX ready:', chip['RX'].is_ready
            
for i in range(8):     
    chip['CONTROL']['LED'] = 0
    chip['CONTROL']['LED'][i] = 1
    
    chip['CONTROL'].write()
    time.sleep(0.1)

    
chip['CONTROL']['CNT_FIFO_EN'] = 1
chip['CONTROL'].write()
count = 0
stime = time.time()
for _ in range(1000):
    count += len(chip['FIFO'].get_data())
etime = time.time()
chip['CONTROL']['CNT_FIFO_EN'] = 0
chip['CONTROL'].write()

ttime = etime - stime
bits = count*4*8
print ttime, 's ', bits, 'b ', (float(bits)/ttime)/(1024*1024), 'Mb/s'

print('Happy day!')