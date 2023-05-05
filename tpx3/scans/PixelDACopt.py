#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs optimizing the Ibias_PixelDAC via linear regression
    based on several threshold scans.
    Compared to the normal PixelDac_opt this scans only over 1/16 of the chip
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

from tpx3.scan_base import DacTable, ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting
import tpx3.utils as utils

from tables.exceptions import NoSuchNodeError
from io import open
from six.moves import range

local_configuration = {
    # Scan parameters
    'offset'           : 0,
    'Vthreshold_start' : 1600,
    'Vthreshold_stop'  : 2200,
    'n_injections'     : 100
}

class IterationTable(tb.IsDescription):
    attribute = tb.StringCol(64)
    value = tb.StringCol(128)

class PixelDACopt(ScanBase):

    scan_id = "PixelDACopt"

    def __init__(self, dut_conf=None, no_chip=False, run_name=None):
        super().__init__(dut_conf, no_chip, run_name)

        self.chips_not_optimized = []
        for chip in self.chips[1:]:
            self.chips_not_optimized.append(chip)

        dac_yaml = os.path.join(self.proj_dir, 'tpx3' + os.sep + 'chip_dacs.yml')        

        # To keep better track of the optimization parameters create a dictionary with start parameters
        self.optimization_params = {}
        for chip in self.chips_not_optimized:
            self.optimization_params[chip.chipId_decoded] = {'last_delta': 1.0, 'last_rms_delta': 22.0,
                                                             'pixeldac': 127, 'last_pixeldac': 127}
            # Update YAML
            with open(dac_yaml, 'r') as f:
                doc = yaml.load(f, Loader=yaml.FullLoader)

            for yaml_chip in doc['chips']:
                # Select current chip
                if yaml_chip['chip_ID'] == chip.chipId_int:
                    for register in yaml_chip['registers']:
                        # Select Ibias_PixelDAC register
                        if register['name'] == 'Ibias_PixelDAC':
                            # Write out new value
                            register['value'] = 127
                    
            # Save new settings
            with open(dac_yaml, 'w') as f:
                yaml.dump(doc, f)
            # Update internal dict of chip
            chip.read_yaml(dac_yaml, 'DacsDict')


    def scan(self, Vthreshold_start = 1500, Vthreshold_stop = 2500, n_injections = 100, tp_period = 1, offset = 0, progress = None, status = None, result = None, **kwargs):
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
        if offset not in range(16):
            raise ValueError("Value {} for offset is not in the allowed range (0-15)".format(offset))

        print("Chips to be optimized: " + str([chip.chipId_decoded for chip in self.chips_not_optimized]))

        # Start parameters for the optimization
        iteration  = 0

        # Create the masks for all steps for the scan at 0 and at 15
        mask_cmds  = self.create_scan_masks(16, pixel_threshold = 0, number = 1, append_datadriven = False, progress = progress)
        mask_cmds2 = self.create_scan_masks(16, pixel_threshold = 15, number = 1, append_datadriven = False, progress = progress)

        # Repeat until optimization for all chips is done
        while len(self.chips_not_optimized) > 0:

            if status != None:
                for chip in self.chips_not_optimized:
                    status.put(f"Linear regression step number {iteration + 1} for chip {chip.chipId_decoded} with pixeldac {self.optimization_params[chip.chipId_decoded]['pixeldac']}")

            # Create argument list for the current iteration step
            args = {
                'pixeldac'         : self.optimization_params,
                'last_pixeldac'    : self.optimization_params,
                'last_delta'       : self.optimization_params,
                'offset'           : offset,
                'Vthreshold_start' : Vthreshold_start,
                'Vthreshold_stop'  : Vthreshold_stop,
                'n_injections'     : n_injections,
                'tp_period'        : tp_period,
                'mask_cmds'        : mask_cmds,
                'mask_cmds2'       : mask_cmds2,
                'maskfile'         : self.maskfile
            }

            # In the 0th iteration all files and tables are already created by the start() function of scan_base
            # In further iterations this is not the case so its triggered by the following commands
            if iteration != 0:
                self.setup_files(iteration = iteration)

            # Start the scan for the current iteration
            # For chips, which are not optimized yet
            self.scan_iteration(progress = progress, status = status, **args)

            # Trigger configuration dump after the scan, the dacs will then be set and the correct
            # values for the scan are written off
            if iteration != 0:
                self.dump_configuration(iteration = iteration, **args)

            # Analyse the data of the current iteration
            opt_results = self.analyze_iteration(iteration, chip_links = kwargs['chip_link'], progress = progress, status = status)

            # Check, if the chips are optimized 
            for chip in self.chips_not_optimized:
                last_delta     = self.optimization_params[chip.chipId_decoded]['last_delta']
                last_rms_delta = self.optimization_params[chip.chipId_decoded]['last_rms_delta']
                
                if (last_delta < last_rms_delta - 2) or (last_delta > last_rms_delta + 2):
                    pass
                else:
                    self.chips_not_optimized.remove(chip)
                    
            iteration += 1

        # Write number of iterations to HDF file
        h5_filename = self.output_filename + '.h5'
        with tb.open_file(h5_filename, 'r+') as h5_file:
            iterations_table = self.h5_file.create_table(self.h5_file.root.configuration, name='iterations', title='iterations', description=IterationTable)
            # Common scan/run configuration parameters
            row              = iterations_table.row
            row['attribute'] = 'iterations'
            row['value']     = iteration
            row.append()
            iterations_table.flush()

        # Write results off
        result.put(self.optimization_params)
    

    def scan_iteration(self, pixeldac = 127, last_pixeldac = 127, last_delta = 127, Vthreshold_start=1500, Vthreshold_stop=2500, n_injections=100, tp_period = 1, offset=0, mask_cmds = None, mask_cmds2 = None, progress = None, status = None, **kwargs):
        '''
            Takes data for one iteration of the optimization. Therefore a threshold scan is performed for all pixel thresholds at 0 and at 15.
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''
        # Set general configuration registers of the Timepix3
        for chip in self.chips_not_optimized:
            self.chips[0].write(chip.write_general_config(write=False))

            # Write to the test pulse registers of the Timepix3
            # Write to period and phase tp register
            self.chips[0].write(chip.write_tp_period(tp_period, 0, write=False)) 

            # Write to pulse number tp register
            self.chips[0].write(chip.write_tp_pulsenumber(n_injections, write=False))

            chip_pixeldac = self.optimization_params[chip.chipId_decoded]['pixeldac']

            # Set the pixeldac to the current iteration value -- !! can be different for each chip !!
            self.chips[0].write(chip.set_dac("Ibias_PixelDAC", chip_pixeldac, write=False))
            self.logger.info(f'Ibias_PixelDAC set to {chip_pixeldac} on chip {chip.chipId_decoded}')

        # Get the shutter sleep time
        sleep_time = self.get_shutter_sleep_time(tp_period = tp_period, n_injections = n_injections)

        self.logger.info('Preparing injection masks...')
        if status != None:
            status.put("Preparing injection masks")

        # Scan with all masks over the given threshold range for pixelthreshold 0
        thresholds = utils.create_threshold_list(utils.get_coarse_jumps(Vthreshold_start, Vthreshold_stop))
        self.logger.info('Starting scan for THR = 0...')
        if status != None:
            status.put("Starting scan for THR = 0")
        if status != None:
            status.put("iteration_symbol")

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(thresholds))
        else:
            # Initialize counter for progress
            step_counter = 0

        for chip in self.chips_not_optimized:
            # Only activate testpulses for columns with active pixels
            self.chips[0].write(chip.write_ctpr(list(range(offset, 256, 4)), write=False))

        # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
        self.chips[0].write(mask_cmds)

        scan_param_id = 0
        for threshold in thresholds:
            for chip in self.chips_not_optimized:
                # Set the threshold, change back to broadcast
                self.chips[0].write(chip.set_dac("Vthreshold_coarse", int(threshold[0]), write=False))
                self.chips[0].write(chip.set_dac("Vthreshold_fine", int(threshold[1]), write=False))

            with self.readout(scan_param_id=scan_param_id):
                for chip in self.chips_not_optimized:
                    self.chips[0].write(chip.read_pixel_matrix_datadriven(write=False))

                # Open the shutter, take data and update the progress bar
                with self.shutter():
                    time.sleep(sleep_time)
                    if progress == None:
                        # Update the progress bar
                        pbar.update(1)
                    else:
                        # Update the progress fraction and put it in the queue
                        step_counter += 1
                        fraction      = step_counter / len(thresholds)
                        progress.put(fraction)
                for chip in self.chips_not_optimized:
                    self.chips[0].write(chip.stop_readout(write=False)) # should change back to broadcast
                    time.sleep(0.01)
            for chip in self.chips_not_optimized:
                self.chips[0].write(chip.reset_sequential(write=False)) # should change back to broadcast 
                time.sleep(0.001)
            scan_param_id += 1

        if progress == None:
            # Close the progress bar
            pbar.close()

        # Scan with all masks over the given threshold range for pixelthreshold 15
        self.logger.info('Starting scan for THR = 15...')
        if status != None:
            status.put("Starting scan for THR = 15")
        if status != None:
            status.put("iteration_symbol")

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total = len(thresholds))
        else:
            # Initialize counter for progress
            step_counter = 0

        # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
        self.chips[0].write(mask_cmds2)

        scan_param_id = 0
        for threshold in thresholds:
            for chip in self.chips_not_optimized:
                # Set the threshold
                self.chips[0].write(chip.set_dac("Vthreshold_coarse", int(threshold[0]), write=False))
                self.chips[0].write(chip.set_dac("Vthreshold_fine", int(threshold[1]), write=False))

            with self.readout(scan_param_id=scan_param_id + len(thresholds)):
                for chip in self.chips_not_optimized:
                    self.chips[0].write(chip.read_pixel_matrix_datadriven(write=False))

                # Open the shutter, take data and update the progress bar
                with self.shutter():
                    time.sleep(sleep_time)
                    if progress == None:
                        # Update the progress bar
                        pbar.update(1)
                    else:
                        # Update the progress fraction and put it in the queue
                        step_counter += 1
                        fraction      = step_counter / len(thresholds)
                        progress.put(fraction)
                for chip in self.chips_not_optimized:
                    self.chips[0].write(chip.stop_readout(write=False))
                    time.sleep(0.01)
            for chip in self.chips_not_optimized:
                self.chips[0].write(chip.reset_sequential(write=False))
                time.sleep(0.001)
            scan_param_id += 1

        if progress == None:
            # Close the progress bar
            pbar.close()

        if status != None:
            status.put("iteration_finish_symbol")

        self.logger.info('Scan finished')

    def analyze_iteration(self, iteration = 0, chip_links = None, progress = None, status = None):
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
            meta_data      = eval(f'h5_file.root.meta_data_{iteration}[:]')
            run_config     = eval(f'h5_file.root.configuration.run_config_{iteration}')
            general_config = h5_file.root.configuration.generalConfig
            op_mode        = general_config.col('Op_mode')[0]
            vco            = general_config.col('Fast_Io_en')[0]

            self.logger.info('Interpret raw data...')

            # THR = 0
            param_range, index       = np.unique(meta_data['scan_param_id'], return_index=True)
            meta_data_th0            = meta_data[meta_data['scan_param_id'] < len(param_range) // 2]
            meta_data_th0_index_stop = meta_data_th0['index_stop'][-1]

            # THR = 15
            meta_data_th15   = meta_data[meta_data['scan_param_id'] >= len(param_range) // 2]

            # shift indices so that they start with zero
            start                         = meta_data_th15['index_start'][0]
            meta_data_th15['index_start'] = meta_data_th15['index_start']-start
            meta_data_th15['index_stop']  = meta_data_th15['index_stop']-start

            self.logger.info('THR = 0')
            #THR = 0
            raw_data_thr0 = eval(f'h5_file.root.raw_data_{iteration}[:{meta_data_th0_index_stop}]')
            hit_data_thr0 = analysis.interpret_raw_data(raw_data_thr0, op_mode, vco, chip_links, meta_data_th0, progress = progress)

            self.logger.info('THR = 15')
            #THR = 15
            raw_data_thr15 = eval(f'h5_file.root.raw_data_{iteration}[{meta_data_th0_index_stop}:]')
            hit_data_thr15 = analysis.interpret_raw_data(raw_data_thr15, op_mode, vco, chip_links, meta_data_th15, progress = progress)

            # Read needed configuration parameters
            Vthreshold_start = run_config.col('Vthreshold_start')[0]
            Vthreshold_stop  = run_config.col('Vthreshold_stop')[0]
            n_injections     = run_config.col('n_injections')[0]

            # create group for interpreted data of current iteration
            h5_file.create_group(h5_file.root, ('interpreted_' + str(iteration)))

            for chip in self.chips_not_optimized:
                # Get the index of current chip in regards to the chip_links dictionary. This is the index, where
                # the hit_data of the chip is.
                chip_num = [number for number, ID in enumerate(chip_links) if ID==chip.chipId_decoded][0]
                # Get chipID in desirable formatting for HDF5 files (without '-')
                chipID = f'W{chip.wafer_number}_{chip.x_position}{chip.y_position}'
                
                # create group for current chip
                h5_file.create_group(eval(f'h5_file.root.interpreted_{iteration}'), name = chipID)

                # get group for current chip
                chip_group = eval(f'h5_file.root.interpreted_{iteration}._f_get_child(chipID)')

                # Select only data which is hit data
                hit_data_thr0_chip  = hit_data_thr0[chip_num][hit_data_thr0[chip_num]['data_header'] == 1]
                hit_data_thr15_chip = hit_data_thr15[chip_num][hit_data_thr15[chip_num]['data_header'] == 1]

                # Divide the data into two parts - data for pixel threshold 0 and 15
                param_range      = np.unique(meta_data['scan_param_id'])

                # Create histograms for number of detected hits for individual thresholds
                self.logger.info('Get the global threshold distributions for all pixels...')
                scurve_th0          = analysis.scurve_hist(hit_data_thr0_chip, np.arange(len(param_range) // 2))
                hit_data_thr0_chip  = None
                scurve_th15         = analysis.scurve_hist(hit_data_thr15_chip, np.arange(len(param_range) // 2, len(param_range)))
                hit_data_thr15_chip = None

                # Fit S-Curves to the histograms for all pixels
                self.logger.info('Fit the scurves for all pixels...')
                thr2D_th0, _, _  = analysis.fit_scurves_multithread(scurve_th0, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop + 1)), n_injections=n_injections, invert_x=chip.configs['Polarity'], progress = progress)
                h5_file.create_carray(chip_group, name='HistSCurve_th0', obj=scurve_th0)
                h5_file.create_carray(chip_group, name='ThresholdMap_th0', obj=thr2D_th0.T)
                scurve_th0       = None
                thr2D_th15, _, _ = analysis.fit_scurves_multithread(scurve_th15, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop + 1)), n_injections=n_injections, invert_x=chip.configs['Polarity'], progress = progress)
                h5_file.create_carray(chip_group, name='HistSCurve_th15', obj=scurve_th15)
                h5_file.create_carray(chip_group, name='ThresholdMap_th15', obj=thr2D_th15.T)
                scurve_th15      = None

                # Put the threshold distribution based on the fit results in two histograms
                self.logger.info('Get the cumulated global threshold distributions...')
                hist_th0   = analysis.vth_hist(thr2D_th0, Vthreshold_stop)
                thr2D_th0  = None
                hist_th15  = analysis.vth_hist(thr2D_th15, Vthreshold_stop)
                thr2D_th15 = None

                pixeldac      = self.optimization_params[chip.chipId_decoded]['pixeldac'] 
                last_pixeldac = self.optimization_params[chip.chipId_decoded]['last_pixeldac'] 
                last_delta    = self.optimization_params[chip.chipId_decoded]['last_delta'] 

                # Use the threshold histograms to calculate the new Ibias_PixelDAC setting
                self.logger.info('Calculate new pixelDAC value...')
                pixeldac_result = analysis.pixeldac_opt(hist_th0, hist_th15, pixeldac, last_pixeldac, last_delta, Vthreshold_start, Vthreshold_stop)

                self.logger.info(f'Result of iteration for chip {chip.chipId_decoded}: Scan with pixeldac {pixeldac} - New pixeldac {int(pixeldac_result[0])}. Delta was {pixeldac_result[1]} with optimal delta {pixeldac_result[2]}')
                
                # Update params
                self.optimization_params[chip.chipId_decoded]['pixeldac']       = int(pixeldac_result[0])
                self.optimization_params[chip.chipId_decoded]['last_delta']     = pixeldac_result[1]
                self.optimization_params[chip.chipId_decoded]['last_rms_delta'] = pixeldac_result[2]
                self.optimization_params[chip.chipId_decoded]['last_pixeldac']  = pixeldac
        return pixeldac_result

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
            iterations_table = h5_file.root.configuration.iterations
            iterations       = 0
            for row in iterations_table:
                if row['attribute'] == b'iterations':
                    iterations = int(row['value'])

            with plotting.Plotting(h5_filename, iteration = 0) as p:

                # Read needed configuration parameters
                Vthreshold_start = p.run_config['Vthreshold_start'][0]
                Vthreshold_stop  = p.run_config['Vthreshold_stop'][0]
                n_injections     = p.run_config['n_injections'][0]

                # Plot a page with all parameters
                p.plot_parameter_page()

                for iteration in range(iterations):
                    pixelDAC_table = eval(f'h5_file.root.configuration.run_config_{iteration}')
                    
                    # Get chipIDs for current iteration
                    chip_wafer = pixelDAC_table.col('wafer_number')
                    chip_x     = pixelDAC_table.col('x_position')
                    chip_y     = pixelDAC_table.col('y_position')
                    chip_dac   = pixelDAC_table.col('pixeldac')
                    chip_IDs   = [f'W{chip_wafer[number].decode()}-{chip_x[number].decode()}{chip_y[number].decode()}' for number, item in enumerate(chip_wafer)]
                    chip_h5    = [f'W{chip_wafer[number].decode()}_{chip_x[number].decode()}{chip_y[number].decode()}' for number, item in enumerate(chip_wafer)]

                    for (index, chip) in enumerate(chip_IDs):
                        # Get chipID in desirable formatting for HDF5 files (without '-')
                        chipID = chip_h5[index]
                        dac    = chip_dac[index]

                        # get group for current chip
                        chip_group      = eval(f'h5_file.root.interpreted_{iteration}._f_get_child(chipID)')

                        # get for each chip
                        mask = eval(f'h5_file.root.configuration.mask_matrix_{chipID}[:].T')

                        # Plot the S-Curve histogram
                        scurve_th0_hist = chip_group.HistSCurve_th0[:].T
                        max_occ         = n_injections * 5
                        p.plot_scurves(scurve_th0_hist, chip, list(range(Vthreshold_start, Vthreshold_stop+1)), scan_parameter_name="Vthreshold", title=f'SCurves - PixelDAC 0 - IBias_PixelDAC {dac}', max_occ=max_occ, plot_queue=plot_queue)

                        # Plot the threshold distribution based on the S-Curve fits
                        hist_th0 = np.ma.masked_array(chip_group.ThresholdMap_th0[:], mask)
                        p.plot_distribution(hist_th0, chip, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop+0.5, 1), y_axis_title='# of pixels', x_axis_title='Vthreshold', title=f'Threshold distribution - PixelDAC 0 - IBias_PixelDAC {dac}', suffix='threshold_distribution_th0', plot_queue=plot_queue)

                        # Plot the S-Curve histogram
                        scurve_th15_hist = chip_group.HistSCurve_th15[:].T
                        max_occ          = n_injections * 5
                        p.plot_scurves(scurve_th15_hist, chip, list(range(Vthreshold_start, Vthreshold_stop+1)), scan_parameter_name="Vthreshold", title=f'SCurves - PixelDAC 15 - IBias_PixelDAC {dac}', max_occ=max_occ, plot_queue=plot_queue)

                        # Plot the threshold distribution based on the S-Curve fits
                        hist_th15 = np.ma.masked_array(chip_group.ThresholdMap_th15[:], mask)
                        p.plot_distribution(hist_th15, chip, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop+0.5, 1), y_axis_title='# of pixels', x_axis_title='Vthreshold', title=f'Threshold distribution - PixelDAC 15 - IBias_PixelDAC {dac}', suffix='threshold_distribution_th15', plot_queue=plot_queue)

if __name__ == "__main__":
    scan = PixelDACopt()
    scan.start(iteration = 0, **local_configuration)
    scan.plot()
