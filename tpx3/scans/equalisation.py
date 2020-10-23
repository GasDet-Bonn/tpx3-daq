#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs an equalisation of pixels based on a threshold scan
    with noise.
'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import os
import math

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

from tables.exceptions import NoSuchNodeError
from six.moves import range

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'Vthreshold_start' : 1000,
    'Vthreshold_stop'  : 1350
}


class Equalisation(ScanBase):

    scan_id = "Equalisation"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self, Vthreshold_start = 1000, Vthreshold_stop = 1350, mask_step = 16, **kwargs):
        '''
            Takes data for equalisation. Therefore a threshold scan is performed for all pixel thresholds at 0 and at 15.
        '''

        # Check if parameters are valid before starting the scan
        if Vthreshold_start < 0 or Vthreshold_start > 2911:
            raise ValueError("Value {} for Vthreshold_start is not in the allowed range (0-2911)".format(Vthreshold_start))
        if Vthreshold_stop < 0 or Vthreshold_stop > 2911:
            raise ValueError("Value {} for Vthreshold_stop is not in the allowed range (0-2911)".format(Vthreshold_stop))
        if Vthreshold_stop <= Vthreshold_start:
            raise ValueError("Value for Vthreshold_stop must be bigger than value for Vthreshold_start")
        if mask_step not in {4, 16, 64, 256}:
            raise ValueError("Value {} for mask_step is not in the allowed range (4, 16, 64, 256)".format(mask_step))

        # Set general configuration registers of the Timepix3 
        self.chip.write_general_config()

        # Write to the test pulse registers of the Timepix3
        # Write to period and phase tp registers
        # This is needed here to open the internal Timepix3 shutter
        data = self.chip.write_tp_period(1, 0)

        self.logger.info('Preparing injection masks...')

        # Empty arrays for the masks command for the scan at 0 and at 15
        mask_cmds = []
        mask_cmds2 = []

        # Initialize progress bar
        pbar = tqdm(total=mask_step)

        # Create the masks for all steps and for both threshold scans
        for j in range(mask_step):
            mask_step_cmd = []
            mask_step_cmd2 = []

            # Start with deactivated testpulses on all pixels and all pixels masked
            self.chip.test_matrix[:, :] = self.chip.TP_OFF
            self.chip.mask_matrix[:, :] = self.chip.MASK_OFF
            
            # Switch on pixels based on mask_step
            # e.g. for mask_step=16 every 4th pixel in x and y is active
            self.chip.mask_matrix[(j//(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step))),
                                  (j%(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step)))] = self.chip.MASK_ON

            # Create the list of mask commands for the scan at pixel threshold = 0
            self.chip.thr_matrix[:, :] = 0
            for i in range(256 // 4):
                mask_step_cmd.append(self.chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))

            # Create the list of mask commands for the scan at pixel threshold = 15
            self.chip.thr_matrix[:, :] = 15
            for i in range(256 // 4):
                mask_step_cmd2.append(self.chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))

            # Append the command for initializing a data driven readout
            mask_step_cmd.append(self.chip.read_pixel_matrix_datadriven())
            mask_step_cmd2.append(self.chip.read_pixel_matrix_datadriven())

            # Append the list of command for the current mask_step to the full command list
            mask_cmds.append(mask_step_cmd)
            mask_cmds2.append(mask_step_cmd2)

            # Update the progress bar
            pbar.update(1)

        # Close the progress bar
        pbar.close()

        # Scan with pixel threshold 0
        self.logger.info('Starting scan for THR = 0...')
        cal_high_range = list(range(Vthreshold_start, Vthreshold_stop, 1))

        # Initialize progress bar
        pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            # Calculate the value for the fine and the coarse threshold DACs
            if(vcal <= 511):
                coarse_threshold = 0
                fine_threshold = vcal
            else:
                relative_fine_threshold = (vcal - 512) % 160
                coarse_threshold = (((vcal - 512) - relative_fine_threshold) // 160) + 1
                fine_threshold = relative_fine_threshold + 352

            # Set the threshold DACs
            self.chip.set_dac("Vthreshold_coarse", coarse_threshold)
            self.chip.set_dac("Vthreshold_fine", fine_threshold)
            time.sleep(0.001)

            with self.readout(scan_param_id=scan_param_id):
                for mask_step_cmd in mask_cmds:
                    # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
                    self.chip.write(mask_step_cmd)

                    # Open the shutter, take data and update the progress bar
                    with self.shutter():
                        time.sleep(0.01)
                        pbar.update(1)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)

        # Close the progress bar
        pbar.close()

        # Scan with pixel threshold 15
        self.logger.info('Starting scan for THR = 15...')

        # Initialize progress bar
        pbar = tqdm(total=len(mask_cmds2) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            # Calculate the value for the fine and the coarse threshold DACs
            if(vcal <= 511):
                coarse_threshold = 0
                fine_threshold = vcal
            else:
                relative_fine_threshold = (vcal - 512) % 160
                coarse_threshold = (((vcal - 512) - relative_fine_threshold) // 160) + 1
                fine_threshold = relative_fine_threshold + 352
            
            # Set the threshold DACs
            self.chip.set_dac("Vthreshold_coarse", coarse_threshold)
            self.chip.set_dac("Vthreshold_fine", fine_threshold)
            time.sleep(0.001)

            with self.readout(scan_param_id=scan_param_id + len(cal_high_range)):
                for mask_step_cmd in mask_cmds2:
                    # Only activate testpulses for columns with active pixels
                    self.chip.write(mask_step_cmd)

                    # Open the shutter, take data and update the progress bar
                    with self.shutter():
                        time.sleep(0.01)
                        pbar.update(1)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)

        # Close the progress bar
        pbar.close()

        self.logger.info('Scan finished')

    def analyze(self):
        '''
            Analyze the data of the equalisation and calculate the equalisation matrix
        '''
        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting data analysis...')

        # Open the HDF5 which contains all data of the equalisation
        with tb.open_file(h5_filename, 'r+') as h5_file:
            # Read raw data, meta data and configuration parameters
            raw_data = h5_file.root.raw_data[:]
            meta_data = h5_file.root.meta_data[:]
            run_config = h5_file.root.configuration.run_config[:]

            self.logger.info('Interpret raw data...')

            # Read needed configuration parameters
            hit_data = analysis.interpret_raw_data(raw_data, meta_data)
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
            Vthreshold_stop = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]
            chip_wafer = [int(item[1]) for item in run_config if item[0] == b'chip_wafer'][0]
            chip_x = [int(item[1]) for item in run_config if item[0] == b'chip_x'][0]
            chip_y = [int(item[1]) for item in run_config if item[0] == b'chip_y'][0]

            # Select only data which is hit data
            hit_data = hit_data[hit_data['data_header'] == 1]

            # Divide the data into two parts - data for pixel threshold 0 and 15
            param_range = np.unique(meta_data['scan_param_id'])
            hit_data_th0 = hit_data[hit_data['scan_param_id'] < len(param_range) // 2]
            param_range_th0 = np.unique(hit_data_th0['scan_param_id'])
            hit_data_th15 = hit_data[hit_data['scan_param_id'] >= len(param_range) // 2]
            param_range_th15 = np.unique(hit_data_th15['scan_param_id'])
            
            # Create histograms for number of detected hits for individual thresholds
            self.logger.info('Get the global threshold distributions for all pixels...')
            scurve_th0 = analysis.scurve_hist(hit_data_th0, param_range_th0)
            scurve_th15 = analysis.scurve_hist(hit_data_th15, param_range_th15)

            # Calculate the mean of the threshold distributions for all pixels
            self.logger.info('Calculate the mean of the global threshold distributions for all pixels...')
            vths_th0 = analysis.vths(scurve_th0, param_range_th0, Vthreshold_start)
            vths_th15 = analysis.vths(scurve_th15, param_range_th15, Vthreshold_start)

            # Get the treshold distributions for both scan
            self.logger.info('Get the cumulated global threshold distributions...')
            hist_th0 = analysis.vth_hist(vths_th0, Vthreshold_stop)
            hist_th15 = analysis.vth_hist(vths_th15, Vthreshold_stop)

            # Use the threshold histogramms and one threshold distribution to calculate the equalisation
            self.logger.info('Calculate the equalisation matrix...')
            eq_matrix = analysis.eq_matrix(hist_th0, hist_th15, vths_th0, Vthreshold_start, Vthreshold_stop)

            # Don't mask any pixels in the mask file
            mask_matrix = np.zeros((256, 256), dtype=np.bool)
            mask_matrix[:, :] = 0

            # Write the equalisation matrix and the mask matrix to a new HDF5 file
            self.logger.info('Writing mask_matrix to file...')
            output_path = os.path.join(self.working_dir, 'hdf')
            maskfile = os.path.join(output_path, 'equal_W' + chip_wafer + '-' + chip_x + chip_y + '_' + self.timestamp + 'h5')

            with tb.open_file(maskfile, 'a') as out_file:
                try:
                    out_file.remove_node(out_file.root.mask_matrix)
                except NoSuchNodeError:
                    self.logger.debug('Specified maskfile does not include a mask_matrix yet!')

                out_file.create_carray(out_file.root,
                                    name='mask_matrix',
                                    title='Matrix mask',
                                    obj=mask_matrix)
                self.logger.info('Closing mask file: %s' % (maskfile))

            self.logger.info('Writing equalisation matrix to file...')
            with tb.open_file(maskfile, 'a') as out_file:
                try:
                    out_file.remove_node(out_file.root.thr_matrix)
                except NoSuchNodeError:
                    self.logger.debug('Specified maskfile does not include a thr_mask yet!')

                out_file.create_carray(out_file.root,
                                        name='thr_matrix',
                                        title='Matrix Threshold',
                                        obj=eq_matrix)
                self.logger.info('Closing equalisation matrix file: %s' % (maskfile))


if __name__ == "__main__":
    scan = Equalisation()
    scan.start(**local_configuration)
    scan.analyze()