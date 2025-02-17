#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script measures the timewalk for different test pulse amplitudes
'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import math

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting
from tpx3.plotting import ConfigDict
import tpx3.utils as utils
from six.moves import range
from basil.utils.BitLogic import BitLogic

local_configuration = {
    # Scan parameters
    'mask_step'        : 64,
    'VTP_fine_start'   : 260,
    'VTP_fine_stop'    : 400,
    'thrfile'          : '/home/tpc/Timepix3/equalisations/W18-L9_equal_2025-02-11_15-22-12.h5',
    'maskfile'         : '/home/tpc/Timepix3/masks/W18-L9_mask_2025-02-11_14-37-01.h5'
}


class TimewalkCalib(ScanBase):

    scan_id = "TimewalkCalib"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self, VTP_fine_start=0, VTP_fine_stop=2911, tp_period = 4, mask_step=16, progress = None, status = None, **kwargs):
        '''
            Takes data for timewalk calibration in a range of testpulses with one testpule per iteration
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        # Check if parameters are valid before starting the scan
        if VTP_fine_start < 1 or VTP_fine_start > 511:
            raise ValueError("Value {} for Vthreshold_start is not in the allowed range (1-511)".format(VTP_fine_start))
        if VTP_fine_stop < 1 or VTP_fine_stop > 511:
            raise ValueError("Value {} for Vthreshold_stop is not in the allowed range (1-511)".format(VTP_fine_stop))
        if VTP_fine_stop <= VTP_fine_start:
            raise ValueError("Value for Vthreshold_stop must be bigger than value for Vthreshold_start")
        if mask_step not in {4, 16, 64, 256}:
            raise ValueError("Value {} for mask_step is not in the allowed range (4, 16, 64, 256)".format(mask_step))

        # Set general configuration registers of the Timepix3
        self.chip.write_general_config()

        # Write to the test pulse registers of the Timepix3
        # Write to period and phase tp registers
        data = self.chip.write_tp_period(tp_period, 12)

        # Write to pulse number tp register
        self.chip.write_tp_pulsenumber(1)

        self.logger.info('Preparing injection masks...')
        if status != None:
            status.put("Preparing injection masks")

        # Get the shutter sleep time
        sleep_time = self.get_shutter_sleep_time(tp_period = tp_period, n_injections = 1)
        amplitudes = list(range(VTP_fine_start, VTP_fine_stop, 1))

        # Add amplitude 0 that will be used as a reference with digital test pulses
        amplitudes.insert(0,0)

        # Create the masks for all steps
        mask_cmds = self.create_scan_masks(mask_step, progress = progress, append_datadriven=False)

        # Start the scan
        self.logger.info('Starting scan...')
        if status != None:
            status.put("Starting scan")
        if status != None:
            status.put("iteration_symbol")

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds) * len(amplitudes))
        else:
            # Initialize counter for progress
            step_counter = 0

        self.chip['PULSE_GEN'].set_delay(40)
        self.chip['PULSE_GEN'].set_width(4056)
        self.chip['PULSE_GEN'].set_repeat(100)

        scan_param_id = 0
        for amplitude in amplitudes:
            # Set the testpulse amplitude
            if amplitude == 0:
                self.chip.set_dac("VTP_fine", int(400))
            else:
                self.chip.set_dac("VTP_fine", int(amplitude))
            
            with self.readout(scan_param_id=scan_param_id):
                step = 0
                for mask_step_cmd in mask_cmds:
                    # Only activate testpulses for columns with active pixels
                    self.chip.write_ctpr(list(range(step//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))))

                    # Write the pixel matrix for the current step
                    self.chip.write(mask_step_cmd)

                    # Open the shutter, take data and update the progress bar
                    self.chip['PULSE_GEN'].set_en(True)

                    # For the first step inject the testpulses into the digital part of the
                    # pixels to get the time reference. For all other steps inject the testpulses
                    # to the analog part of the pixels.
                    if amplitude == 0:
                        self.chip._configs["SelectTP_Dig_Analog"] = 1
                    else:
                        self.chip._configs["SelectTP_Dig_Analog"] = 0

                    self.chip.write_general_config()
                    self.chip.read_pixel_matrix_datadriven()

                    # Reset the Timepix3 internal timer
                    self.chip.toggle_pin("TO_SYNC")

                    # Open the shutter and close it after a given time
                    with self.shutter():
                        time.sleep(sleep_time)
                    self.chip.stop_readout()
                    self.chip['PULSE_GEN'].set_en(False)
                    time.sleep(0.02)
                        
                    if progress == None:
                        # Update the progress bar
                        pbar.update(1)
                    else:
                        # Update the progress fraction and put it in the queue
                        step_counter += 1
                        fraction = step_counter / (len(mask_cmds) * len(amplitudes))
                        progress.put(fraction)
                    time.sleep(0.001)
                    step += 1
                self.chip.reset_sequential()
                time.sleep(0.001)
            scan_param_id += 1

        if progress == None:
            # Close the progress bar
            pbar.close()

        if status != None:
            status.put("iteration_finish_symbol")

        self.logger.info('Scan finished')

    def analyze(self, progress = None, status = None, **kwargs):
        '''
            Analyze the data of the scan
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting data analysis...')
        if status != None:
            status.put("Performing data analysis")

        # Open the HDF5 which contains all data of the scan
        with tb.open_file(h5_filename, 'r+') as h5_file:
            run_config = ConfigDict(h5_file.root.configuration.run_config[:])
            VTP_fine_start = int(run_config[b'VTP_fine_start'])
            VTP_fine_stop = int(run_config[b'VTP_fine_stop'])

            # create look up table for 4-bit lfsr
            _lfsr_4_lut = np.zeros((2 ** 4), dtype=np.uint16)
            lfsr = BitLogic(4)
            lfsr[3:0] = 0xF
            dummy = 0
            for i in range(2**4):
                _lfsr_4_lut[BitLogic.tovalue(lfsr)] = i
                dummy = lfsr[3]
                lfsr[3] = lfsr[2]
                lfsr[2] = lfsr[1]
                lfsr[1] = lfsr[0]
                lfsr[0] = lfsr[3] ^ dummy
            _lfsr_4_lut[2 ** 4 - 1] = 0

            # create look up table for 10-bit lfsr
            _lfsr_10_lut = np.zeros((2 ** 10), dtype=np.uint16)
            lfsr = BitLogic(10)
            lfsr[7:0] = 0xFF
            lfsr[9:8] = 0b11
            dummy = 0
            for i in range(2 ** 10):
                _lfsr_10_lut[BitLogic.tovalue(lfsr)] = i
                dummy = lfsr[9]
                lfsr[9] = lfsr[8]
                lfsr[8] = lfsr[7]
                lfsr[7] = lfsr[6]
                lfsr[6] = lfsr[5]
                lfsr[5] = lfsr[4]
                lfsr[4] = lfsr[3]
                lfsr[3] = lfsr[2]
                lfsr[2] = lfsr[1]
                lfsr[1] = lfsr[0]
                lfsr[0] = lfsr[7] ^ dummy
            _lfsr_10_lut[2 ** 10 - 1] = 0

            # create look up table for 14-bit grey counter
            _gray_14_lut = np.zeros((2 ** 14), dtype=np.uint16)
            for j in range(2**14):
                encoded_value = BitLogic(14) #48
                encoded_value[13:0]=j #47
                gray_decrypt_v = BitLogic(14) #48
                gray_decrypt_v[13]=encoded_value[13] #47
                for i in range (12, -1, -1): #46
                    gray_decrypt_v[i]=gray_decrypt_v[i+1]^encoded_value[i]
                _gray_14_lut[j] = gray_decrypt_v.tovalue()

            # Read raw data, meta data and configuration parameters
            raw_data = h5_file.root.raw_data[:]
            meta_data = h5_file.root.meta_data[:]
            scan_param_id = meta_data['scan_param_id']
            chunk_start_time = meta_data['timestamp_start']
            start_indices = meta_data['index_start']
            run_config = h5_file.root.configuration.run_config[:]
            mask = h5_file.root.configuration.mask_matrix[:]
            general_config = h5_file.root.configuration.generalConfig[:]
            op_mode = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            vco = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

            raw_indices = (np.arange(meta_data['index_start'][0], meta_data['index_stop'][-1], 1)).astype(np.uint64)
            hit_filter = np.where(np.right_shift(np.bitwise_and(raw_data, 0xf0000000), 28) == 0b0000)
            hits = raw_data[hit_filter]
            hits_indices = raw_indices[hit_filter]

            timestamp_map = np.right_shift(np.bitwise_and(raw_data, 0xf0000000), 28) == 0b0101
            timestamp_filter = np.where(timestamp_map == True)
            timestamps = raw_data[timestamp_filter]
            timestamps_indices = raw_indices[timestamp_filter]

            shutter_timestamp_map = np.right_shift(np.bitwise_and(raw_data, 0xf0000000), 28) == 0b0111
            shutter_timestamp_filter = np.where(shutter_timestamp_map == True)
            shutter_timestamps = raw_data[shutter_timestamp_filter]
            shutter_timestamps_indices = raw_indices[shutter_timestamp_filter]

            # Split the lists in separate lists for word 0 and word 1 (based on header)
            timestamps_0_filter = np.where(np.right_shift(np.bitwise_and(timestamps, 0x3000000), 24) == 0b01)
            timestamps_1_filter = np.where(np.right_shift(np.bitwise_and(timestamps, 0x3000000), 24) == 0b10)
            timestamps_0 = timestamps[timestamps_0_filter].astype(np.uint64)
            timestamps_1 = timestamps[timestamps_1_filter].astype(np.uint64)
            timestamps_0_indices = timestamps_indices[timestamps_0_filter]
            timestamps_1_indices = timestamps_indices[timestamps_1_filter]

            full_timestamps = np.left_shift(np.bitwise_and(timestamps_1, 0xffffff), 24) + np.bitwise_and(timestamps_0, 0xffffff)
            full_timestamps_indices = timestamps_0_indices

            ## Split the lists in separate lists for word 0 and word 1 (based on header)
            shutter_timestamps_0_filter = np.where(np.right_shift(np.bitwise_and(shutter_timestamps, 0x3000000), 24) == 0b01)
            shutter_timestamps_1_filter = np.where(np.right_shift(np.bitwise_and(shutter_timestamps, 0x3000000), 24) == 0b10)
            shutter_timestamps_0 = shutter_timestamps[shutter_timestamps_0_filter].astype(np.uint64)
            shutter_timestamps_1 = shutter_timestamps[shutter_timestamps_1_filter].astype(np.uint64)
            shutter_timestamps_0_indices = shutter_timestamps_indices[shutter_timestamps_0_filter]
            shutter_timestamps_1_indices = shutter_timestamps_indices[shutter_timestamps_1_filter]

            full_shutter_timestamps = np.left_shift(np.bitwise_and(shutter_timestamps_1, 0xffffff), 24) + np.bitwise_and(shutter_timestamps_0, 0xffffff)
            full_shutter_timestamps_indices = shutter_timestamps_0_indices

            link0_hits_filter = np.where(np.right_shift(np.bitwise_and(hits, 0xfe000000), 24) == 0b00000000)
            link1_hits_filter = np.where(np.right_shift(np.bitwise_and(hits, 0xfe000000), 24) == 0b00000010)
            link2_hits_filter = np.where(np.right_shift(np.bitwise_and(hits, 0xfe000000), 24) == 0b00000100)
            link3_hits_filter = np.where(np.right_shift(np.bitwise_and(hits, 0xfe000000), 24) == 0b00000110)
            link4_hits_filter = np.where(np.right_shift(np.bitwise_and(hits, 0xfe000000), 24) == 0b00001000)
            link5_hits_filter = np.where(np.right_shift(np.bitwise_and(hits, 0xfe000000), 24) == 0b00001010)
            link6_hits_filter = np.where(np.right_shift(np.bitwise_and(hits, 0xfe000000), 24) == 0b00001100)
            link7_hits_filter = np.where(np.right_shift(np.bitwise_and(hits, 0xfe000000), 24) == 0b00001110)
            link0_words = hits[link0_hits_filter]
            link1_words = hits[link1_hits_filter]
            link2_words = hits[link2_hits_filter]
            link3_words = hits[link3_hits_filter]
            link4_words = hits[link4_hits_filter]
            link5_words = hits[link5_hits_filter]
            link6_words = hits[link6_hits_filter]
            link7_words = hits[link7_hits_filter]
            link0_words_indices = hits_indices[link0_hits_filter]
            link1_words_indices = hits_indices[link1_hits_filter]
            link2_words_indices = hits_indices[link2_hits_filter]
            link3_words_indices = hits_indices[link3_hits_filter]
            link4_words_indices = hits_indices[link4_hits_filter]
            link5_words_indices = hits_indices[link5_hits_filter]
            link6_words_indices = hits_indices[link6_hits_filter]
            link7_words_indices = hits_indices[link7_hits_filter]
            link0_words0_filter = np.where(np.right_shift(np.bitwise_and(link0_words, 0x1000000), 24) == 0b0)
            link0_words1_filter = np.where(np.right_shift(np.bitwise_and(link0_words, 0x1000000), 24) == 0b1)
            link1_words0_filter = np.where(np.right_shift(np.bitwise_and(link1_words, 0x1000000), 24) == 0b0)
            link1_words1_filter = np.where(np.right_shift(np.bitwise_and(link1_words, 0x1000000), 24) == 0b1)
            link2_words0_filter = np.where(np.right_shift(np.bitwise_and(link2_words, 0x1000000), 24) == 0b0)
            link2_words1_filter = np.where(np.right_shift(np.bitwise_and(link2_words, 0x1000000), 24) == 0b1)
            link3_words0_filter = np.where(np.right_shift(np.bitwise_and(link3_words, 0x1000000), 24) == 0b0)
            link3_words1_filter = np.where(np.right_shift(np.bitwise_and(link3_words, 0x1000000), 24) == 0b1)
            link4_words0_filter = np.where(np.right_shift(np.bitwise_and(link4_words, 0x1000000), 24) == 0b0)
            link4_words1_filter = np.where(np.right_shift(np.bitwise_and(link4_words, 0x1000000), 24) == 0b1)
            link5_words0_filter = np.where(np.right_shift(np.bitwise_and(link5_words, 0x1000000), 24) == 0b0)
            link5_words1_filter = np.where(np.right_shift(np.bitwise_and(link5_words, 0x1000000), 24) == 0b1)
            link6_words0_filter = np.where(np.right_shift(np.bitwise_and(link6_words, 0x1000000), 24) == 0b0)
            link6_words1_filter = np.where(np.right_shift(np.bitwise_and(link6_words, 0x1000000), 24) == 0b1)
            link7_words0_filter = np.where(np.right_shift(np.bitwise_and(link7_words, 0x1000000), 24) == 0b0)
            link7_words1_filter = np.where(np.right_shift(np.bitwise_and(link7_words, 0x1000000), 24) == 0b1)
            link0_words0 = np.right_shift(np.bitwise_and(link0_words[link0_words0_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link0_words1 = np.right_shift(np.bitwise_and(link0_words[link0_words1_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link1_words0 = np.right_shift(np.bitwise_and(link1_words[link1_words0_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link1_words1 = np.right_shift(np.bitwise_and(link1_words[link1_words1_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link2_words0 = np.right_shift(np.bitwise_and(link2_words[link2_words0_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link2_words1 = np.right_shift(np.bitwise_and(link2_words[link2_words1_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link3_words0 = np.right_shift(np.bitwise_and(link3_words[link3_words0_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link3_words1 = np.right_shift(np.bitwise_and(link3_words[link3_words1_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link4_words0 = np.right_shift(np.bitwise_and(link4_words[link4_words0_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link4_words1 = np.right_shift(np.bitwise_and(link4_words[link4_words1_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link5_words0 = np.right_shift(np.bitwise_and(link5_words[link5_words0_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link5_words1 = np.right_shift(np.bitwise_and(link5_words[link5_words1_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link6_words0 = np.right_shift(np.bitwise_and(link6_words[link6_words0_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link6_words1 = np.right_shift(np.bitwise_and(link6_words[link6_words1_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link7_words0 = np.right_shift(np.bitwise_and(link7_words[link7_words0_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link7_words1 = np.right_shift(np.bitwise_and(link7_words[link7_words1_filter], 0xffffff).view('>u4'), 8).astype(np.uint64)
            link0_hits = np.left_shift(link0_words0, 24) + link0_words1
            link1_hits = np.left_shift(link1_words0, 24) + link1_words1
            link2_hits = np.left_shift(link2_words0, 24) + link2_words1
            link3_hits = np.left_shift(link3_words0, 24) + link3_words1
            link4_hits = np.left_shift(link4_words0, 24) + link4_words1
            link5_hits = np.left_shift(link5_words0, 24) + link5_words1
            link6_hits = np.left_shift(link6_words0, 24) + link6_words1
            link7_hits = np.left_shift(link7_words0, 24) + link7_words1
            link0_hits_indices = link0_words_indices[link0_words0_filter]
            link1_hits_indices = link1_words_indices[link1_words0_filter]
            link2_hits_indices = link2_words_indices[link2_words0_filter]
            link3_hits_indices = link3_words_indices[link3_words0_filter]
            link4_hits_indices = link4_words_indices[link4_words0_filter]
            link5_hits_indices = link5_words_indices[link5_words0_filter]
            link6_hits_indices = link6_words_indices[link6_words0_filter]
            link7_hits_indices = link7_words_indices[link7_words0_filter]

            link0_hits_extensions_indices = np.searchsorted(full_timestamps_indices, link0_hits_indices)
            link1_hits_extensions_indices = np.searchsorted(full_timestamps_indices, link1_hits_indices)
            link2_hits_extensions_indices = np.searchsorted(full_timestamps_indices, link2_hits_indices)
            link3_hits_extensions_indices = np.searchsorted(full_timestamps_indices, link3_hits_indices)
            link4_hits_extensions_indices = np.searchsorted(full_timestamps_indices, link4_hits_indices)
            link5_hits_extensions_indices = np.searchsorted(full_timestamps_indices, link5_hits_indices)
            link6_hits_extensions_indices = np.searchsorted(full_timestamps_indices, link6_hits_indices)
            link7_hits_extensions_indices = np.searchsorted(full_timestamps_indices, link7_hits_indices)
            link0_hits_shutter_indices = np.searchsorted(full_shutter_timestamps_indices, link0_hits_indices)
            link1_hits_shutter_indices = np.searchsorted(full_shutter_timestamps_indices, link1_hits_indices)
            link2_hits_shutter_indices = np.searchsorted(full_shutter_timestamps_indices, link2_hits_indices)
            link3_hits_shutter_indices = np.searchsorted(full_shutter_timestamps_indices, link3_hits_indices)
            link4_hits_shutter_indices = np.searchsorted(full_shutter_timestamps_indices, link4_hits_indices)
            link5_hits_shutter_indices = np.searchsorted(full_shutter_timestamps_indices, link5_hits_indices)
            link6_hits_shutter_indices = np.searchsorted(full_shutter_timestamps_indices, link6_hits_indices)
            link7_hits_shutter_indices = np.searchsorted(full_shutter_timestamps_indices, link7_hits_indices)

            link0_hits_extensions_indices = np.maximum(link0_hits_extensions_indices - 1, 0)
            link1_hits_extensions_indices = np.maximum(link1_hits_extensions_indices - 1, 0)
            link2_hits_extensions_indices = np.maximum(link2_hits_extensions_indices - 1, 0)
            link3_hits_extensions_indices = np.maximum(link3_hits_extensions_indices - 1, 0)
            link4_hits_extensions_indices = np.maximum(link4_hits_extensions_indices - 1, 0)
            link5_hits_extensions_indices = np.maximum(link5_hits_extensions_indices - 1, 0)
            link6_hits_extensions_indices = np.maximum(link6_hits_extensions_indices - 1, 0)
            link7_hits_extensions_indices = np.maximum(link7_hits_extensions_indices - 1, 0)
            link0_hits_shutter_indices = np.maximum(link0_hits_shutter_indices - 1, 0)
            link1_hits_shutter_indices = np.maximum(link1_hits_shutter_indices - 1, 0)
            link2_hits_shutter_indices = np.maximum(link2_hits_shutter_indices - 1, 0)
            link3_hits_shutter_indices = np.maximum(link3_hits_shutter_indices - 1, 0)
            link4_hits_shutter_indices = np.maximum(link4_hits_shutter_indices - 1, 0)
            link5_hits_shutter_indices = np.maximum(link5_hits_shutter_indices - 1, 0)
            link6_hits_shutter_indices = np.maximum(link6_hits_shutter_indices - 1, 0)
            link7_hits_shutter_indices = np.maximum(link7_hits_shutter_indices - 1, 0)

            link0_hits_extensions = full_timestamps[link0_hits_extensions_indices]
            link1_hits_extensions = full_timestamps[link1_hits_extensions_indices]
            link2_hits_extensions = full_timestamps[link2_hits_extensions_indices]
            link3_hits_extensions = full_timestamps[link3_hits_extensions_indices]
            link4_hits_extensions = full_timestamps[link4_hits_extensions_indices]
            link5_hits_extensions = full_timestamps[link5_hits_extensions_indices]
            link6_hits_extensions = full_timestamps[link6_hits_extensions_indices]
            link7_hits_extensions = full_timestamps[link7_hits_extensions_indices]
            link0_hits_shutter = full_shutter_timestamps[link0_hits_shutter_indices]
            link1_hits_shutter = full_shutter_timestamps[link1_hits_shutter_indices]
            link2_hits_shutter = full_shutter_timestamps[link2_hits_shutter_indices]
            link3_hits_shutter = full_shutter_timestamps[link3_hits_shutter_indices]
            link4_hits_shutter = full_shutter_timestamps[link4_hits_shutter_indices]
            link5_hits_shutter = full_shutter_timestamps[link5_hits_shutter_indices]
            link6_hits_shutter = full_shutter_timestamps[link6_hits_shutter_indices]
            link7_hits_shutter = full_shutter_timestamps[link7_hits_shutter_indices]

            link0_extension_offsets = np.where(np.bitwise_and(link0_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link0_hits, 14), 0x3fff)], 0x3000))[0]
            link1_extension_offsets = np.where(np.bitwise_and(link1_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link1_hits, 14), 0x3fff)], 0x3000))[0]
            link2_extension_offsets = np.where(np.bitwise_and(link2_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link2_hits, 14), 0x3fff)], 0x3000))[0]
            link3_extension_offsets = np.where(np.bitwise_and(link3_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link3_hits, 14), 0x3fff)], 0x3000))[0]
            link4_extension_offsets = np.where(np.bitwise_and(link4_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link4_hits, 14), 0x3fff)], 0x3000))[0]
            link5_extension_offsets = np.where(np.bitwise_and(link5_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link5_hits, 14), 0x3fff)], 0x3000))[0]
            link6_extension_offsets = np.where(np.bitwise_and(link6_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link6_hits, 14), 0x3fff)], 0x3000))[0]
            link7_extension_offsets = np.where(np.bitwise_and(link7_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link7_hits, 14), 0x3fff)], 0x3000))[0]

            # Shift the extension index for hits that dont fulfill the condition by -1
            link0_hits_extensions[link0_extension_offsets] -= 1
            link1_hits_extensions[link1_extension_offsets] -= 1
            link2_hits_extensions[link2_extension_offsets] -= 1
            link3_hits_extensions[link3_extension_offsets] -= 1
            link4_hits_extensions[link4_extension_offsets] -= 1
            link5_hits_extensions[link5_extension_offsets] -= 1
            link6_hits_extensions[link6_extension_offsets] -= 1
            link7_hits_extensions[link7_extension_offsets] -= 1

            # Check again the overlap of the two bits after the correction
            link0_extension_offsets = np.where(np.bitwise_and(link0_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link0_hits, 14), 0x3fff)], 0x3000))[0]
            link1_extension_offsets = np.where(np.bitwise_and(link1_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link1_hits, 14), 0x3fff)], 0x3000))[0]
            link2_extension_offsets = np.where(np.bitwise_and(link2_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link2_hits, 14), 0x3fff)], 0x3000))[0]
            link3_extension_offsets = np.where(np.bitwise_and(link3_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link3_hits, 14), 0x3fff)], 0x3000))[0]
            link4_extension_offsets = np.where(np.bitwise_and(link4_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link4_hits, 14), 0x3fff)], 0x3000))[0]
            link5_extension_offsets = np.where(np.bitwise_and(link5_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link5_hits, 14), 0x3fff)], 0x3000))[0]
            link6_extension_offsets = np.where(np.bitwise_and(link6_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link6_hits, 14), 0x3fff)], 0x3000))[0]
            link7_extension_offsets = np.where(np.bitwise_and(link7_hits_extensions, 0x3000) != np.bitwise_and(_gray_14_lut[np.bitwise_and(np.right_shift(link7_hits, 14), 0x3fff)], 0x3000))[0]

            data = np.concatenate((link0_hits, link1_hits, link2_hits, link3_hits, link4_hits, link5_hits, link6_hits, link7_hits))
            data_indices = np.concatenate((link0_hits_indices, link1_hits_indices, link2_hits_indices, link3_hits_indices, link4_hits_indices, link5_hits_indices, link6_hits_indices, link7_hits_indices))

            data_sort = np.argsort(data_indices)
            data = data[data_sort]
            data_indices = data_indices[data_sort]

            extensions = np.concatenate((link0_hits_extensions, link1_hits_extensions, link2_hits_extensions, link3_hits_extensions, link4_hits_extensions, link5_hits_extensions, link6_hits_extensions, link7_hits_extensions))
            extensions = extensions[data_sort]

            shutter_timer = np.concatenate((link0_hits_shutter, link1_hits_shutter, link2_hits_shutter, link3_hits_shutter, link4_hits_shutter, link5_hits_shutter, link6_hits_shutter, link7_hits_shutter))
            shutter_timer = shutter_timer[data_sort]

            chunk_indices = np.searchsorted(start_indices, data_indices, side='right')
            chunk_indices = np.maximum(chunk_indices - 1, 0)

            data_scan_param_ids = scan_param_id[chunk_indices]
            data_chunk_start_time = chunk_start_time[chunk_indices]

            data_type = {'names': ['data_header', 'header', 'hit_index', 'x',     'y',     'TOA',    'TOT',    'EventCounter', 'HitCounter', 'FTOA',  'scan_param_id', 'chunk_start_time', 'iTOT',   'TOA_Extension', 'TOA_Combined', 'Shutter_Timer'],
            'formats': ['uint8',       'uint8',  'uint64', 'uint8', 'uint8', 'uint16', 'uint16', 'uint16',       'uint8',      'uint8', 'uint16',        'float',            'uint16', 'uint64',        'uint64',        'uint64']}
            pix_data = np.recarray((data.shape[0]), dtype=data_type)
            n47 = np.uint64(47)
            n44 = np.uint64(44)
            n28 = np.uint64(28)
            n14 = np.uint(14)
            n4 = np.uint64(4)
            n3ff = np.uint64(0x3ff)
            n3fff = np.uint64(0x3fff)
            nf = np.uint64(0xf)
            pixel = (data >> n28) & np.uint64(0b111)
            super_pixel = (data >> np.uint64(28 + 3)) & np.uint64(0x3f)
            right_col = pixel > 3
            eoc = (data >> np.uint64(28 + 9)) & np.uint64(0x7f)
            pix_data['y'] = (super_pixel * 4) + (pixel - right_col * 4)
            pix_data['x'] = eoc * 2 + right_col * 1

            # Put the headers into the recarray
            pix_data['data_header'] = data >> n47
            pix_data['header'] = data >> n44

            # Add chunk based information to the hits into the recarray
            pix_data['scan_param_id'] = data_scan_param_ids
            pix_data['chunk_start_time'] = data_chunk_start_time

            # Write the original indices of word 0 per hit into the recarray
            pix_data['hit_index'] = data_indices

            if(vco == False):
                pix_data['HitCounter'] = _lfsr_4_lut[data & nf]
                pix_data['FTOA'] = np.zeros(len(data))
            else:
                pix_data['HitCounter'] = np.zeros(len(data))
                pix_data['FTOA'] = data & nf

            pix_data['iTOT'] = np.zeros(len(data))
            pix_data['TOT'] = _lfsr_10_lut[(data >> n4) & n3ff]
            pix_data['TOA'] = _gray_14_lut[(data >> n14) & n3fff]
            pix_data['EventCounter'] = np.zeros(len(data))
            pix_data['TOA_Extension'] = extensions & 0xFFFFFFFFFFFF
            pix_data['Shutter_Timer'] = shutter_timer & 0xFFFFFFFFFFFC
            pix_data['TOA_Combined'] = (extensions & 0xFFFFFFFFC000) + pix_data['TOA']
            pix_data = pix_data[pix_data['data_header'] == 1]

            try:
                h5_file.remove_node(h5_file.root.interpreted, recursive=True)
            except:
                pass
            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')
            hit_data = pix_data[pix_data['data_header'] == 1]
            h5_file.create_table(h5_file.root.interpreted, 'hit_data', hit_data, filters=tb.Filters(complib='zlib', complevel=5))

            amplitudes = list(range(VTP_fine_start, VTP_fine_stop, 1))
            amplitudes.insert(0,0)
            means = np.zeros(len(amplitudes), dtype=float)
            deviations = np.zeros(len(amplitudes), dtype=float)
            tot_means = np.zeros(len(amplitudes), dtype=float)
            tot_deviations = np.zeros(len(amplitudes), dtype=float)

            # analyse timewalk for each amplitude step
            for current_id in np.unique(hit_data['scan_param_id']):
                current_data = hit_data[np.where(hit_data['scan_param_id'] == current_id)]
                ftoas, toas, full_toas, mean_full_toa, std_full_toa, tots, mean_tot, std_tot = analysis.toas(current_data, mask)
                name = 'ftoas_' + str(amplitudes[int(current_id)])
                h5_file.create_carray(h5_file.root.interpreted, name=name, obj=ftoas.T)
                name = 'toas_' + str(amplitudes[int(current_id)])
                h5_file.create_carray(h5_file.root.interpreted, name=name, obj=toas.T)
                name = 'full_toa_' + str(amplitudes[int(current_id)])
                h5_file.create_carray(h5_file.root.interpreted, name=name, obj=full_toas.T)
                name = 'tots_' + str(amplitudes[int(current_id)])
                h5_file.create_carray(h5_file.root.interpreted, name=name, obj=tots.T)
                means[current_id] = mean_full_toa
                deviations[current_id] = std_full_toa
                tot_means[current_id] = mean_tot
                tot_deviations[current_id] = std_tot

            data_type = {'names': ['mean', 'error'],
                        'formats': ['float32', 'float32']}
            timewalk = np.recarray(len(amplitudes), dtype=data_type)
            timewalk['mean'] = means
            timewalk['error'] = deviations
            h5_file.create_table(h5_file.root.interpreted, name='timewalk', obj=timewalk)

            tot = np.recarray(len(amplitudes), dtype=data_type)
            tot['mean'] = tot_means
            tot['error'] = tot_deviations
            h5_file.create_table(h5_file.root.interpreted, name='tot', obj=tot)

    def plot(self, status = None, plot_queue = None, **kwargs):
        '''
            Plot data and histograms of the scan
            If there is a status queue information about the status of the scan are put into it
        '''

        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting plotting...')
        if status != None:
            status.put("Create Plots")
        with tb.open_file(h5_filename, 'r+') as h5_file:

            with plotting.Plotting(h5_filename) as p:

                # Read needed configuration parameters
                VTP_fine_start = int(p.run_config[b'VTP_fine_start'])
                VTP_fine_stop = int(p.run_config[b'VTP_fine_stop'])
                VTP_coarse = int(p.dacs[b'VTP_coarse'])

                # Plot a page with all parameters
                p.plot_parameter_page()

                mask = h5_file.root.configuration.mask_matrix[:].T

                pix_data = h5_file.root.interpreted.hit_data[:]

                amplitudes = list(range(VTP_fine_start, VTP_fine_stop, 1))
                amplitudes.insert(0,0)

                # Plot optional 2D histograms for all amplitudes
                debug_plots = False
                if debug_plots:
                    for current_id in np.unique(pix_data['scan_param_id']):
                        ftoas_call = ('h5_file.root.interpreted.ftoas_' + str(amplitudes[int(current_id)]) + '[:]')
                        ftoas = eval(ftoas_call)
                        ftoas = np.ma.masked_array(ftoas, mask)
                        title = 'FToAs ' + str(amplitudes[int(current_id)])
                        suffix = 'ftoa_ ' + str(amplitudes[int(current_id)])
                        p.plot_occupancy(ftoas, title=title, z_min=0, z_max=15, z_label='fToA [cc]', suffix=suffix, plot_queue=plot_queue)

                    for current_id in np.unique(pix_data['scan_param_id']):
                        toas_call = ('h5_file.root.interpreted.toas_' + str(amplitudes[int(current_id)]) + '[:]')
                        toas = eval(toas_call)
                        toas = np.ma.masked_array(toas, mask)
                        title = 'ToAs ' + str(amplitudes[int(current_id)])
                        suffix = 'toa_ ' + str(amplitudes[int(current_id)])
                        p.plot_occupancy(toas, title=title, z_min=6350, z_max=6500, z_label='Delta ToA [ns]', suffix=suffix, plot_queue=plot_queue)

                    for current_id in np.unique(pix_data['scan_param_id']):
                        full_toa_call = ('h5_file.root.interpreted.full_toa_' + str(amplitudes[int(current_id)]) + '[:]')
                        full_toa = eval(full_toa_call)
                        full_toa = np.ma.masked_array(full_toa, mask)
                        title = 'Full ToA ' + str(amplitudes[int(current_id)])
                        suffix = 'full_toa_ ' + str(amplitudes[int(current_id)])
                        p.plot_occupancy(full_toa, title=title, z_min=6350, z_max=6500, z_label='ToA [ns]', suffix=suffix, plot_queue=plot_queue)

                    for current_id in np.unique(pix_data['scan_param_id']):
                        tot_call = ('h5_file.root.interpreted.tots_' + str(amplitudes[int(current_id)]) + '[:]')
                        tot = eval(tot_call)
                        tot = np.ma.masked_array(tot, mask)
                        title = 'ToT ' + str(amplitudes[int(current_id)])
                        suffix = 'tot_ ' + str(amplitudes[int(current_id)])
                        p.plot_occupancy(tot, title=title, z_min=0, z_max=150, z_label='ToT [CC]', suffix=suffix, plot_queue=plot_queue)

                timewalk = h5_file.root.interpreted.timewalk[:]
                tot = h5_file.root.interpreted.tot[:]

                amplitudes = list(range(VTP_fine_start, VTP_fine_stop, 1))
                amplitudes.insert(0,0)

                # Plot the calibration results
                p.plot_datapoints(x=amplitudes[1:], y=timewalk['mean'][1:] - timewalk['mean'][0], y_err=timewalk['error'][1:], x_plot_range=amplitudes[1:], y_plot_range=range(0, 125, 1), x_axis_title='VTP_fine', y_axis_title='Timewalk [ns]', title='Timewalk mean', suffix='timewalk_mean', fit='exp', plot_queue=plot_queue)
                p.plot_datapoints(x=amplitudes[1:], y=tot['mean'][1:], y_err=tot['error'][1:], x_plot_range=range(0, 500, 1), y_plot_range=range(0, 150, 1), x_axis_title='VTP_fine [2.5 mV]', y_axis_title='ToT [CC]', title='ToT mean', suffix='tot_mean', fit='tot', plot_queue=plot_queue, vtp_coarse=VTP_coarse)
                p.plot_datapoints(x=tot['mean'][1:], x_err=tot['error'][1:], y=timewalk['mean'][1:] - timewalk['mean'][0], y_err=timewalk['error'][1:], x_plot_range=range(0, 150, 1), y_plot_range=range(0, 125, 1), x_axis_title='ToT [CC]', y_axis_title='Timewalk [ns]', title='Timewalk calibration', suffix='timewalk_calibration', fit='exp', plot_queue=plot_queue)


if __name__ == "__main__":
    scan = TimewalkCalib(no_chip=False)
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
