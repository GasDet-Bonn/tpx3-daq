import readline
import sys
import os
from multiprocessing import Process
from shutil import copy
from tpx3.scans.ToT_calib import ToTCalib
from tpx3.scans.scan_threshold import ThresholdScan
from tpx3.scans.scan_testpulse import TestpulseScan
from tpx3.scans.PixelDAC_opt import PixelDAC_opt
from tpx3.scans.take_data import DataTake
from tpx3.scans.Threshold_calib import ThresholdCalib
import tpx3.scans.scan_hardware as Init_Hardware
from tpx3.scan_base import ConfigError

#In this part all callable function names should be in the list functions
functions = ['ToT', 'ToT_Calibration', 'tot_Calibration', 'tot', 
                'Threshold_Scan', 'THL_Scan', 'THL', 'threshold_scan', 'thl_scan', 'thl', 
                'Threshold_Calibration', 'THL_Calib', 'threshold_calibration', 'thl_calib',
                'Pixel_DAC_Optimisation', 'Pixel_DAC', 'PDAC', 'pixel_dac_optimisation', 'pixel_dac', 'pdac', 
                'Testpulse_Scan', 'TP_Scan', 'Tp_Scan' 'TP', 'testpulse_scan', 'tp_scan' 'tp', 
                'Initialise_Hardware', 'Init_Hardware', 'Init', 'initialise_hardware', 'init_hardware', 'init',
                'Run_Datataking', 'Run', 'Datataking', 'R', 'run_datataking', 'run', 'datataking', 'r',
                'Set_DAC', 'set_dac',
                'Load_Equalisation', 'Load_Equal', 'LEQ','load_equalisation', 'load_equal', 'leq',
                'Save_Equalisation', 'Save_Equal', 'SEQ','save_equalisation', 'save_equal', 'seq',
                'Save_Backup', 'Backup','save_backup', 'backup',
                'Load_Backup', 'load_backup',
                'Set_Default', 'Default', 'set_default', 'default',
                'GUI',
                'Set_Polarity', 'Set_Pol', 'Polarity', 'Pol','set_polarity', 'set_pol', 'polarity','pol',
                'Set_Mask', 'Mask', 'set_mask', 'mask', 
                'Unset_Mask', 'Unmask','unset_mask', 'unmask',
                'Load_Mask', 'load_mask',
                'Save_Mask', 'save_mask',
                'Set_operation_mode', 'Set_Op_mode', 'Op_mode', 'set_operation_mode', 'set_Op_mode', 'op_mode',
                'Set_Fast_Io', 'Fast_Io', 'set_fast_io', 'fast_io', 'Fast_Io_en', 'fast_io_en',
                'Expert', 'expert',
                'Help', 'help', 'h', '-h',
                'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit']

expert_functions =['Set_CLK_fast_mode', 'set_clk_fast_mode', 'CLK_fast_mode', 'clk_fast_mode',
                    'Set_Acknowledgement', 'set_acknowledgement', 'Acknowledgement', 'acknowledgement',
                    'Set_TP_ext_in', 'set_tp_ext_in', 'TP_ext_in', 'tp_ext_in',
                    'Set_ClkOut_frequency', 'set_clkout_frequency', 'ClkOut_frequency', 'clkout_frequency']

help_functions = ['ToT_Calibration', 'Threshold_Scan', 'Threshold_Calibration', 'Pixel_DAC_Optimisation', 
                    'Testpulse_Scan', 'Run_Datataking', 'Initialise_Hardware', 'Set_DAC','Load_Equalisation', 'Save_Equalisation', 
                    'Set_Polarity', 'Set_operation_mode', 'Set_Fast_Io', 'Save_Backup', 'Load_Backup', 'Load_Mask', 'Set_Mask',
                    'Unset_Mask', 'Set_Default', 'GUI', 'Help', 'Quit']

help_expert = ['Set_CLK_fast_mode', 'Set_Acknowledgement', 'Set_TP_ext_in', 'Set_ClkOut_frequency']

expert_help_functions = help_functions + help_expert
exit_list = ['Quit', 'quit', 'q', 'Q', 'Exit', 'exit']

def completer(text, state):
    options = [function for function in functions if function.startswith(text)]
    try:
        return options[state]
    except IndexError:
        return None

# Auto completion for all functions in the "function" and the "expert_function" list
def expert_completer(text, state):
    expertfunctions = functions + expert_functions
    options = [function for function in expertfunctions if function.startswith(text)]
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
            except ConfigError:
                print("The currnt link configuration is not valid. Please start 'Init' or check your hardware.")
            except NotImplementedError:
                pass

        p = Process(target=startup_func, args=(function,), kwargs=kwargs)
        p.start()
        p.join()


