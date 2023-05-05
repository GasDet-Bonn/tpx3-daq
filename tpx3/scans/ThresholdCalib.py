#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script scans over different thresholds for several testpulse heights
    to calibrate the threshold
'''

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from http.client import FORBIDDEN
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import math

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting
import tpx3.utils as utils
from six.moves import range

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'Vthreshold_start' : 1350,
    'Vthreshold_stop'  : 2911,
    'n_injections'     : 100,
    'n_pulse_heights'  : 5,
    'thrfile'         : './output_data/20201019_184320_mask.h5'
}


class ThresholdCalib(ScanBase):

    scan_id      = "ThresholdCalib"

    def scan(self, Vthreshold_start = 1350, Vthreshold_stop = 2911, n_injections = 100, tp_period = 1, mask_step = 16, n_pulse_heights = 5, progress = None, status = None, plot_queue = None, **kwargs):
        '''
            Threshold scan main loop
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
        if n_pulse_heights < 2 or n_pulse_heights > 100:
            raise ValueError("Value {} for n_pulse_heights s not in the allowed range (2-100)".format(n_pulse_heights))

        for iteration in range(n_pulse_heights):
            if status != None:
                status.put("Perform scan of pulse height number {} of {}".format(iteration + 1, n_pulse_heights))

            # Create argument list for the current iteration step
            args = {
                'mask_step'        : mask_step,
                'Vthreshold_start' : Vthreshold_start,
                'Vthreshold_stop'  : Vthreshold_stop,
                'n_injections'     : n_injections,
                'n_pulse_heights'  : n_pulse_heights,
                'tp_period'        : tp_period,
            }

            # In the 0th iteration all files and tables are already created by the start() function of scan_base
            # In further iterations this is not the case so its triggered by the following commands
            if iteration != 0:
                self.setup_files(iteration = iteration)
                self.dump_configuration(iteration = iteration, **args)

            # Start the scan for the current iteration
            self.scan_iteration(iteration, progress = progress, status = status, **args)

            # Analyse the data of the current iteration
            opt_results = self.analyze_iteration(iteration, progress = progress, status = status, chip_link = kwargs['chip_link'])

        # Create the plots for the full calibration
        self.plot(status = status, plot_queue = plot_queue)


    def scan_iteration(self, iteration, n_pulse_heights, Vthreshold_start=1500, Vthreshold_stop=2500, n_injections=100, tp_period = 1, mask_step=16, progress = None, status = None, **kwargs):
        '''
            Takes data for one iteration of the calibration. Therefore a threshold scan is performed for all pixel thresholds
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        # Get the shutter sleep time
        sleep_time = self.get_shutter_sleep_time(tp_period = tp_period, n_injections = n_injections)
        
        # Here are a couple redundancies, which are probably not neccessary for each iteration
        for chip in self.chips[1:]:
            # Set general configuration registers of the Timepix3
            self.chips[0].write(chip.write_general_config(write=False))

            # Write to the test pulse registers of the Timepix3
            # Write to period and phase tp registers
            self.chips[0].write(chip.write_tp_period(tp_period, 0, write=False))

            # Write to pulse number tp register
            self.chips[0].write(chip.write_tp_pulsenumber(n_injections, write=False))

        self.logger.info('Preparing injection masks...')
        if status != None:
            status.put("Preparing injection masks")

        # Create the masks for all steps
        mask_cmds = self.create_scan_masks(mask_step, progress = progress)

        # Start the scan
        self.logger.info('Threshold calibration iteration %i', iteration)
        self.logger.info('Starting scan...')
        if status != None:
            status.put("Starting scan")
        if status != None:
            status.put("iteration_symbol")
        thresholds = utils.create_threshold_list(utils.get_coarse_jumps(Vthreshold_start, Vthreshold_stop))

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds) * len(thresholds))
        else:
            # Initialize counter for progress
            step_counter = 0

        # Set testpulse DACs
        for chip in self.chips[1:]:
            self.chips[0].write(chip.set_dac("VTP_coarse", 100, write=False)) # redundant?
            self.chips[0].write(chip.set_dac("VTP_fine", 211 + (100 // n_pulse_heights) * iteration, write=False))

        scan_param_id = 0
        for threshold in thresholds:
            for chip in self.chips[1:]:
                # Set the threshold
                self.chips[0].write(chip.set_dac("Vthreshold_coarse", int(threshold[0]), write=False))
                self.chips[0].write(chip.set_dac("Vthreshold_fine", int(threshold[1]), write=False))

            with self.readout(scan_param_id=scan_param_id):
                step = 0
                for mask_step_cmd in mask_cmds:
                    for chip in self.chips[1:]:
                        # Only activate testpulses for columns with active pixels
                        self.chips[0].write(chip.write_ctpr(list(range(step//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))), write=False))

                    # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
                    self.chips[0].write(mask_step_cmd)

                    # Open the shutter, take data and update the progress bar
                    with self.shutter():
                        time.sleep(sleep_time)
                        if progress == None:
                            # Update the progress bar
                            pbar.update(1)
                        else:
                            # Update the progress fraction and put it in the queue
                            step_counter += 1
                            fraction = step_counter / (len(mask_cmds) * len(thresholds))
                            progress.put(fraction)
                    for chip in self.chips[1:]:
                        self.chips[0].write(chip.stop_readout(write=False))
                        time.sleep(0.001)
                    step += 1
                for chip in self.chips[1:]:
                    self.chips[0].write(chip.reset_sequential(write=False))
                    time.sleep(0.001)
            scan_param_id += 1

        if progress == None:
            # Close the progress bar
            pbar.close()

        if status != None:
            status.put("iteration_finish_symbol")

        self.logger.info('Iteration %i finished', iteration)

    def analyze_iteration(self, iteration, chip_link, progress = None, status = None):
        '''
            Analyze the data of the iteration
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting data analysis...')
        if status != None:
            status.put("Performing data analysis")

        # Open the HDF5 which contains all data of the scan
        with tb.open_file(h5_filename, 'r+') as h5_file:

            # Read raw data, meta data and configuration parameters for the current iteration
            raw_data        = eval(f'h5_file.root.raw_data_{iteration}[:]')
            meta_data       = eval(f'h5_file.root.meta_data_{iteration}[:]')
            run_config      = eval(f'h5_file.root.configuration.run_config_{iteration}')
            general_config  = h5_file.root.configuration.generalConfig
            op_mode         = general_config.col('Op_mode')[0]
            vco             = general_config.col('Fast_Io_en')[0]

            # Create group to save all data and histograms to the HDF file
            h5_file.create_group(h5_file.root, f'interpreted_{iteration}', 'Interpreted Data')

            self.logger.info('Interpret raw data...')
            # Interpret the raw data (2x 32 bit to 1x 48 bit)
            hit_data = analysis.interpret_raw_data(raw_data, op_mode, vco, kwargs['chip_link'], meta_data, progress = progress)
            raw_data = None

            for chip in self.chips[1:]:
                # Get the index of current chip in regards to the chip_links dictionary. This is the index, where
                # the hit_data of the chip is.
                chip_num = [number for number, ID in enumerate(kwargs['chip_link']) if ID==chip.chipId_decoded][0]
                # Get chipID in desirable formatting for HDF5 files (without '-')
                chipID = f'W{chip.wafer_number}_{chip.x_position}{chip.y_position}'

                # create group for current chip
                create_group_call = f'h5_file.root.interpreted_{iteration}'
                h5_file.create_group(eval(create_group_call), name = chipID)

                # get group for current chip
                chip_group_call = create_group_call + '._f_get_child(chipID)'
                chip_group      = eval(chip_group_call)

                # Select only data which is hit data
                hit_data_chip = hit_data[chip_num][hit_data[chip_num]['data_header'] == 1]
                h5_file.create_table(chip_group, 'hit_data', hit_data_chip, filters=tb.Filters(complib='zlib', complevel=5))
                pix_occ       = np.bincount(hit_data_chip['x'] * 256 + hit_data_chip['y'], minlength=256 * 256).astype(np.uint32)
                hist_occ      = np.reshape(pix_occ, (256, 256)).T
                h5_file.create_carray(chip_group, name='HistOcc', obj=hist_occ)
                param_range   = np.unique(meta_data['scan_param_id'])
                
                pix_occ       = None
                hist_occ      = None

                # Create histograms for number of detected hits for individual thresholds
                scurve   = analysis.scurve_hist(hit_data_chip, param_range)
                hit_data_chip = None

                # Read needed configuration parameters
                n_injections     = run_config.col('n_injections')[0]
                Vthreshold_start = run_config.col('Vthreshold_start')[0]
                Vthreshold_stop  = run_config.col('Vthreshold_stop')[0]

                # Fit S-Curves to the histograms for all pixels
                param_range             = list(range(Vthreshold_start, Vthreshold_stop + 1))
                thr2D, sig2D, chi2ndf2D = analysis.fit_scurves_multithread(scurve, scan_param_range=param_range, n_injections=n_injections, invert_x=chip.configs['Polarity'], progress = progress)

                h5_file.create_carray(chip_group, name='HistSCurve', obj=scurve)
                h5_file.create_carray(chip_group, name='Chi2Map', obj=chi2ndf2D.T)
                h5_file.create_carray(chip_group, name='ThresholdMap', obj=thr2D.T)
                h5_file.create_carray(chip_group, name='NoiseMap', obj=sig2D.T)

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
            with plotting.Plotting(h5_filename, iteration = 0) as p:

                # Read needed configuration parameters
                iterations       = p.run_config['n_pulse_heights'][0]
                Vthreshold_start = p.run_config['Vthreshold_start'][0]
                Vthreshold_stop  = p.run_config['Vthreshold_stop'][0]
                n_injections     = p.run_config['n_injections'][0]

                # Plot a page with all parameters
                p.plot_parameter_page()

                # remove the calibration node if it already exists
                try:
                    h5_file.remove_node(h5_file.root.calibration, recursive=True)
                except:
                    pass

                # create a group for the calibration results
                h5_file.create_group(h5_file.root, 'calibration', 'Threshold calibration results')

                for chip in self.chips[1:]:
                    # get chipID of current chip
                    chipID = f'W{chip.wafer_number}_{chip.x_position}{chip.y_position}'

                    # Plot the equalisation bits histograms
                    thr_matrix = eval(f'h5_file.root.configuration.thr_matrix_{chipID}[:]')
                    p.plot_distribution(thr_matrix, chip.chipId_decoded, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution', x_axis_title='Pixel threshold', y_axis_title='# of pixels', suffix='pixel_threshold_distribution', plot_queue=plot_queue)

                    # create a table for the calibration results
                    data_type = {'names': ['pulse_height', 'threshold', 'threshold_error'],
                                'formats': ['double', 'double', 'double']}
                    calib_results = np.recarray(iterations, dtype=data_type)

                    # create arrays for the calibration data points
                    pulse_heights = np.zeros(iterations, dtype=float)
                    thresholds    = np.zeros(iterations, dtype=float)
                    errors        = np.zeros(iterations, dtype=float)

                    # Get pixel mask
                    mask = eval(f'h5_file.root.configuration.mask_matrix_{chipID}[:].T')

                    # iterate though the iteration to plot the iteration specific results
                    for iteration in range(iterations):
                        
                        # Get the chip group of the HDF5 file
                        chip_group      = eval(f'h5_file.root.interpreted_{iteration}._f_get_child(chipID)')

                        # Plot the S-Curve histogram
                        scurve_hist = chip_group.HistSCurve[:].T
                        max_occ     = n_injections * 5
                        p.plot_scurves(scurve_hist, chip.chipId_decoded, list(range(Vthreshold_start, Vthreshold_stop+1)), iteration=iteration, scan_parameter_name="Vthreshold", max_occ=max_occ, plot_queue=plot_queue)

                        # Do not plot pixels with converged  S-Curve fits
                        chi2_sel        = chip_group.Chi2Map[:] > 0. # Mask not converged fits (chi2 = 0)
                        mask[~chi2_sel] = True

                        # Plot the threshold distribution based on the S-Curve fits
                        hist                     = np.ma.masked_array(chip_group.ThresholdMap[:], mask)
                        it_parameters, it_errors = p.plot_distribution(hist, chip.chipId_decoded, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop+0.5, 1), y_axis_title='# of pixels', x_axis_title='Vthreshold', title='Threshold distribution, it %d' %iteration, suffix='threshold_distribution', plot_queue=plot_queue)

                        # Fill the iteration results in the calibration parameter arrays
                        pulse_heights[iteration] = ((211 + (100 // iterations) * iteration) - 200) * 46.75
                        thresholds[iteration]    = it_parameters[1]
                        errors[iteration]        = it_parameters[2]

                    # Fill the table with the calibration results
                    calib_results['pulse_height']    = pulse_heights
                    calib_results['threshold']       = thresholds
                    calib_results['threshold_error'] = errors

                    # Save the table to the HDF5 file
                    h5_file.create_table(h5_file.root.calibration, chipID, calib_results)

                    # Create the calibration plot
                    p.plot_datapoints(pulse_heights, thresholds, chip.chipId_decoded, x_plot_range=np.arange(0, 7500, 1), y_plot_range=np.arange(0, 3000, 1), y_err = errors, x_axis_title = 'Charge in electrons', y_axis_title = 'Threshold', title='Threshold calibration', suffix='threshold_calibration', plot_queue=plot_queue)

if __name__ == "__main__":
    scan = ThresholdCalib()
    scan.start(iteration = 0, **local_configuration)
    scan.plot()
