#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs optimized the Ibias_PixelDAC via linear regression
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

from tpx3.scan_base import ScanBase
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

    scan_id      = "PixelDACopt"
    wafer_number = 0
    y_position   = 0
    x_position   = 'A'

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
        
        # For now, just work with one chip
        self.num_of_chips = 1

        # Start parameters for the optimization
        last_delta     = [1]*self.num_of_chips
        last_rms_delta = [22]*self.num_of_chips
        pixeldac       = [127]*self.num_of_chips
        last_pixeldac  = pixeldac
        iteration      = 0

        # Create the masks for all steps for the scan at 0 and at 15
        mask_cmds  = self.create_scan_masks(16, pixel_threshold = 0, number = 1, append_datadriven = False, progress = progress)
        mask_cmds2 = self.create_scan_masks(16, pixel_threshold = 15, number = 1, append_datadriven = False, progress = progress)

        # Create a list of chips we want to optimize
        self.chips_not_optimized = []
        
        #for chip in self.chips[1:]:
        #    self.chips_not_optimized.append(chip)
        # For now just work with one chip, should be like above
        self.chips_not_optimized.append(self.chips[1])
        print("Chips to be optimized: " + str([chip.chipId for chip in self.chips_not_optimized]))

        # Repeat until optimization for all chips is done
        #while last_delta < last_rms_delta - 2 or last_delta > last_rms_delta + 2:
        while len(self.chips_not_optimized) > 0:

            # Disable all links, which are connected to chips, which are already optimized
            # Use real chipID like 'W12-C7'
            if status != None:
                for chip in range(len(self.chips_not_optimized)):
                    status.put("Linear regression step for chip {}: number {} with pixeldac {}".format(int(self.chips_not_optimized[chip].chipID_int),
                                                                                                        iteration + 1, int(pixeldac[chip])))

            # Create argument list for the current iteration step
            args = {
                'pixeldac'         : int(pixeldac),
                'last_pixeldac'    : int(last_pixeldac),
                'last_delta'       : float(last_delta),
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
                self.dump_configuration(iteration = iteration, **args)

            # Start the scan for the current iteration
            # For chips, which are not optimized yet
            self.scan_iteration(progress = progress, status = status, **args)

            # Analyse the data of the current iteration
            opt_results   = self.analyze_iteration(iteration, progress = progress, status = status)
            last_pixeldac = pixeldac

            # Store results of iteration, make an array out of pixeldac, last_delta, last_rms_delta
            for chip in range(len(self.chips_not_optimized)):
                pixeldac[chip]       = opt_results[chip][0]
                last_delta[chip]     = opt_results[chip][1]
                last_rms_delta[chip] = opt_results[chip][2]

            # Check, if the chips are optimized 
            for chip in range(len(self.chips_not_optimized)):
                if (last_delta < last_rms_delta - 2) or (last_delta > last_rms_delta + 2):
                    pass
                else:
                    # If optimized, delete chip from the list
                    self.chips_not_optimized.remove(self.chips_not_optimized[chip])

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

        if result == None:
            # Write new pixeldac into DAC YAML file
            with open('../chip_dacs.yml') as f:
                doc = yaml.load(f, Loader=yaml.FullLoader)

            for current_chip in self.chips_not_optimized:
                # Get register set of current chip
                registers = [chip[registers] for chip in doc['chips'] if chip['chip_ID'] == current_chip.chipId_int]

                for register in registers:
                    if register['name'] == 'Ibias_PixelDAC':
                        register['value'] = int(last_pixeldac)

            with open('../chip_dacs.yml', 'w') as f:
                yaml.dump(doc, f)
        else:
            result.put(int(last_pixeldac))

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

            # Set the pixeldac to the current iteration value -- !! can be different for each chip !!
            self.chips[0].write(chip.set_dac("Ibias_PixelDAC", pixeldac, write=False))

        # Get the shutter sleep time
        sleep_time = self.get_shutter_sleep_time(tp_period = tp_period, n_injections = n_injections)

        self.logger.info('Scan with Pixeldac %i', pixeldac)
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
                # Set the threshold
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
                    self.chips[0].write(chip.stop_readout(write=False))
                    time.sleep(0.01)
            for chip in self.chips_not_optimized:
                self.chips[0].write(chip.reset_sequential(write=False))
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
            meta_data_call  = ('h5_file.root.' + 'meta_data_' + str(iteration) + '[:]')
            meta_data       = eval(meta_data_call)
            run_config_call = ('h5_file.root.' + 'configuration.run_config_' + str(iteration) + '[:]')
            run_config      = eval(run_config_call)
            general_config  = h5_file.root.configuration.generalConfig[:]
            op_mode         = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            vco             = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

            # 'Simulate' more chips, in this case, just work on one
            chip_IDs_new = [b'W18-K7',b'W18-K7',b'W18-K7',b'W18-K7',b'W18-K7', b'W18-K7',b'W18-K7', b'W18-K7']
            for new_Id in range(8):
                h5_file.root.configuration.links.cols.chip_id[new_Id] = chip_IDs_new[new_Id]

            # Get link configuration
            link_config = h5_file.root.configuration.links[:]
            print(link_config)
            chip_IDs    = link_config['chip_id']

            # Create dictionary of Chips and the links they are connected to
            self.chip_links = {}
    
            for link, ID in enumerate(chip_IDs):
                if ID not in self.chip_links:
                    self.chip_links[ID] = [link]
                else:
                    self.chip_links[ID].append(link)
            print('Chip links: ' + str(self.chip_links))

            # Get the number of chips
            self.num_of_chips = len(self.chip_links)

            self.logger.info('Interpret raw data...')

            # THR = 0
            param_range, index = np.unique(meta_data['scan_param_id'], return_index=True)
            meta_data_th0      = meta_data[meta_data['scan_param_id'] < len(param_range) // 2]
            param_range_th0    = np.unique(meta_data_th0['scan_param_id'])

            # THR = 15
            meta_data_th15   = meta_data[meta_data['scan_param_id'] >= len(param_range) // 2]
            param_range_th15 = np.unique(meta_data_th15['scan_param_id'])

            # shift indices so that they start with zero
            start                         = meta_data_th15['index_start'][0]
            meta_data_th15['index_start'] = meta_data_th15['index_start']-start
            meta_data_th15['index_stop']  = meta_data_th15['index_stop']-start

            self.logger.info('THR = 0')
            #THR = 0
            raw_data_call = ('h5_file.root.' + 'raw_data_' + str(iteration) + '[:' + str(meta_data_th0['index_stop'][-1]) + ']')
            raw_data_thr0 = eval(raw_data_call)
            hit_data_thr0 = analysis.interpret_raw_data(raw_data_thr0, op_mode, vco, self.chip_links, meta_data_th0, progress = progress)
            #raw_data_thr0 = None

            self.logger.info('THR = 15')
            #THR = 15
            raw_data_call  = ('h5_file.root.' + 'raw_data_' + str(iteration) + '[' + str(meta_data_th0['index_stop'][-1]) + ':]')
            raw_data_thr15 = eval(raw_data_call)
            hit_data_thr15 = analysis.interpret_raw_data(raw_data_thr15, op_mode, vco, self.chip_links, meta_data_th15, progress = progress)
            #raw_data_thr15 = None

            # Read needed configuration parameters
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
            Vthreshold_stop  = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]
            n_injections     = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]
            pixeldac         = [int(item[1]) for item in run_config if item[0] == b'pixeldac'][0]
            last_pixeldac    = [int(item[1]) for item in run_config if item[0] == b'last_pixeldac'][0]
            last_delta       = [float(item[1]) for item in run_config if item[0] == b'last_delta'][0]

            pixeldac_result  = [[]]*len(self.chips_not_optimized)

            # create group for interpreted data of current iteration
            h5_file.create_group(h5_file.root, ('interpreted_' + str(iteration)))

            for chip in range(self.num_of_chips):
                # get chipID of current chip
                chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                print(chip, chipID)

                # create group for current chip
                create_group_call = ('h5_file.root.interpreted_' + str(iteration))
                h5_file.create_group(eval(create_group_call), name = chipID)

                # get group for current chip
                chip_group_call = create_group_call + '._f_get_child(chipID)'
                chip_group      = eval(chip_group_call)

                # Select only data which is hit data
                hit_data_thr0_chip  = hit_data_thr0[chip][hit_data_thr0[chip]['data_header'] == 1]
                hit_data_thr15_chip = hit_data_thr15[chip][hit_data_thr15[chip]['data_header'] == 1]

                # Divide the data into two parts - data for pixel threshold 0 and 15
                param_range      = np.unique(meta_data['scan_param_id'])
                #meta_data   = None
                param_range_th0  = np.unique(hit_data_thr0_chip['scan_param_id'])
                param_range_th15 = np.unique(hit_data_thr15_chip['scan_param_id'])

                # Create histograms for number of detected hits for individual thresholds
                self.logger.info('Get the global threshold distributions for all pixels...')
                scurve_th0          = analysis.scurve_hist(hit_data_thr0_chip, np.arange(len(param_range) // 2))
                hit_data_thr0_chip  = None
                scurve_th15         = analysis.scurve_hist(hit_data_thr15_chip, np.arange(len(param_range) // 2, len(param_range)))
                hit_data_thr15_chip = None

                # Fit S-Curves to the histograms for all pixels
                self.logger.info('Fit the scurves for all pixels...')
                thr2D_th0, _, _  = analysis.fit_scurves_multithread(scurve_th0, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop + 1)), n_injections=n_injections, invert_x=False, progress = progress)
                h5_file.create_carray(chip_group, name='HistSCurve_th0', obj=scurve_th0)
                h5_file.create_carray(chip_group, name='ThresholdMap_th0', obj=thr2D_th0.T)
                scurve_th0       = None
                thr2D_th15, _, _ = analysis.fit_scurves_multithread(scurve_th15, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop + 1)), n_injections=n_injections, invert_x=False, progress = progress)
                h5_file.create_carray(chip_group, name='HistSCurve_th15', obj=scurve_th15)
                h5_file.create_carray(chip_group, name='ThresholdMap_th15', obj=thr2D_th15.T)
                scurve_th15      = None

                # Put the threshold distribution based on the fit results in two histograms
                self.logger.info('Get the cumulated global threshold distributions...')
                hist_th0   = analysis.vth_hist(thr2D_th0, Vthreshold_stop)
                thr2D_th0  = None
                hist_th15  = analysis.vth_hist(thr2D_th15, Vthreshold_stop)
                thr2D_th15 = None

                # Use the threshold histograms to calculate the new Ibias_PixelDAC setting
                self.logger.info('Calculate new pixelDAC value...')
                pixeldac_result[chip] = analysis.pixeldac_opt(hist_th0, hist_th15, pixeldac, last_pixeldac, last_delta, Vthreshold_start, Vthreshold_stop)
                delta                 = pixeldac_result[chip][1]
                rms_delta             = pixeldac_result[chip][2]

                self.logger.info('Result of iteration: Scan with pixeldac %i - New pixeldac %i. Delta was %f with optimal delta %f' % (int(pixeldac), int(pixeldac_result[chip][0]), pixeldac_result[chip][1], pixeldac_result[chip][2]))
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
            mask = h5_file.root.configuration.mask_matrix[:].T

            with plotting.Plotting(h5_filename, iteration = 0) as p:

                # Read needed configuration parameters
                Vthreshold_start = int(p.run_config[b'Vthreshold_start'])
                Vthreshold_stop  = int(p.run_config[b'Vthreshold_stop'])
                n_injections     = int(p.run_config[b'n_injections'])

                # Plot a page with all parameters
                p.plot_parameter_page()

                for iteration in range(iterations):
                    pixelDAC_call  = ('h5_file.root.configuration.run_config_' + str(iteration))
                    pixelDAC_table = eval(pixelDAC_call)
                    pixelDAC       = 0
                    for row in pixelDAC_table:
                        if row['attribute'] == b'pixeldac':
                            pixelDAC = str(int(row['value']))

                    for chip in range(self.num_of_chips):
                        # get chipID of current chip
                        chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                        print(chip, chipID)

                        # get group for current chip
                        chip_group_call = 'h5_file.root.interpreted_' + str(iteration) + '._f_get_child(chipID)'
                        chip_group      = eval(chip_group_call)

                        # Plot the S-Curve histogram
                        scurve_th0_hist = chip_group.HistSCurve_th0[:].T
                        max_occ         = n_injections * 5
                        p.plot_scurves(scurve_th0_hist, list(range(Vthreshold_start, Vthreshold_stop)), chipID, scan_parameter_name="Vthreshold", title='SCurves - PixelDAC 0 - IBias_PixelDAC ' + pixelDAC, max_occ=max_occ, plot_queue=None)

                        # Plot the threshold distribution based on the S-Curve fits
                        hist_th0 = np.ma.masked_array(chip_group.ThresholdMap_th0[:], mask)
                        p.plot_distribution(hist_th0, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title=('Threshold distribution - PixelDAC 0 - IBias_PixelDAC ' + pixelDAC + ', chip %s') %str(chipID), suffix='threshold_distribution_th0', plot_queue=None)

                        # Plot the S-Curve histogram
                        scurve_th15_hist = chip_group.HistSCurve_th15[:].T
                        max_occ          = n_injections * 5
                        p.plot_scurves(scurve_th15_hist, list(range(Vthreshold_start, Vthreshold_stop)), chipID, scan_parameter_name="Vthreshold", title='SCurves - PixelDAC 15 - IBias_PixelDAC ' + pixelDAC, max_occ=max_occ, plot_queue=None)

                        # Plot the threshold distribution based on the S-Curve fits
                        hist_th15 = np.ma.masked_array(chip_group.ThresholdMap_th15[:], mask)
                        p.plot_distribution(hist_th15, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title=('Threshold distribution - PixelDAC 15 - IBias_PixelDAC ' + pixelDAC + ', chip %s') %str(chipID), suffix='threshold_distribution_th15', plot_queue=None)

if __name__ == "__main__":
    scan = PixelDACopt()
    scan.start(iteration = 0, **local_configuration)
    scan.plot()
