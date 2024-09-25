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

    scan_id = "ThresholdCalib"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

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
            opt_results = self.analyze_iteration(iteration, progress = progress, status = status)

        # Create the plots for the full calibration
        self.plot(status = status, plot_queue = plot_queue)


    def scan_iteration(self, iteration, n_pulse_heights, Vthreshold_start=1500, Vthreshold_stop=2500, n_injections=100, tp_period = 1, mask_step=16, progress = None, status = None, **kwargs):
        '''
            Takes data for one iteration of the calibration. Therefore a threshold scan is performed for all pixel thresholds
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        # Set general configuration registers of the Timepix3
        self.chip.write_general_config()

        # Get the shutter sleep time
        sleep_time = self.get_shutter_sleep_time(tp_period = tp_period, n_injections = n_injections)

        # Write to the test pulse registers of the Timepix3
        # Write to period and phase tp registers
        data = self.chip.write_tp_period(tp_period, 0)

        # Write to pulse number tp register
        self.chip.write_tp_pulsenumber(n_injections)

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
        self.chip.set_dac("VTP_coarse", 100)
        self.chip.set_dac("VTP_fine", 240 + (100 // n_pulse_heights) * iteration)

        scan_param_id = 0
        for threshold in thresholds:
            # Set the threshold
            self.chip.set_dac("Vthreshold_coarse", int(threshold[0]))
            self.chip.set_dac("Vthreshold_fine", int(threshold[1]))

            with self.readout(scan_param_id=scan_param_id):
                step = 0
                for mask_step_cmd in mask_cmds:
                    # Only activate testpulses for columns with active pixels
                    self.chip.write_ctpr(list(range(step//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))))

                    # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
                    self.chip.write(mask_step_cmd)

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
                    self.chip.stop_readout()
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

        self.logger.info('Iteration %i finished', iteration)

    def analyze_iteration(self, iteration, progress = None, status = None):
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
            raw_data_call = ('h5_file.root.' + 'raw_data_' + str(iteration) + '[:]')
            raw_data = eval(raw_data_call)
            meta_data_call = ('h5_file.root.' + 'meta_data_' + str(iteration) + '[:]')
            meta_data = eval(meta_data_call)
            run_config_call = ('h5_file.root.' + 'configuration.run_config_' + str(iteration) + '[:]')
            run_config = eval(run_config_call)
            general_config = h5_file.root.configuration.generalConfig[:]
            op_mode = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            vco = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

            # Create group to save all data and histograms to the HDF file
            h5_file.create_group(h5_file.root, 'interpreted_' + str(iteration), 'Interpreted Data')
            interpreted_call = ('h5_file.root.' + 'interpreted_' + str(iteration))

            self.logger.info('Interpret raw data...')
            # Interpret the raw data (2x 32 bit to 1x 48 bit)
            hit_data = analysis.interpret_raw_data(raw_data, op_mode, vco, meta_data, progress = progress)
            raw_data = None

            # Select only data which is hit data
            hit_data = hit_data[hit_data['data_header'] == 1]
            h5_file.create_table(eval(interpreted_call), 'hit_data', hit_data, filters=tb.Filters(complib='zlib', complevel=5))
            pix_occ = np.bincount(hit_data['x'].astype(np.uint32) * 256 + hit_data['y'].astype(np.uint32), minlength=256 * 256)
            hist_occ = np.reshape(pix_occ, (256, 256)).T
            h5_file.create_carray(eval(interpreted_call), name='HistOcc', obj=hist_occ)
            param_range = np.unique(meta_data['scan_param_id'])
            meta_data = None
            pix_occ = None
            hist_occ = None

            # Create histograms for number of detected hits for individual thresholds
            scurve = analysis.scurve_hist(hit_data, param_range)
            hit_data = None

            # Read needed configuration parameters
            n_injections = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
            Vthreshold_stop = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]

            # Fit S-Curves to the histograms for all pixels
            param_range = list(range(Vthreshold_start, Vthreshold_stop + 1))
            thr2D, sig2D, chi2ndf2D = analysis.fit_scurves_multithread(scurve, scan_param_range=param_range, n_injections=n_injections, invert_x=True, progress = progress)

            h5_file.create_carray(eval(interpreted_call), name='HistSCurve', obj=scurve)
            h5_file.create_carray(eval(interpreted_call), name='Chi2Map', obj=chi2ndf2D.T)
            h5_file.create_carray(eval(interpreted_call), name='ThresholdMap', obj=thr2D.T)
            h5_file.create_carray(eval(interpreted_call), name='NoiseMap', obj=sig2D.T)

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
                iterations = int(p.run_config[b'n_pulse_heights'])
                Vthreshold_start = int(p.run_config[b'Vthreshold_start'])
                Vthreshold_stop = int(p.run_config[b'Vthreshold_stop'])
                n_injections = int(p.run_config[b'n_injections'])

                # Plot a page with all parameters
                p.plot_parameter_page()

                # Plot the equalisation bits histograms
                thr_matrix = h5_file.root.configuration.thr_matrix[:],
                p.plot_distribution(thr_matrix, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution', x_axis_title='Pixel threshold', y_axis_title='# of hits', suffix='pixel_threshold_distribution', plot_queue=plot_queue)

                mask = h5_file.root.configuration.mask_matrix[:].T

                # remove the calibration node if it already exists
                try:
                    h5_file.remove_node(h5_file.root.calibration, recursive=True)
                except:
                    pass

                # create a group for the calibration results
                h5_file.create_group(h5_file.root, 'calibration', 'Threshold calibration results')

                # create a table for the calibration results
                data_type = {'names': ['pulse_height', 'threshold', 'threshold_error'],
                             'formats': ['double', 'double', 'double']}
                calib_results = np.recarray(iterations, dtype=data_type)

                # create arrays for the calibration data points
                pulse_heights = np.zeros(iterations, dtype=float)
                thresholds = np.zeros(iterations, dtype=float)
                errors = np.zeros(iterations, dtype=float)

                # iterate though the iteration to plot the iteration specific results
                for iteration in range(iterations):

                    HistSCurve_call = ('h5_file.root.interpreted_' + str(iteration) + '.HistSCurve' + '[:]')
                    Chi2Map_call = ('h5_file.root.interpreted_' + str(iteration) + '.Chi2Map' + '[:]')
                    ThresholdMap_call = ('h5_file.root.interpreted_' + str(iteration) + '.ThresholdMap' + '[:]')

                    # Plot the S-Curve histogram
                    scurve_hist = eval(HistSCurve_call).T
                    max_occ = n_injections * 5
                    p.plot_scurves(scurve_hist, list(range(Vthreshold_start, Vthreshold_stop)), scan_parameter_name="Vthreshold", max_occ=max_occ, plot_queue=plot_queue)

                    # Do not plot pixels with converged  S-Curve fits
                    chi2_sel = eval(Chi2Map_call) > 0. # Mask not converged fits (chi2 = 0)
                    mask[~chi2_sel] = True

                    # Plot the threshold distribution based on the S-Curve fits
                    hist = np.ma.masked_array(eval(ThresholdMap_call), mask)
                    it_parameters, it_errors = p.plot_distribution(hist, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution', suffix='threshold_distribution', plot_queue=plot_queue)

                    # Fill the iteration results in the calibration parameter arrays
                    pulse_heights[iteration] = ((240 + (100 // iterations) * iteration) - 200) * 46.75
                    thresholds[iteration] = it_parameters[1]
                    errors[iteration] = it_parameters[2]

                # Fill the table with the calibration results
                calib_results['pulse_height'] = pulse_heights
                calib_results['threshold'] = thresholds
                calib_results['threshold_error'] = errors

                # Save the table to the HDF5 file
                h5_file.create_table(h5_file.root.calibration, 'calibration_results', calib_results)

                # Create the calibration plot
                p.plot_datapoints(pulse_heights, thresholds, x_plot_range=np.arange(0, 7500, 1), y_plot_range=np.arange(0, 3000, 1), y_err = errors, x_axis_title = 'Charge in electrons', y_axis_title = 'Threshold', title='Threshold calibration', suffix='threshold_calibration', plot_queue=plot_queue)

if __name__ == "__main__":
    scan = ThresholdCalib()
    scan.start(iteration = 0, **local_configuration)
    scan.plot()
