import readline
import sys
import os
import time
from multiprocessing import Process, Queue, Pipe
from subprocess import Popen, PIPE
from shutil import copy

from tpx3.scans.ToT_calib import ToTCalib
from tpx3.scans.scan_threshold import ThresholdScan
from tpx3.scans.scan_testpulse import TestpulseScan
from tpx3.scans.PixelDAC_opt_fast import PixelDAC_opt
from tpx3.scans.equalisation_charge import Equalisation_charge
from tpx3.scans.equalisation import Equalisation
from tpx3.scans.take_data import DataTake
from tpx3.scans.Threshold_calib import ThresholdCalib
from tpx3.scans.scan_hardware import ScanHardware
from tpx3.scan_base import ConfigError
from UI.tpx3_logger import file_logger, mask_logger, TPX3_datalogger
from UI.GUI.converter import utils as conv_utils
from UI.GUI.converter.converter_manager import ConverterManager
from tpx3.utils import get_software_version, get_git_branch, get_git_commit, get_git_date


# In this part all callable normal function names should be in the list functions
functions = ['ToT', 'ToT_Calibration', 'tot_Calibration', 'tot',
                'Threshold_Scan', 'THL_Scan', 'THL', 'threshold_scan', 'thl_scan', 'thl',
                'Threshold_Calibration', 'THL_Calib', 'threshold_calibration', 'thl_calib',
                'Pixel_DAC_Optimisation', 'Pixel_DAC', 'PDAC', 'pixel_dac_optimisation', 'pixel_dac', 'pdac',
                'Equalisation', 'Equal', 'EQ', 'equalisation', 'equal', 'eq',
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
                'TP_Period', 'tp_period',
                'Set_operation_mode', 'Set_Op_mode', 'Op_mode', 'set_operation_mode', 'set_Op_mode', 'op_mode',
                'Set_Fast_Io', 'Fast_Io', 'set_fast_io', 'fast_io', 'Fast_Io_en', 'fast_io_en',
                'Set_Readout_Intervall', 'set_readout_intervall', 'Readout_Intervall', 'readout_intervall',
                'Plot', 'plot',
                'Stop_Plot', 'stop_plot',
                'Expert', 'expert',
                'Chip_names', 'chip_names', 'Who', 'who',
                'Mask_name', 'mask_name',
                'Equalisation_name', 'equalisation_name', 'Equal_name', 'equal_name',
                'Help', 'help', 'h', '-h',
                'About', 'about',
                'End', 'end', 'Quit', 'quit', 'q', 'Q', 'Exit', 'exit']

# In this part all callable expert function names should be in the list expert_functions
expert_functions = ['Set_CLK_fast_mode', 'set_clk_fast_mode', 'CLK_fast_mode', 'clk_fast_mode',
                    'Set_Acknowledgement', 'set_acknowledgement', 'Acknowledgement', 'acknowledgement',
                    'Set_TP_ext_in', 'set_tp_ext_in', 'TP_ext_in', 'tp_ext_in',
                    'Set_ClkOut_frequency', 'set_clkout_frequency', 'ClkOut_frequency', 'clkout_frequency',
                    'Set_Sense_DAC', 'set_sense_DAC', 'Sense_DAC', 'sense_DAC',
                    'Enable_Link', 'enable_link', 'Disable_Link', 'disable_link']

# In this list all functions are named which will be shown when the help command is used
help_functions = ['ToT_Calibration', 'Threshold_Scan', 'Threshold_Calibration', 'Pixel_DAC_Optimisation', 'Equalisation',
                    'Testpulse_Scan', 'Run_Datataking', 'Initialise_Hardware', 'Set_DAC','Load_Equalisation', 'Save_Equalisation',
                    'Unset_Mask', 'Set_Default', 'Set_Readout_Intervall', 'Plot', 'Stop_Plot', 'GUI', 'Chip_names', 'Mask_name', 'Equalisation_name', 'About', 'Help', 'Quit']

