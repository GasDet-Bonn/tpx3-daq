import readline
import sys
import os
import time
import numpy as np
from multiprocessing import Process, Queue, Pipe
from subprocess import Popen, PIPE
from shutil import copy

from tpx3.scans.ToTCalib import ToTCalib
from tpx3.scans.ThresholdScan import ThresholdScan
from tpx3.scans.TestpulseScan import TestpulseScan
from tpx3.scans.PixelDACopt import PixelDACopt
from tpx3.scans.EqualisationCharge import EqualisationCharge
from tpx3.scans.EqualisationNoise import EqualisationNoise
from tpx3.scans.DataTake import DataTake
from tpx3.scans.ThresholdCalib import ThresholdCalib
from tpx3.scans.TimewalkCalib import TimewalkCalib
from tpx3.scans.ScanHardware import ScanHardware
from tpx3.scans.NoiseScan import NoiseScan
from tpx3.scan_base import ConfigError
from UI.tpx3_logger import file_logger, mask_logger, equal_logger, TPX3_datalogger
from UI.GUI.converter import utils as conv_utils
from UI.GUI.converter.converter_manager import ConverterManager
from tpx3.utils import get_software_version, get_git_branch, get_git_commit, get_git_date, threshold_compose, threshold_decompose


# In this part all callable normal function names should be in the list functions
functions = ['ToT', 'ToT_Calibration', 'tot_Calibration', 'tot',
                'Timewalk_Calibration', 'Timewalk', 'timewalk_calibration', 'timewalk',
                'Threshold_Scan', 'THL_Scan', 'THL', 'threshold_scan', 'thl_scan', 'thl',
                'Threshold_Calibration', 'THL_Calib', 'threshold_calibration', 'thl_calib',
                'Pixel_DAC_Optimisation', 'Pixel_DAC', 'PDAC', 'pixel_dac_optimisation', 'pixel_dac', 'pdac',
                'Equalisation', 'Equal', 'EQ', 'equalisation', 'equal', 'eq',
                'Testpulse_Scan', 'TP_Scan', 'Tp_Scan' 'TP', 'testpulse_scan', 'tp_scan' 'tp',
                'Noise_Scan', 'Noise', 'noise_scan', 'noise',
                'Initialise_Hardware', 'Init_Hardware', 'Init', 'initialise_hardware', 'init_hardware', 'init',
                'Run_Datataking', 'Run', 'Datataking', 'R', 'run_datataking', 'run', 'datataking', 'r',
                'Set_DAC', 'set_dac',
                'Select_Chips', 'select_chips', 'chips', 'chip',
                'Load_Equalisation', 'Load_Equal', 'LEQ','load_equalisation', 'load_equal', 'leq',
                'Save_Equalisation', 'Save_Equal', 'SEQ','save_equalisation', 'save_equal', 'seq',
                'Uniform_Equalisation', 'Uniform_Equal', 'UE', 'uniform_equalisation', 'uniform_equal', 'ue',
                'Save_Backup', 'Backup','save_backup', 'backup',
                'Load_Backup', 'load_backup',
                'Set_Default', 'Default', 'set_default', 'default',
                'GUI',
                'Set_Polarity', 'Set_Pol', 'Polarity', 'Pol','set_polarity', 'set_pol', 'polarity','pol',
                'Set_Mask', 'Mask', 'set_mask', 'mask',
                'Unset_Mask', 'Unmask','unset_mask', 'unmask',
                'Load_Mask', 'load_mask',
                'Save_Mask', 'save_mask',
                'TP_Period', 'tp_period',
                'Set_operation_mode', 'Set_Op_mode', 'Op_mode', 'set_operation_mode', 'set_Op_mode', 'op_mode',
                'Set_Fast_Io', 'Fast_Io', 'set_fast_io', 'fast_io', 'Fast_Io_en', 'fast_io_en',
                'Set_Readout_Intervall', 'set_readout_intervall', 'Readout_Intervall', 'readout_intervall',
                'Set_Run_Name', 'Run_Name', 'set_run_name', 'run_name',
                'Get_Run_Name', 'get_run_name',
                'Get_Link_Configuration', 'get_link_configuration', 'links', 'link_config',
                'Enable_Chips', 'enable_chips',
                'Plot', 'plot',
                'Stop_Plot', 'stop_plot',
                'Expert', 'expert',
                'Chip_names', 'chip_names', 'Who', 'who',
                'Mask_name', 'mask_name',
                'Equalisation_name', 'equalisation_name', 'Equal_name', 'equal_name',
                'Get_DAC_Values', 'get_dac_values', 'DAC_Values', 'dac_values'
                'About', 'about',
                'Help', 'help', 'h', '-h',
                'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit']

# In this part all callable expert function names should be in the list expert_functions
expert_functions = ['Set_CLK_fast_mode', 'set_clk_fast_mode', 'CLK_fast_mode', 'clk_fast_mode',
                    'Set_Acknowledgement', 'set_acknowledgement', 'Acknowledgement', 'acknowledgement',
                    'Set_TP_ext_in', 'set_tp_ext_in', 'TP_ext_in', 'tp_ext_in',
                    'Set_ClkOut_frequency', 'set_clkout_frequency', 'ClkOut_frequency', 'clkout_frequency',
                    'Set_Sense_DAC', 'set_sense_DAC', 'Sense_DAC', 'sense_DAC',
                    'Enable_Link', 'enable_link', 'Disable_Link', 'disable_link']

# In this list all functions are named which will be shown when the help command is used
help_functions = ['ToT_Calibration', 'Timewalk_Calibration', 'Threshold_Scan', 'Threshold_Calibration', 'Pixel_DAC_Optimisation', 'Equalisation',
                    'Noise_Scan', 'Testpulse_Scan', 'Initialise_Hardware', 'Run_Datataking', 'Set_DAC', 'Load_Equalisation', 'Save_Equalisation',
                    'Uniform_Equalisation', 'Save_Backup', 'Load_Backup', 'Select_Chips', 'Set_Default', 'GUI', 'Set_Polarity', 'Set_Mask', 'Unset_Mask', 'Load_Mask',
                    'Save_Mask', 'TP_Period', 'Set_operation_mode', 'Set_Fast_Io', 'Set_Readout_Intervall', 'Set_Run_Name', 'Get_Run_Name',
                    'Plot', 'Stop_Plot', 'Chip_names', 'Mask_name', 'Equalisation_name','Get_DAC_Values', 'Get_Link_Configuration', 'About', 'Help', 'Quit']

help_expert = ['Set_CLK_fast_mode', 'Set_Acknowledgement', 'Set_TP_ext_in', 'Set_ClkOut_frequency', 'Set_Sense_DAC', 'Enable_Link', 'Enable_Chips']

expert_help_functions = help_functions + help_expert

# In this list all exit commands for the TPX3 CLI functions are defined
exit_list = ['Quit', 'quit', 'q', 'Q', 'Exit', 'exit']

# Auto completion for all functions in the "function" list
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


def Set_DAC_value(DAC_Name):
    if DAC_Name in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'Ibias_CP_PLL', 'PLL_Vcntrl'}:
        range_max = 255
    elif DAC_Name in {'Vthreshold_coarse'}:
        range_max = 15
    elif DAC_Name in {'Vthreshold_fine', 'VTP_fine'}:
        range_max = 511
    elif DAC_Name in {'Vthreshold_combined'}:
        range_max = 2911
    else:
        print(f'Not a valid DAC name: {DAC_Name}')
        return

    print(f'> Please enter the DAC value of {DAC_Name} in range (0-{range_max}):')
    while(1):
        DAC_value = input('>> ')
        try:
            DAC_value = int(DAC_value)
            if DAC_value in range(range_max+1):
                return DAC_value
            else:
                print(f'> Value for DAC {DAC_Name} {DAC_value} is not in range (0-{range_max})')
        except:
            if DAC_value in exit_list:
                return
            else:
                print('Input needs to be a number!')
    

def Set_DAC_name():
    while(True):
        print('> Please enter the DAC name or number from:\n     1.) Ibias_Preamp_ON (0-255)\n     2.) VPreamp_NCAS (0-255)\n     3.) Ibias_Ikrum (0-255)\n     4.) Vfbk (0-255)\n     5.) Vthreshold_fine (0-511)\n     6.) Vthreshold_coarse (0-15)\n     7.) Vthreshold_combined (0-2911)\n     8.) Ibias_DiscS1_ON (0-255)\n     9.) Ibias_DiscS2_ON (0-255)\n    10.) Ibias_PixelDAC (0-255)\n    11.) Ibias_TPbufferIn (0-255)\n    12.) Ibias_TPbufferOut (0-255)\n    13.) VTP_coarse (0-255)\n    14.) VTP_fine (0-511)\n    15.) Ibias_CP_PLL (0-255)\n    16.) PLL_Vcntrl (0-255)')
        DAC_Name = input('>> ')
        if DAC_Name.isnumeric():
            DAC_Name = int(DAC_Name)
            if DAC_Name == 1:
                return 'Ibias_Preamp_ON'
            elif DAC_Name == 2:
                return 'VPreamp_NCAS'
            elif DAC_Name == 3:
                return 'Ibias_Ikrum'
            elif DAC_Name == 4:
                return 'Vfbk'
            elif DAC_Name == 5:
                return 'Vthreshold_fine'
            elif DAC_Name == 6:
                return 'Vthreshold_coarse'
            elif DAC_Name == 7:
                return 'Vthreshold_combined'
            elif DAC_Name == 8:
                return 'Ibias_DiscS1_ON'
            elif DAC_Name == 9:
                return 'Ibias_DiscS2_ON'
            elif DAC_Name == 10:
                return 'Ibias_PixelDAC'
            elif DAC_Name == 11:
                return 'Ibias_TPbufferIn'
            elif DAC_Name == 12:
                return 'Ibias_TPbufferOut'
            elif DAC_Name == 13:
                return 'VTP_coarse'
            elif DAC_Name == 14:
                return 'VTP_fine'
            elif DAC_Name == 15:
                return 'Ibias_CP_PLL'
            elif DAC_Name == 16:
                return 'PLL_Vcntrl'
        elif DAC_Name in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine', 'Vthreshold_coarse',
                        'Vthreshold_combined', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 'Ibias_TPbufferIn',
                        'Ibias_TPbufferOut', 'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl'}:
            return DAC_Name
        else:
            print(f'> {DAC_Name} not a valid DAC name.')