class TPX3_CLI_function_call(object):
    TPX3_multiprocess_start = TPX3_multiprocess_start()

    def ToT_Calibration(object, VTP_fine_start = None, VTP_fine_stop = None, mask_step = None):
        if VTP_fine_start == None:
            print('> Please enter the VTP_fine_start value (0-511):')
            while(1):
                VTP_fine_start = input('>> ')
                try:
                    VTP_fine_start = int(VTP_fine_start)
                    break
                except:
                    if VTP_fine_start in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the VTP_fine_stop value (0-511):')
            while(1):
                VTP_fine_stop = input('>> ')
                try:
                    VTP_fine_stop = int(VTP_fine_stop)
                    break
                except:
                    if VTP_fine_stop in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of steps(4, 16, 64, 256):')
            while(1):
                mask_step = input('>> ')
                try:
                    mask_step = int(mask_step)
                    break
                except:
                    if mask_step in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            
        print ('ToT calibration with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'mask_step =', mask_step)
        TPX3_multiprocess_start.process_call(function = 'ToTCalib', VTP_fine_start = VTP_fine_start, VTP_fine_stop = VTP_fine_stop, mask_step = mask_step, thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'))

    def Threshold_Scan(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911):')
            while(1):
                Vthreshold_start = input('>> ')
                try:
                    Vthreshold_start = int(Vthreshold_start)
                    break
                except:
                    if Vthreshold_start in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the Vthreshold_stop value (0-2911):')
            while(1):
                Vthreshold_stop = input('>> ')
                try:
                    Vthreshold_stop = int(Vthreshold_stop)
                    break
                except:
                    if Vthreshold_stop in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of injections (1-65535):')
            while(1):
                n_injections = input('>> ')
                try:
                    n_injections = int(n_injections)
                    break
                except:
                    if n_injections in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of steps(4, 16, 64, 256):')
            while(1):
                mask_step = input('>> ')
                try:
                    mask_step = int(mask_step)
                    break
                except:
                    if mask_step in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            
        print ('Threshold scan with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step = ', mask_step)
        TPX3_multiprocess_start.process_call(function = 'ThresholdScan', Vthreshold_start = Vthreshold_start, Vthreshold_stop = Vthreshold_stop, n_injections = n_injections, mask_step = mask_step, thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'))

    def Threshold_Calib(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None, n_pulse_heights = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911):')
            while(1):
                Vthreshold_start = input('>> ')
                try:
                    Vthreshold_start = int(Vthreshold_start)
                    break
                except:
                    if Vthreshold_start in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the Vthreshold_stop value (0-2911):')
            while(1):
                Vthreshold_stop = input('>> ')
                try:
                    Vthreshold_stop = int(Vthreshold_stop)
                    break
                except:
                    if Vthreshold_stop in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of injections (1-65535):')
            while(1):
                n_injections = input('>> ')
                try:
                    n_injections = int(n_injections)
                    break
                except:
                    if n_injections in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of steps(4, 16, 64, 256):')
            while(1):
                mask_step = input('>> ')
                try:
                    mask_step = int(mask_step)
                    break
                except:
                    if mask_step in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of pulse height steps(2-100):')
            n_pulse_heights = int(input('>> '))
            
        print ('Threshold scan with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step = ', mask_step, 'Number of pulse heights = ', n_pulse_heights)
        TPX3_multiprocess_start.process_call(function = 'ThresholdCalib', iteration = 0, Vthreshold_start = Vthreshold_start, Vthreshold_stop = Vthreshold_stop, n_injections = n_injections, mask_step = mask_step, n_pulse_heights = n_pulse_heights, thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'))


    def Testpulse_Scan(object, VTP_fine_start = None, VTP_fine_stop = None, n_injections = None, mask_step = None):
        if VTP_fine_start == None:
            print('> Please enter the VTP_fine_start value (0-511):')
            while(1):
                VTP_fine_start = input('>> ')
                try:
                    VTP_fine_start = int(VTP_fine_start)
                    break
                except:
                    if VTP_fine_start in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the VTP_fine_stop value (0-511):')
            while(1):
                VTP_fine_stop = input('>> ')
                try:
                    VTP_fine_stop = int(VTP_fine_stop)
                    break
                except:
                    if VTP_fine_stop in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of injections (1-65535):')
            while(1):
                n_injections = input('>> ')
                try:
                    n_injections = int(n_injections)
                    break
                except:
                    if n_injections in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of steps(4, 16, 64, 256):')
            while(1):
                mask_step = input('>> ')
                try:
                    mask_step = int(mask_step)
                    break
                except:
                    if mask_step in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            
        print ('Testpulse scan with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        TPX3_multiprocess_start.process_call(function = 'TestpulseScan', VTP_fine_start = VTP_fine_start, VTP_fine_stop = VTP_fine_stop, n_injections = n_injections, mask_step = mask_step, thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'))

    def Pixel_DAC_Optimisation(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911):')
            while(1):
                Vthreshold_start = input('>> ')
                try:
                    Vthreshold_start = int(Vthreshold_start)
                    break
                except:
                    if Vthreshold_start in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the Vthreshold_stop value (0-2911):')
            while(1):
                Vthreshold_stop = input('>> ')
                try:
                    Vthreshold_stop = int(Vthreshold_stop)
                    break
                except:
                    if Vthreshold_stop in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of injections (1-65535):')
            while(1):
                n_injections = input('>> ')
                try:
                    n_injections = int(n_injections)
                    break
                except:
                    if n_injections in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> Please enter the number of steps (4, 16, 64, 256):')
            while(1):
                mask_step = input('>> ')
                try:
                    mask_step = int(mask_step)
                    break
                except:
                    if mask_step in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        print ('Pixel DAC optimisation with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        TPX3_multiprocess_start.process_call(function = 'PixelDAC_opt', iteration = 0, Vthreshold_start = Vthreshold_start, Vthreshold_stop = Vthreshold_stop, n_injections = n_injections, mask_step = mask_step)

    def Set_DAC(object, DAC_Name = None, DAC_value = None):
        if DAC_Name == None:
            print('> Please enter the DAC-name from:\n    Ibias_Preamp_ON (0-255)\n    VPreamp_NCAS (0-255)\n    Ibias_Ikrum (0-255)\n    Vfbk (0-255)\n    Vthreshold_fine (0-511)\n    Vthreshold_coarse (0-15)\n    Ibias_DiscS1_ON (0-255)\n    Ibias_DiscS2_ON (0-255)\n    Ibias_PixelDAC (0-255)\n    Ibias_TPbufferIn (0-255)\n    Ibias_TPbufferOut (0-255)\n    VTP_coarse (0-255)\n    VTP_fine (0-511)\n    Ibias_CP_PLL (0-255)\n    PLL_Vcntrl (0-255)')
            DAC_Name = input('>> ')
            if DAC_Name in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'Ibias_CP_PLL', 'PLL_Vcntrl'}:
                print('> Please enter the DAC value (0-255):')
                while(1):
                    DAC_value = input('>> ')
                    try:
                        DAC_value = int(DAC_value)
                        break
                    except:
                        if DAC_value in exit_list:
                            return
                        else:
                            print('Input needs to be a number!')
            elif DAC_Name in {'Vthreshold_coarse'}:
                print('> Please enter the DAC value ( 0-15):')
                while(1):
                    DAC_value = input('>> ')
                    try:
                        DAC_value = int(DAC_value)
                        break
                    except:
                        if DAC_value in exit_list:
                            return
                        else:
                            print('Input needs to be a number!')
            elif DAC_Name in {'Vthreshold_fine', 'VTP_fine'}:
                print('> Please enter the DAC value (0-511):')
                while(1):
                    DAC_value = input('>> ')
                    try:
                        DAC_value = int(DAC_value)
                        break
                    except:
                        if DAC_value in exit_list:
                            return
                        else:
                            print('Input needs to be a number!')

        if DAC_Name in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'Ibias_CP_PLL', 'PLL_Vcntrl'}:
            if DAC_value >= 0 and DAC_value <= 255:
                TPX3_datalogger.write_value(name = DAC_Name, value = DAC_value)
                TPX3_datalogger.write_to_yaml(name = DAC_Name)
                print('> Set ' + DAC_Name + ' to value ' + str(DAC_value) + '.')
            else:
                print('> Value ' + str(DAC_value) + ' is not in range (0-255)')
        elif DAC_Name in {'Vthreshold_coarse'}:
            if DAC_value >= 0 and DAC_value <= 15:
                TPX3_datalogger.write_value(name = DAC_Name, value = DAC_value)
                TPX3_datalogger.write_to_yaml(name = DAC_Name)
                print('> Set ' + DAC_Name + ' to value ' + str(DAC_value) + '.')
            else:
                print('> Value ' + str(DAC_value) + ' is not in range (0-15)')
        elif DAC_Name in {'Vthreshold_fine', 'VTP_fine'}:
            if DAC_value >= 0 and DAC_value <= 511:
                TPX3_datalogger.write_value(name = DAC_Name, value = DAC_value)
                TPX3_datalogger.write_to_yaml(name = DAC_Name)
                print('> Set ' + DAC_Name + ' to value ' + str(DAC_value) + '.')
            else:
                print('> Value ' + str(DAC_value) + ' is not in range (0-511)')
        else:
            print('Unknown DAC-name')

    def Load_Equalisation(object, equal_path = None):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'scans')
        user_path = os.path.join(user_path, 'hdf')
        
        if equal_path == None:
            print('> Please enter the name of the equalisation you like to load:')
            equal_path = input('>> ')
        try:
            #look if path exists
            full_path = user_path + os.sep + equal_path
            if os.path.isfile(full_path) == True:
                TPX3_datalogger.write_value(name = 'Equalisation_path', value = full_path)
        except:
            print('Path does not exist')

    def Save_Equalisation(object, file_name = None):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'scans')
        user_path = os.path.join(user_path, 'hdf')
        
        if file_name == None:
            print('> Please enter the path of the name you like to save the equalisation under:')
            file_name = input('>> ')
        try:
            #look if path exists
            full_path = user_path + os.sep + file_name + '.h5'
            if os.path.isfile(full_path) == True:
                print('File already exists')
            else:
                current_equal = TPX3_datalogger.read_value(name = 'Equalisation_path')
                copy(current_equal, full_path)
        except:
            print('Could not write file')

    def Save_Backup(object, file_name = None):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        
        if file_name == None:
            print('> Please enter the path you like to save the backup under:')
            file_name = input('>> ')
        try:
            #look if path exists
            full_path = user_path + os.sep + file_name + '.TPX3'
            if os.path.isfile(full_path) == True:
                print('File already exists')
            else:
                file = open(full_path, "w")
                file_logger.write_backup(file = file)
        except:
            print('Could not write file')

    def Set_Polarity(object, polarity = None):
        if polarity == None:
            print('> Please enter the polarity (0 for positive or 1 for negative):')
            while(1):
                polarity = input('>> ')
                try:
                    polarity = int(polarity)
                    break
                except:
                    if polarity in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        if polarity == 1 or polarity == 0:
            TPX3_datalogger.write_value(name = 'Polarity', value = polarity)
            TPX3_datalogger.write_to_yaml(name = 'Polarity')
        else:
            print('Unknown polarity')
    
    def Set_operation_mode(object, Op_mode = None):
        if Op_mode == None:
            print('> Please enter the operation mode (0 for ToT and TOA, 1 for only TOA, 2 for Event Count & Integral ToT):')
            while(1):
                Op_mode = input('>> ')
                try:
                    Op_mode = int(Op_mode)
                    break
                except:
                    if Op_mode in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        if Op_mode >= 0 and Op_mode <= 2:
            TPX3_datalogger.write_value(name = 'Op_mode', value = Op_mode)
            TPX3_datalogger.write_to_yaml(name = 'Op_mode')
        else:
            print('Unknown operation mode')

    def Set_Fast_Io(object, Fast_Io_en = None):
        if Fast_Io_en == None:
            print('> Please enter the fast IO enable (0 for off or 1 for on):')
            while(1):
                Fast_Io_en = input('>> ')
                try:
                    Fast_Io_en = int(Fast_Io_en)
                    break
                except:
                    if Fast_Io_en in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        if Fast_Io_en == 1 or Fast_Io_en == 0:
            TPX3_datalogger.write_value(name = 'Fast_Io_en', value = Fast_Io_en)
            TPX3_datalogger.write_to_yaml(name = 'Fast_Io_en')
        else:
            print('Unknown polarity')

    def Set_Mask(object, mask_input_list = None):
        if mask_input_list == None:
            print('> Please enter what you like to mask: (commands are "row rownumber", "column columnnumber" or "pixel x y". Multiple entrys can be made by a "+" between them)')
            mask_input = input('>> ')
            mask_input_list = mask_input.split()

        mask_list = [[]]
        mask_element = []
        for element in mask_input_list:
            if not element == '+':
                mask_element.append(element)
            elif element == '+':
                mask_list.append(mask_element)
                mask_element = []
        mask_list.append(mask_element)
        mask_list.pop(0)
        #print(mask_list)
        for mask in mask_list:
            if mask[0] in {'row', 'Row'}:
                if len(mask) >= 2:
                    if int(mask[1]) >=0 and int(mask[1]) <256:
                        print('Mask row', int(mask[1]))
                        mask_logger.write_mask(mask_element = ['row', int(mask[1])])
                    else:
                        print('Row number out of range: There is only row 0 to 255')
                else: 
                    print('Error: No row number given!')
            elif mask[0] in {'column', 'Column'}:
                if len(mask) >= 2:
                    if int(mask[1]) >=0 and int(mask[1]) <256:
                        print('Mask column', int(mask[1]))
                        mask_logger.write_mask(mask_element = ['column', int(mask[1])])
                    else:
                        print('Column number out of range: There is only column 0 to 255')
                else: 
                    print('Error: No column number given!')
            elif mask[0] in {'pixel', 'Pixel'}:
                if len(mask) >= 3:
                    if int(mask[1]) >=0 and int(mask[1]) <256 and int(mask[2]) >=0 and int(mask[2]) <256:
                        print('Mask pixel', int(mask[1]), int(mask[2]))
                        mask_logger.write_mask(mask_element = ['pixel', int(mask[1]), int(mask[2])])
                    else:
                        print('Pixel number out of range: There is only 0 to 255 for x and y')
                else: 
                    print('Error: No full set of pixel coordinates. Needs x and y!')
            else:
                print('Unknown type:', mask)

    def Unset_Mask(object, mask_input_list = None):
        if not TPX3_datalogger.read_value(name = 'Mask_path') == None: 
            if mask_input_list == None:
                print('> Please enter what you like to unmask: (commands are "row rownumber", "column columnnumber", "pixel x y" or "all". Multiple entrys can be made by a "+" between them)')
                mask_input = input('>> ')
                mask_input_list = mask_input.split()

            mask_list = [[]]
            mask_element = []
            for element in mask_input_list:
                if not element == '+':
                    mask_element.append(element)
                elif element == '+':
                    mask_list.append(mask_element)
                    mask_element = []
            mask_list.append(mask_element)
            mask_list.pop(0)
            #print(mask_list)
            for mask in mask_list:
                if mask[0] in {'row', 'Row'}:
                    if len(mask) >= 2:
                        if int(mask[1]) >=0 and int(mask[1]) <256:
                            print('Unmask row', int(mask[1]))
                            mask_logger.delete_mask(mask_element = ['row', int(mask[1])])
                        else:
                            print('Row number out of range: There is only row 0 to 255')
                    else: 
                        print('Error: No row number given!')
                elif mask[0] in {'column', 'Column'}:
                    if len(mask) >= 2:
                        if int(mask[1]) >=0 and int(mask[1]) <256:
                            print('Unmask column', int(mask[1]))
                            mask_logger.delete_mask(mask_element = ['column', int(mask[1])])
                        else:
                            print('Column number out of range: There is only column 0 to 255')
                    else: 
                        print('Error: No column number given!')
                elif mask[0] in {'pixel', 'Pixel'}:
                    if len(mask) >= 3:
                        if int(mask[1]) >=0 and int(mask[1]) <256 and int(mask[2]) >=0 and int(mask[2]) <256:
                            print('Unmask pixel', int(mask[1]), int(mask[2]))
                            mask_logger.delete_mask(mask_element = ['pixel', int(mask[1]), int(mask[2])])
                        else:
                            print('Pixel number out of range: There is only 0 to 255 for x and y')
                    else: 
                        print('Error: No full set of pixel coordinates. Needs x and y!')
                elif mask[0] in {'all', 'All'}:
                    print('Unmask all')
                    mask_logger.delete_mask(mask_element = ['all'])
                else:
                    print('Unknown type:', mask)
        else:
            print('No mask file loaded, you cannot unmask nothing!')

    def Load_Mask(object, mask_path = None):
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'masks')
        
        if mask_path == None:
            print('> Please enter the name of the mask file you like to load:')
            mask_path = input('>> ')
        try:
            #look if path exists
            full_path = user_path + os.sep + mask_path
            if os.path.isfile(full_path) == True:
                TPX3_datalogger.write_value(name = 'Mask_path', value = full_path)
        except:
            print('Path does not exist')

    def Save_Mask(object, file_name = None):
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'masks')
        
        if file_name == None:
            print('> Please enter the the name you like to save the mask under:')
            file_name = input('>> ')
        try:
            #look if path exists
            full_path = user_path + os.sep + file_name + '.h5'
            if os.path.isfile(full_path) == True:
                print('File already exists')
            else:
                current_equal = TPX3_datalogger.read_value(name = 'Mask_path')
                copy(current_equal, full_path)
        except:
            print('Could not write file')

    def Run_Datataking(object, scan_timeout = None):
        if scan_timeout == None:
            print('> Please enter the required run time in seconds (choose 0 for an infinite run):')
            while(1):
                scan_timeout = input('>> ')
                try:
                    scan_timeout = int(scan_timeout)
                    break
                except:
                    if scan_timeout in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')

        if scan_timeout == 0:
            print('Infinite data taking run started! You can close the run with "ctrl. c"')
        else:
            print('{} s long data taking run started!'.format(scan_timeout))
            
        TPX3_multiprocess_start.process_call(function = 'DataTake', scan_timeout = scan_timeout, thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'), maskfile = TPX3_datalogger.read_value(name = 'Mask_path'))

    def Set_Acknowledgement(object, Acknowledgement_en = None):
        if Acknowledgement_en == None:
            print('> Please enter the Acknowledgement enable (0 for off or 1 for on):')
            while(1):
                Acknowledgement_en = input('>> ')
                try:
                    Acknowledgement_en = int(Acknowledgement_en)
                    break
                except:
                    if Acknowledgement_en in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        if Acknowledgement_en == 1 or Acknowledgement_en == 0:
            TPX3_datalogger.write_value(name = 'AckCommand_en', value = Acknowledgement_en)
            TPX3_datalogger.write_to_yaml(name = 'AckCommand_en')
        else:
            print('Unknown value')

    def Set_CLK_fast_mode(object, CLK_fast_mode_en = None):
        if CLK_fast_mode_en == None:
            print('> Please enter the CLK_fast_mode enable (0 for off or 1 for on):')
            while(1):
                CLK_fast_mode_en = input('>> ')
                try:
                    CLK_fast_mode_en = int(CLK_fast_mode_en)
                    break
                except:
                    if CLK_fast_mode_en in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        if CLK_fast_mode_en == 1 or CLK_fast_mode_en == 0:
            TPX3_datalogger.write_value(name = 'clk_fast_out', value = CLK_fast_mode_en)
            TPX3_datalogger.write_to_yaml(name = 'clk_fast_out')
        else:
            print('Unknown value')

    def Set_TP_ext_in(object, TP_ext_in_en = None):
        if TP_ext_in_en == None:
            print('> Please enter the TP_ext_in enable (0 for off or 1 for on):')
            while(1):
                TP_ext_in_en = input('>> ')
                try:
                    TP_ext_in_en = int(TP_ext_in_en)
                    break
                except:
                    if TP_ext_in_en in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        if TP_ext_in_en == 1 or TP_ext_in_en == 0:
            TPX3_datalogger.write_value(name = 'SelectTP_Ext_Int', value = TP_ext_in_en)
            TPX3_datalogger.write_to_yaml(name = 'SelectTP_Ext_Int')
        else:
            print('Unknown value')

    def Set_ClkOut_frequency(object, ClkOut_frequency = None):
        if ClkOut_frequency == None:
            print('> Please enter the desired ClkOut_frequency: "1" for 320MHz ; "2" for 160MHz; "3" for 80MHz; "4" for 40MHz; "5" for Extern')
            while(1):
                ClkOut_frequency = input('>> ')
                try:
                    ClkOut_frequency = int(ClkOut_frequency)
                    break
                except:
                    if ClkOut_frequency in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        if ClkOut_frequency >= 1 and ClkOut_frequency <= 5:
            TPX3_datalogger.write_value(name = 'ClkOut_frequency_src', value = ClkOut_frequency)
            TPX3_datalogger.write_to_yaml(name = 'ClkOut_frequency_src')
        else:
            print('Unknown value')




 ###################################################
 ###                                             ###
####                 CLI main                    ####
 ###                                             ###
 ###################################################


class TPX3_CLI_TOP(object):
    def __init__(self, ext_input_list = None):
        readline.set_completer(completer)
        readline.parse_and_bind("tab: complete")
        function_call = TPX3_CLI_function_call()
        expertmode = False
        print ('\n Welcome to the Timepix3 control Software\n')

        if not ext_input_list == None:
            cmd_list_element = []
            cmd_list = []
            for element in ext_input_list:
                if not element == '+':
                    cmd_list_element.append(element)
                elif element == '+':
                    cmd_list.append(cmd_list_element)
                    cmd_list_element = []
            cmd_list.append(cmd_list_element)
            cmd_list.append(['Quit'])#To exit loop at the end

        # Here the main part of the cli starts. Every usercomand needs to be processed here.
        while 1:

            #if no external input is given
            if ext_input_list == None:
                if expertmode == True:
                    cmd_input = input('expert> ')
                else:
                cmd_input = input('> ')
                #Catch if no input given
                if cmd_input == '':
                    print ('Something enter you must!')
                    inputlist = []
                else:
                    inputlist = cmd_input.split()
            #Input is given
            else:
                inputlist = cmd_list[0]
                cmd_input = ' '.join(cmd_list[0])
                print(inputlist)
                cmd_list.pop(0)
                print(cmd_list)
            
            if inputlist:
                #Help
                if inputlist[0] in {'Help', 'help', 'h', '-h'}:
                    if expertmode == False:
                    print('If you need detailed help on a function type [functionname -h].\n Possible options are:')
                    for function in help_functions:
                        print (function)
                    elif expertmode == True:
                        print('If you need detailed help on a function type [functionname -h].\n Possible options are:')
                        for function in expert_help_functions:
                            print (function)

                #ToT_Calibration
                elif inputlist[0] in {'ToT', 'ToT_Calibration', 'tot_Calibration', 'tot'}:
                    if len(inputlist) == 1:
                        print('ToT_Calibration')
                        try:
                            function_call.ToT_Calibration()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the ToT calibration. As arguments you can give the start testpulse value (0-511), the stop testpulse value (0-511) and the number of steps (4, 16, 64, 256).')
                        elif len(inputlist) < 4:
                            print ('Incomplete set of parameters:')
                            try:
                                function_call.ToT_Calibration()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 4:
                            try:
                                function_call.ToT_Calibration(VTP_fine_start = int(inputlist[1]), VTP_fine_stop = int(inputlist[2]), mask_step = int(inputlist[3]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 4:
                            print ('To many parameters! The given function takes only three parameters:\n start testpulse value (0-511),\n stop testpulse value (0-511),\n number of steps (4, 16, 64, 256).')

                #Threshold_Scan
                elif inputlist[0] in {'Threshold_Scan', 'THL_Scan', 'THL', 'threshold_scan', 'thl_scan', 'thl'}:
                    if len(inputlist) == 1:
                        print('Threshold_Scan')
                        try:
                            function_call.Threshold_Scan()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Threshold scan. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
                        elif len(inputlist) < 5:
                            print ('Incomplete set of parameters:')
                            try:
                                function_call.Threshold_Scan()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 5:
                            try:
                                function_call.Threshold_Scan(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 5:
                            print ('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')
               
                #Threshold_Calib
                elif inputlist[0] in {'Threshold_Calibration', 'THL_Calib', 'threshold_calibration', 'thl_calib',}:
                    if len(inputlist) == 1:
                        print('Threshold_Calibration')
                        try:
                            function_call.Threshold_Calib()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Threshold calibration. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535), the number of steps (4, 16, 64, 256) and the number of pulse height steps (2-100).')
                        elif len(inputlist) < 6:
                            print ('Incomplete set of parameters:')
                            try:
                                function_call.Threshold_Scan()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 6:
                            try:
                                function_call.Threshold_Scan(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]), n_pulse_height = int(inputlist[5]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 6:
                            print ('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256),\n number of pulse height steps (2-100).')

                #Testpulse_Scan
                elif inputlist[0] in {'Testpulse_Scan', 'TP_Scan', 'Tp_Scan' 'TP', 'testpulse_scan', 'tp_scan' 'tp'}:
                    if len(inputlist) == 1:
                        print('Testpulse_Scan')
                        try:
                            function_call.Testpulse_Scan()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Testpulse Scan. As arguments you can give the the start testpulse value (0-511), the stop testpulse value (0-511), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
                        elif len(inputlist) < 5:
                            print ('Incomplete set of parameters:')
                            try:
                                function_call.Testpulse_Scan()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 5:
                            try:
                                function_call.Testpulse_Scan(VTP_fine_start = int(inputlist[1]), VTP_fine_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 5:
                            print ('To many parameters! The given function takes only four parameters:\n start testpulse value (0-511),\n stop testpulse value (0-511),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')

                #Pixel_DAC_Optimisation
                elif inputlist[0] in {'Pixel_DAC_Optimisation', 'Pixel_DAC', 'PDAC', 'pixel_dac_optimisation', 'pixel_dac', 'pdac'}:
                    if len(inputlist) == 1:
                        print('Pixel_DAC_Optimisation')
                        try:
                            function_call.Pixel_DAC_Optimisation()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Pixel DAC Optimisation. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
                        elif len(inputlist) < 5:
                            print ('Incomplete set of parameters:')
                            try:
                                function_call.Pixel_DAC_Optimisation()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 5:
                            try:
                                function_call.Pixel_DAC_Optimisation(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 5:
                            print ('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')

                #Set_DAC
                elif inputlist[0] in {'Set_DAC', 'set_dac'}:
                    if len(inputlist) == 1:
                        print('Set_DAC')
                        try:
                            funkcion_call.Set_DAC()
                        except:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Set DAC function. As arguments you can give the DAC-name/DAC-number  and the new value.\n The following DACs are aviable:\n     1.) Ibias_Preamp_ON (0-255)\n     2.) VPreamp_NCAS (0-255)\n     3.) Ibias_Ikrum (0-255)\n     4.) Vfbk (0-255)\n     5.) Vthreshold_fine (0-511)\n     6.) Vthreshold_coarse (0-15)\n     7.) Ibias_DiscS1_ON (0-255)\n     8.) Ibias_DiscS2_ON (0-255)\n     9.) Ibias_PixelDAC (0-255)\n    10.) Ibias_TPbufferIn (0-255)\n    11.) Ibias_TPbufferOut (0-255)\n    12.) VTP_coarse (0-255)\n    13.) VTP_fine (0-511)\n    14.) Ibias_CP_PLL (0-255)\n    15.) PLL_Vcntrl (0-255)')                
                        elif len(inputlist) < 3:
                            print ('Incomplete set of parameters:')
                            try:
                                function_call.Set_DAC()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 3:
                            if inputlist[1] in {'1', 'Ibias_Preamp_ON'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Ibias_Preamp_ON', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'2', 'VPreamp_NCAS'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'VPreamp_NCAS', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'3', 'Ibias_Ikrum'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Ibias_Ikrum', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'4', 'Vfbk'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Vfbk', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'5', 'Vthreshold_fine'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Vthreshold_fine', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'6', 'Vthreshold_coarse'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Vthreshold_coarse', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'7', 'Ibias_DiscS1_ON'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Ibias_DiscS1_ON', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'8', 'Ibias_DiscS2_ON'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Ibias_DiscS2_ON', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'9', 'Ibias_PixelDAC'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Ibias_PixelDAC', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'10', 'Ibias_TPbufferIn'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Ibias_TPbufferIn', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'11', 'Ibias_TPbufferOut'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Ibias_TPbufferOut', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'12', 'VTP_coarse'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'VTP_coarse', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'13', 'VTP_fine'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'VTP_fine', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'14', 'Ibias_CP_PLL'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'Ibias_CP_PLL', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'15', 'PLL_Vcntrl'}:
                                try:
                                    function_call.Set_DAC(DAC_Name = 'PLL_Vcntrl', DAC_value = int(inputlist[2]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            else:
                                print ('Unknown DAC-name')
                        elif len(inputlist) > 3:
                            print ('To many parameters! The given function takes only two parameters:\n The DAC-name and its value.')

                #Data taking
                elif inputlist[0] in {'Run_Datataking', 'Run', 'Datataking', 'R', 'run_datataking', 'run', 'datataking', 'r'}:
                    if len(inputlist) == 1:
                        print('Run_Datataking')
                        try:
                            function_call.Run_Datataking()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the datataking function. As argument you can give the scan timeout (in seconds, if 0 is entered the datataking will run infinitely')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Run_Datataking(scan_timeout = int(inputlist[1]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n scan timeout (in seconds).')

                #Load equalisation
                elif inputlist[0] in {'Load_Equalisation', 'Load_Equal', 'LEQ','load_equalisation', 'load_equal', 'leq'}:
                    if len(inputlist) == 1:
                        print('Load_Equalisation')
                        try:
                            function_call.Load_Equalisation()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the load equalisation function. As argument you can give the path of the equalisation you like to load')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Load_Equalisation(equal_path = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n equalisation path.')

                #Save equalisation
                elif inputlist[0] in {'Save_Equalisation', 'Save_Equal', 'SEQ','save_equalisation', 'save_equal', 'seq'}:
                    if len(inputlist) == 1:
                        print('Save_Equalisation')
                        try:
                            function_call.Save_Equalisation()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the save equalisation function. As argument you can give the name of the equalisation file')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Save_Equalisation(file_name = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n equalisation file name.')

                #Save backup
                elif inputlist[0] in {'Save_Backup', 'Backup','save_backup', 'backup'}:
                    if len(inputlist) == 1:
                        print('Save_Backup')
                        try:
                            function_call.Save_Backup()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the save backup function. As argument you can give the name of the backup file')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Save_Backup(file_name = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n backup file name.')

                #Load backup
                elif inputlist[0] in {'Load_Backup', 'load_backup'}:
                    if len(inputlist) == 1:
                        print('Load_Backup')
                        try:
                            backup_data = file_logger.read_backup()
                            TPX3_datalogger.set_data(config = backup_data)
                            TPX3_datalogger.write_backup_to_yaml()
                            print('backup set')
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the load backup function. As argument you can give the name of the backup file you like to load')
                        elif len(inputlist) == 2:
                            try:
                                backup_data = file_logger.read_backup(file = (inputlist[1] + '.TPX3'))
                                TPX3_datalogger.set_data(config = backup_data)
                                TPX3_datalogger.write_backup_to_yaml()
                                print('backup set')
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n backup file name.')


                #Set polarity
                elif inputlist[0] in {'Set_Polarity', 'Set_Pol', 'Polarity', 'Pol','set_polarity', 'set_pol', 'polarity','pol'}:
                    if len(inputlist) == 1:
                        print('Set_Polarity')
                        try:
                            function_call.Set_Polarity()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the set polarity function. As argument you can give the polarity as {negative, neg, -, 1} or {positive, pos, +, 0}')
                        elif len(inputlist) == 2:
                            if inputlist[1] in {'negative', 'neg', '-', '1'}:
                                try:
                                    function_call.Set_Polarity(polarity = 1)
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[1] in {'positive', 'pos', '+', '0'}:
                                try:
                                    function_call.Set_Polarity(polarity = 0)
                                except KeyboardInterrupt:
                                    print('User quit')
                            else:
                                print('Unknown polarity use {negative, neg, -, 1} or {positive, pos, +, 0}')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n polarity.')

                #Set mask
                elif inputlist[0] in {'Set_Mask', 'Mask', 'set_mask', 'mask'}:
                    if len(inputlist) == 1:
                        print('Set_Mask')
                        try:
                            function_call.Set_Mask()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the set mask function. As argument you can give mask commands: "row rownumber", "column columnnumber" or "pixel x y". Multiple entrys can be made by a "+" between them')
                        elif len(inputlist) >= 2:
                            mask_input = inputlist[1:]
                            try:
                                function_call.Set_Mask(mask_input_list = mask_input)
                            except KeyboardInterrupt:
                                print('User quit')

                #Unset mask
                elif inputlist[0] in {'Unset_Mask', 'Unmask','unset_mask', 'unmask'}:
                    if len(inputlist) == 1:
                        print('Unset_Mask')
                        try:
                            function_call.Unset_Mask()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the unset mask function. As argument you can give mask commands: "row rownumber", "column columnnumber", "pixel x y" or "all" from the pixels you like to unmask. Multiple entrys can be made by a "+" between them')
                        elif len(inputlist) >= 2:
                            mask_input = inputlist[1:]
                            try:
                                function_call.Unset_Mask(mask_input_list = mask_input)
                            except KeyboardInterrupt:
                                print('User quit')

                #Load Mask
                elif inputlist[0] in {'Load_Mask', 'load_mask'}:
                    if len(inputlist) == 1:
                        print('Load_Mask')
                        try:
                            function_call.Load_Mask()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the load mask function. As argument you can give the name of the mask file you like to load')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Load_Mask(mask_path = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n mask file name.')

                #Save mask
                elif inputlist[0] in {'Save_Mask', 'save_mask'}:
                    if len(inputlist) == 1:
                        print('Save_ask')
                        try:
                            function_call.Save_Mask()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the save mask function. As argument you can give the name of the mask file')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Save_Mask(file_name = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n mask file name.')

                #Set operation mode
                elif inputlist[0] in {'Set_operation_mode', 'Set_Op_mode', 'Op_mode', 'set_operation_mode', 'set_Op_mode', 'op_mode'}:
                    if len(inputlist) == 1:
                        print('Set_operation_mode')
                        try:
                            function_call.Set_operation_mode()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Set operation mode function. As argument you can give the operation mode as 0 for ToT & ToA, 1 for only ToA or 2 for Event Count & Integral ToT')
                        elif len(inputlist) == 2:
                                try:
                                    function_call.Set_operation_mode(Op_mode = int(inputlist[1]))
                                except KeyboardInterrupt:
                                    print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n polarity.')

                #Set Fast Io mode
                elif inputlist[0] in {'Set_Fast_Io', 'Fast_Io', 'Fast_Io_en', 'set_fast_io', 'fast_io', 'fast_io_en'}:
                    if len(inputlist) == 1:
                        print('Set_Fast_Io')
                        try:
                            function_call.Set_Fast_Io()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Fast Io enable function. As argument you can give the enable as 0 (off) or 1 (on)')
                        elif len(inputlist) == 2:
                                try:
                                    function_call.Set_Fast_Io(Fast_Io_en = int(inputlist[1]))
                                except KeyboardInterrupt:
                                    print('User quit')
                        elif len(inputlist) > 2:
                            print ('To many parameters! The given function takes only one parameters:\n Fast Io enable.')

                #Set Default
                elif inputlist[0] in {'Set_Default', 'Default', 'set_default', 'default'}:
                    if len(inputlist) == 1:
                        print('Set Default')
                        try:
                            TPX3_datalogger.set_data(config = TPX3_datalogger.default_config())
                            TPX3_datalogger.write_backup_to_yaml()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the set default function. It sets everything back to default')
                        else :
                            print ('Set default does not take parameters!')

                #Initialise Hardware
                elif inputlist[0] in {'Initialise_Hardware', 'Init_Hardware', 'Init', 'initialise_hardware', 'init_hardware', 'init'}:
                    if len(inputlist) == 1:
                        print('Initialise Hardware')
                        try:
                            Chip_List = Init_Hardware.HardwareScan()
                            #print(Chip_List)
                            for n, chip in enumerate(Chip_List):
                                name = 'Chip' + str(n) + '_name'
                                TPX3_datalogger.write_value(name = name, value = chip)
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the initialise hardware function. It initialises the hardware and looks how many links and Chips are connected')
                        else :
                            print ('Initialise hardware does not take parameters!')

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
                        readline.set_completer(expert_completer)
                        #readline.parse_and_bind("tab: complete")
                        print('Welcome to the expert mode my dear friend. In this mode you can do more advanced things to the Timepix3. If you have no idea why you are here, type "expert" again.')
                    elif expertmode == True:
                        expertmode = False
                        readline.set_completer(completer)
                        #readline.parse_and_bind("tab: complete")
                        print('Goodbye my dear friend. I hope you enjoyed the world of experts. Enjoy your further stay in the normal mode.')

                #Quit
                elif inputlist[0] in {'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit'}:
                    file_logger.write_backup(file = file_logger.create_file())
                    file_logger.delete_tmp_backups()
                    print('Goodbye and have a nice day.')
                    break

                # Expert mode functions
                elif expertmode == True:

                    # Set CLK fast mode
                    if inputlist[0] in {'Set_CLK_fast_mode', 'set_clk_fast_mode', 'CLK_fast_mode', 'clk_fast_mode'}:
                        if len(inputlist) == 1:
                            print('Set CLK_fast_mode')
                            try:
                                function_call.Set_CLK_fast_mode()
                            except KeyboardInterrupt:
                                print('User quit')
                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This is the set CLK_fast_mode function. As argument you can give the enable as 0 (off) or 1 (on)')
                            elif len(inputlist) == 2:
                                    try:
                                        function_call.Set_CLK_fast_mode(CLK_fast_mode_en = int(inputlist[1]))
                                    except KeyboardInterrupt:
                                        print('User quit')
                            elif len(inputlist) > 2:
                                print ('To many parameters! The given function takes only one parameters:\n CLK_fast_mode enable.')

                    #Set Acknowledgement
                    elif inputlist[0] in {'Set_Acknowledgement', 'set_acknowledgement', 'Acknowledgement', 'acknowledgement'}:
                        if len(inputlist) == 1:
                            print('Set Acknowledgement')
                            try:
                                function_call.Set_Acknowledgement()
                            except KeyboardInterrupt:
                                print('User quit')
                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This is the set acknowledgement function. As argument you can give the enable as 0 (off) or 1 (on)')
                            elif len(inputlist) == 2:
                                    try:
                                        function_call.Set_Acknowledgement(Acknowledgement_en = int(inputlist[1]))
                                    except KeyboardInterrupt:
                                        print('User quit')
                            elif len(inputlist) > 2:
                                print ('To many parameters! The given function takes only one parameters:\n Acknowledgement enable.')

                    #Select TP_ext_in
                    elif inputlist[0] in {'Set_TP_ext_in', 'set_tp_ext_in', 'TP_ext_in', 'tp_ext_in'}:
                        if len(inputlist) == 1:
                            print('Set TP_ext_in')
                            try:
                                function_call.Set_TP_ext_in()
                            except KeyboardInterrupt:
                                print('User quit')
                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This is the set TP_ext_in function. As argument you can give the enable as 0 (off) or 1 (on)')
                            elif len(inputlist) == 2:
                                    try:
                                        function_call.Set_TP_ext_in(TP_ext_in_en = int(inputlist[1]))
                                    except KeyboardInterrupt:
                                        print('User quit')
                            elif len(inputlist) > 2:
                                print ('To many parameters! The given function takes only one parameters:\n TP_ext_in enable.')

                    #ClkOut_frequency_source
                    elif inputlist[0] in {'Set_ClkOut_frequency', 'set_clkout_frequency', 'ClkOut_frequency', 'clkout_frequency'}:
                        if len(inputlist) == 1:
                            print('Set ClkOut_frequency')
                            try:
                                function_call.Set_ClkOut_frequency()
                            except KeyboardInterrupt:
                                print('User quit')
                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This is the set ClkOut_frequency function. As argument you can give the desired frequency: 320MHz["1" or "320"]; 160MHz["2" or "160"]; 80MHz["3" or "80"]; 40MHz["4" or "40"]; Extern["5" or "Ext"]')
                            elif len(inputlist) == 2:
                                if inputlist[1] in {'1', '320'}:
                                    try:
                                        function_call.Set_ClkOut_frequency(ClkOut_frequency = 1)
                                    except KeyboardInterrupt:
                                        print('User quit')
                                elif inputlist[1] in {'2', '160'}:
                                    try:
                                        function_call.Set_ClkOut_frequency(ClkOut_frequency = 2)
                                    except KeyboardInterrupt:
                                        print('User quit')
                                elif inputlist[1] in {'3', '80'}:
                                    try:
                                        function_call.Set_ClkOut_frequency(ClkOut_frequency = 3)
                                    except KeyboardInterrupt:
                                        print('User quit')
                                elif inputlist[1] in {'4', '40'}:
                                    try:
                                        function_call.Set_ClkOut_frequency(ClkOut_frequency = 4)
                                    except KeyboardInterrupt:
                                        print('User quit')
                                elif inputlist[1] in {'5','Ext', 'ext'}:
                                    try:
                                        function_call.Set_ClkOut_frequency(ClkOut_frequency = 5)
                                    except KeyboardInterrupt:
                                        print('User quit')
                                else:
                                    print('Unknown argument')
                            elif len(inputlist) > 2:
                                print ('To many parameters! The given function takes only one parameters:\n ClkOut_frequency.')


                    #Unknown command
                    else:
                        print ('Unknown command: ', cmd_input, ' Use a language I understand.')

                #Unknown command
                else:
                    print ('Unknown command: ', cmd_input, ' Use a language I understand.')

if __name__ == "__main__":
    ext_input_list = sys.argv
    ext_input_list.pop(0)
    if ext_input_list == []:
        tpx3_cli = TPX3_CLI_TOP()
    else:
        tpx3_cli = TPX3_CLI_TOP(ext_input_list = ext_input_list)