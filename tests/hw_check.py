
from tpx3.tpx3 import TPX3
import time
from basil.utils.BitLogic import BitLogic
import array

def pretty_print(string_val, bits = 32):
    val = int(string_val)
    bits = BitLogic(bits)
    bits[:] = val
    lst = bits.toByteList()
    print "Int ", lst
    print "Binary ", bits

def main():

    chip = TPX3()
    chip.init()


    chip['CONTROL']['RESET'] = 1
    chip['CONTROL'].write()

    chip['CONTROL']['RESET'] = 0
    chip['CONTROL'].write()

    print 'RX ready:', chip['RX'].is_ready
    print 'get_decoder_error_counter', chip['RX'].get_decoder_error_counter()


    data = chip.getGlobalSyncHeader() + [0x10] + [0b10101010, 0x01] + [0x0]
    #data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0b10101100, 0x01]
    #data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0xAD, 0x01] #org
    #data = [0xAA,0x00,0x00,0x00,0x00,0x10, 0x0, 0x0] + [0x0]
    # write some value to the register
    #data = chip.setDac("Vfbk", 128, write = False)

    chip['SPI'].set_size(len(data)*8) #in bits
    chip['SPI'].set_data(data)
    chip['SPI'].start()

    print(chip.get_configuration())
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

            data = [0xAA,0x00,0x00,0x00,0x00] + [0x11] + [0x00 for _ in range(3)] #[0b10101010, 0xFF] + [0x0]
            # read back the value we just wrote
            #data = chip.setDac("Vfbk", 128, write = False)
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
        b = BitLogic(32)
        b[:] = int(i)
        print b[:]
        pretty_print(i)


    chip['RX'].reset()
    chip['RX'].DATA_DELAY = 4
    chip['RX'].ENABLE = 1
        
    data = chip.setDac("Vfbk", 128, write = False)
    chip['SPI'].set_size(len(data)*8) #in bits
    chip['SPI'].set_data(data)
    chip['SPI'].start()
    while(not chip['SPI'].is_ready):
        pass
    data = chip.readDac("Vfbk", write = False)
    chip['SPI'].set_size(len(data)*8) #in bits
    chip['SPI'].set_data(data)
    chip['SPI'].start()
    while(not chip['SPI'].is_ready):
        pass
    fdata = chip['FIFO'].get_data()
    print "decimal ", fdata[-1]
    print "list of bytes ", pretty_print(fdata[-1])
    print "list of bytes ", pretty_print(fdata[0])
    #for i in range(len(fdata)):
    #    pretty_print(fdata[i])

    print 'FIFO_SIZE', chip['FIFO'].FIFO_SIZE  

    # let LEDs blink!
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


if __name__=="__main__":
    main()