# This class starts a new process when a function is called. this is used for all TPX3 Scan functions and the datataking function. 
# With this you can end a wrong started function with "Ctrl. c" without ending the whole CLI.
class TPX3_multiprocess_start(object):
    def process_call(function, **kwargs):
        if function != "ScanHardware":
            run_name = TPX3_datalogger.get_run_name(scan_type = function)
        else:
            run_name = ""

        def startup_func(function, run_name, **kwargs):
            system_exit = False
            scan_error = False
            scan = None
            call_func = (function + '(run_name = "' + run_name + '")')
            scan = eval(call_func)
            try:
                scan.start(**kwargs)
            except KeyboardInterrupt:
                sys.exit(1)
            except ValueError as e:
                print(e)
                scan_error = True
            except ConfigError:
                print('The current link configuration is not valid. Please start "Init" or check your hardware.')
                scan_error = True
            except NotImplementedError:
                pass
            except SystemExit:
                system_exit = True
            if system_exit == False and scan_error == False:
                try:
                    scan.analyze(**kwargs)
                except KeyboardInterrupt:
                    sys.exit(1)
                except NotImplementedError:
                    pass
                except SystemExit:
                    system_exit = True
            if system_exit == False and scan_error == False:
                try:
                    scan.plot(**kwargs)
                except KeyboardInterrupt:
                    sys.exit(1)
                except NotImplementedError:
                    pass
                except SystemExit:
                    system_exit = True

            status = kwargs.pop('status', None)
            if status != None and system_exit != True:
                status.put('Scan finished')

        file_logger.write_tmp_backup()
        new_process = Process(target = startup_func, args = (function, run_name, ), kwargs = kwargs)
        new_process.start()
        return new_process


