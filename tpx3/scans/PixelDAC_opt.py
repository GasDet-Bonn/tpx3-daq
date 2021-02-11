#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs optimized the Ibias_PixelDAC via linear regression
    based on several threshold scans.
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
import yaml

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

from tables.exceptions import NoSuchNodeError
from io import open
from six.moves import range

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'Vthreshold_start' : 1600,
    'Vthreshold_stop'  : 2300,
    'n_injections'     : 100
}


class PixelDAC_opt(ScanBase):

    scan_id = "PixelDAC_opt"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self, Vthreshold_start = 1500, Vthreshold_stop = 2500, n_injections = 100, tp_period = 1, mask_step = 16, progress = None, status = None, result = None, **kwargs):
        '''
            Main function of the pixel dac optimization. Starts the scan iterations and the analysis of
            of the individual iterations.
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        # Check if parameters are valid before starting the scan
        if Vthreshold_start < 0 or Vthreshold_start > 2911:
            raise ValueError("Value {} for Vthreshold_start is not in the allowed range (0-2911)".format(Vthreshold_start))
        if Vthreshold_stop < 0 or Vthreshold_stop > 2911:
            raise ValueError("Value {} for Vthreshold_stop is not in the allowed range (0-2911)".format(Vthreshold_stop))
        if Vthreshold_stop <= Vthreshold_start:
            raise ValueError("Value for Vthreshold_stop must be bigger than value for Vthreshold_start")
        if n_injections < 1 or n_injections > 65535:
            raise ValueError("Value {} for n_injections is not in the allowed range (1-65535)".format(n_injections))
        if mask_step not in {4, 16, 64, 256}:
            raise ValueError("Value {} for mask_step is not in the allowed range (4, 16, 64, 256)".format(mask_step))

        # Start parameters for the optimization
        last_delta = 1
        last_rms_delta = 22
        pixeldac = 127
        last_pixeldac = pixeldac
        iteration = 0

        # Repeat until optimization is done
        while last_delta < last_rms_delta - 2 or last_delta > last_rms_delta + 2:
            if status != None:
                status.put("Linear regression step number {} with pixeldac {}".format(iteration + 1, int(pixeldac)))

            # Create argument list for the current iteration step
            args = {
                'pixeldac'         : int(pixeldac),
                'last_pixeldac'    : int(last_pixeldac),
                'last_delta'       : float(last_delta),
                'mask_step'        : mask_step,
                'Vthreshold_start' : Vthreshold_start,
                'Vthreshold_stop'  : Vthreshold_stop,
                'n_injections'     : n_injections,
                'tp_period'        : tp_period
            }

            # In the 0th iteration all files and tables are already created by the start() function of scan_base
            # In further iterations this is not the case so its triggered by the following commands
            if iteration != 0:
                self.setup_files(iteration = iteration)
                self.dump_configuration(iteration = iteration, **args)

            # Start the scan for the current iteration
            self.scan_iteration(progress = progress, status = status, **args)

            # Analyse the data of the current iteration
            opt_results = self.analyze_iteration(iteration, progress = progress, status = status)
            last_pixeldac = pixeldac

            # Store results of iteration
            pixeldac = opt_results[0]
            last_delta = opt_results[1]
            last_rms_delta = opt_results[2]

            iteration += 1

        if result == None:
            # Write new pixeldac into DAC YAML file
            with open('../dacs.yml') as f:
                doc = yaml.load(f, Loader=yaml.FullLoader)

            for register in doc['registers']:
                if register['name'] == 'Ibias_PixelDAC':
                    register['value'] = int(pixeldac)

            with open('../dacs.yml', 'w') as f:
                yaml.dump(doc, f)
        else:
            result.put(int(pixeldac))

    def scan_iteration(self, pixeldac = 127, last_pixeldac = 127, last_delta = 127, Vthreshold_start=1500, Vthreshold_stop=2500, n_injections=100, tp_period = 1, mask_step=16, progress = None, status = None, **kwargs):
        '''
            Takes data for one iteration of the optimization. Therefore a threshold scan is performed for all pixel thresholds at 0 and at 15.
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        # Set general configuration registers of the Timepix3 
        self.chip.write_general_config()

        # Write to the test pulse registers of the Timepix3
        # Write to period and phase tp register
        data = self.chip.write_tp_period(tp_period, 0)

        # Write to pulse number tp register
        self.chip.write_tp_pulsenumber(n_injections)

        # Set the pixeldac to the current iteration value
        self.chip.set_dac("Ibias_PixelDAC", pixeldac)

        self.logger.info('Scan with Pixeldac %i', pixeldac)
        self.logger.info('Preparing injection masks...')
        if status != None:
            status.put("Preparing injection masks")

        # Create the masks for all steps for the scan at 0 and at 15
        mask_cmds = self.create_scan_masks(mask_step, pixel_threhsold = 0, progress = progress)
        mask_cmds2 = self.create_scan_masks(mask_step, pixel_threhsold = 15, progress = progress)

        # Scan with all masks over the given threshold range for pixelthreshold 0
        cal_high_range = list(range(Vthreshold_start, Vthreshold_stop, 1))
        self.logger.info('Starting scan for THR = 0...')
        if status != None:
            status.put("Starting scan")
        if status != None:
            status.put("iteration_symbol")

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))
        else:
            # Initailize counter for progress
            step_counter = 0

        for scan_param_id, vcal in enumerate(cal_high_range):
            # Set the threshold
            self.chip.set_threshold(vcal)

            with self.readout(scan_param_id=scan_param_id):
                if status != None:
                    status.put("Scan iteration {} of {} for THR = 0".format(scan_param_id + 1, len(cal_high_range)))
                for i, mask_step_cmd in enumerate(mask_cmds):
                    # Only activate testpulses for columns with active pixels
                    self.chip.write_ctpr(list(range(i//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))))

                    # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
                    self.chip.write(mask_step_cmd)

                    # Open the shutter, take data and update the progress bar
                    with self.shutter():
                        time.sleep(0.01)
                        if progress == None:
                            # Update the progress bar
                            pbar.update(1)
                        else:
                            # Update the progress fraction and put it in the queue
                            step_counter += 1
                            fraction = step_counter / (len(mask_cmds) * len(cal_high_range))
                            progress.put(fraction)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)

        if progress == None:
            # Close the progress bar
            pbar.close()

        # Scan with all masks over the given threshold range for pixelthreshold 15
        self.logger.info('Starting scan for THR = 15...')

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds2) * len(cal_high_range))
        else:
            # Initailize counter for progress
            step_counter = 0

        for scan_param_id, vcal in enumerate(cal_high_range):
            # Set the threshold
            self.chip.set_threshold(vcal)

            with self.readout(scan_param_id=scan_param_id + len(cal_high_range)):
                if status != None:
                    status.put("Scan iteration {} of {} for THR = 15".format(scan_param_id + 1, len(cal_high_range)))
                for i, mask_step_cmd in enumerate(mask_cmds2):
                    # Only activate testpulses for columns with active pixels
                    self.chip.write_ctpr(list(range(i//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))))

                    # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
                    self.chip.write(mask_step_cmd)

                    # Open the shutter, take data and update the progress bar
                    with self.shutter():
                        time.sleep(0.01)
                        if progress == None:
                            # Update the progress bar
                            pbar.update(1)
                        else:
                            # Update the progress fraction and put it in the queue
                            step_counter += 1
                            fraction = step_counter / (len(mask_cmds2) * len(cal_high_range))
                            progress.put(fraction)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)

        if progress == None:
            # Close the progress bar
            pbar.close()

        if status != None:
            status.put("iteration_finish_symbol")

        self.logger.info('Scan finished')

    def analyze_iteration(self, iteration = 0, progress = None, status = None):
        '''
            Analyze the data of the iteration and calculate the new Ibias_PixelDAC value.
            In the last iteration the data is also used to calculate an equalisation matrix.
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting data analysis...')
        if status != None:
            status.put("Performing data analysis")

        # Open the HDF5 which contains all data of the optimization iteration
        with tb.open_file(h5_filename, 'r+') as h5_file:
            # Read raw data, meta data and configuration parameters for the current iteration
            meta_data_call = ('h5_file.root.' + 'meta_data_' + str(iteration) + '[:]')
            meta_data = eval(meta_data_call)
            run_config_call = ('h5_file.root.' + 'configuration.run_config_' + str(iteration) + '[:]')
            run_config = eval(run_config_call)
            general_config_call = ('h5_file.root.' + 'configuration.generalConfig_' + str(iteration) + '[:]')
            general_config = eval(general_config_call)
            op_mode = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            vco = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

            self.logger.info('Interpret raw data...')

            # THR = 0
            param_range, index = np.unique(meta_data['scan_param_id'], return_index=True)
            meta_data_th0 = meta_data[meta_data['scan_param_id'] < len(param_range) // 2]
            param_range_th0 = np.unique(meta_data_th0['scan_param_id'])
            
            # THR = 15
            meta_data_th15 = meta_data[meta_data['scan_param_id'] >= len(param_range) // 2]
            param_range_th15 = np.unique(meta_data_th15['scan_param_id'])

            # shift indices so that they start with zero
            start = meta_data_th15['index_start'][0]
            meta_data_th15['index_start'] = meta_data_th15['index_start']-start
            meta_data_th15['index_stop'] = meta_data_th15['index_stop']-start

            self.logger.info('THR = 0')
            #THR = 0
            raw_data_call = ('h5_file.root.' + 'raw_data_' + str(iteration) + '[:' + meta_data_th0['index_stop'][-1] + ']')
            raw_data_thr0 = eval(raw_data_call)
            hit_data_thr0 = analysis.interpret_raw_data(raw_data_thr0, op_mode, vco, meta_data_th0, progress = progress)
            raw_data_thr0 = None

            self.logger.info('THR = 15')
            #THR = 15
            raw_data_call = ('h5_file.root.' + 'raw_data_' + str(iteration) + '[' + meta_data_th0['index_stop'][-1] + ':]')
            raw_data_thr15 = eval(raw_data_call)
            hit_data_thr15 = analysis.interpret_raw_data(raw_data_thr15, op_mode, vco, meta_data_th15, progress = progress)
            raw_data_thr15 = None

        # Read needed configuration parameters
        Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
        Vthreshold_stop = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]
        n_injections = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]
        pixeldac = [int(item[1]) for item in run_config if item[0] == b'pixeldac'][0]
        last_pixeldac = [int(item[1]) for item in run_config if item[0] == b'last_pixeldac'][0]
        last_delta = [float(item[1]) for item in run_config if item[0] == b'last_delta'][0]
        chip_wafer = [int(item[1]) for item in run_config if item[0] == b'chip_wafer'][0]
        chip_x = [item[1].decode() for item in run_config if item[0] == b'chip_x'][0]
        chip_y = [int(item[1]) for item in run_config if item[0] == b'chip_y'][0]

        # Select only data which is hit data
        hit_data_thr0 = hit_data_thr0[hit_data_thr0['data_header'] == 1]
        hit_data_thr15 = hit_data_thr15[hit_data_thr15['data_header'] == 1]

        # Divide the data into two parts - data for pixel threshold 0 and 15
        param_range = np.unique(meta_data['scan_param_id'])
        meta_data = None
        param_range_th0 = np.unique(hit_data_thr0['scan_param_id'])
        param_range_th15 = np.unique(hit_data_thr15['scan_param_id'])
        
        # Create histograms for number of detected hits for individual thresholds
        self.logger.info('Get the global threshold distributions for all pixels...')
        scurve_th0 = analysis.scurve_hist(hit_data_thr0, np.arange(len(param_range) // 2))
        hit_data_thr0 = None
        scurve_th15 = analysis.scurve_hist(hit_data_thr15, np.arange(len(param_range) // 2, len(param_range)))
        hit_data_thr15 = None

        # Fit S-Curves to the histogramms for all pixels
        self.logger.info('Fit the scurves for all pixels...')
        thr2D_th0, sig2D_th0, chi2ndf2D_th0 = analysis.fit_scurves_multithread(scurve_th0, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop)), n_injections=n_injections, invert_x=True, progress = progress)
        scurve_th0 = None
        thr2D_th15, sig2D_th15, chi2ndf2D_th15 = analysis.fit_scurves_multithread(scurve_th15, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop)), n_injections=n_injections, invert_x=True, progress = progress)
        scurve_th15 = None

        # Put the threshold distribution based on the fit results in two histogramms
        self.logger.info('Get the cumulated global threshold distributions...')
        hist_th0 = analysis.vth_hist(thr2D_th0, Vthreshold_stop)
        hist_th15 = analysis.vth_hist(thr2D_th15, Vthreshold_stop)

        # Use the threshold histogramms to calculate the new Ibias_PixelDAC setting
        self.logger.info('Calculate new pixelDAC value...')
        pixeldac_result = analysis.pixeldac_opt(hist_th0, hist_th15, pixeldac, last_pixeldac, last_delta, Vthreshold_start, Vthreshold_stop)
        delta = pixeldac_result[1]
        rms_delta = pixeldac_result[2]

        # In the last iteration calculate also the equalisation matrix
        if delta > rms_delta - 2 and delta < rms_delta + 2:
            # Use the threshold histogramms and one threshold distribution to calculate the equalisation
            self.logger.info('Calculate the equalisation matrix...')
            eq_matrix = analysis.eq_matrix(hist_th0, hist_th15, thr2D_th0, Vthreshold_start, Vthreshold_stop)

            # Don't mask any pixels in the mask file
            mask_matrix = np.zeros((256, 256), dtype=np.bool)
            mask_matrix[:, :] = 0

            # Write the equalisation matrix to a new HDF5 file
            self.save_thr_mask(eq_matrix, chip_wafer, chip_x ,chip_y)

        self.logger.info('Result of iteration: Scan with pixeldac %i - New pixeldac %i. Delta was %f with optimal delta %f' % (int(pixeldac), int(pixeldac_result[0]), pixeldac_result[1], pixeldac_result[2]))
        return pixeldac_result


if __name__ == "__main__":
    scan = PixelDAC_opt()
    scan.start(iteration = 0, **local_configuration)