#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from __future__ import absolute_import
from __future__ import division
import time
import os
import yaml
import logging
import tables as tb
import numpy as np
import zmq
from tqdm import tqdm
import math
from basil.utils.BitLogic import BitLogic

from contextlib import contextmanager
from .tpx3 import TPX3
from .fifo_readout import FifoReadout
from basil.dut import Dut
from tpx3.utils import check_user_folders, get_equal_path, get_software_version
from tables.exceptions import NoSuchNodeError
import six
from six.moves import range

loglevel = logging.getLogger('TPX3').getEffectiveLevel()


class ConfigError(Exception):
    pass

class MetaTable(tb.IsDescription):
    index_start = tb.UInt64Col(pos=0)
    index_stop = tb.UInt64Col(pos=1)
    data_length = tb.UInt32Col(pos=2)
    timestamp_start = tb.Float64Col(pos=3)
    timestamp_stop = tb.Float64Col(pos=4)
    scan_param_id = tb.UInt32Col(pos=5)
    discard_error = tb.UInt32Col(pos=6)
    decode_error = tb.UInt32Col(pos=7)
    trigger = tb.Float64Col(pos=8)


class RunConfig_General(tb.IsDescription):
    scan_id          = tb.StringCol(128)
    run_name         = tb.StringCol(128) 
    software_version = tb.StringCol(128)
    board_name       = tb.StringCol(128)
    firmware_version = tb.StringCol(128)
    wafer_number     = tb.StringCol(128)
    x_position       = tb.StringCol(128)
    y_position       = tb.StringCol(128)

class RunConfig_PixelDACopt(RunConfig_General):
    Vthreshold_start = tb.UInt16Col()
    Vthreshold_stop  = tb.UInt16Col()
    n_injections     = tb.UInt16Col()
    offset           = tb.UInt16Col()
    tp_period        = tb.UInt16Col()
    maskfile         = tb.StringCol(128)
    pixeldac         = tb.UInt16Col()
    last_pixeldac    = tb.UInt16Col()
    last_delta       = tb.Float64Col()

class RunConfig_EqualisationCharge(RunConfig_General):
    Vthreshold_start = tb.UInt16Col()
    Vthreshold_stop  = tb.UInt16Col()
    n_injections     = tb.UInt16Col()
    mask_step        = tb.UInt16Col()
    maskfile         = tb.StringCol(128)
    tp_period        = tb.UInt16Col()


class RunConfig_ThresholdCalib(RunConfig_General):
    Vthreshold_start = tb.UInt16Col()
    Vthreshold_stop  = tb.UInt16Col()
    n_injections     = tb.UInt16Col()
    mask_step        = tb.UInt16Col()
    tp_period        = tb.UInt16Col()
    n_pulse_heights  = tb.UInt16Col()
    thrfile          = tb.StringCol(128)
    maskfile         = tb.StringCol(128)
    
class RunConfig_ThresholdScan(RunConfig_General):
    Vthreshold_start = tb.UInt16Col()
    Vthreshold_stop  = tb.UInt16Col()
    n_injections     = tb.UInt16Col()
    mask_step        = tb.UInt16Col()
    tp_period        = tb.UInt16Col()
    thrfile          = tb.StringCol(128)
    maskfile         = tb.StringCol(128)

class RunConfig_TestpulseScan(RunConfig_General):
    VTP_fine_start = tb.UInt16Col()
    VTP_fine_stop  = tb.UInt16Col()
    n_injections   = tb.UInt16Col()
    mask_step      = tb.UInt16Col()
    tp_period      = tb.UInt16Col()
    thrfile        = tb.StringCol(128)
    maskfile       = tb.StringCol(128)

class RunConfig_ToTCalib(RunConfig_General):
    VTP_fine_start = tb.UInt16Col()
    VTP_fine_stop  = tb.UInt16Col()
    mask_step      = tb.UInt16Col()
    tp_period      = tb.UInt16Col()
    thrfile        = tb.StringCol(128)
    maskfile       = tb.StringCol(128)


class RunConfig_NoiseScan(RunConfig_General):
    Vthreshold_start = tb.UInt16Col()
    Vthreshold_stop  = tb.UInt16Col()
    shutter          = tb.Float64Col()
    thrfile          = tb.StringCol(128)
    maskfile         = tb.StringCol(128)

class RunConfig_DataTake(RunConfig_General):
    thrfile  = tb.StringCol(128)
    maskfile = tb.StringCol(128)


RunConfigTables = {
    'EqualisationCharge': RunConfig_EqualisationCharge,
    'EqualisationNoise' : RunConfig_EqualisationCharge,
    'PixelDACopt'       : RunConfig_PixelDACopt,
    'TestpulseScan'     : RunConfig_TestpulseScan,
    'ThresholdScan'     : RunConfig_ThresholdScan,
    'ThresholdCalib'    : RunConfig_ThresholdCalib,
    'NoiseScan'         : RunConfig_NoiseScan,
    'ToTCalib'          : RunConfig_ToTCalib,
    'DataTake'          : RunConfig_DataTake
}


class RunConfigTable(tb.IsDescription):
    attribute = tb.StringCol(64)
    value = tb.StringCol(128)


class DacTable(tb.IsDescription):
    DAC = tb.StringCol(64)
    value = tb.UInt16Col()