class TPX3_CLI_function_call(object):
    TPX3_multiprocess_start = TPX3_multiprocess_start()

    def ToT_Calibration(object, VTP_fine_start = None, VTP_fine_stop = None, mask_step = None):
        if VTP_fine_start == None:
            print('> Please enter the VTP_fine_start value (0-511)[200]:')
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
            print('> Please enter the VTP_fine_stop value (0-511)[500]:')
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
            print('> Please enter the number of steps (4, 16, 64, 256)[16]:')
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

        print('ToT calibration with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'mask_step =', mask_step)
        new_process = TPX3_multiprocess_start.process_call(function = 'ToTCalib',
                                                           VTP_fine_start = VTP_fine_start,
                                                           VTP_fine_stop = VTP_fine_stop,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()

    def Timewalk_Calibration(object, VTP_fine_start = None, VTP_fine_stop = None, mask_step = None):
        if VTP_fine_start == None:
            print('> Please enter the VTP_fine_start value (1-511)[200]:')
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
            print('> Please enter the VTP_fine_stop value (1-511)[500]:')
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
            print('> Please enter the number of steps(4, 16, 64, 256)[64]:')
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
        
        print('Timewalk calibration with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =', VTP_fine_stop, 'mask_step =', mask_step)
        new_process = TPX3_multiprocess_start.process_call(function = 'TimewalkCalib',
                                                           VTP_fine_start = VTP_fine_start,
                                                           VTP_fine_stop = VTP_fine_stop,
                                                           mask_step = mask_step,
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()

    def Threshold_Scan(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911)[1400]:')
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
            print('> Please enter the Vthreshold_stop value (0-2911)[2900]:')
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
            print('> Please enter the number of injections (1-65535)[100]:')
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
            print('> Please enter the number of steps (4, 16, 64, 256)[16]:')
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

        print('Threshold scan with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step = ', mask_step)
        new_process = TPX3_multiprocess_start.process_call(function = 'ThresholdScan',
                                                           Vthreshold_start = Vthreshold_start,
                                                           Vthreshold_stop = Vthreshold_stop,
                                                           n_injections = n_injections,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()

    def Threshold_Calib(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None, n_pulse_heights = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911)[1400]:')
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
            print('> Please enter the Vthreshold_stop value (0-2911)[2900]:')
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
            print('> Please enter the number of injections (1-65535)[100]:')
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
            print('> Please enter the number of steps(4, 16, 64, 256)[16]:')
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
            print('> Please enter the number of pulse height steps (2-100)[4]:')
            while(1):
                n_pulse_heights = input('>> ')
                try:
                    n_pulse_heights = int(n_pulse_heights)
                    break
                except:
                    if n_pulse_heights in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')

        print('Threshold scan with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step = ', mask_step, 'Number of pulse heights = ', n_pulse_heights)
        new_process = TPX3_multiprocess_start.process_call(function = 'ThresholdCalib',
                                                           iteration = 0,
                                                           Vthreshold_start = Vthreshold_start,
                                                           Vthreshold_stop = Vthreshold_stop,
                                                           n_injections = n_injections,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           n_pulse_heights = n_pulse_heights,
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()

    def Testpulse_Scan(object, VTP_fine_start = None, VTP_fine_stop = None, n_injections = None, mask_step = None):
        if VTP_fine_start == None:
            print('> Please enter the VTP_fine_start value (0-511)[200]:')
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
            print('> Please enter the VTP_fine_stop value (0-511)[500]:')
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
            print('> Please enter the number of injections (1-65535)[100]:')
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
            print('> Please enter the number of steps (4, 16, 64, 256)[16]:')
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

        print('Testpulse scan with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        new_process = TPX3_multiprocess_start.process_call(function = 'TestpulseScan',
                                                           VTP_fine_start = VTP_fine_start,
                                                           VTP_fine_stop = VTP_fine_stop,
                                                           n_injections = n_injections,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()

    def Pixel_DAC_Optimisation(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, offset = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911)[1400]:')
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
            print('> Please enter the Vthreshold_stop value (0-2911)[2900]:')
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
            print('> Please enter the number of injections (1-65535)[100]:')
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
            print('> Please enter the column offset (0-15)[0]:')
            while(1):
                offset = input('>> ')
                try:
                    offset = int(offset)
                    break
                except:
                    if offset in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        print('Pixel DAC optimisation with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'offset =', offset)
        pixeldac_result = Queue()
        new_process = TPX3_multiprocess_start.process_call(function = 'PixelDACopt',
                                                           iteration = 0,
                                                           Vthreshold_start = Vthreshold_start,
                                                           Vthreshold_stop = Vthreshold_stop,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           n_injections = n_injections,
                                                           offset = offset,
                                                           result = pixeldac_result,
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()
        TPX3_datalogger.write_value(name = 'Ibias_PixelDAC', value = pixeldac_result.get())
        TPX3_datalogger.write_to_yaml(name = 'Ibias_PixelDAC')

    def Equalisation(object, Vthreshold_start = None, Vthreshold_stop = None, n_injections = None, mask_step = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911)[1400]:')
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
            print('> Please enter the Vthreshold_stop value (0-2911)[2900]:')
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
            print('> Please enter the number of injections (1-65535)[100]:')
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
            print('> Please enter the number of steps (4, 16, 64, 256)[16]:')
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

        print('Equalisation with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        result_path = Queue()
        new_process = TPX3_multiprocess_start.process_call(function = 'EqualisationCharge',
                                                           Vthreshold_start = Vthreshold_start,
                                                           Vthreshold_stop = Vthreshold_stop,
                                                           n_injections = n_injections,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           result_path = result_path,
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()
        TPX3_datalogger.write_value(name = 'Equalisation_path', value = result_path.get())

    def Noise_Scan(object, Vthreshold_start = None, Vthreshold_stop = None, shutter = None):
        if Vthreshold_start == None:
            print('> Please enter the Vthreshold_start value (0-2911)[1400]:')
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
            print('> Please enter the Vthreshold_stop value (0-2911)[2900]:')
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
            print('> Please enter a shutter length in seconds [0.01]:')
            while(1):
                shutter = input('>> ')
                try:
                    shutter = float(shutter)
                    break
                except:
                    if shutter in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')

        print(f'Noise scan with threshold start = {Vthreshold_start}, threshold stop = {Vthreshold_stop}, shutter length in seconds = {shutter}')
        new_process = TPX3_multiprocess_start.process_call(function = 'NoiseScan',
                                                           Vthreshold_start = Vthreshold_start,
                                                           Vthreshold_stop = Vthreshold_stop,
                                                           shutter = shutter,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()

    def Set_DAC(object, DAC_Name = None, DAC_value = None, chip_selection = None):
        menu = 1
        while menu:
            print(f'> Your current chip selection is {chip_selection}')
            print('> Do you want to give every chip the same value (y/n)?:')
            same_value = input('>> ')
            if same_value in ['yes', 'y', '1']:
                print('All chips get the same value here!')
                DAC_Name  = Set_DAC_name()
                DAC_value = Set_DAC_value(DAC_Name)
                for chip in chip_selection:
                    self.Set_DAC_chip(chip, DAC_Name, DAC_value)  
            elif same_value in ['no', 'n', '0']:
                print('Iterate over all chips and select DAC values individually.')
                for chip in chip_selection:
                    DAC_Name  = Set_DAC_name()
                    DAC_value = Set_DAC_value(DAC_Name)
                    self.Set_DAC_chip(chip, DAC_Name, DAC_value)
            else:
                print('I don\'t understand, go to the beginning')
            
            valid = 1
            while valid:
                print('Do you want to stay in the menu and configure other DACs for the same selection of chips (y/n)?')
                continue_menu = input('>> ')
                if continue_menu in ['yes','no','y','n','0','1']:
                    valid = 0
                else:
                    print('I don\'t understand ...\n' )
                    continue
                if continue_menu in ['0', 'n', 'no']:
                    menu = 0
                    print('Exiting Set DAC menu ...')
                elif continue_menu in ['yes', 'y', '1']:
                    pass

    def Set_DAC_chip(object, chip, DAC_Name, DAC_value):
        if DAC_Name in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Ibias_DiscS1_ON',
                        'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut',
                        'VTP_coarse', 'Ibias_CP_PLL', 'PLL_Vcntrl', 'Vthreshold_coarse', 'Vthreshold_fine', 'VTP_fine'}:
            TPX3_datalogger.write_value(name = DAC_Name, value = DAC_value, chip = chip)
            TPX3_datalogger.write_to_yaml(name = DAC_Name, chip = chip)
            print(f'> Set {DAC_Name} to value {DAC_value}.')
        elif DAC_Name in {'Vthreshold_combined'}:
            fine, coarse = threshold_decompose(DAC_value)
            TPX3_datalogger.write_value(name = 'Vthreshold_fine', value = fine, chip = chip)
            TPX3_datalogger.write_to_yaml(name = 'Vthreshold_fine', chip = chip)
            TPX3_datalogger.write_value(name = 'Vthreshold_coarse', value = coarse, chip = chip)
            TPX3_datalogger.write_to_yaml(name = 'Vthreshold_coarse', chip = chip)
            print(f'> Set {DAC_Name} to value {DAC_value}.')
            print(f'> This corresponds to Vthreshold_fine {fine} and Vthreshold_coarse {coarse}.')
        else:
            print(f'{DAC_Name}: Unknown DAC name.')

    def set_advanced_DAC(object, chip_list=None, DAC_name=None, DAC_value=None):
        all  = 1
        menu = 1
        while(menu):
            print('In set_advanced_DAC function ...')
            print(f'Selected chips: {chip_list}')
            print(f'Selected DAC: {DAC_name}')
            print(f'Current values: ')
            for chip in chip_list:
                a = 'chip_dacs'
                print(f'{chip}\t{TPX3_datalogger.data[a][chip][DAC_name]}')
            
            while(True):
                print('> Do you want to give every chip the same value (y/n)?:')
                user_input = input('>> ')            
                if user_input in ('y', 'yes', 'Yes', 'Y', '1'):
                    all = 1
                    break
                elif user_input in ('n', 'no', 'N', 'No' '0'):
                    all = 0
                    break
                else:
                    print('Input needs to be Yes/y/1 or No/no/0!')
            
            # normal mode
            if DAC_name == 'Polarity':
                valid_options = [0,1]
                print('> Please enter the polarity (0 for positive or 1 for negative)')    
            elif DAC_name == 'Op_mode':
                valid_options = [0,1,2]
                print('> Please enter the operation mode (0 for ToT and TOA, 1 for only TOA, 2 for Event Count & Integral ToT)')
            elif DAC_name == 'Fast_Io_en':
                valid_options = [0,1]
                print('> Please enter the fast IO enable (0 for off or 1 for on)')
            # expert mode
            elif DAC_name == 'clk_fast_out':
                valid_options = [0,1]
                print('> Please enter the CLK_fast_mode enable (0 for off or 1 for on):')
            elif DAC_name == 'ClkOut_frequency_src':
                valid_options = [1,2,3,4,5]
                print('> Please enter the desired ClkOut_frequency: "1" for 320MHz ; "2" for 160MHz; "3" for 80MHz; "4" for 40MHz; "5" for Extern')
            elif DAC_name == 'AckCommand_en':
                valid_options = [0,1]
                print('> Please enter the Acknowledgement enable (0 for off or 1 for on):')
            elif DAC_name == 'SelectTP_Ext_Int':
                valid_options = [0,1]
                print('> Please enter the TP_ext_in enable (0 for off or 1 for on):')
            elif DAC_name == 'Sense_DAC':
                valid_options = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,28,29,30,31]
                print('> Please enter the desired DAC Number: Off["0"]; Ibias_Preamp_ON["1"]; Ibias_Preamp_OFF["2"]; VPreamp_NCAS["3"]; Ibias_Ikrum["4"]; Vfbk["5"]; Vthreshold_fine["6"]; Vtreshold_corse["7"]; IBias_DiscS1_ON["8"]; IBias_DiscS1_OFF["9"]; IBias_DiscS2_ON["10"]; IBias_DiscS2_OFF["11"]; IBias_PixelDAC["12"]; IBias_TPbufferIn["13"]; IBias_TPbufferOut["14"]; VTP_coarse["15"]; VTP_fine["16"]; Ibias_CP_PLL["17"]; PLL_Vcntrl["18"]; BandGap_output["28"]; BandGap_Temp["29"]; Ibias_dac["30"]; Ibias_dac_cas["31"]')

            if all:
                print(f'For all chips: {chip_list}')
                while(True):
                    value = input('>> ')
                    try:
                        value = int(value)
                        if value in valid_options:
                            break
                        else:
                            print('Invalid option!')
                    except:
                        if value in exit_list:
                            return
                        else:
                            print('Input needs to be a number!')
                for chip in chip_list:
                    TPX3_datalogger.write_value(name = DAC_name, value = value, chip = chip)
                    TPX3_datalogger.write_to_yaml(name = DAC_name, chip = chip)
            else:
                for chip in chip_list:
                    print(f'For chip {chip}')
                    while(True):
                        value = input('>> ')
                        try:
                            value = int(value)
                            if value in valid_options:
                                break
                            else:
                                print('Invalid option!')
                        except:
                            if value in exit_list:
                                return
                            else:
                                print('Input needs to be a number!')
                    TPX3_datalogger.write_value(name = DAC_name, value = value, chip = chip)
                    TPX3_datalogger.write_to_yaml(name = DAC_name, chip = chip)

            while(True):
                stay_in_menu = input('>> Do you want to stay in this menu (y/n)?: ')

                if stay_in_menu in ('y', 'yes', 'Y', 'Yes', '1'):
                    print('YES')
                    break
                elif stay_in_menu in ('n', 'no', 'N', 'No' '0'):
                    print('NO! Exiting Set advanced DAC menu ...')
                    menu = 0
                    break
                else:
                    print('I don\'t understand ...')

    def Load_Equalisation(object, equal_path = None, chip = None):
        active_file     = TPX3_datalogger.data['Equalisation_path'][chip]['active'] 
        available_files = list(TPX3_datalogger.data['Equalisation_path'][chip]['available'])
        print(f'The currently selected mask file for chip {chip}:')
        print(f'\t\t{active_file}')
        print('Select from available files:')
        for num, f in enumerate(available_files):
            print(f'{num}\t{available_files[num]}')
        while(True):
            selection = input('>> ')
            try:
                TPX3_datalogger.data['Equalisation_path'][chip]['active'] = available_files[int(selection)]
                print(f'You chose file {available_files[int(selection)]}')
                break
            except:
                print(f'This option does not exist! Try again or press ctrl-c ...')

    def Save_Equalisation(object, file_name = None):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'equalisations')

        if file_name == None:
            print('> Please enter the path of the name you like to save the equalisation under (without ".h5"):')
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
        else:
            print('> Saved equalisation to ' + full_path)

    def Uniform_Equalisation(object, pixel_threshold = None, chip = None):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'equalisations')
        user_path = os.path.join(user_path, chip)

        if pixel_threshold == None:
            print('> Please enter pixel threshold [0-15] that should be set for all pixels:')
            while True:
                try:
                    entered_text = input('>> ')
                    if entered_text in exit_list:
                        return
                    pixel_threshold = int(entered_text)
                    if pixel_threshold < 0 or pixel_threshold > 15:
                        raise ValueError
                except ValueError:
                    print('> Entered text is not valid. Please enter an integer between 0 and 15:')
                else:
                    break
        
        uniform_equalisation_array = np.full((256, 256), dtype=np.uint8, fill_value=pixel_threshold)
        full_path = f'{user_path}{os.sep}{chip}_Uniform_thr_{pixel_threshold}.h5'
        equal_logger.write_full_equal(full_equal = uniform_equalisation_array, path = full_path)
        print(f'> Set a uniform equalisation matrix with pixel threshold {pixel_threshold} for chip {chip}.')

    def Save_Backup(object, file_name = None):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')

        if file_name == None:
            print('> Please enter the path you like to save the backup under (without ".TPX3"):')
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
        else:
            print('> Saved backup to ' + full_path)

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
            print('Unknown value')

    def Set_Run_Name(object, run_name = None):
        if run_name == None:
            print('> Please enter the file name addition for the run data file:')
            run_name = input('>> ')
        TPX3_datalogger.write_value(name = 'Run_name', value = run_name) 

    def Set_Mask(object, mask_input_list = None, chip = None, mask_file = None):
        if mask_input_list == None:
            print('> Please enter what you like to mask: (commands are "all", "row rownumber", "column columnnumber" or "pixel x y". Multiple entries can be made by a "+" between them)')
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
        for mask in mask_list:
            if mask[0] in {'all', 'All', 'a'}:
                print('Mask all')
                mask_logger.write_mask(mask_element = ['all'])
            elif mask[0] in {'row', 'Row', 'r'}:
                if len(mask) >= 2:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256:
                        print('Mask row', int(mask[1]))
                        mask_logger.write_mask(mask_element = ['row', int(mask[1])], file_path = mask_file, chip=chip)
                    else:
                        print('Row number out of range: There is only row 0 to 255')
                else:
                    print('Error: No row number given!')
            elif mask[0] in {'column', 'Column', 'c'}:
                if len(mask) >= 2:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256:
                        print('Mask column', int(mask[1]))
                        mask_logger.write_mask(mask_element = ['column', int(mask[1])], file_path = mask_file, chip=chip)
                    else:
                        print('Column number out of range: There is only column 0 to 255')
                else:
                    print('Error: No column number given!')
            elif mask[0] in {'pixel', 'Pixel', 'p'}:
                if len(mask) >= 3:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256 and int(mask[2]) >= 0 and int(mask[2]) < 256:
                        print('Mask pixel', int(mask[1]), int(mask[2]))
                        mask_logger.write_mask(mask_element = ['pixel', int(mask[1]), int(mask[2])], file_path = mask_file, chip=chip)
                    else:
                        print('Pixel number out of range: There is only 0 to 255 for x and y')
                else:
                    print('Error: No full set of pixel coordinates. Needs x and y!')
            else:
                print('Unknown type:', mask)

    def Unset_Mask(object, mask_input_list = None, chip = None, mask_file = None):
        if mask_file in TPX3_datalogger.data['Mask_path'][chip]['available']:
            if mask_input_list == None:
                print('> Please enter what you like to unmask: (commands are "all", "row rownumber", "column columnnumber", "pixel x y" or "all". Multiple entries can be made by a "+" between them)')
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
            for mask in mask_list:
                if mask[0] in {'all', 'All', 'a'}:
                    print('Unmask all')
                    mask_logger.delete_mask(mask_element = ['all'])
                elif mask[0] in {'row', 'Row', 'r'}:
                    if len(mask) >= 2:
                        if int(mask[1]) >= 0 and int(mask[1]) < 256:
                            print('Unmask row', int(mask[1]))
                            mask_logger.delete_mask(mask_element = ['row', int(mask[1])], file_path = mask_file, chip = chip)
                        else:
                            print('Row number out of range: There is only row 0 to 255')
                    else:
                        print('Error: No row number given!')
                elif mask[0] in {'column', 'Column', 'c'}:
                    if len(mask) >= 2:
                        if int(mask[1]) >= 0 and int(mask[1]) < 256:
                            print('Unmask column', int(mask[1]))
                            mask_logger.delete_mask(mask_element = ['column', int(mask[1])],file_path = mask_file, chip = chip)
                        else:
                            print('Column number out of range: There is only column 0 to 255')
                    else:
                        print('Error: No column number given!')
                elif mask[0] in {'pixel', 'Pixel', 'p'}:
                    if len(mask) >= 3:
                        if int(mask[1]) >= 0 and int(mask[1]) < 256 and int(mask[2]) >= 0 and int(mask[2]) < 256:
                            print('Unmask pixel', int(mask[1]), int(mask[2]))
                            mask_logger.delete_mask(mask_element = ['pixel', int(mask[1]), int(mask[2])],file_path = mask_file, chip = chip)
                        else:
                            print('Pixel number out of range: There is only 0 to 255 for x and y')
                    else:
                        print('Error: No full set of pixel coordinates. Needs x and y!')
                elif mask[0] in {'all', 'All'}:
                    print('Unmask all')
                    mask_logger.delete_mask(mask_element = ['all'], file_path = mask_file, chip = chip)
                else:
                    print('Unknown type:', mask)
        else:
            print('No mask file loaded, you cannot unmask nothing!')

    def Load_Mask(object, mask_path = None, chip = None):
        active_file     = TPX3_datalogger.data['Mask_path'][chip]['active'] 
        available_files = list(TPX3_datalogger.data['Mask_path'][chip]['available'])
        print(f'The currently selected mask file for chip {chip}:')
        print(f'\t\t{active_file}')
        print('Select from available files:')
        for num, f in enumerate(available_files):
            print(f'{num}\t{available_files[num]}')
        while(True):
            selection = input('>> ')
            try:
                TPX3_datalogger.data['Mask_path'][chip]['active'] = available_files[int(selection)]
                print(f'You chose file {available_files[int(selection)]}')
                break
            except:
                print(f'This option does not exist! Try again or press ctrl-c ...')


    def Get_link_configuration(object):
        # Create a dict, from where we can print out the important information beautifully
        info = {}
        for link in TPX3_datalogger.data['links']:
            chipID = TPX3_datalogger.data['links'][link]['chip-id-decoded']
            if chipID not in info:
                info.update({chipID: {'link_number': [TPX3_datalogger.data['links'][link]['fpga-link']], 'link_status': [TPX3_datalogger.data['links'][link]['link-status']]}})     
            else:
                info[chipID]['link_number'].append(TPX3_datalogger.data['links'][link]['fpga-link'])
                info[chipID]['link_status'].append(TPX3_datalogger.data['links'][link]['link-status'])
        
        for chip in info:
            print(f'\nLink configuration for chip {chip}\n')
            for num, link in enumerate(info[chip]['link_number']):
                link_number = info[chip]['link_number'][num]
                link_status = info[chip]['link_status'][num]
                if link_status == 0:
                    status_message = 'not active, not connected'
                elif link_status == 1:
                    status_message = 'active, no errors'
                elif link_status == 2:
                    status_message = 'not active, no errors'
                elif link_status == 3:
                    status_message = 'active, error: No suitable setting for data sampling within FPGA (delay, sampling edge, invert) was found'
                elif link_status == 4:
                    status_message = 'not active, error: No suitable setting for data sampling within FPGA (delay, sampling edge, invert) was found'
                elif link_status == 5:
                    status_message = 'active, error: Even if no data was transmitted on the link, there occured data in the receiver'
                elif link_status == 6:
                    status_message = 'not active, error: Even if no data was transmitted on the link, there occured data in the receiver'
                elif link_status == 7:
                    status_message = 'active, error: The ChipID could not be read correctly (packages missing, too many packages or wrong order of packages)'
                elif link_status == 8:
                    status_message = 'not active, error: The ChipID could not be read correctly (packages missing, too many packages or wrong order of packages)'
                print(f'Link {link_number}\t status: {status_message}')

    def Save_Mask(object, file_name = None):
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'masks')

        if file_name == None:
            print('> Please enter the the name you like to save the mask under (without ".h5"):')
            file_name = input('>> ')
        try:
            #look if path exists
            full_path = user_path + os.sep + file_name + '.h5'
            if os.path.isfile(full_path) == True:
                print('File already exists')
            else:
                current_mask = TPX3_datalogger.read_value(name = 'Mask_path')
                copy(current_mask, full_path)
        except:
            print('Could not write file')
        else:
            print('> Saved mask to ' + full_path)

    def Enable_Link(object, link = None, flag = None):
        hardware_links = TPX3_datalogger.read_value('hardware_links')
        if link == None:
            print('> Please enter the link you like to disable/enable [0-' + str(hardware_links - 1) + ']:')
            while(1):
                link = input('>> ')
                try:
                    link = int(link)
                    if link in range(hardware_links):
                        break
                    else:
                        print('Link needs to be between "0" and "' + str(hardware_links - 1) + '"')
                except:
                    if link in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
            print('> To disable or enable link ' + str(link) + ' enter "0" or "1":')
            while(1):
                flag = input('>> ')
                try:
                    flag = int(flag)
                    if flag in (0,1):
                        break
                    else:
                        print('Input needs to be "0" or "1"')
                except:
                    if flag in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        else:
            link = link
            flag = flag

        TPX3_datalogger.change_link_status(link = link, status = flag)

    def Enable_Chips(object, selected_chips, connected_chips):
        for chip in connected_chips:
            if chip not in selected_chips:
                for link in TPX3_datalogger.data['chip_links'][chip]:
                    TPX3_datalogger.change_link_status(link, 0)
            else:
                for link in TPX3_datalogger.data['chip_links'][chip]:
                    TPX3_datalogger.change_link_status(link, 1)
                            
        print('\nEnabled chip/s:')
        for chip in selected_chips:
            link_list = TPX3_datalogger.data['chip_links'][chip]
            print(f'{chip} on link/s {link_list}')

        print('\nDisabled chip/s:')
        for chip in connected_chips:
            if chip not in selected_chips:
                link_list = TPX3_datalogger.data['chip_links'][chip]
                print(f'{chip} on link/s {link_list}')


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

        new_process = TPX3_multiprocess_start.process_call(function = 'DataTake',
                                                           scan_timeout = scan_timeout,
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                           readout_interval = TPX3_datalogger.read_value(name = 'Readout_Speed'),
                                                           chip_link = TPX3_datalogger.data['chip_links'])
        new_process.join()

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

    def Set_Readout_Intervall(object, Readout_Intervall = None):
        if Readout_Intervall == None:
            print('> Please enter the readout intervall in seconds:')
            while(1):
                Readout_Intervall = input('>> ')
                try:
                    Readout_Intervall = float(Readout_Intervall)
                    break
                except:
                    if Readout_Intervall in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        try:
            Readout_Intervall = float(Readout_Intervall)
            TPX3_datalogger.write_value(name = 'Readout_Speed', value = Readout_Intervall)
        except:
            print('Unknown value')

    def TP_Period(object, TP_Period = None):
        if TP_Period == None:
            print('> Please enter the period (0-255):')
            while(1):
                TP_Period = input('>> ')
                try:
                    TP_Period = int(TP_Period)
                    if TP_Period not in range(256):
                        raise ValueError
                    break
                except:
                    if TP_Period in exit_list:
                        return
                    else:
                        print('Input needs to be an integer between 0 and 255!')
        try:
            TP_Period = int(TP_Period)
            TPX3_datalogger.write_value(name = 'TP_Period', value = TP_Period)
        except:
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

    def Set_Sense_DAC(object, DAC = None):
        print(DAC)
        if DAC == None:
            print('> Please enter the desired DAC Number: Off["0"]; Ibias_Preamp_ON["1"]; Ibias_Preamp_OFF["2"]; VPreamp_NCAS["3"]; Ibias_Ikrum["4"]; Vfbk["5"]; Vthreshold_fine["6"]; Vtreshold_corse["7"]; IBias_DiscS1_ON["8"]; IBias_DiscS1_OFF["9"]; IBias_DiscS2_ON["10"]; IBias_DiscS2_OFF["11"]; IBias_PixelDAC["12"]; IBias_TPbufferIn["13"]; IBias_TPbufferOut["14"]; VTP_coarse["15"]; VTP_fine["16"]; Ibias_CP_PLL["17"]; PLL_Vcntrl["18"]; BandGap_output["28"]; BandGap_Temp["29"]; Ibias_dac["30"]; Ibias_dac_cas["31"]')
            while(1):
                DAC = input('>> ')
                try:
                    DAC = int(DAC)
                    break
                except:
                    if DAC in exit_list:
                        return
                    else:
                        print('Input needs to be a number!')
        if DAC in {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 28, 29, 30, 31}:
            TPX3_datalogger.write_value(name = 'Sense_DAC', value = DAC)
            TPX3_datalogger.write_to_yaml(name = 'Sense_DAC')
        else:
            print('Unknown value')

    def Initialise_Hardware(object):
        hardware_scan_results = Queue()
        new_process = TPX3_multiprocess_start.process_call(function = 'ScanHardware',
                                                           results = hardware_scan_results)
        new_process.join()
        return hardware_scan_results.get()



 ###################################################
 ###                                             ###
####                 CLI main                    ####
 ###                                             ###
 ###################################################


class TPX3_CLI_TOP(object):
    def __init__(self, Gui, ext_input_list = None):
        readline.set_completer(completer)
        readline.parse_and_bind('tab: complete')
        data = file_logger.read_backup()
        TPX3_datalogger.set_data(data)
        TPX3_datalogger.write_backup_to_yaml()
        self.software_version = get_software_version(git = False)
        TPX3_datalogger.write_value(name = 'software_version', value = self.software_version)
        self.firmware_version = 'x.x'
        self.data_queue = None
        self.plot_window_process = None
        self.Gui_activated = Gui
        function_call            = TPX3_CLI_function_call()
        expertmode               = False

        TPX3_datalogger.check_mask_equal() # update list of files
        self.chip_list       = list(TPX3_datalogger.data['chip_dacs'])
        self.connected_chips = list(TPX3_datalogger.data['chip_links'])
        self.chip_options    = self.set_chip_options()
        self.selected_chips  = self.connected_chips

        self.DAC_dict = {'Fast_Io_en'           : ['Set_Fast_Io', 'Fast_Io', 'Fast_Io_en', 'set_fast_io', 'fast_io', 'fast_io_en'],
                         'Op_mode'              : ['Set_operation_mode', 'Set_Op_mode', 'Op_mode', 'set_operation_mode', 'set_Op_mode', 'op_mode'],
                         'Polarity'             : ['Set_Polarity', 'Set_Pol', 'Polarity', 'Pol','set_polarity', 'set_pol', 'polarity','pol'],
                         'clk_fast_out'         : ['Set_CLK_fast_mode', 'set_clk_fast_mode', 'CLK_fast_mode', 'clk_fast_mode'],
                         'ClkOut_frequency_src' : ['Set_ClkOut_frequency', 'set_clkout_frequency', 'ClkOut_frequency', 'clkout_frequency'],
                         'AckCommand_en'        : ['Set_Acknowledgement', 'set_acknowledgement', 'Acknowledgement', 'acknowledgement'],
                         'SelectTP_Ext_Int'     : ['Set_TP_ext_in', 'set_tp_ext_in', 'TP_ext_in', 'tp_ext_in'],
                         'Sense_DAC'            : ['Set_Sense_DAC', 'set_sense_DAC', 'Sense_DAC', 'sense_DAC'],}

        self.help_text= {'Fast_Io_en'           : 'This is the Fast Io enable function. As argument you can give the enable as 0 (off) or 1 (on)',
                         'Op_mode'              : 'This is the Set operation mode function. As argument you can give the operation mode as 0 for ToT & ToA, 1 for only ToA or 2 for Event Count & Integral ToT',
                         'Polarity'             : 'This is the set polarity function. As argument you can give the polarity as {negative, neg, -, 1} or {positive, pos, +, 0}',
                         'clk_fast_out'         : 'This is the set CLK_fast_mode function. As argument you can give the enable as 0 (off) or 1 (on)',
                         'ClkOut_frequency_src' : 'This is the set ClkOut_frequency function. As argument you can give the desired frequency: 320MHz["1" or "320"]; 160MHz["2" or "160"]; 80MHz["3" or "80"]; 40MHz["4" or "40"]; Extern["5" or "Ext"]',
                         'AckCommand_en'        : 'This is the set acknowledgement function. As argument you can give the enable as 0 (off) or 1 (on)',
                         'SelectTP_Ext_Int'     : 'This is the set TP_ext_in function. As argument you can give the enable as 0 (off) or 1 (on)',
                         'Sense_DAC'            : 'This is the set Sense_DAC function. As argument you can give the DAC you like to read out: Off["0"]; Ibias_Preamp_ON["1"]; Ibias_Preamp_OFF["2"]; VPreamp_NCAS["3"]; Ibias_Ikrum["4"]; Vfbk["5"]; Vthreshold_fine["6"]; Vtreshold_corse["7"]; IBias_DiscS1_ON["8"]; IBias_DiscS1_OFF["9"]; IBias_DiscS2_ON["10"]; IBias_DiscS2_OFF["11"]; IBias_PixelDAC["12"]; IBias_TPbufferIn["13"]; IBias_TPbufferOut["14"]; VTP_coarse["15"]; VTP_fine["16"]; Ibias_CP_PLL["17"]; PLL_Vcntrl["18"]; BandGap_output["28"]; BandGap_Temp["29"]; Ibias_dac["30"]; Ibias_dac_cas["31"]'
                                                    }
        
        print('\n Welcome to the Timepix3 control Software\n')

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

            # Exit loop at the end
            cmd_list.append(['Quit'])

        # Here the main part of the CLI starts. Every user command needs to be processed here.
        while 1:

            #if no external input is given
            if ext_input_list == None:
                if expertmode == True:
                    cmd_input = input('expert> ')
                else:
                    cmd_input = input('> ')
                #Catch if no input given
                if cmd_input == '':
                    print('Something enter you must!')
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
                            print(function)
                    elif expertmode == True:
                        print('If you need detailed help on a function type [functionname -h].\n Possible options are:')
                        for function in expert_help_functions:
                            print(function)

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
                            print('Incomplete set of parameters:')
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
                            print('To many parameters! The given function takes only three parameters:\n start testpulse value (0-511),\n stop testpulse value (0-511),\n number of steps (4, 16, 64, 256).')

                #Timewalk_Calibration
                elif inputlist[0] in {'Timewalk_Calibration', 'Timewalk', 'timewalk_calibration', 'timewalk'}:
                    if len(inputlist) == 1:
                        print('Timewalk_calibration')
                        try:
                            function_call.Timewalk_Calibration()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the ToT calibration. As arguments you can give the start testpulse value (1-511), the stop testpulse value (1-511) and the number of steps (4, 16, 64, 256).')
                        elif len(inputlist) < 4:
                            print('Incomplete set of parameters:')
                            try:
                                function_call.Timewalk_Calibration()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 4:
                            try:
                                function_call.Timewalk_Calibration(VTP_fine_start = int(inputlist[1]), VTP_fine_stop = int(inputlist[2]), mask_step = int(inputlist[3]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 4:
                            print('To many parameters! The given function takes only three parameters:\n start testpulse value (1-511),\n stop testpulse value (1-511),\n number of steps (4, 16, 64, 256).')

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
                            print('Incomplete set of parameters:')
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
                            print('To many parameters! The given function takes only four parameters:\n start threshold value (0-2911),\n stop threshold value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')

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
                            print('Incomplete set of parameters:')
                            try:
                                function_call.Threshold_Calib()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 6:
                            try:
                                function_call.Threshold_Calib(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]), n_pulse_heights = int(inputlist[5]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 6:
                            print('To many parameters! The given function takes only four parameters:\n start threshold value (0-2911),\n stop threshold value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256),\n number of pulse height steps (2-100).')

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
                            print('Incomplete set of parameters:')
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
                            print('To many parameters! The given function takes only four parameters:\n start testpulse value (0-511),\n stop testpulse value (0-511),\n number of injections (1-65535),\n column offset (0-15).')

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
                            print('This is the Pixel DAC Optimisation. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535) and the column offset (0-15).')
                        elif len(inputlist) < 5:
                            print('Incomplete set of parameters:')
                            try:
                                function_call.Pixel_DAC_Optimisation()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 5:
                            try:
                                function_call.Pixel_DAC_Optimisation(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), offset = int(inputlist[4]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 5:
                            print('To many parameters! The given function takes only four parameters:\n start threshold value (0-2911),\n stop threshold value (0-2911),\n number of injections (1-65535),\n column offset (0-15).')

                #Equalisation
                elif inputlist[0] in {'Equalisation', 'Equal', 'EQ', 'equalisation', 'equal', 'eq'}:
                    if len(inputlist) == 1:
                        print('Equalisation')
                        try:
                            function_call.Equalisation()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Equalisation. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911), the number of testpulse injections (1-65535) and the number of steps (4, 16, 64, 256).')
                        elif len(inputlist) < 5:
                            print('Incomplete set of parameters:')
                            try:
                                function_call.Equalisation()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 5:
                            try:
                                function_call.Equalisation(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 5:
                            print('To many parameters! The given function takes only four parameters:\n start threshold value (0-2911),\n stop threshold value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')

                #Noise_Scan
                elif inputlist[0] in {'Noise_Scan', 'Noise', 'noise_scan', 'noise'}:
                    if len(inputlist) == 1:
                        print('Noise_Scan')
                        try:
                            function_call.Noise_Scan()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Threshold scan. As arguments you can give the start threshold value (0-2911), the stop threshold value (0-2911) and the shutter length in seconds.')
                        elif len(inputlist) < 4:
                            print('Incomplete set of parameters:')
                            try:
                                function_call.Noise_Scan()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 4:
                            try:
                                function_call.Noise_Scan(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), shutter = float(inputlist[3]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 4:
                            print('To many parameters! The given function takes only two parameters:\n start threshold value (0-2911),\n stop threshold value (0-2911).')

                #Select_Chips
                elif inputlist[0] in {'Select_Chips', 'select_chips', 'chips', 'chip'}:
                    if len(inputlist) == 1:
                        print('\nWelcome! Here you can select chips from following options:\n')                       
                        menu = 1
                        while menu:
                            self.print_chip_options()
                            print(f'\nYour current selection is: {self.selected_chips}\n')
                            self.selected_chips = self.chip_selection()
                            print(f'\nYour new selection is {self.selected_chips}')
                            menu = self.stay_in_menu('Select Chips')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the chip selection menu. Here you can choose a list of chips for which you can inspect and set DACs, equalisation and mask files.')
                        else:
                            print('I don\'t understand, quitting menu.')

                #Set_DAC
                elif inputlist[0] in {'Set_DAC', 'set_dac'}:
                    if len(inputlist) == 1:
                        print('Set_DAC')
                        try:
                            function_call.Set_DAC(chip_selection = self.selected_chips)
                        except:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Set DAC function. As arguments you can give the chip ID, the DAC-name/DAC-number and the new value.\n The following DACs are aviable:\n     1.) Ibias_Preamp_ON (0-255)\n     2.) VPreamp_NCAS (0-255)\n     3.) Ibias_Ikrum (0-255)\n     4.) Vfbk (0-255)\n     5.) Vthreshold_fine (0-511)\n     6.) Vthreshold_coarse (0-15)\n     7.) Vthreshold_combined (0-2911)\n     8.) Ibias_DiscS1_ON (0-255)\n     9.) Ibias_DiscS2_ON (0-255)\n    10.) Ibias_PixelDAC (0-255)\n    11.) Ibias_TPbufferIn (0-255)\n    12.) Ibias_TPbufferOut (0-255)\n    13.) VTP_coarse (0-255)\n    14.) VTP_fine (0-511)\n    15.) Ibias_CP_PLL (0-255)\n    16.) PLL_Vcntrl (0-255)')
                            print('\n Following chips are available: ')
                            for chip in self.chip_list:
                                if chip == 'default':
                                    continue
                                if chip in self.connected_chips:
                                    print(f'    {chip}\tconnected')
                                else:
                                    print(f'    {chip}')
                        elif len(inputlist) < 4:
                            print('Incomplete set of parameters:')
                            try:
                                function_call.Set_DAC()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 4:
                            if inputlist[2] in {'1', 'Ibias_Preamp_ON'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Ibias_Preamp_ON', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'2', 'VPreamp_NCAS'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'VPreamp_NCAS', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'3', 'Ibias_Ikrum'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Ibias_Ikrum', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'4', 'Vfbk'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Vfbk', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'5', 'Vthreshold_fine'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Vthreshold_fine', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'6', 'Vthreshold_coarse'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Vthreshold_coarse', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'7', 'Vthreshold_combined'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Vthreshold_combined', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'8', 'Ibias_DiscS1_ON'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Ibias_DiscS1_ON', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'9', 'Ibias_DiscS2_ON'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Ibias_DiscS2_ON', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'10', 'Ibias_PixelDAC'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Ibias_PixelDAC', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'11', 'Ibias_TPbufferIn'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Ibias_TPbufferIn', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'12', 'Ibias_TPbufferOut'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Ibias_TPbufferOut', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'13', 'VTP_coarse'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'VTP_coarse', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'14', 'VTP_fine'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'VTP_fine', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'15', 'Ibias_CP_PLL'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'Ibias_CP_PLL', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            elif inputlist[2] in {'16', 'PLL_Vcntrl'}:
                                try:
                                    function_call.Set_DAC_chip(chip = inputlist[1], DAC_Name = 'PLL_Vcntrl', DAC_value = int(inputlist[3]))
                                except KeyboardInterrupt:
                                    print('User quit')
                            else:
                                print('Unknown DAC-name')
                        elif len(inputlist) > 4:
                            print('To many parameters! The given function takes only three parameters:\n The chip ID, the DAC-name and its value.')

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
                            print('This is the datataking function. As argument you can give the run time (in seconds, if 0 is entered the datataking will run infinitely')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Run_Datataking(scan_timeout = int(inputlist[1]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print('To many parameters! The given function takes only one parameter:\n run time (in seconds).')

                #Load equalisation
                elif inputlist[0] in {'Load_Equalisation', 'Load_Equal', 'LEQ','load_equalisation', 'load_equal', 'leq'}:
                    if len(inputlist) == 1:
                        print('Load_Equalisation')
                        if len(self.selected_chips)>0:
                            for chip in self.selected_chips:
                                try:
                                    print(f'\nEqualisation file selection for chip {chip}\n')
                                    function_call.Load_Equalisation(chip = chip)
                                except KeyboardInterrupt:
                                    print('User quit')
                            print(f'Finished loading equalisation/s. Exiting Load Equalisation menu ...\n')
                        else:
                            print('There are no chips selected! Exiting Load Equalisation menu ...')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the load equalisation function. As argument you can give the path of the equalisation you like to load')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Load_Equalisation(equal_path = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print('To many parameters! The given function takes only one parameter:\n equalisation path.')

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
                            print('To many parameters! The given function takes only one parameter:\n equalisation file name.')

                #Create uniform equalisation
                elif inputlist[0] in {'Uniform_Equalisation', 'Uniform_Equal', 'UE', 'uniform_equalisation', 'uniform_equal', 'ue'}:
                    if len(inputlist) == 1:
                        print('Uniform_Equalisation')
                        if len(self.selected_chips)>0:
                            for chip in self.selected_chips:
                                try:
                                    print(f'\nUniform equalisation creation for chip {chip}\n')
                                    function_call.Uniform_Equalisation(chip = chip)
                                except KeyboardInterrupt:
                                    print('User quit')
                            TPX3_datalogger.check_mask_equal() # update list of files in logger
                        else:
                            print(f'There are no chips selected!. Exiting Create Uniform Equalisation menu ...\n')
                        print('Creation of uniform equalisation matrices done. Exiting Create Uniform Equalisation menu ...\n')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the uniform equalisation function. As argument you can give a pixel threshold [0-15]. All pixels will be set to this pixel threshold.')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Uniform_Equalisation(pixel_threshold = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print('To many parameters! The given function takes only one parameter:\n equalisation file name.')

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
                            print('To many parameters! The given function takes only one parameter:\n backup file name.')

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
                            print('To many parameters! The given function takes only one parameter:\n backup file name.')

                #Set TP_Period
                elif inputlist[0] in {'TP_Period', 'tp_period'}:
                    if len(inputlist) == 1:
                        print('Set TP_Period')
                        try:
                            function_call.TP_Period()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the set tp_period function. As argument you can give the period between 0 and 255.')
                        elif len(inputlist) == 2:
                                try:
                                    function_call.TP_Period(TP_Period = inputlist[1])
                                except KeyboardInterrupt:
                                    print('User quit')
                        elif len(inputlist) > 2:
                            print('To many parameters! The given function takes only one parameter:\n tp_period.')

                #Set mask
                elif inputlist[0] in {'Set_Mask', 'Mask', 'set_mask', 'mask',
                                      'Unset_Mask', 'Unmask','unset_mask', 'unmask'}:
                    if len(inputlist) == 1:
                        if inputlist[0] in {'Set_Mask', 'Mask', 'set_mask', 'mask'}:
                            mode = 1
                            print('Set mask')
                        else:
                            mode = 0
                            print('Unset mask')

                        print('\nSelect a chip/multiple chips: \n')
                        self.print_chip_options()
                        chips = self.chip_selection()
                        for chip in chips:
                            print(f'\nThese mask files are currently available for chip {chip}:\n')
                            files = TPX3_datalogger.data['Mask_path'][chip]['available']
                            files_list = []
                            for file in files:
                                if file != 'None':
                                    files_list.append(file)
                            if mode == 1:
                                files_list.append('new')
                            for num, file in enumerate(files_list):
                                print(f'{num}\t{file}')
                            print('Select option/s: ')
                            selection = input('>> ')
                            selection = selection.split()
                            print(f'Files list: {files_list}')
                            for current_selection in selection:
                                if int(current_selection) in range(len(files_list)):
                                    try:
                                        print(files_list[int(current_selection)])
                                        if files_list[int(current_selection)] == 'new':
                                            time_stamp = time.strftime('%Y-%m-%d_%H-%M-%S')
                                            file_name  = f'{chip}_mask_{time_stamp}.h5'
                                            user_path  = os.path.expanduser('~')
                                            user_path  = os.path.join(user_path, 'Timepix3')
                                            user_path  = os.path.join(user_path, 'masks')
                                            mask_file  = os.path.join(user_path, chip + os.sep + file_name)
                                        else:
                                            mask_file = files_list[int(current_selection)]
                                        if mode == 1:
                                            print(f'Set a mask for file {current_selection}')
                                            function_call.Set_Mask(chip = chip, mask_file = mask_file)
                                        else:
                                            print(f'Unset a mask for file {current_selection}')
                                            function_call.Unset_Mask(chip = chip, mask_file = files_list[int(current_selection)])
                                    except KeyboardInterrupt:
                                        print('User quit')
                                else:
                                    print('Not a viable option! Skip ...')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the set mask function. As argument you can give mask commands: "row rownumber", "column columnnumber" or "pixel x y". Multiple entrys can be made by a "+" between them')
                        elif len(inputlist) >= 2:
                            mask_input = inputlist[1:]
                            try:
                                function_call.Set_Mask(mask_input_list = mask_input)
                            except KeyboardInterrupt:
                                print('User quit')

                    # update logger here

                #Load mask
                elif inputlist[0] in {'Load_Mask', 'load_mask'}:
                    if len(inputlist) == 1:
                        print('Load_Mask')
                        if len(self.selected_chips) > 0:
                            for chip in self.selected_chips:
                                try:
                                    print(f'Mask file selection for chip {chip} ...')
                                    function_call.Load_Mask(chip = chip)
                                except KeyboardInterrupt:
                                    print('User quit')
                            print('Loading mask/s finished, exiting Load Mask menu...\n')
                        else:
                            print('No chips selected! Exiting Load Mask menu ...')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the load mask function. As argument you can give the name of the mask file you like to load')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Load_Mask(mask_path = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print('To many parameters! The given function takes only one parameter:\n mask file name.')

                #Save mask
                elif inputlist[0] in {'Save_Mask', 'save_mask'}:
                    if len(inputlist) == 1:
                        print('Save mask')
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
                            print('To many parameters! The given function takes only one parameter:\n mask file name.')

                #Combine Set polarity, Set operation mode, Set Io mode
                elif inputlist[0] in ['Set_Polarity', 'Set_Pol', 'Polarity', 'Pol','set_polarity', 'set_pol', 'polarity','pol',
                                      'Set_operation_mode', 'Set_Op_mode', 'Op_mode', 'set_operation_mode', 'set_Op_mode', 'op_mode',
                                      'Set_Fast_Io', 'Fast_Io', 'Fast_Io_en', 'set_fast_io', 'fast_io', 'fast_io_en']:
                    # Get DAC name
                    for key, value in self.DAC_dict.items():
                        if inputlist[0] in value:
                            DAC_name = key
                          
                    if len(inputlist) == 1:
                        try:
                            function_call.set_advanced_DAC(chip_list=self.selected_chips, DAC_name=DAC_name)
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in ['Help', 'help', 'h', '-h']:
                            print(self.help_text[DAC_name])
                        else:
                            print('Not implemented yet')

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
                            print('Set default does not take parameters!')

                #Initialise Hardware
                elif inputlist[0] in {'Initialise_Hardware', 'Init_Hardware', 'Init', 'initialise_hardware', 'init_hardware', 'init'}:
                    if len(inputlist) == 1:
                        print('Initialise Hardware')
                        try:
                            Chip_List = function_call.Initialise_Hardware()
                            for n in range(0, len(Chip_List[2])):
                                if n == 0 and Chip_List:
                                    self.firmware_version = Chip_List.pop(0)
                                    TPX3_datalogger.write_value(name = 'firmware_version', value = self.firmware_version)
                                elif n == 1 and Chip_List:
                                    TPX3_datalogger.write_value(name = 'hardware_links', value = Chip_List.pop(0))
                                elif Chip_List:
                                    name = 'Chip' + str(n - 2) + '_name'
                                    TPX3_datalogger.write_value(name = name, value = Chip_List.pop(0))
                                else:
                                    name = 'Chip' + str(n - 2) + '_name'
                                    TPX3_datalogger.write_value(name = name, value = [None])
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the initialise hardware function. It initializes the hardware and looks how many links and Chips are connected')
                        else :
                            print('Initialise hardware does not take parameters!')

                #Set Readout Intervall
                elif inputlist[0] in {'Set_Readout_Intervall', 'set_readout_intervall', 'Readout_Intervall', 'readout_intervall'}:
                    if len(inputlist) == 1:
                        print('Set Readout Intervall')
                        try:
                            function_call.Set_Readout_Intervall()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the set readout intervall function. As argument you can give the readout intervall in seconds')
                        elif len(inputlist) == 2:
                                try:
                                    function_call.Set_Readout_Intervall(Readout_Intervall = inputlist[1])
                                except KeyboardInterrupt:
                                    print('User quit')
                        elif len(inputlist) > 2:
                            print('To many parameters! The given function takes only one parameter:\n Readout intervall.')

                #Start GUI
                elif inputlist[0] in {'GUI'}:
                    if self.Gui_activated == True:
                        if len(inputlist) == 1:
                            file_logger.write_backup(file = file_logger.create_file())
                            GUI.GUI_start()
                            backup_data = file_logger.read_backup()
                            TPX3_datalogger.set_data(config = backup_data)
                            TPX3_datalogger.write_backup_to_yaml()
                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This will start the GUI')
                            elif len(inputlist) > 1:
                                print('GUI takes no parameters')
                    else:
                        print('This is only available with a graphic backend')

                #Start Plot window
                elif inputlist[0] in {'Plot', 'plot'}:
                    if self.Gui_activated == True:
                        if len(inputlist) == 1:
                            if self.plot_window_process == None:
                                plottype = ('plottype=' + str(TPX3_datalogger.read_value('plottype')))
                                integration_length = ('integration_length=' + str(TPX3_datalogger.read_value('integration_length')))
                                color_depth = ('color_depth=' + str(TPX3_datalogger.read_value('color_depth')))
                                colorsteps = ('colorsteps=' + str(TPX3_datalogger.read_value('colorsteps')))

                                self.plot_window_process = Popen(['python', 'CLI_Plot_main.py',
                                                                                    plottype,
                                                                                    integration_length,
                                                                                    color_depth,
                                                                                    colorsteps],
                                                                                    stdout = PIPE,
                                                                                    text = True)
                            else:
                                print('The Plot window is still open or not stopped vie "stop_plot". This will be done for you now.')
                                try:
                                    self.plot_window_process.terminate()
                                except:
                                    pass
                                try:
                                    return_values, signal = self.plot_window_process.communicate()
                                    for key, value in dict(arg.split('=') for arg in return_values.split()[0:]).items():
                                        if key == 'plottype':
                                            TPX3_datalogger.write_value(name = 'plottype', value = value)
                                        elif key == 'integration_length':
                                            TPX3_datalogger.write_value(name = 'integration_length', value = int(value))
                                        elif key == 'color_depth':
                                            TPX3_datalogger.write_value(name = 'color_depth', value = int(value))
                                        elif key == 'colorsteps':
                                            TPX3_datalogger.write_value(name = 'colorsteps', value = int(value))
                                except:
                                    print('Error: I did not receive any values from plotting window')
                                self.plot_window_process = None

                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This will start an online plotting window for the data taken')
                            elif len(inputlist) > 1:
                                print('Plot takes no parameters')
                    else:
                        print('This is only amiable with a graphic backend')

                #Stop Plot window
                elif inputlist[0] in {'Stop_Plot', 'stop_plot'}:
                    if self.Gui_activated == True:
                        if len(inputlist) == 1:
                            if self.plot_window_process != None:
                                try:
                                    self.plot_window_process.terminate()
                                except:
                                    pass
                                try:
                                    return_values, signal = self.plot_window_process.communicate()
                                    for key, value in dict(arg.split('=') for arg in return_values.split()[0:]).items():
                                        if key == 'plottype':
                                            TPX3_datalogger.write_value(name = 'plottype', value = value)
                                        elif key == 'integration_length':
                                            TPX3_datalogger.write_value(name = 'integration_length', value = int(value))
                                        elif key == 'color_depth':
                                            TPX3_datalogger.write_value(name = 'color_depth', value = int(value))
                                        elif key == 'colorsteps':
                                            TPX3_datalogger.write_value(name = 'colorsteps', value = int(value))
                                except:
                                    print('Error: I did not receive any values from plotting window')
                                self.plot_window_process = None

                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This will stop the online plotting window for the data taken')
                            elif len(inputlist) > 1:
                                print('Stop Plot takes no parameters')
                    else:
                        print('This is only available with a graphic backend')

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

                #Set Run name
                elif inputlist[0] in {'Set_Run_Name', 'Run_Name', 'set_run_name', 'run_name'}:
                    if len(inputlist) == 1:
                        try:
                            function_call.Set_Run_Name()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the set run name function. As argument you can give the name addition of the run data file')
                        elif len(inputlist) == 2:
                            try:
                                function_call.Set_Run_Name(run_name = inputlist[1])
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 2:
                            print('To many parameters! The given function takes only one parameter:\n name addition of the run data file.')

                #Get Run name
                elif inputlist[0] in {'Get_Run_Name', 'get_run_name'}:
                    if len(inputlist) == 1:
                        if TPX3_datalogger.read_value('Run_name') in [None, 'False', 'false', '', 'None', 'none']:
                            print('No run name is set. So the default file name will be taken [scan_type + YYYY-MM-DD_hh-mm-ss]')
                        else:
                            print('The run name is set to ' + str(TPX3_datalogger.read_value('Run_name')) + '. So the file name will be [scan_type + ' + str(TPX3_datalogger.read_value('Run_name')) + ']')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the get run name function. It shows the current run file name.')
                        else:
                            print('The get run name function takes no parameters.')

                #Get Chip names
                elif inputlist[0] in {'Chip_names', 'chip_names', 'Who', 'who'}:
                    if len(inputlist) == 1:
                        print('Connected chips are:')
                        for Chipname in TPX3_datalogger.get_chipnames():
                            number_of_links = TPX3_datalogger.get_links(chipname=Chipname)
                            if number_of_links == 1:
                                print(Chipname + ' on ' + str(number_of_links) + ' active link')
                            else:
                                print(Chipname + ' on ' + str(number_of_links) + ' active links')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the get chip names function. It shows the connected chips with their number of connected links.')
                        else :
                            print('Get chip names does not take parameters!')

                #Get Mask name
                elif inputlist[0] in {'Mask_name', 'mask_name'}:
                    if len(inputlist) == 1:
                        for chip in self.selected_chips:
                            if chip != 'default':
                                print(f'\nMask files for chip {chip}\n')
                            else:
                                print(f'\nDefault mask files\n')
                            active_file     = TPX3_datalogger.data['Mask_path'][chip]['active']
                            available_files = TPX3_datalogger.data['Mask_path'][chip]['available']
                            print(f'Active:\n\t{active_file}\n')
                            print('Available:\n')
                            for file in available_files:
                                if file=='None' and len(available_files)==1:
                                    print(f'\tNone\n')
                                elif file=='None' and len(available_files)>1:
                                    pass
                                elif file=='None' and active_file != 'None':
                                    print(f'\tNone\n')
                                elif file != active_file:
                                    print(f'\t{file}\n')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the get mask names function. It shows the path of the current mask.')
                        else :
                            print('Get mask name does not take parameters!')

                #Get Equalisation name
                elif inputlist[0] in {'Equalisation_name', 'equalisation_name', 'Equal_name', 'equal_name'}:
                    if len(inputlist) == 1:
                        for chip in self.selected_chips:
                            if chip != 'default':
                                print(f'\nEqualisation files for chip {chip}\n')
                            else:
                                print(f'\nDefault Equalisation files\n')
                            active_file     = TPX3_datalogger.data['Equalisation_path'][chip]['active']
                            available_files = TPX3_datalogger.data['Equalisation_path'][chip]['available']
                            print(f'Active:\n\t{active_file}\n')
                            print('Available:\n')
                            for file in available_files:
                                if file=='None' and len(available_files)==1:
                                    print(f'\tNone\n')
                                elif file=='None' and len(available_files)>1:
                                    pass
                                elif file=='None' and active_file != 'None':
                                    print(f'\tNone\n')
                                elif file != active_file:
                                    print(f'\t{file}\n')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the get equalisation names function. It shows the path of the current equalisation.')
                        else :
                            print('Get equalisation name does not take parameters!')
                
                #Get DAC Values
                elif inputlist[0] in {'Get_DAC_Values', 'get_dac_values', 'DAC_Values', 'dac_values'}:
                    if len(inputlist) == 1:
                        for chip in self.selected_chips:
                            if chip != 'default':
                                print(f'\nDAC settings for chip {chip}\n')
                            else:
                                print('\nDefault DAC settings\n')
                            print(f'Ibias_Preamp_ON:\t' + str(TPX3_datalogger.read_value('Ibias_Preamp_ON', chip=chip)))
                            print(f'VPreamp_NCAS:\t\t' + str(TPX3_datalogger.read_value('VPreamp_NCAS', chip=chip)))
                            print(f'Ibias_Ikrum:\t\t' + str(TPX3_datalogger.read_value('Ibias_Ikrum', chip=chip)))
                            print(f'Vfbk:\t\t\t' + str(TPX3_datalogger.read_value('Vfbk', chip=chip)))
                            print(f'Vthreshold_fine:\t' + str(TPX3_datalogger.read_value('Vthreshold_fine', chip=chip)))
                            print(f'Vthreshold_coarse:\t' + str(TPX3_datalogger.read_value('Vthreshold_coarse', chip=chip)))
                            print(f'Vthreshold_combined:\t' + str(int(threshold_compose(TPX3_datalogger.read_value('Vthreshold_fine', chip=chip), TPX3_datalogger.read_value('Vthreshold_coarse', chip=chip)))))
                            print(f'Ibias_DiscS1_ON:\t' + str(TPX3_datalogger.read_value('Ibias_DiscS1_ON', chip=chip)))
                            print(f'Ibias_DiscS2_ON:\t' + str(TPX3_datalogger.read_value('Ibias_DiscS2_ON', chip=chip)))
                            print(f'Ibias_PixelDAC:\t\t' + str(TPX3_datalogger.read_value('Ibias_PixelDAC', chip=chip)))
                            print(f'Ibias_TPbufferIn:\t' + str(TPX3_datalogger.read_value('Ibias_TPbufferIn', chip=chip)))
                            print(f'Ibias_TPbufferOut:\t' + str(TPX3_datalogger.read_value('Ibias_TPbufferOut', chip=chip)))
                            print(f'VTP_coarse:\t\t' + str(TPX3_datalogger.read_value('VTP_coarse', chip=chip)))
                            print(f'VTP_fine:\t\t' + str(TPX3_datalogger.read_value('VTP_fine', chip=chip)))
                            print(f'Ibias_CP_PLL:\t\t' + str(TPX3_datalogger.read_value('Ibias_CP_PLL', chip=chip)))
                            print(f'PLL_Vcntrl:\t\t' + str(TPX3_datalogger.read_value('PLL_Vcntrl', chip=chip)))
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the get DAC values function. It shows the current DAC values.')
                        else :
                            print('Get DAC values does not take parameters!')

                #Get Link configuration
                elif inputlist[0] in {'Get_Link_Configuration', 'get_link_configuration', 'links', 'link_config'}:
                    if len(inputlist) == 1:
                        try:
                            function_call.Get_link_configuration()
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        try:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('Get link configuration.  This shows which links are enabled and which chips are connected.')
                            else:
                                print('Get link configuration does not take parameters!')
                        except KeyboardInterrupt:
                            print('User quit')

                #About
                elif inputlist[0] in {'About', 'about'}:
                    if len(inputlist) == 1:
                        print('TPX3 CLI')
                        print('Software version: ' + str(self.software_version))
                        print('Firmware version: ' + str(self.firmware_version))
                        try:
                            print('Git branch: ' + str(get_git_branch()))
                            print('Git commit: ' + str(get_git_commit()))
                            print('Git date: ' + str(get_git_date(short = False)))
                        except:
                            pass
                        print('GasDet Bonn 2018-2022')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the about function. It shows software and firmware information.')
                        else :
                            print('About does not take parameters!')

                #Quit
                elif inputlist[0] in {'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit'}:
                    if self.Gui_activated == True and self.plot_window_process != None:
                        try:
                            self.plot_window_process.terminate()
                        except:
                            pass
                        try:
                            return_values, signal = self.plot_window_process.communicate()
                            for key, value in dict(arg.split('=') for arg in return_values.split()[0:]).items():
                                if key == 'plottype':
                                    TPX3_datalogger.write_value(name = 'plottype', value = value)
                                elif key == 'integration_length':
                                    TPX3_datalogger.write_value(name = 'integration_length', value = int(value))
                                elif key == 'color_depth':
                                    TPX3_datalogger.write_value(name = 'color_depth', value = int(value))
                                elif key == 'colorsteps':
                                    TPX3_datalogger.write_value(name = 'colorsteps', value = int(value))
                        except:
                            print('Error: I did not receive any values from plotting window')
                        self.plot_window_process = None
                    file_logger.write_backup(file = file_logger.create_file())
                    file_logger.delete_tmp_backups()
                    print('Goodbye and have a nice day.')
                    break

                #Expert mode functions
                elif expertmode == True:

                    # Combine Set CLK_fast_mode, Set Acknowledgement, Select TP_ext_in, Set ClkOut_frequency_source, Set Sense DAC
                    if inputlist[0] in ['Set_CLK_fast_mode', 'set_clk_fast_mode', 'CLK_fast_mode', 'clk_fast_mode',
                                        'Set_Acknowledgement', 'set_acknowledgement', 'Acknowledgement', 'acknowledgement',
                                        'Set_TP_ext_in', 'set_tp_ext_in', 'TP_ext_in', 'tp_ext_in',
                                        'Set_ClkOut_frequency', 'set_clkout_frequency', 'ClkOut_frequency', 'clkout_frequency',
                                        'Set_Sense_DAC', 'set_sense_DAC', 'Sense_DAC', 'sense_DAC']:
                        # Get DAC name
                        for key, value in self.DAC_dict.items():
                            if inputlist[0] in value:
                                DAC_name = key
                        
                        if len(inputlist) == 1:
                            try:
                                function_call.set_advanced_DAC(chip_list=self.selected_chips, DAC_name=DAC_name)
                            except KeyboardInterrupt:
                                print('User quit')
                        else:
                            if inputlist[1] in ['Help', 'help', 'h', '-h']:
                                print(self.help_text[DAC_name])
                            else:
                                print('Not implemented yet')

                    #Enable Link
                    elif inputlist[0] in {'Enable_Link', 'enable_link', 'Disable_Link', 'disable_link'}:
                        if len(inputlist) == 1:
                            print('Enable Link')
                            try:
                                function_call.Enable_Link()
                            except KeyboardInterrupt:
                                print('User quit')
                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This is the set Enable Link function. You can disable or enable links by assigning "0" disable or "1" enable to the link number "0-7".')
                            elif len(inputlist) == 2 and not inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('Not enough parameters! The given function takes two parameters:\n Link number and "0" or "1".')
                            elif len(inputlist) == 3:
                                if inputlist[1] in {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'} and inputlist[2] in {'0', '1'}:
                                    try:
                                        function_call.Enable_Link(link = inputlist[1], flag = inputlist[2])
                                    except KeyboardInterrupt:
                                        print('User quit')
                                else:
                                    print('Unknown argument')
                            elif len(inputlist) > 3:
                                print('To many parameters! The given function takes two parameters:\n Link number and "0" or "1".')

                    elif inputlist[0] in {'Enable_Chips', 'enable_chips'}:
                        if len(inputlist) == 1:
                            print('Enable Chips')
                            try:
                                function_call.Enable_Chips(self.selected_chips, self.connected_chips)
                                function_call.Get_link_configuration()
                            except KeyboardInterrupt:
                                print('User quit')
                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This is the Enable Chip function. It enables all links, which are connected to the selected chips, and disables all other links.')
                                print('You can select chips with the Select_Chips command.')
                            else:
                                print('I don\'t understand!')

                    #Unknown command
                    else:
                        print('Unknown command: ', cmd_input, ' Use a language I understand.')

                #Unknown command
                else:
                    print('Unknown command: ', cmd_input, ' Use a language I understand.')

    
    def print_chip_options(self):
        '''
            This function prints the available choices for selecting chips in the format "option - chip"
        '''
        print('1\tconnected chips')
        print('2\tall chips')
        for num, chip in enumerate(self.chip_list):
            print(f'{num+3}\t{chip}')

    def chip_selection(self):
        '''
            In this function the user selects one or more chips
        '''
        input_options = input('\nSelect option/s: ')
        input_list    = input_options.split()
        chip_output   = []
                            
        for item in input_list:
            if item not in self.chip_options:
                print('This option is not available!')
                chip_output = self.selected_chips
            elif item == '1':
                chip_output = self.connected_chips
            elif item == '2':
                chip_output = self.chip_list
            else:
                chip_output.append(self.chip_list[int(item)-3])

        return chip_output

    def stay_in_menu(self, menu_name):
        '''
            Here the user is asked, whether he wants to stay in a menu or not
        '''
        continue_menu = input('\nDo you want to stay in this menu? [0 - get out!, 1 - let me try again...] ')
        if continue_menu in ['0','1']:
            continue_menu = int(continue_menu)
        else:
            print('I don\'t understand, jump back to the beginning ...\n' )
            return 1
        if continue_menu == 0:
            print(f'Exiting {menu_name} menu ...')
        else:
            print('I don\'t understand, jump back to the beginning ...\n' )
            return 1

        return continue_menu
    
    def set_chip_options(self):
        '''
            A helper function, which creates a list of which options are available for chip selection.
            Each chip gets a number, while option '1' and a option '2' are shortcuts for connected
            chips and all chips respectively.
        '''
        options = ['1','2']

        for num, chip in enumerate(self.chip_list):
            options.append(f'{num+3}')

        return options

def main():
    Gui = None
    try:
        import UI.GUI.GUI as GUI
        Gui = True
    except:
        print('The GUI module could not be loaded. This means the plot and the GUI functions are disabeled')
        Gui = False
    ext_input_list = sys.argv
    ext_input_list.pop(0)
    if ext_input_list == []:
        tpx3_cli = TPX3_CLI_TOP(Gui = Gui)
    else:
        tpx3_cli = TPX3_CLI_TOP(Gui = Gui, ext_input_list = ext_input_list)

if __name__ == '__main__':
    main()
