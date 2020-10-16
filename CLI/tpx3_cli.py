import readline
import sys
from multiprocessing import Process
from tpx3.scans.ToT_calib import ToTCalib
from tpx3.scans.scan_threshold import ThresholdScan

#In this part all callable function names should be in the list functions
functions = ['ToT', 'ToA', 'ToT_Calibration', 'tot_Calibration',
             'ToA_Calibration', 'toa_Calibration', 'Threshold_Scan',
             'Threshold_scan', 'threshold_scan', 'Help', 'help', 'h',
             'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit']
help_functions = ['ToT_Calibration', 'ToA_Calibration', 'Threshold_Scan', 'Help', 'Quit']

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

        def Threshold_Scan(Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None):
            if Vthreshold_start == None:
                print('> Please Enter the Vthreshold_start value (0-2911):')
                Vthreshold_start = int(input('>> '))
                print('> Please Enter the Vthreshold_stop value (0-2911):')
                Vthreshold_stop = int(input('>> '))
                print('> Please Enter the number of injections (1-65535):')
                n_injections = int(input('>> '))
                print('> Please Enter the number of steps(4, 16, 64, 256):')
                mask_step = int(input('>> '))
                
                print ('Threshold scan with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
            print('Start')
            TPX3_CLI_multiprocess_start.process_call(function = 'ThresholdScan', Vthreshold_start = Vthreshold_start, Vthreshold_stop = Vthreshold_stop, n_injections = n_injections, mask_step = mask_step)
        
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

            elif inputlist[0] in {'Threshold_Scan', 'Threshold_scan', 'threshold_scan'}:
                if len(inputlist) == 1:
                    print('Threshold_Scan')
                    try:
                        Threshold_Scan()
                    except KeyboardInterrupt:
                           print('User quit')
                else:
                    if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                        print('This is the Threshold_Scan. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
                    elif len(inputlist) < 5:
                        print ('Incomplete set of parameters:')
                        try:
                            Threshold_Scan()
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) == 5:
                        try:
                            Threshold_Scan(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]))
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) > 5:
                        print ('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')
                    
            elif inputlist[0] in {'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit'}:
                break
            else:
                print ('You entered', a)

if __name__ == "__main__":
    tpx3_cli = TPX3_CLI_TOP()