import readline
import sys
from multiprocessing import Process
from tpx3.scans.ToT_calib import ToTCalib
from tpx3.scans.scan_threshold import ThresholdScan
from tpx3.scans.scan_testpulse import TestpulseScan
from tpx3.scans.PixelDAC_opt import PixelDAC_opt
from tpx3.scans.take_data import DataTake

#In this part all callable function names should be in the list functions
functions = ['ToT', 'ToT_Calibration', 'tot_Calibration', 'tot', 
                'Threshold_Scan', 'THL_Scan', 'THL', 'threshold_scan', 'thl_scan', 'thl', 
                'Pixel_DAC_Optimisation', 'Pixel_DAC', 'PDAC', 'pixel_dac_optimisation', 'pixel_dac', 'pdac', 
                'Testpulse_Scan', 'TP_Scan', 'Tp_Scan' 'TP', 'testpulse_scan', 'tp_scan' 'tp', 
                'Run_Datataking', 'Run', 'Datataking', 'R', 'run_datataking', 'run', 'datataking', 'r',
                'Set_DAC', 'set_dac',
                'GUI',
                'Expert', 'expert',
                'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit']
help_functions = ['ToT_Calibration', 'Threshold_Scan', 'Pixel_DAC_Optimisation', 'Testpulse_Scan', 'Run_Datataking', 'Set_DAC','Load_Equalisation', 'Help', 'Quit']

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
                scan.analyze()
                scan.plot()
            except KeyboardInterrupt:
                sys.exit(1)
            except ValueError as e:
                print(e)
            except NotImplementedError:
                pass

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
            
        print ('ToT calibration with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'mask_step =', mask_step)
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
        TPX3_multiprocess_start.process_call(function = 'ThresholdScan', Vthreshold_start = Vthreshold_start, Vthreshold_stop = Vthreshold_stop, n_injections = n_injections, mask_step = mask_step)

    def Testpulse_Scan(object, VTP_fine_start = None, VTP_fine_stop = None, n_injections = None, mask_step = None):
        if VTP_fine_start == None:
            print('> Please enter the VTP_fine_start value (0-511):')
            VTP_fine_start = int(input('>> '))
            print('> Please enter the VTP_fine_stop value (0-511):')
            VTP_fine_stop = int(input('>> '))
            print('> Please enter the number of injections (1-65535):')
            n_injections = int(input('>> '))
            print('> Please enter the number of steps(4, 16, 64, 256):')
            mask_step = int(input('>> '))
            
        print ('Testpulse scan with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        TPX3_multiprocess_start.process_call(function = 'TestpulseScan', VTP_fine_start = VTP_fine_start, VTP_fine_stop = VTP_fine_stop, n_injections = n_injections, mask_step = mask_step)

    def Pixel_DAC_Optimisation(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911):')
            Vthreshold_start = int(input('>> '))
            print('> Please enter the Vthreshold_stop value (0-2911):')
            Vthreshold_stop = int(input('>> '))
            print('> Please enter the number of injections (1-65535):')
            n_injections = int(input('>> '))
            print('> Please enter the number of steps(4, 16, 64, 256):')
            mask_step = int(input('>> '))
        print ('Pixel DAC optimisation with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        TPX3_multiprocess_start.process_call(function = 'PixelDAC_opt', iteration = 0, Vthreshold_start = Vthreshold_start, Vthreshold_stop = Vthreshold_stop, n_injections = n_injections, mask_step = mask_step)

    def Set_DAC(object, DAC_Name = None, DAC_value = None):
        if DAC_Name == None:
            print('> Please enter the DAC-name (Possibilities:\n    Ibias_Preamp(0-255)\n    VPreamp_NCAS(0-255)\n    Ibias_Ikrum(0-255)\n    Vfbk(0-255)\n    Vthreshold_fine(0-511)\n    Vthreshold_coarse(0-15)\n    Ibias_DiscS1(0-255)\n    Ibias_DiscS2(0-255)\n    Ibias_PixelDAC(0-255)\n    Ibias_TPbufferIn(0-255)\n    Ibias_TPbufferOut(0-255)\n    VTP_coarse(0-255)\n    VTP_fine(0-511)\n    Ibias_CP_PLL(0-255)\n    PLL_Vcntrl(0-255)')
            DAC_Name = input('>> ')
            if DAC_Name in {Ibias_Preamp, VPreamp_NCAS, Ibias_Ikrum, Vfbk, Ibias_DiscS1, Ibias_DiscS2, Ibias_PixelDAC, Ibias_TPbufferIn, Ibias_TPbufferOut, VTP_coarse, Ibias_CP_PLL, PLL_Vcntrl}:
                print('> Please enter the DAC value(0-255):')
                Dac_value = int(input('>> '))
            elif DAC_Name in {Vthreshold_coarse}:
                print('> Please enter the DAC value(0-15):')
                Dac_value = int(input('>> '))
            elif DAC_Name in {Vthreshold_fine, VTP_fine}:
                print('> Please enter the DAC value(0-511):')
                Dac_value = int(input('>> '))
            else:
                print('Unknown DAC-name')

        if DAC_Name in {Ibias_Preamp, VPreamp_NCAS, Ibias_Ikrum, Vfbk, Ibias_DiscS1, Ibias_DiscS2, Ibias_PixelDAC, Ibias_TPbufferIn, Ibias_TPbufferOut, VTP_coarse, Ibias_CP_PLL, PLL_Vcntrl}:
            if DAC_value >= 0 and DAC_value <= 255:
                #Set_DAC(DAC_Name = DAC_Name, DAC_value = DAC_value)
                print('> Set ' + DAC_Name + ' to value' + DAC_value + '.')
            else:
                print('> Value ' + DAC_value + 'is not in range (0-255)')
        elif DAC_Name in {Vthreshold_coarse}:
            if DAC_value >= 0 and DAC_value <= 15:
                #Set_DAC(DAC_Name = DAC_Name, DAC_value = DAC_value)
                print('> Set ' + DAC_Name + ' to value' + DAC_value + '.')
            else:
                print('> Value ' + DAC_value + 'is not in range (0-15)')
        elif DAC_Name in {Vthreshold_fine, VTP_fine}:
            if DAC_value >= 0 and DAC_value <= 511:
                #Set_DAC(DAC_Name = DAC_Name, DAC_value = DAC_value)
                print('> Set ' + DAC_Name + ' to value' + DAC_value + '.')
            else:
                print('> Value ' + DAC_value + 'is not in range (0-511)')
        else:
            print('Unknown DAC-name')

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
    def __init__(self, ext_input_list = None):
        readline.set_completer(completer)
        readline.parse_and_bind("tab: complete")
        funktion_call = TPX3_CLI_funktion_call()
        expertmode = False
        print ('\n Welcome to the Timepix3 control Software\n')

        # Here the main part of the cli starts. Every usercomand needs to be processed here.
        while 1:

            #if
            if ext_input_list == None:
                cmd_input = input('> ')
                #Catch if no input given
                if cmd_input == '':
                    print ('Something enter you must!')
                else:
                    inputlist = cmd_input.split()
            #Input is given
            else:
                inputlist = ext_input_list
                cmd_input = ' '.join(ext_input_list)
                ext_input_list = ['Quit']# To exit the while loop
            if inputlist:
                #Help
                if inputlist[0] in {'Help', 'help', 'h', '-h'}:
                    print('If you need detailed help on a function type [functionname -h].\n Possible options are:')
                    for function in help_functions:
                        print (function)

                #ToT_Calibration
            #ToT_Calibration 
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
                                funktion_call.ToT_Calibration(VTP_fine_start = int(inputlist[1]), VTP_fine_stop = int(inputlist[2]), mask_step = int(inputlist[3]))
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
                            print('This is the Threshold scan. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
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

                #Testpulse_Scan
                elif inputlist[0] in {'Testpulse_Scan', 'TP_Scan', 'Tp_Scan' 'TP', 'testpulse_scan', 'tp_scan' 'tp'}:
                    if len(inputlist) == 1:
                        print('Testpulse_Scan')
                        try:
                            funktion_call.Testpulse_Scan()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Testpulse Scan. As arguments you can give the the start testpulse value (0-511), the stop testpulse value (0-511), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
                        elif len(inputlist) < 5:
                            print ('Incomplete set of parameters:')
                            try:
                                funktion_call.Testpulse_Scan()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 5:
                            try:
                                funktion_call.Testpulse_Scan(VTP_fine_start = int(inputlist[1]), VTP_fine_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 5:
                            print ('To many parameters! The given function takes only four parameters:\n start testpulse value (0-511),\n stop testpulse value (0-511),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')

                #Pixel_DAC_Optimisation
                elif inputlist[0] in {'Pixel_DAC_Optimisation', 'Pixel_DAC', 'PDAC', 'pixel_dac_optimisation', 'pixel_dac', 'pdac'}:
                    if len(inputlist) == 1:
                        print('Pixel_DAC_Optimisation')
                        try:
                            funktion_call.Pixel_DAC_Optimisation()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Pixel DAC Optimisation. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
                        elif len(inputlist) < 5:
                            print ('Incomplete set of parameters:')
                            try:
                                funktion_call.Pixel_DAC_Optimisation()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 5:
                            try:
                                funktion_call.Pixel_DAC_Optimisation(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 5:
                            print ('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')

                #Set_DAC
                elif inputlist[0] in {'Set_DAC', 'set_dac'}:
                    if len(inputlist) == 1:
                        print('Set_DAC')
                        try:
                            funktion_call.Set_DAC()
                        except:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Set DAC function. As arguments you can give the DAC-name/DAC-number  and the new value.\n The following DACs are aviable:\n     1.) Ibias_Preamp_ON (0-255)\n     2.) VPreamp_NCAS (0-255)\n     3.) Ibias_Ikrum (0-255)\n     4.) Vfbk (0-255)\n     5.) Vthreshold_fine (0-511)\n     6.) Vthreshold_coarse (0-15)\n     7.) Ibias_DiscS1_ON (0-255)\n     8.) Ibias_DiscS2_ON (0-255)\n     9.) Ibias_PixelDAC (0-255)\n    10.) Ibias_TPbufferIn (0-255)\n    11.) Ibias_TPbufferOut (0-255)\n    12.) VTP_coarse (0-255)\n    13.) VTP_fine (0-511)\n    14.) Ibias_CP_PLL (0-255)\n    15.) PLL_Vcntrl (0-255)')                
                        elif len(inputlist) < 3:
                            print ('Incomplete set of parameters:')
                            try:
                                funktion_call.Set_DAC()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 3:
                            if inputlist[1] in {'1', 'Ibias_Preamp_ON'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Ibias_Preamp_ON', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'2', 'VPreamp_NCAS'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'VPreamp_NCAS', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'3', 'Ibias_Ikrum'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Ibias_Ikrum', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'4', 'Vfbk'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Vfbk', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'5', 'Vthreshold_fine'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Vthreshold_fine', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'6', 'Vthreshold_coarse'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Vthreshold_coarse', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'7', 'Ibias_DiscS1_ON'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Ibias_DiscS1_ON', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'8', 'Ibias_DiscS2_ON'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Ibias_DiscS2_ON', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'9', 'Ibias_PixelDAC'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Ibias_PixelDAC', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'10', 'Ibias_TPbufferIn'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Ibias_TPbufferIn', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'11', 'Ibias_TPbufferOut'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Ibias_TPbufferOut', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'12', 'VTP_coarse'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'VTP_coarse', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'13', 'VTP_fine'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'VTP_fine', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'14', 'Ibias_CP_PLL'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'Ibias_CP_PLL', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'15', 'PLL_Vcntrl'}:
                                try:
                                    funktion_call.Set_DAC(DAC_Name = 'PLL_Vcntrl', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            else:
                                print ('Unknown DAC-name')
                            print ('Unknown DAC-name')                            
                                print ('Unknown DAC-name')
                        elif len(inputlist) > 3:
                            print ('To many parameters! The given function takes only two parameters:\n The DAC-name and its value.')

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

                #Start GUI
                elif inputlist[0] in {'GUI'}:
                    if len(inputlist) == 1:
                        #Start GUI
                        print('GUI started')
                        break
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This will start the GUI')
                        elif len(inputlist) > 1:
                            print('GUI takes no parameters')

                #Set expert mode
                elif inputlist[0] in {'Expert', 'expert'}:
                    if expertmode == False:
                        expertmode = True
                    elif expertmode == True:
                        expertmode = False

                #Quit
                elif inputlist[0] in {'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit'}:
                    print('Goodbye and have a nice day.')
                    break

                #Unknown command
                else:
                    print ('Unknown command: ', cmd_input, 'Use a language I understand.')

if __name__ == "__main__":
    ext_input_list = sys.argv
    ext_input_list.pop(0)
    if ext_input_list == []:
        tpx3_cli = TPX3_CLI_TOP()

    else:
        tpx3_cli = TPX3_CLI_TOP(ext_input_list = ext_input_list)