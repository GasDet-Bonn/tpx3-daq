import readline
import sys
from multiprocessing import Process
from tpx3.scans.ToT_calib import ToTCalib

#In this part all callable function names should be in the list functions
functions = ['ToT', 'ToA', 'ToT_Calibration', 'tot_Calibration', 'ToA_Calibration', 'toa_Calibration', 'Help', 'help', 'h', 'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit']
help_functions = ['ToT_Calibration', 'ToA_Calibration', 'Help', 'Quit']

def completer(text, state):
    options = [function for function in functions if function.startswith(text)]
    try:
        return options[state]
    except IndexError:
        return None

class TPX3_CLI_multiprocess_start(object):
    #def __init__(self):
    def process_call(function, **kwargs):
        
        def startup_func(function, **kwargs):
            try:  
                call_func = (function+'()')
                scan = eval(call_func)
                scan.start(**kwargs)
                scan.analyze()
                scan.plot()
            except KeyboardInterrupt:
                sys.exit(1)
            
        p = Process(target=startup_func, args=(function,), kwargs=kwargs)
        p.start()
        p.join()


class TPX3_CLI_TOP(object):
    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")
    TPX3_CLI_multiprocess_start = TPX3_CLI_multiprocess_start()
    print ('\n Welcome to the Timepix3 controle Software\n')
    while 1:
        
        def ToT_Calibration(VTP_fine_start = None, VTP_fine_stop = None, mask_step = None):
            if VTP_fine_start == None:
                print('> Please Enter the VTP_fine_start value (0-511):')
                VTP_fine_start = int(input('>> '))
                print('> Please Enter the VTP_fine_stop value (0-511):')
                VTP_fine_stop = int(input('>> '))
                print('> Please Enter the number of steps(4, 16, 64, 256):')
                mask_step = int(input('>> '))
                
                print ('ToT with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'mask_step =', mask_step)
            print('Start')
            TPX3_CLI_multiprocess_start.process_call(function = 'ToTCalib', VTP_fine_start = VTP_fine_start, VTP_fine_stop = VTP_fine_stop, mask_step = mask_step)
        
        a = input('> ')
        if a == '':
            print ('Something enter you must')
        else:
            inputlist = a.split()
            if inputlist[0] in {'Help', 'help', 'h'}:
                print('If you need detailed help on a function type [functionname -h].\n Possible options are:')
                for function in help_functions:
                    print (function)
                    
            elif inputlist[0] in {'ToT', 'ToT_Calibration', 'tot_Calibration'}:
                if len(inputlist) == 1:
                    print('ToT')
                    try:
                        ToT_Calibration()
                    except KeyboardInterrupt:
                           print('User quit')
                else:
                    if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                        print('This is the ToT calibration. As arguments you can give the start testpulse value (0-511), the stop testpulse value (0-511) and the number of steps(4, 16, 64, 256).')
                    elif len(inputlist) < 4:
                        print ('Incomplete set of parameters:')
                        try:
                            ToT_Calibration()
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) == 4:
                        try:
                            ToT_Calibration(VTP_fine_start = int(inputlist[1]),VTP_fine_stop = int(inputlist[2]),mask_step = int(inputlist[3]))
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) > 4:
                        print ('To many parameters! The given function takes only three parameters:\n start testpulse value (0-511),\n stop testpulse value (0-511),\n number of steps(4, 16, 64, 256).')
                    
            elif inputlist[0] in {'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit'}:
                break
            else:
                print ('You entered', a)

if __name__ == "__main__":
    tpx3_cli = TPX3_CLI_TOP()