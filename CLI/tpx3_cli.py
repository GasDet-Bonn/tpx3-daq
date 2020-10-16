import readline
import sys
from multiprocessing import Process
from tpx3.scans.ToT_calib import ToTCalib
from tpx3.scans.scan_threshold import ThresholdScan
from tpx3.scans.take_data import DataTake

#In this part all callable function names should be in the list functions
functions = ['ToT', 'ToT_Calibration', 'tot_Calibration', 'tot', 
                'Threshold_Scan', 'THL_Scan', 'THL', 'threshold_scan', 'thl_scan', 'thl', 
                'Pixel_DAC_Optimisation', 'Pixel_DAC', 'PDAC', 'pixel_dac_optimisation', 'pixel_dac', 'pdac', 
                'Testpulse_Scan', 'TP_Scan', 'Tp_Scan' 'TP', 'testpulse_scan', 'tp_scan' 'tp', 
                'Run_Datataking', 'Run', 'Datataking', 'R', 'run_datataking', 'run', 'datataking', 'r',
                'Set_DAC', 'set_dac',
                'Help', 'help', 'h', '-h'
                'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit']
help_functions = ['ToT_Calibration', 'Threshold_Scan', 'Pixel_DAC_Optimisation', 'Testpulse_Scan', 'Run_Datataking', 'Set_DAC' 'Help', 'Quit']

def completer(text, state):
    options = [function for function in functions if function.startswith(text)]
    try:
        return options[state]
    except IndexError:
        return None

class TPX3_multiprocess_start(object):
    def process_call(function, **kwargs):
        
        def startup_func(function, **kwargs):
            try:  
                call_func = (function+'()')
                scan = eval(call_func)
                scan.start(**kwargs)
                try:
                scan.analyze()
                except NotImplementedError:
                    pass
                try:
                scan.plot()
                except NotImplementedError:
                    pass
            except KeyboardInterrupt:
                sys.exit(1)
            
        p = Process(target=startup_func, args=(function,), kwargs=kwargs)
        p.start()
        p.join()

class TPX3_CLI_funktion_call(object):

    TPX3_multiprocess_start = TPX3_multiprocess_start()

    def ToT_Calibration(object, VTP_fine_start = None, VTP_fine_stop = None, mask_step = None):
        if VTP_fine_start == None:
            print('> Please enter the VTP_fine_start value (0-511):')
            VTP_fine_start = int(input('>> '))
            print('> Please enter the VTP_fine_stop value (0-511):')
            VTP_fine_stop = int(input('>> '))
            print('> Please enter the number of steps(4, 16, 64, 256):')
            mask_step = int(input('>> '))
            
            print ('ToT with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'mask_step =', mask_step)
        print('Start')
        TPX3_multiprocess_start.process_call(function = 'ToTCalib', VTP_fine_start = VTP_fine_start, VTP_fine_stop = VTP_fine_stop, mask_step = mask_step)


    def Threshold_Scan(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911):')
            Vthreshold_start = int(input('>> '))
            print('> Please enter the Vthreshold_stop value (0-2911):')
            Vthreshold_stop = int(input('>> '))
            print('> Please enter the number of injections (1-65535):')
            n_injections = int(input('>> '))
            print('> Please enter the number of steps(4, 16, 64, 256):')
            mask_step = int(input('>> '))
            
            print ('Threshold scan with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        print('Start')
        TPX3_multiprocess_start.process_call(function = 'ThresholdScan', Vthreshold_start = Vthreshold_start, Vthreshold_stop = Vthreshold_stop, n_injections = n_injections, mask_step = mask_step)



    def Run_Datataking(object, scan_timeout = None):
        if scan_timeout == None:
            print('> Please enter the required run time in seconds (choose 0 for an infinite run):')
            scan_timeout = int(input('>> '))
        
        if scan_timeout == 0:
           print('Infinite data taking run started! You can close the run with "ctrl. c"') 
        else:
            print('{} s long data taking run started!'.format(scan_timeout))
            
        TPX3_multiprocess_start.process_call(function = 'DataTake', scan_timeout = scan_timeout)


class TPX3_CLI_TOP(object):
    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")
    funktion_call = TPX3_CLI_funktion_call()
    print ('\n Welcome to the Timepix3 control Software\n')
    while 1:
        
        a = input('> ')
        if a == '':
            print ('Something enter you must')
        else:
            inputlist = a.split()
            if inputlist[0] in {'Help', 'help', 'h', '-h'}:
                print('If you need detailed help on a function type [functionname -h].\n Possible options are:')
                for function in help_functions:
                    print (function)
                    
            #ToT_Calibration 
            elif inputlist[0] in {'ToT', 'ToT_Calibration', 'tot_Calibration', 'tot'}:
                if len(inputlist) == 1:
                    print('ToT_Calibration')
                    try:
                        funktion_call.ToT_Calibration()
                    except KeyboardInterrupt:
                           print('User quit')
                else:
                    if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                        print('This is the ToT calibration. As arguments you can give the start testpulse value (0-511), the stop testpulse value (0-511) and the number of steps (4, 16, 64, 256).')
                    elif len(inputlist) < 4:
                        print ('Incomplete set of parameters:')
                        try:
                            funktion_call.ToT_Calibration()
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) == 4:
                        try:
                            funktion_call.ToT_Calibration(VTP_fine_start = int(inputlist[1]),VTP_fine_stop = int(inputlist[2]),mask_step = int(inputlist[3]))
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) > 4:
                        print ('To many parameters! The given function takes only three parameters:\n start testpulse value (0-511),\n stop testpulse value (0-511),\n number of steps (4, 16, 64, 256).')

            #Threshold_Scan
            elif inputlist[0] in {'Threshold_Scan', 'THL_Scan', 'THL', 'threshold_scan', 'thl_scan', 'thl'}:
                if len(inputlist) == 1:
                    print('Threshold_Scan')
                    try:
                        funktion_call.Threshold_Scan()
                    except KeyboardInterrupt:
                           print('User quit')
                else:
                    if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                        print('This is the Threshold_Scan. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
                    elif len(inputlist) < 5:
                        print ('Incomplete set of parameters:')
                        try:
                            funktion_call.Threshold_Scan()
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) == 5:
                        try:
                            funktion_call.Threshold_Scan(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]))
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) > 5:
                        print ('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')
                    
            #Data taking
            elif inputlist[0] in {'Run_Datataking', 'Run', 'Datataking', 'R', 'run_datataking', 'run', 'datataking', 'r'}:
                if len(inputlist) == 1:
                    print('Run_Datataking')
                    try:
                        funktion_call.Run_Datataking()
                    except KeyboardInterrupt:
                           print('User quit')
                else:
                    if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                        print('This is the datataking function. As argument you can give the scan timeout (in seconds, if 0 is entered the datataking will run infinitely')
                    elif len(inputlist) == 2:
                        try:
                            funktion_call.Run_Datataking(scan_timeout = int(inputlist[1]))
                        except KeyboardInterrupt:
                           print('User quit')
                    elif len(inputlist) > 2:
                        print ('To many parameters! The given function takes only one parameters:\n scan timeout (in seconds).')
                    
            elif inputlist[0] in {'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit'}:
                break
            else:
                print ('You entered', a)

if __name__ == "__main__":
    tpx3_cli = TPX3_CLI_TOP()