class DacTable_alt(tb.IsDescription):
    wafer_number      = tb.StringCol(128)
    x_position        = tb.StringCol(128)
    y_position        = tb.StringCol(128)
    Ibias_Preamp_ON   = tb.UInt16Col()
    Ibias_Preamp_OFF  = tb.UInt16Col()
    VPreamp_NCAS      = tb.UInt16Col()
    Ibias_Ikrum       = tb.UInt16Col()
    Vfbk              = tb.UInt16Col()
    Vthreshold_fine   = tb.UInt16Col()
    Vthreshold_coarse = tb.UInt16Col()
    Ibias_DiscS1_ON   = tb.UInt16Col()
    Ibias_DiscS1_OFF  = tb.UInt16Col()
    Ibias_DiscS2_ON   = tb.UInt16Col()
    Ibias_DiscS2_OFF  = tb.UInt16Col()
    Ibias_PixelDAC    = tb.UInt16Col()
    Ibias_TPbufferIn  = tb.UInt16Col()
    Ibias_TPbufferOut = tb.UInt16Col()
    VTP_coarse        = tb.UInt16Col()
    VTP_fine          = tb.UInt16Col()
    Ibias_CP_PLL      = tb.UInt16Col()
    PLL_Vcntrl        = tb.UInt16Col()
    Sense_DAC         = tb.UInt16Col()


class ConfTable(tb.IsDescription):
    configuration = tb.StringCol(64)
    value = tb.UInt16Col()


class ConfTable_alt(tb.IsDescription):
    wafer_number         = tb.StringCol(128)
    x_position           = tb.StringCol(128)
    y_position           = tb.StringCol(128)
    Polarity             = tb.UInt16Col()
    Op_mode              = tb.UInt16Col()
    Gray_count_en        = tb.UInt16Col()
    AckCommand_en        = tb.UInt16Col()
    TP_en                = tb.UInt16Col()
    Fast_Io_en           = tb.UInt16Col()
    TimerOverflowControl = tb.UInt16Col()
    SelectTP_Dig_Analog  = tb.UInt16Col()
    SelectTP_Ext_Int     = tb.UInt16Col()
    SelectTP_ToA_Clk     = tb.UInt16Col()


class Links(tb.IsDescription):
    receiver = tb.StringCol(64)
    fpga_link = tb.UInt8Col()
    chip_link = tb.UInt8Col()
    chip_id = tb.StringCol(64)
    data_delay = tb.UInt8Col()
    data_invert = tb.UInt8Col()
    data_edge = tb.UInt8Col()
    link_status = tb.UInt8Col()


def send_data(socket, data, scan_par_id, name='ReadoutData'):
    '''
        Sends the data of every read out (raw data and meta data)
        via ZeroMQ to a specified socket
    '''

    data_meta_data = dict(
        name = name,
        dtype = str(data[0].dtype),
        shape = data[0].shape,
        timestamp_start = data[1],  # float
        timestamp_stop = data[2],  # float
        error = data[3],  # int
        scan_par_id = scan_par_id
    )
    try:
        socket.send_json(data_meta_data, flags=zmq.SNDMORE | zmq.NOBLOCK)
        # PyZMQ supports sending numpy arrays without copying any data
        socket.send(data[0], flags=zmq.NOBLOCK)
    except zmq.Again:
        pass