help_expert = ['Set_CLK_fast_mode', 'Set_Acknowledgement', 'Set_TP_ext_in', 'Set_ClkOut_frequency', 'Set_Sense_DAC', 'Enable_Link']

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

# This class starts a new process when a function is called. this is used for all TPX3 Scan functions and the datataking function. 
# With this you can end a wrong started function with "Ctrl. c" without ending the whole CLI.
class TPX3_multiprocess_start(object):
    def process_call(function, **kwargs):

        def startup_func(function, **kwargs):
            system_exit = False
            try:  
                call_func = (function + '()')
                scan = eval(call_func)
                scan.start(**kwargs)
                scan.analyze(**kwargs)
                scan.plot(**kwargs)
            except KeyboardInterrupt:
                sys.exit(1)
            except ValueError as e:
                print(e)
            except ConfigError:
                print('The current link configuration is not valid. Please start "Init" or check your hardware.')
            except NotImplementedError:
                pass
            except SystemExit:
                system_exit = True

            status = kwargs.pop('status', None)
            if status != None and system_exit != True:
                status.put('Scan finished')

        file_logger.write_tmp_backup()
        new_process = Process(target = startup_func, args = (function, ), kwargs = kwargs)
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

        print('ToT calibration with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'mask_step =', mask_step)
        new_process = TPX3_multiprocess_start.process_call(function = 'ToTCalib',
                                                           VTP_fine_start = VTP_fine_start,
                                                           VTP_fine_stop = VTP_fine_stop,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'))
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

        print('Threshold scan with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step = ', mask_step)
        new_process = TPX3_multiprocess_start.process_call(function = 'ThresholdScan',
                                                           Vthreshold_start = Vthreshold_start,
                                                           Vthreshold_stop = Vthreshold_stop,
                                                           n_injections = n_injections,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'))
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
            print('> Please enter the number of pulse height steps(2-100)[4]:')
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
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'))
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

        print('Testpulse scan with VTP_fine_start =', VTP_fine_start, 'VTP_fine_stop =',VTP_fine_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        new_process = TPX3_multiprocess_start.process_call(function = 'TestpulseScan',
                                                           VTP_fine_start = VTP_fine_start,
                                                           VTP_fine_stop = VTP_fine_stop,
                                                           n_injections = n_injections,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'))
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
        new_process = TPX3_multiprocess_start.process_call(function = 'PixelDAC_opt',
                                                           iteration = 0,
                                                           Vthreshold_start = Vthreshold_start,
                                                           Vthreshold_stop = Vthreshold_stop,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           n_injections = n_injections,
                                                           offset = offset,
                                                           result = pixeldac_result,
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'))
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

        print('Equalisation with Vthreshold_start =', Vthreshold_start, 'Vthreshold_stop =', Vthreshold_stop, 'Number of injections = ', n_injections, 'mask_step =', mask_step)
        result_path = Queue()
        new_process = TPX3_multiprocess_start.process_call(function = 'Equalisation_charge',
                                                           Vthreshold_start = Vthreshold_start,
                                                           Vthreshold_stop = Vthreshold_stop,
                                                           n_injections = n_injections,
                                                           mask_step = mask_step,
                                                           tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                           result_path = result_path,
                                                           maskfile = TPX3_datalogger.read_value(name = 'Mask_path'))
        new_process.join()
        TPX3_datalogger.write_value(name = 'Equalisation_path', value = result_path.get())

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
                print('> Please enter the DAC value (0-15):')
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
        user_path = os.path.join(user_path, 'equalisations')

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
        user_path = os.path.join(user_path, 'equalisations')

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
            print('Unknown value')

    def Set_Mask(object, mask_input_list = None):
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
                        mask_logger.write_mask(mask_element = ['row', int(mask[1])])
                    else:
                        print('Row number out of range: There is only row 0 to 255')
                else: 
                    print('Error: No row number given!')
            elif mask[0] in {'column', 'Column', 'c'}:
                if len(mask) >= 2:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256:
                        print('Mask column', int(mask[1]))
                        mask_logger.write_mask(mask_element = ['column', int(mask[1])])
                    else:
                        print('Column number out of range: There is only column 0 to 255')
                else: 
                    print('Error: No column number given!')
            elif mask[0] in {'pixel', 'Pixel', 'p'}:
                if len(mask) >= 3:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256 and int(mask[2]) >= 0 and int(mask[2]) < 256:
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
                            mask_logger.delete_mask(mask_element = ['row', int(mask[1])])
                        else:
                            print('Row number out of range: There is only row 0 to 255')
                    else: 
                        print('Error: No row number given!')
                elif mask[0] in {'column', 'Column', 'c'}:
                    if len(mask) >= 2:
                        if int(mask[1]) >= 0 and int(mask[1]) < 256:
                            print('Unmask column', int(mask[1]))
                            mask_logger.delete_mask(mask_element = ['column', int(mask[1])])
                        else:
                            print('Column number out of range: There is only column 0 to 255')
                    else: 
                        print('Error: No column number given!')
                elif mask[0] in {'pixel', 'Pixel', 'p'}:
                    if len(mask) >= 3:
                        if int(mask[1]) >= 0 and int(mask[1]) < 256 and int(mask[2]) >= 0 and int(mask[2]) < 256:
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
                current_mask = TPX3_datalogger.read_value(name = 'Mask_path')
                copy(current_mask, full_path)
        except:
            print('Could not write file')

    def Enable_Link(object, link = None, flag = None):
        if link == None:
            print('> Please enter the link you like to disable/enable[0-7]:')
            while(1):
                link = input('>> ')
                try:
                    link = int(link)
                    if link in (0,1,2,3,4,5,6,7):
                        break
                    else:
                        print('Link needs to be between "0" and "7"')
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
                                                           readout_interval = TPX3_datalogger.read_value(name = 'Readout_Speed'))
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
        function_call = TPX3_CLI_function_call()
        expertmode = False
        data = file_logger.read_backup()
        TPX3_datalogger.set_data(data)
        TPX3_datalogger.write_backup_to_yaml()
        self.software_version = get_software_version(git = False)
        TPX3_datalogger.write_value(name = 'software_version', value = self.software_version)
        self.firmware_version = 'x.x'
        print('\n Welcome to the Timepix3 control Software\n')
        self.data_queue = None
        self.plot_window_process = None
        self.Gui_activated = Gui

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
                            print('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')

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
                                function_call.Threshold_Scan()
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) == 6:
                            try:
                                function_call.Threshold_Scan(Vthreshold_start = int(inputlist[1]), Vthreshold_stop = int(inputlist[2]), n_injections = int(inputlist[3]), mask_step = int(inputlist[4]), n_pulse_height = int(inputlist[5]))
                            except KeyboardInterrupt:
                                print('User quit')
                        elif len(inputlist) > 6:
                            print('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256),\n number of pulse height steps (2-100).')

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
                            print('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n column offset (0-15).')

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
                            print('To many parameters! The given function takes only four parameters:\n start testpulse value (0-2911),\n stop testpulse value (0-2911),\n number of injections (1-65535),\n number of steps (4, 16, 64, 256).')

                #Set_DAC
                elif inputlist[0] in {'Set_DAC', 'set_dac'}:
                    if len(inputlist) == 1:
                        print('Set_DAC')
                        try:
                            function_call.Set_DAC()
                        except:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the Set DAC function. As arguments you can give the DAC-name/DAC-number and the new value.\n The following DACs are aviable:\n     1.) Ibias_Preamp_ON (0-255)\n     2.) VPreamp_NCAS (0-255)\n     3.) Ibias_Ikrum (0-255)\n     4.) Vfbk (0-255)\n     5.) Vthreshold_fine (0-511)\n     6.) Vthreshold_coarse (0-15)\n     7.) Ibias_DiscS1_ON (0-255)\n     8.) Ibias_DiscS2_ON (0-255)\n     9.) Ibias_PixelDAC (0-255)\n    10.) Ibias_TPbufferIn (0-255)\n    11.) Ibias_TPbufferOut (0-255)\n    12.) VTP_coarse (0-255)\n    13.) VTP_fine (0-511)\n    14.) Ibias_CP_PLL (0-255)\n    15.) PLL_Vcntrl (0-255)')
                        elif len(inputlist) < 3:
                            print('Incomplete set of parameters:')
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
                                print('Unknown DAC-name')
                        elif len(inputlist) > 3:
                            print('To many parameters! The given function takes only two parameters:\n The DAC-name and its value.')

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
                            print('To many parameters! The given function takes only one parameters:\n scan timeout (in seconds).')

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
                            print('To many parameters! The given function takes only one parameters:\n equalisation path.')

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
                            print('To many parameters! The given function takes only one parameters:\n equalisation file name.')

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
                            print('To many parameters! The given function takes only one parameters:\n backup file name.')

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
                            print('To many parameters! The given function takes only one parameters:\n backup file name.')

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
                            print('To many parameters! The given function takes only one parameters:\n polarity.')

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
                            print('To many parameters! The given function takes only one parameters:\n mask file name.')

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
                            print('To many parameters! The given function takes only one parameters:\n mask file name.')

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
                            print('To many parameters! The given function takes only one parameters:\n operation mode.')

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
                            print('To many parameters! The given function takes only one parameters:\n Fast Io enable.')

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
                            for n in range(0, 2):
                                if n == 0 and Chip_List:
                                    self.firmware_version = Chip_List.pop(0)
                                    TPX3_datalogger.write_value(name = 'firmware_version', value = self.firmware_version)
                                elif Chip_List:
                                    name = 'Chip' + str(n - 1) + '_name'
                                    TPX3_datalogger.write_value(name = name, value = Chip_List.pop(0))
                                else:
                                    name = 'Chip' + str(n - 1) + '_name'
                                    TPX3_datalogger.write_value(name = name, value = [None])
                        except KeyboardInterrupt:
                            print('User quit')
                    else:
                        if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                            print('This is the initialise hardware function. It initialises the hardware and looks how many links and Chips are connected')
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
                        print('This is only aviable with a graphic backend')

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
                                print('The Plot window is still open or not stoped vie "stop_plot". This will be done for you now.')
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
                                    print('Error: I did not recieve any values from plotting window')
                                self.plot_window_process = None

                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This will start the a online ploting window for the data taken')
                            elif len(inputlist) > 1:
                                print('Plot takes no parameters')
                    else:
                        print('This is only aviable with a graphic backend')

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
                                    print('Error: I did not recieve any values from plotting window')
                                self.plot_window_process = None

                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This will start the a online ploting window for the data taken')
                            elif len(inputlist) > 1:
                                print('Plot takes no parameters')
                    else:
                        print('This is only aviable with a graphic backend')

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

                # Get Chip names
                elif inputlist[0] in {'Chip_names', 'chip_names', 'Who', 'who'}:
                    print('Connected chips are:')
                    for Chipname in TPX3_datalogger.get_chipnames():
                        number_of_links = TPX3_datalogger.get_links(chipname=Chipname)
                        if number_of_links == 1:
                            print(Chipname + ' on ' + str(number_of_links) + ' link')
                        else:
                            print(Chipname + ' on ' + str(number_of_links) + ' links')

                #Get Mask name
                elif inputlist[0] in {'Mask_name', 'mask_name'}:
                    mask_path = TPX3_datalogger.read_value(name = 'Mask_path')
                    if mask_path == None:
                            print('No mask is loaded')
                    else:
                        print('The mask file "' + mask_path + '" is loaded')

                #Get Equalisation name
                elif inputlist[0] in {'Equalisation_name', 'equalisation_name', 'Equal_name', 'equal_name'}:
                    mask_path = TPX3_datalogger.read_value(name = 'Equalisation_path')
                    if mask_path == None:
                            print('No equalisation is loaded')
                    else:
                        print('The equalisation file "' + mask_path + '" is loaded')

                #About
                elif inputlist[0] in {'About', 'about'}:
                    print('TPX3 CLI')
                    print('Software version: ' + str(self.software_version))
                    print('Firmware version: ' + str(self.firmware_version))
                    try:
                        print('Git branch: ' + str(get_git_branch()))
                        print('Git commit: ' + str(get_git_commit()))
                        print('Git date: ' + str(get_git_date(short = False)))
                    except:
                        pass
                    print('GasDet Bonn 2019-2021')

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
                            print('Error: I did not recieve any values from plotting window')
                        self.plot_window_process = None
                    file_logger.write_backup(file = file_logger.create_file())
                    file_logger.delete_tmp_backups()
                    print('Goodbye and have a nice day.')
                    break

                #Expert mode functions
                elif expertmode == True:

                    #Set CLK fast mode
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
                                print('To many parameters! The given function takes only one parameters:\n CLK_fast_mode enable.')

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
                                print('To many parameters! The given function takes only one parameter:\n Acknowledgement enable.')

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
                                print('To many parameters! The given function takes only one parameter:\n TP_ext_in enable.')

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
                                print('To many parameters! The given function takes only one parameters:\n ClkOut_frequency.')

                    #Set Sense DAC
                    elif inputlist[0] in {'Set_Sense_DAC', 'set_sense_DAC', 'Sense_DAC', 'sense_DAC'}:
                        if len(inputlist) == 1:
                            print('Set Sense_DAC')
                            try:
                                function_call.Set_Sense_DAC()
                            except KeyboardInterrupt:
                                print('User quit')
                        else:
                            if inputlist[1] in {'Help', 'help', 'h', '-h'}:
                                print('This is the set Sense_DAC function. As argument you can give the DAC you like to read out: Off["0"]; Ibias_Preamp_ON["1"]; Ibias_Preamp_OFF["2"]; VPreamp_NCAS["3"]; Ibias_Ikrum["4"]; Vfbk["5"]; Vthreshold_fine["6"]; Vtreshold_corse["7"]; IBias_DiscS1_ON["8"]; IBias_DiscS1_OFF["9"]; IBias_DiscS2_ON["10"]; IBias_DiscS2_OFF["11"]; IBias_PixelDAC["12"]; IBias_TPbufferIn["13"]; IBias_TPbufferOut["14"]; VTP_coarse["15"]; VTP_fine["16"]; Ibias_CP_PLL["17"]; PLL_Vcntrl["18"]; BandGap_output["28"]; BandGap_Temp["29"]; Ibias_dac["30"]; Ibias_dac_cas["31"]')
                            elif len(inputlist) == 2:
                                if inputlist[1] in {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '28', '29', '30', '31'}:
                                    try:
                                        function_call.Set_Sense_DAC(DAC = int(inputlist[1]))
                                    except KeyboardInterrupt:
                                        print('User quit')
                                else:
                                    print('Unknown argument')
                            elif len(inputlist) > 2:
                                print('To many parameters! The given function takes only one parameters:\n DAC number.')

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
                                if inputlist[1] in {'0', '1', '2', '3', '4', '5', '6', '7'} and inputlist[2] in {'0', '1'}:
                                    try:
                                        function_call.Enable_Link(link = inputlist[1], flag = inputlist[2])
                                    except KeyboardInterrupt:
                                        print('User quit')
                                else:
                                    print('Unknown argument')
                            elif len(inputlist) > 3:
                                print('To many parameters! The given function takes two parameters:\n Link number and "0" or "1".')

                    #Unknown command
                    else:
                        print('Unknown command: ', cmd_input, ' Use a language I understand.')

                #Unknown command
                else:
                    print('Unknown command: ', cmd_input, ' Use a language I understand.')

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