class ScanBase(object):
    '''
        Basic run meta class.
        Base class for scan- / tune- / analyze-class.
    '''

    def __init__(self, dut_conf=None, no_chip=False, run_name = None):

        # Create list for chipIds and chip objects
        self.chipIds = []
        self.chips   = []

        self.proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.expanduser('~')
        self.data_dir = os.path.join(self.data_dir, 'Timepix3')

        # Create Intermediate layer
        if not dut_conf:
            dut_conf = os.path.join(self.proj_dir, 'tpx3' + os.sep + 'tpx3.yml')

        #logger.info("Loading configuration file from %s" % conf)
        Dut_layer = Dut(dut_conf)
        Dut_layer.init()

        # Initialize the chip communication
        if no_chip == False:
            chip = TPX3()
            chip.init(inter_layer=Dut_layer)
            self.chips.append(chip)

        # Initialize the files
        check_user_folders()
        self.set_directory()
        self.make_files(run_name)

        if no_chip == False:
            self.number_of_chips = 1
            self.chip_links = 0

            # Test if the link configuration is valid
            if self.test_links() == True:
                self.logger.info("Validity check of link configuration successful")
                # If link config is valid, initialize more chips via chipId from links.yml
                # create list of chipIds, no duplicates
                # from this list create list of chip objects 
                for chipId in self.chipIds:
                    # Convert chipId to 4 byte representation: [0x--, 0x--, 0x--, 0x--]
                    Id_binary = '{:032b}'.format(chipId)
                    Id_bytes  = [int(Id_binary[:8],2),int(Id_binary[8:16],2) ,int(Id_binary[16:24],2) ,int(Id_binary[24:],2)]
                    bit_id    = BitLogic.from_value(chipId)

                    # Decode the Chip-ID
                    wafer_number = bit_id[19:8].tovalue()
                    x_position   = chr(ord('a') + bit_id[3:0].tovalue() - 1).upper()
                    y_position   = bit_id[7:4].tovalue()
                    ID           = 'W' + str(wafer_number) + '-' + x_position + str(y_position)
                    # Write information about the chip into chip object
                    chip         = TPX3()
                    chip.init(ChipId = [Id_bytes, chipId, ID, wafer_number, x_position, y_position])
                    self.chips.append(chip)
            else:
                self.logger.info("Validity check of link configuration failed")
                raise ConfigError("Link configuration is not valid for current setup")

        self.num_of_chips = len(self.chipIds)

    def set_directory(self,sub_dir=None):
        # Get the user directory
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        if not os.path.exists(user_path):
            os.makedirs(user_path)

        # Store runs in '~/Timepix3/data' and other scans in '~/Timepix3/scans'
        if self.scan_id == "DataTake":
            scan_path = os.path.join(user_path, 'data')
        else:
            scan_path = os.path.join(user_path, 'scans')

        if not os.path.exists(scan_path):
            os.makedirs(scan_path)

        # Setup the output_data directory
        if sub_dir:
            self.working_dir = os.path.join(scan_path, sub_dir)
            if not os.path.exists(self.working_dir):
                os.makedirs(self.working_dir)
        else:
            self.working_dir = scan_path

    def make_files(self, run_name = None):
        # Create the filename for the HDF5 file and the logger by combining timestamp and run_name
        self.timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        if run_name == None:
            self.run_name = self.scan_id + '_' + self.timestamp
        else:
            self.run_name = run_name
        output_path = os.path.join(self.working_dir, 'hdf')
        self.output_filename = os.path.join(output_path, self.run_name)

        # Setup the logger and the logfile
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(loglevel)
        self.setup_logfile()
        self.logger.info('Initializing %s...', self.__class__.__name__)

    def get_basil_dir(self):
        '''
            Returns the directory of the basil installation
        '''
        return str(os.path.dirname(os.path.dirname(basil.__file__)))

    def get_chip(self):
        '''
            Returns the chip object
        '''
        return self.chips

    def test_links(self):
        '''
            Checks if communication with the chip based on the settings in links.yml is possible.
            If it is possible true is returned if not false is returned
        '''
        # Open the link yaml file
        proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yaml_file = os.path.join(proj_dir, 'tpx3' + os.sep + 'links.yml')

        if not yaml_file == None:
            with open(yaml_file) as file:
                yaml_data = yaml.load(file, Loader=yaml.FullLoader)

        # Variable to track if the configuration is valid
        valid = True

        # Iterate over all links
        for register in yaml_data['registers']:
            # Reset the chip
            self.chips[0].toggle_pin("RESET")

            # Write the PLL
            data = self.chips[0].write_pll_config()

            # Create the chip output channel mask and write the output block
            self.chips[0]._outputBlocks["chan_mask"] = 0b1 << register['chip-link']
            self.chips[0].write_outputBlock_config()

            # Deactivate all fpga links
            for register2 in yaml_data['registers']:
                self.chips[0].Dut_layer[register2['name']].ENABLE = 0
                self.chips[0].Dut_layer[register2['name']].reset()

            if register['link-status'] in [1, 3, 5]:
                # Activate the current fpga link and set all its settings
                self.chips[0].Dut_layer[register['name']].ENABLE = 1
                self.chips[0].Dut_layer[register['name']].DATA_DELAY = register['data-delay']
                self.chips[0].Dut_layer[register['name']].INVERT = register['data-invert']
                self.chips[0].Dut_layer[register['name']].SAMPLING_EDGE = register['data-edge']

                # Reset and clean the FIFO
                self.chips[0].Dut_layer['FIFO'].RESET
                time.sleep(0.01)
                self.chips[0].Dut_layer['FIFO'].get_data()

                # Send the EFuse_Read command to get the Chip ID and test the communication
                data = self.chips[0].read_periphery_template("EFuse_Read")
                data += [0x00]*4
                self.chips[0].write(data)

                # Wait some time to collect the response of the chip
                time.sleep(0.01)

                # Get the data from the chip
                fdata = self.chips[0].Dut_layer['FIFO'].get_data()
                dout = self.chips[0].decode_fpga(fdata, True)

                # Check if the received Chip ID is identical with the expected
                if dout[1][19:0].tovalue() != register['chip-id']:
                    valid = False
                    break
                else:
                    if register['chip-id'] not in self.chipIds:
                        self.chipIds.append(register['chip-id'])

        return valid

    def init_links(self):
        '''
            Initializes the links for communication
        '''
        # Open the link yaml file
        proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yaml_file = os.path.join(proj_dir, 'tpx3' + os.sep + 'links.yml')

        if not yaml_file == None:
            with open(yaml_file) as file:
                yaml_data = yaml.load(file, Loader=yaml.FullLoader)

        # Deactivate all fpga links
        for channel_dissable in self.chips[0].Dut_layer.get_modules('tpx3_rx'):
            channel_dissable.ENABLE = 0
            channel_dissable.reset()

        self.chips[0]._outputBlocks["chan_mask"] = 0

        ID_List = []

        self.chip_links = 0

        # Iterate over all links
        for register in yaml_data['registers']:
            if register['link-status'] in [1, 3, 5]:
                # Create the chip output channel mask and write the output block
                self.chips[0]._outputBlocks["chan_mask"] = self.chips[0]._outputBlocks["chan_mask"] | (0b1 << register['chip-link'])

                # Activate the current fpga link and set all its settings
                self.chips[0].Dut_layer[register['name']].ENABLE = 1
                self.chips[0].Dut_layer[register['name']].DATA_DELAY = register['data-delay']
                self.chips[0].Dut_layer[register['name']].INVERT = register['data-invert']
                self.chips[0].Dut_layer[register['name']].SAMPLING_EDGE = register['data-edge']

                bit_id = BitLogic.from_value(register['chip-id'])

                # Decode the Chip-ID
                self.wafer_number = bit_id[19:8].tovalue()
                self.x_position = chr(ord('a') + bit_id[3:0].tovalue() - 1).upper()
                self.y_position = bit_id[7:4].tovalue()
                ID = 'W' + str(self.wafer_number) + '-' + self.x_position + str(self.y_position)

                # Write new Chip-ID to the list
                if ID not in ID_List:
                    ID_List.append(ID)

                self.chip_links += 1

        self.number_of_chips = len(ID_List)
        if self.number_of_chips > 1:
            raise NotImplementedError('Handling of multiple chips is not implemented yet')

    def create_scan_masks(self, mask_step, pixel_threshold = None, number = None, offset = 0, append_datadriven = True, progress = None):
        '''
            Creates the pixel configuration register masks for scans based on the number of mask_step.
            If a value is set for pixel threshold it is used for all pixels. Else the value which is
            already stored for the pixels is used.
            Number sets the number of matrices (starting with offset) which is returned. If number
            is None all matrices are returned.
            If append_datadriven is True the command read_pixel_matrix_datadriven is appended to the
            matrix command list.
            If progress is None a tqdm progress bar is used else progress should be a
            Multiprocess Queue which stores the progress as fraction of 1
            A list of commands to set the masks is returned
        '''
        # Check if parameters are valid
        if mask_step not in {4, 16, 64, 256}:
            raise ValueError("Value {} for mask_step is not in the allowed range (4, 16, 64, 256)".format(mask_step))
        if pixel_threshold not in range(16) and pixel_threshold != None:
            raise ValueError("Value {} for pixel_threshold is not in the allowed range (0 to 15 or None)".format(pixel_threshold))

        # Empty array for the masks command for the scan
        mask_cmds = []

        if number == None:
            number = mask_step

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=number)
        else:
            # Initailize counter for progress
            step_counter = 0

        #temp_mask_matrix = np.zeros((256, 256), dtype=bool)
        #if self.maskfile:
        #    with tb.open_file(self.maskfile, 'r') as infile:
        #        temp_mask_matrix = infile.root.mask_matrix[:]

        # Create the masks for all steps
        for i in range(offset, number + offset):
            mask_step_cmd = []

            for chip in self.chips[1:]:
                temp_mask_matrix = np.zeros((256, 256), dtype=bool)
                # Start with deactivated testpulses on all pixels and all pixels masked
                chip.test_matrix[:, :] = chip.TP_OFF
                chip.mask_matrix[:, :] = chip.MASK_OFF

                # Switch on pixels and test pulses for pixels based on mask_step
                # e.g. for mask_step=16 every 4th pixel in x and y is active
                column_start = i//(mask_step//int(math.sqrt(mask_step)))
                row_start = i%(mask_step//int(math.sqrt(mask_step)))
                step = mask_step//int(math.sqrt(mask_step))
                chip.test_matrix[column_start::step, row_start::step] = chip.TP_ON
                chip.mask_matrix[column_start::step, row_start::step] = chip.MASK_ON

                chip_mask_file = self.maskfile[chip.chipId_decoded]['active']
                if chip_mask_file:
                    try:
                        with tb.open_file(chip_mask_file, 'r') as infile:
                            temp_mask_matrix = infile.root.mask_matrix[:]
                        chip.test_matrix[temp_mask_matrix == True] = chip.TP_OFF
                        chip.mask_matrix[temp_mask_matrix == True] = chip.MASK_OFF
                    except:
                        pass

                # If a pixel threshold is defined set it to all pixels
                if pixel_threshold != None:
                    chip.thr_matrix[:, :] = pixel_threshold

                # Create the list of mask commands - only for columns that changed the pcr
                column_list = list(range(column_start, 256, step))
                if i == offset:
                    for i in range(256 // 4):
                        mask_step_cmd.append(chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))
                else:
                    if column_start == (i-1)//(mask_step//int(math.sqrt(mask_step))):
                        for j in range((256 // int(math.sqrt(mask_step))) // 4):
                            mask_step_cmd.append(chip.write_pcr(column_list[4 * j : 4 * j + 4], write=False))
                    else:
                        previous_column_list = list([x - 1 for x in column_list])
                        if previous_column_list[0] < 0:
                            previous_column_list = previous_column_list[1:]
                            previous_column_list.append(255)
                        for j in range((256 // int(math.sqrt(mask_step))) // 4):
                            mask_step_cmd.append(chip.write_pcr(previous_column_list[4 * j : 4 * j + 4], write=False))
                            mask_step_cmd.append(chip.write_pcr(column_list[4 * j : 4 * j + 4], write=False))

                if append_datadriven == True:
                    # Append the command for initializing a data driven readout
                    mask_step_cmd.append(chip.read_pixel_matrix_datadriven(write=False))

                # Append the list of command for the current mask_step to the full command list
                mask_cmds.append(mask_step_cmd)

            if progress == None:
                # Update the progress bar
                pbar.update(1)
            else:
                # Update the progress fraction and put it in the queue
                step_counter += 1
                fraction = step_counter / number
                progress.put(fraction)

        if progress == None:
            # Close the progress bar
            pbar.close()

        return mask_cmds

    def create_noise_scan_masks(self, mask_step, append_datadriven = True):
        '''
            Creates the pixel configuration register masks for noise scans based on the number of mask_step.
            If append_datadriven is True the command read_pixel_matrix_datadriven is appended to the
            matrix command list.
            A list of commands to set the masks is returned
        '''
        mask_cmds = []

        #temp_mask_matrix = np.zeros((256, 256), dtype=bool)
        #if self.maskfile:
        #    with tb.open_file(self.maskfile, 'r') as infile:
        #        temp_mask_matrix = infile.root.mask_matrix[:]

        for i in range(mask_step):
            mask_step_cmd = []

            for chip in self.chips[1:]:
                temp_mask_matrix = np.zeros((256, 256), dtype=bool)
                chip.mask_matrix[:, :]                                             = chip.MASK_ON
                chip.mask_matrix[i*(256//mask_step):((i+1)*(256//mask_step))-1, :] = chip.MASK_ON

                chip_mask_file = self.maskfile[chip.chipId_decoded]['active']
                if chip_mask_file:
                    try:
                        with tb.open_file(chip_mask_file, 'r') as infile:
                            temp_mask_matrix = infile.root.mask_matrix[:]
                        chip.mask_matrix[temp_mask_matrix == True] = chip.MASK_OFF
                    except:
                        pass

                for j in range(256 // 4):
                    mask_step_cmd.append(chip.write_pcr(list(range(4 * j, 4 * j + 4)), write=False))

                if append_datadriven == True:
                    # Append the command for initializing a data driven readout
                    mask_step_cmd.append(chip.read_pixel_matrix_datadriven(write=False))

            mask_cmds.append(mask_step_cmd)

        return mask_cmds

    def get_shutter_sleep_time(self, sys_clock = 40, n_injections = 100, tp_period = 1, TOT = False):
        '''
            Calculates the shutter sleep time for scans. It is based on the number of testpulses,
            the tp_period and the system clock frequency in MHz as those define the length of
            the testpulse injections.
            An additional factor is used for ToT-based scans as there is additional time needed
            for ToT counting.
        '''
        # The testpulse is 64 clock cycles times the tp_period low and then for the same time high
        period_time = 64 * 2 * tp_period * 1.0 / sys_clock # time in µs

        # For each pulse one period_time is needed
        pulse_time = period_time * n_injections / 1000.0 # time in ms

        # Multiply with a factor to give time for the radout
        sleep_time = pulse_time * 1.5 / 1000.0 # time in s

        # In case of a TOT data taking give additional time for TOT counting
        if TOT:
            sleep_time *= 5

        return sleep_time


    def dump_configuration(self, iteration = None, **kwargs):
        '''
            Dumps the current configuration in tables of the configuration group in the HDF5 file.
            For scans with multiple iterations separate tables for each iteration will be created.
        '''
        # Get table description for this run
        config_table = RunConfigTables[self.scan_id]

        # Save the scan/run configuration
        # Scans without multiple iterations
        if iteration == None:
            run_config_table = self.h5_file.create_table(self.h5_file.root.configuration, name='run_config', title='Run config', description=config_table)
        # Scans with multiple iterations
        else:
            run_config_table = self.h5_file.create_table(self.h5_file.root.configuration, name='run_config_' + str(iteration), title='Run config' + str(iteration), description=config_table)

        if self.scan_id != 'PixelDACopt': # or (self.scan_id == 'PixelDACopt' and iteration == 0):
            chip_list = self.chips[1:]
        else:
            chip_list = self.chips_not_optimized

        for chip in chip_list:
            # Common scan/run configuration parameters
            row = run_config_table.row
            row['scan_id'] = self.scan_id
            row['run_name'] = self.run_name
            row['software_version'] = get_software_version()
            row['board_name'] = self.board_name
            row['firmware_version'] = self.firmware_version
            row['wafer_number'] = chip.wafer_number
            row['x_position'] = chip.x_position
            row['y_position'] = chip.y_position

            # scan/run specific configuration parameters
            run_config_attributes = ['VTP_fine_start', 'VTP_fine_stop', 'n_injections', 'tp_period', 'n_pulse_heights',
                                     'Vthreshold_start', 'Vthreshold_stop', 'pixeldac', 'last_pixeldac', 'last_delta',
                                     'mask_step', 'thrfile', 'maskfile', 'offset', 'shutter']
            for kw, value in six.iteritems(kwargs):
                if kw in run_config_attributes:
                    if kw not in ['pixeldac', 'last_pixeldac', 'last_delta', 'thrfile', 'maskfile']:
                        row[kw] = value
                    elif kw in ['thrfile', 'maskfile']:
                        row[kw] = value[chip.chipId_decoded]['active']
                    else: # use this for PixelDACopt
                        if iteration == 0: 
                            # here the start values set in GUI.py - class GUI_PixelDAC_opt 
                            # -> process_call are used 
                            # (pixeldac = 127, last_pixeldac = 127, last_delta = 1.0)
                            row[kw] = value
                        else: # here for value the optimization_params dict is used in PixelDACopt
                            row[kw] = value[chip.chipId_decoded][kw]
            row.append()

        run_config_table.flush()

        # save the general configuration
        # In scans with multiple iterations only for the first iteration
        if iteration == None or iteration == 0:
            general_config_table = self.h5_file.create_table(self.h5_file.root.configuration, name='generalConfig',
                                                                 title='GeneralConfig', description=ConfTable_alt)
            for chip in chip_list:
                row = general_config_table.row
                row['wafer_number'] = chip.wafer_number
                row['x_position']   = chip.x_position
                row['y_position']   = chip.y_position
                for conf, value in six.iteritems(chip.configs):
                    row[conf] = value
                row.append()
            general_config_table.flush()

        # Save the dac settings
        # In scans with multiple iterations only for the first iteration
        if iteration == None:
            dac_table = self.h5_file.create_table(self.h5_file.root.configuration, name='dacs', title='DACs', description=DacTable_alt)
        # Scans with multiple iterations
        else:
            dac_table = self.h5_file.create_table(self.h5_file.root.configuration, name='dacs_' + str(iteration), title='DACs ' + str(iteration), description=DacTable_alt)
        for chip in chip_list:
            row                 = dac_table.row
            row['wafer_number'] = chip.wafer_number
            row['x_position']   = chip.x_position
            row['y_position']   = chip.y_position

            for dac, value in six.iteritems(chip.dacs):
                row[dac] = value

            row.append()
        dac_table.flush()

        # Save the mask and the pixel threshold matrices
        # In scans with multiple iterations only for the first iteration
        if iteration == None or iteration == 0:
            for chip in chip_list:
                self.h5_file.create_carray(self.h5_file.root.configuration, name=f'mask_matrix_W{chip.wafer_number}_{chip.x_position}{chip.y_position}', title='Mask Matrix', obj=chip.mask_matrix)
                self.h5_file.create_carray(self.h5_file.root.configuration, name=f'thr_matrix_W{chip.wafer_number}_{chip.x_position}{chip.y_position}', title='Threshold Matrix', obj=chip.thr_matrix)

        # save the link configuration
        # In scans with multiple iterations only for the first iteration
        if iteration == None or iteration == 0:
            link_config_table = self.h5_file.create_table(self.h5_file.root.configuration, name='links', title='Links', description=Links)

            # Open the link yaml file
            proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            yaml_file = os.path.join(proj_dir, 'tpx3' + os.sep + 'links.yml')

            if not yaml_file == None:
                with open(yaml_file) as file:
                    yaml_data = yaml.load(file, Loader=yaml.FullLoader)

            for register in yaml_data['registers']:
                row = link_config_table.row
                row['receiver'] = register['name']
                row['fpga_link'] = register['fpga-link']
                row['chip_link'] = register['chip-link']

                # Decode the Chip-ID
                bit_id = BitLogic.from_value(register['chip-id'])
                wafer = bit_id[19:8].tovalue()
                x = chr(ord('a') + bit_id[3:0].tovalue() - 1).upper()
                y = bit_id[7:4].tovalue()
                ID = 'W' + str(wafer) + '-' + x + str(y)
                row['chip_id'] = ID
                row['data_delay'] = register['data-delay']
                row['data_invert'] = register['data-invert']
                row['data_edge'] = register['data-edge']
                row['link_status'] = register['link-status']
                row.append()
            link_config_table.flush()

    def setup_files(self, iteration = None):
        '''
            Setup the HDF5 file by creating the earrays and tables for raw_data and meta_data
            If a scan has multiple iterations individual earrays and tables can be created for
            each iteration
        '''

        filter_raw_data = tb.Filters(complib='blosc', complevel=5, fletcher32=False)
        self.filter_tables = tb.Filters(complib='zlib', complevel=5, fletcher32=False)

        # Scans without multiple iterations
        if iteration == None:
            self.raw_data_earray = self.h5_file.create_earray(self.h5_file.root, name='raw_data', atom=tb.UIntAtom(),
                                                            shape=(0,), title='raw_data', filters=filter_raw_data)
            self.meta_data_table = self.h5_file.create_table(self.h5_file.root, name='meta_data', description=MetaTable,
                                                            title='meta_data', filters=self.filter_tables)
        # Scans with multiple iterations
        else:
            self.raw_data_earray = self.h5_file.create_earray(self.h5_file.root, name='raw_data_' + str(iteration), atom=tb.UIntAtom(),
                                                            shape=(0,), title='raw_data_' + str(iteration), filters=filter_raw_data)
            self.meta_data_table = self.h5_file.create_table(self.h5_file.root, name='meta_data_' + str(iteration), description=MetaTable,
                                                            title='meta_data_' + str(iteration), filters=self.filter_tables)

    def configure(self, **kwargs):
        '''
            Configuring step before scan start
        '''
        self.logger.info('Configuring chip...')

        # Load the mask and pixel threshold matrices
        self.load_mask_matrix(**kwargs)
        self.load_thr_matrix(**kwargs)

    def start(self, readout_interval = 0.005, moving_average_time_period = 10, iteration = None, status = None, **kwargs):
        '''
            Prepares the scan and starts the actual test routine
        '''

        if status != None:
            status.put("Initialize scan")

        self._first_read = False
        self.scan_param_id = 0

        # Initialize the communication with the chip and read the board name and firmware version
        self.fifo_readout = FifoReadout(chip = self.chips[0], readout_interval = readout_interval, moving_average_time_period = moving_average_time_period)
        self.board_name = self.chips[0].board_version
        self.firmware_version = self.chips[0].fw_version

        # Chip start-up sequence
        # Reset the chip
        self.chips[0].toggle_pin("RESET")

        self.init_links()

        # Set the output settings of the chip
        self.chips[0].write_outputBlock_config(write=True)
        self.fifo_readout.print_readout_status()

        # To use local headers, we need to execute EFuse_Read globally
        # once after resetting the chip, so that the ChipID of the
        # chip is known to itself.
        data = self.chips[0].read_periphery_template('EFuse_Read')
        data += [0x00]*4
        self.chips[0].Dut_layer['FIFO'].RESET
        time.sleep(0.1)
        self.chips[0].write(data)
        time.sleep(0.1)
        fdata = self.chips[0].Dut_layer['FIFO'].get_data()

        # Enable power pulsing
        self.chips[0].Dut_layer['CONTROL']['EN_POWER_PULSING'] = 1
        self.chips[0].Dut_layer['CONTROL'].write()

        # Set PLL Config
        for chip in self.chips:
            self.chips[0].write(chip.write_pll_config(write=False))

        # Reset the fpga timestamp pulser
        self.chips[0].Dut_layer['PULSE_GEN'].reset()

        # Only activate the timestamp pulse if TOA is of interest
        if self.scan_id in {"DataTake"}:
            self.chips[0].Dut_layer['PULSE_GEN'].set_delay(40)
            self.chips[0].Dut_layer['PULSE_GEN'].set_width(4056)
            self.chips[0].Dut_layer['PULSE_GEN'].set_repeat(0)
            self.chips[0].Dut_layer['PULSE_GEN'].set_en(True)
        else:
            self.chips[0].Dut_layer['PULSE_GEN'].set_en(False)

        # Reset DACs and set them to the values defined in dacs.yaml / chip_dacs.yml
        for chip in self.chips[1:]:
            chip.reset_dac_attributes(to_default = False)
            data = chip.write_dacs()
            for chunk in data:
                self.chips[0].write(chunk)

            # Sequential reset of the pixel matrix
            self.chips[0].write(chip.reset_sequential(write=False), True)

        self.maskfile = kwargs.get('maskfile', None)
        self.thrfile = kwargs.get('thrfile', None)
        self.configure(**kwargs)

        # Produce needed PCR (Pixel configuration register)
        for chip in self.chips[1:]:
            for i in range(256 // 4):
                self.chips[0].write(chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))

        # Set Op_mode for the scans, based on the scan id
        for chip in self.chips:
            if self.scan_id in ['EqualisationCharge', 'EqualisationNoise', 'PixelDACopt', 'TestpulseScan',
                                'ThresholdScan', 'ThresholdCalib', 'NoiseScan']:
                chip._configs["Op_mode"] = 2
            elif self.scan_id in ['ToTCalib', 'TimewalkCalib']:
                chip._configs["Op_mode"] = 0
            if self.scan_id in ['TimewalkCalib']:
                chip._configs["Fast_Io_en"] = 1

        # Setup HDF5 file
        filename = self.output_filename + '.h5'
        self.h5_file = tb.open_file(filename, mode='w', title=self.scan_id)
        self.setup_files(iteration = iteration)

        # Save configuration to HDF5 file in configuration group
        self.h5_file.create_group(self.h5_file.root, 'configuration', 'Configuration')
        self.dump_configuration(iteration = iteration, **kwargs)

        # Setup data sending - can be used eg. for an event Display
        socket_addr = kwargs.pop('send_data', 'tcp://127.0.0.1:5500')
        if socket_addr:
            try:
                self.context = zmq.Context()
                self.socket = self.context.socket(zmq.PUB)  # publisher socket
                self.socket.bind(socket_addr)
                self.logger.debug('Sending data to server %s', socket_addr)
            except zmq.error.ZMQError:
                self.logger.exception('Cannot connect to socket for data sending.')
                self.socket = None
        else:
            self.socket = None

        # Start the scan
        self.scan(status = status, **kwargs)

        # Print the readout status and disable the receiver after the scan
        self.fifo_readout.print_readout_status()
        self.fifo_readout.enable_rx(False)

        # Close HDF5 file
        self.logger.info('Closing raw data file: %s', self.output_filename + '.h5')
        self.h5_file.close()

        # Close the data socket
        if self.socket:
            self.logger.debug('Closing socket connection')
            self.socket.close()
            self.socket = None

    def analyze(self, **kwargs):
        raise NotImplementedError('ScanBase.analyze() not implemented')

    def plot(self, **kwargs):
        raise NotImplementedError('ScanBase.plot() not implemented')

    def scan(self, **kwargs):
        raise NotImplementedError('ScanBase.scan() not implemented')

    @contextmanager
    def readout(self, *args, **kwargs):
        '''
           Start the readout and keep it running in the readout context
        '''
        timeout = kwargs.pop('timeout', 30.0)

        self.start_readout(*args, **kwargs)
        yield

        self.fifo_readout.stop(timeout=timeout)

    @contextmanager
    def shutter(self):
        '''
            Open the external Timepix3 shutter and keep it open in context of a readout
        '''
        self.chips[0].Dut_layer['CONTROL']['SHUTTER'] = 1
        self.chips[0].Dut_layer['CONTROL'].write()
        yield
        self.chips[0].Dut_layer['CONTROL']['SHUTTER'] = 0
        self.chips[0].Dut_layer['CONTROL'].write()

    def start_readout(self, scan_param_id=0, *args, **kwargs):
        # Pop parameters for fifo_readout.start
        callback = kwargs.pop('callback', self.handle_data)
        clear_buffer = kwargs.pop('clear_buffer', False)
        fill_buffer = kwargs.pop('fill_buffer', False)
        reset_sram_fifo = kwargs.pop('reset_sram_fifo', True)
        errback = kwargs.pop('errback', self.handle_err)
        no_data_timeout = kwargs.pop('no_data_timeout', None)
        self.scan_param_id = scan_param_id
        time.sleep(0.02)  # sleep here for a while
        self.fifo_readout.start(reset_sram_fifo=reset_sram_fifo, fill_buffer=fill_buffer, clear_buffer=clear_buffer,
                                callback=callback, errback=errback, no_data_timeout=no_data_timeout)

    def handle_data(self, data_tuple):
        '''
            Handling of a chunk of data.
        '''

        total_words = self.raw_data_earray.nrows

        # Append the data to the raw data earray in the HDF5 file
        self.raw_data_earray.append(data_tuple[0])
        self.raw_data_earray.flush()

        # Get the meta data of the raw data and create a new row with it
        len_raw_data = data_tuple[0].shape[0]
        self.meta_data_table.row['timestamp_start'] = data_tuple[1]
        self.meta_data_table.row['timestamp_stop'] = data_tuple[2]
        self.meta_data_table.row['discard_error'] = data_tuple[3]
        self.meta_data_table.row['decode_error'] = data_tuple[4]
        self.meta_data_table.row['data_length'] = len_raw_data
        self.meta_data_table.row['index_start'] = total_words
        total_words += len_raw_data
        self.meta_data_table.row['index_stop'] = total_words
        self.meta_data_table.row['scan_param_id'] = self.scan_param_id

        # Write the new meta data row to the meta data table in the HDF5 file
        self.meta_data_table.row.append()
        self.meta_data_table.flush()

        # Send the data to the socket (eg. for the event display)
        if self.socket:
            send_data(self.socket, data=data_tuple, scan_par_id=self.scan_param_id)

    def handle_err(self, exc):
        '''
            Handle data error massages for the logger
        '''
        msg = '%s' % exc[1]
        if msg:
            self.logger.error('%s Data Errors...', msg)
        else:
            self.logger.error(' Data Errors...')

    def setup_logfile(self):
        '''
            Setup the logfile
        '''
        output_path = os.path.join(self.working_dir, 'logs')
        logger_filename = os.path.join(output_path, self.run_name)
        self.fh = logging.FileHandler(logger_filename + '.log')
        self.fh.setLevel(loglevel)
        self.fh.setFormatter(logging.Formatter("%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s"))
        for lg in six.itervalues(logging.Logger.manager.loggerDict):
            if isinstance(lg, logging.Logger):
                lg.addHandler(self.fh)

        return self.fh

    def close_logfile(self):
        '''
            Close the logfile
        '''
        for lg in six.itervalues(logging.Logger.manager.loggerDict):
            if isinstance(lg, logging.Logger):
                lg.removeHandler(self.fh)

    def save_mask_matrix(self, chip):
        '''
            Write the mask matrix to file
        '''
        self.logger.info('Writing mask_matrix to file...')
        #if not self.maskfile:
        user_path = os.path.expanduser('~')
        mask_path = os.path.join(user_path, 'Timepix3')
        mask_path = os.path.join(mask_path, 'masks')
        mask_path = os.path.join(mask_path, chip.chipId_decoded)
        maskfile  = os.path.join(mask_path, f'{chip.chipId_decoded}_{self.timestamp}_mask.h5')

        with tb.open_file(maskfile, 'a') as out_file:
            try:
                out_file.remove_node(out_file.root.mask_matrix)
            except NoSuchNodeError:
                self.logger.debug('Specified maskfile does not include a mask_matrix yet!')

            out_file.create_carray(out_file.root,
                                    name = f'mask_matrix_W{chip.wafer_number}_{chip.x_postition}{chip.y_position}',
                                    title = 'Matrix mask',
                                    obj = chip.mask_matrix)
            self.logger.info('Closing mask file: %s' % (self.maskfile))

    def save_thr_mask(self, eq_matrix, chip):
        '''
            Write the pixel threshold matrix to file
        '''
        self.logger.info(f'Writing equalisation matrix for chip {chip.chipId_decoded} to file...')

        thrfile = os.path.join(get_equal_path(), chip.chipId_decoded)
        thrfile = os.path.join(thrfile, f'{chip.chipId_decoded}_equal_{self.timestamp}.h5')

        with tb.open_file(thrfile, 'a') as out_file:
            try:
                out_file.remove_node(out_file.root.thr_matrix)
            except NoSuchNodeError:
                self.logger.debug('Specified thrfile does not include a thr_mask yet!')

            out_file.create_carray(out_file.root,
                                   name = f'thr_matrix',
                                   title = 'Matrix Threshold',
                                   obj = eq_matrix)
            self.logger.info('Closing thr_matrix file: %s' % (thrfile))

        return thrfile


    def load_mask_matrix(self, **kwargs):
        '''
            Load the mask matrix for each active chip
        '''
        try:
            maskfiles = kwargs['maskfile']
        except:
            maskfiles = None

        for chip in self.chips[1:]:
            try:
                maskfile = maskfiles[chip.chipId_decoded]['active']
            except:
                maskfile = None
            
            if not maskfile in [None, 'None']:
                self.logger.info(f'Loading mask_matrix file: {maskfile} for chip {chip.chipId_decoded}')
                try:
                    with tb.open_file(maskfile, 'r') as infile:
                        table_name       = f'infile.root.mask_matrix_W{chip.wafer_number}_{chip.x_position}{chip.y_position}[:]'
                        chip.mask_matrix = eval(table_name)
                except NoSuchNodeError:
                    self.logger.debug('Specified maskfile does not include a mask_matrix!')
                    pass

    def load_thr_matrix(self, **kwargs):
        '''
            Load the pixel threshold matrix for each active chip
        '''
        try:
            thrfiles = kwargs['thrfile']
        except:
            thrfiles = None

        for chip in self.chips[1:]:
            try:
                thrfile = thrfiles[chip.chipId_decoded]['active']
                print(f'Used threshold file: {thrfile}')
            except:
                thrfile = None

            if not thrfile in [None, 'None']:
                self.logger.info(f'Loading thr_matrix file: {thrfile} for chip {chip.chipId_decoded}')
                try:
                    with tb.open_file(thrfile, 'r') as infile:
                        table_name      = f'infile.root.thr_matrix[:]'
                        chip.thr_matrix = eval(table_name)
                except NoSuchNodeError:
                    self.logger.debug('Specified thrfile does not include a thr_matrix!')
                    pass

    def close(self):
        '''
            Close the chip and the logfile
        '''
        for chip in self.chips:
            chip.close()
        self.close_logfile()
