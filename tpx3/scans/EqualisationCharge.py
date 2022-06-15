#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs an equalisation of pixels based on a threshold scan
    with injected charge.
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
import tpx3.utils as utils

from tables.exceptions import NoSuchNodeError
from six.moves import range

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'Vthreshold_start' : 1500,
    'Vthreshold_stop'  : 2000,
    'n_injections'     : 100
}


class EqualisationCharge(ScanBase):

    scan_id = "EqualisationCharge"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self, Vthreshold_start = 1500, Vthreshold_stop = 2000, n_injections = 16, mask_step = 32, tp_period = 1, progress = None, status = None, **kwargs):
        '''
            Takes data for equalisation. Therefore a threshold scan is performed for all pixel thresholds at 0 and at 15.
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

        # Create the masks for all steps for the scan at 0 and at 15
        mask_cmds = self.create_scan_masks(mask_step, pixel_threshold = 0, progress = progress)
        mask_cmds2 = self.create_scan_masks(mask_step, pixel_threshold = 15, progress = progress)

        # Get the shutter sleep time
        sleep_time = self.get_shutter_sleep_time(tp_period = tp_period, n_injections = n_injections)

        # Scan with pixel threshold 0
        self.logger.info('Starting scan for THR = 0...')
        if status != None:
            status.put("Starting scan for THR = 0")
        if status != None:
            status.put("iteration_symbol")
        thresholds = utils.create_threshold_list(utils.get_coarse_jumps(Vthreshold_start, Vthreshold_stop))

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds) * len(thresholds))
        else:
            # Initialize counter for progress
            step_counter = 0

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
                            fraction      = step_counter / (len(mask_cmds) * len(thresholds))
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

        # Scan with pixel threshold 15
        self.logger.info('Starting scan for THR = 15...')
        if status != None:
            status.put("Starting scan for THR = 15")
        if status != None:
            status.put("iteration_symbol")

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds2) * len(thresholds))
        else:
            # Initialize counter for progress
            step_counter = 0

        scan_param_id = 0
        for threshold in thresholds:
            for chip in self.chips[1:]:
                # Set the threshold
                self.chips[0].write(chip.set_dac("Vthreshold_coarse", int(threshold[0]), write=False))
                self.chips[0].write(chip.set_dac("Vthreshold_fine", int(threshold[1]), write=False))

            with self.readout(scan_param_id=scan_param_id + len(thresholds)):
                step = 0
                for mask_step_cmd in mask_cmds2:
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
                            fraction      = step_counter / (len(mask_cmds2) * len(thresholds))
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

        self.logger.info('Scan finished')

    def analyze(self, progress = None, status = None, result_path = None, **kwargs):
        '''
            Analyze the data of the equalisation and calculate the equalisation matrix
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting data analysis...')
        if status != None:
            status.put("Performing data analysis")

        # Open the HDF5 which contains all data of the equalisation
        with tb.open_file(h5_filename, 'r+') as h5_file:
            # Read raw data, meta data and configuration parameters
            meta_data      = h5_file.root.meta_data[:]
            run_config     = h5_file.root.configuration.run_config[:]
            general_config = h5_file.root.configuration.generalConfig[:]
            op_mode        = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            vco            = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

            # 'Simulate' more chips
            chip_IDs_new = [b'W18-K7',b'W18-K7',b'W17-D8',b'W17-D8',b'W14-E9', b'W14-E9',b'W15-C5', b'W15-C5']
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

            # Create group to save all data and histograms to the HDF file
            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

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
            raw_data_thr0 = h5_file.root.raw_data[:meta_data_th0['index_stop'][-1]]
            hit_data_thr0 = analysis.interpret_raw_data(raw_data_thr0, op_mode, vco, self.chip_links, meta_data_th0, progress = progress)
            #h5_file.create_table(h5_file.root.interpreted, 'hit_data_th0', hit_data_thr0, filters=tb.Filters(complib='zlib', complevel=5))
            #raw_data_thr0 = None

            self.logger.info('THR = 15')
            #THR = 15
            raw_data_thr15 = h5_file.root.raw_data[meta_data_th0['index_stop'][-1]:]
            hit_data_thr15 = analysis.interpret_raw_data(raw_data_thr15, op_mode, vco, self.chip_links, meta_data_th15, progress = progress)
            #h5_file.create_table(h5_file.root.interpreted, 'hit_data_th15', hit_data_thr15, filters=tb.Filters(complib='zlib', complevel=5))
            #raw_data_thr15 = None

            # Read needed configuration parameters
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
            Vthreshold_stop  = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]
            n_injections     = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]
            chip_wafer       = [int(item[1]) for item in run_config if item[0] == b'chip_wafer'][0]
            chip_x           = [item[1].decode() for item in run_config if item[0] == b'chip_x'][0]
            chip_y           = [int(item[1]) for item in run_config if item[0] == b'chip_y'][0]

            for chip in range(self.num_of_chips):
                # get chipID of current chip
                chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                print(chip, chipID)
                
                # create group for current chip
                h5_file.create_group(h5_file.root.interpreted, name=chipID)

                # get group for current chip
                chip_group  = h5_file.root.interpreted._f_get_child(chipID)

                # Select only data which is hit data
                hit_data_thr0_chip  = hit_data_thr0[chip][hit_data_thr0[chip]['data_header'] == 1]
                hit_data_thr15_chip = hit_data_thr15[chip][hit_data_thr15[chip]['data_header'] == 1]

                h5_file.create_table(chip_group, 'hit_data_th0', hit_data_thr0_chip, filters=tb.Filters(complib='zlib', complevel=5))
                h5_file.create_table(chip_group, 'hit_data_th15', hit_data_thr15_chip, filters=tb.Filters(complib='zlib', complevel=5))

                # Divide the data into two parts - data for pixel threshold 0 and 15
                param_range      = np.unique(meta_data['scan_param_id'])
                #meta_data        = None
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
                thr2D_th0, sig2D_th0, chi2ndf2D_th0 = analysis.fit_scurves_multithread(scurve_th0, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop + 1)), n_injections=n_injections, invert_x=False, progress = progress)
                h5_file.create_carray(chip_group, name='HistSCurve_th0', obj=scurve_th0)
                h5_file.create_carray(chip_group, name='ThresholdMap_th0', obj=thr2D_th0.T)
                scurve_th0 = None
                thr2D_th15, sig2D_th15, chi2ndf2D_th15 = analysis.fit_scurves_multithread(scurve_th15, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop + 1)), n_injections=n_injections, invert_x=False, progress = progress)
                h5_file.create_carray(chip_group, name='HistSCurve_th15', obj=scurve_th15)
                h5_file.create_carray(chip_group, name='ThresholdMap_th15', obj=thr2D_th15.T)
                scurve_th15 = None

                # Put the threshold distribution based on the fit results in two histograms
                self.logger.info('Get the cumulated global threshold distributions...')
                hist_th0  = analysis.vth_hist(thr2D_th0, Vthreshold_stop)
                hist_th15 = analysis.vth_hist(thr2D_th15, Vthreshold_stop)

                # Use the threshold histograms and one threshold distribution to calculate the equalisation
                self.logger.info('Calculate the equalisation matrix...')
                eq_matrix = analysis.eq_matrix(hist_th0, hist_th15, thr2D_th0, Vthreshold_start, Vthreshold_stop)
                h5_file.create_carray(chip_group, name='EqualisationMap', obj=eq_matrix)

                # Don't mask any pixels in the mask file
                mask_matrix = np.zeros((256, 256), dtype=bool)
                mask_matrix[:, :] = 0

                # Write the equalisation matrix to a new HDF5 file
                #self.save_thr_mask(eq_matrix, chip_wafer, chip_x ,chip_y)
                self.save_thr_mask(eq_matrix, chipID[:3], chipID[4], chipID[5])
                if result_path != None:
                    result_path.put(self.thrfile)

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
                Vthreshold_start = int(p.run_config[b'Vthreshold_start'])
                Vthreshold_stop = int(p.run_config[b'Vthreshold_stop'])
                n_injections = int(p.run_config[b'n_injections'])

                # Plot a page with all parameters
                p.plot_parameter_page()

                mask = h5_file.root.configuration.mask_matrix[:].T

                for chip in range(self.num_of_chips):
                    # get chipID of current chip
                    chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                    print(chip, chipID)

                    # get group for current chip
                    chip_group  = h5_file.root.interpreted._f_get_child(chipID)

                    # Plot the S-Curve histogram
                    scurve_th0_hist = chip_group.HistSCurve_th0[:].T
                    max_occ = n_injections * 5
                    p.plot_scurves(scurve_th0_hist, list(range(Vthreshold_start, Vthreshold_stop)), chipID, scan_parameter_name="Vthreshold", title='SCurves - PixelDAC 0', max_occ=max_occ, plot_queue=plot_queue)

                    # Plot the threshold distribution based on the S-Curve fits
                    hist_th0 = np.ma.masked_array(chip_group.ThresholdMap_th0[:], mask)
                    p.plot_distribution(hist_th0, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution - PixelDAC 0, chip %s' %chipID, suffix='threshold_distribution_th0', plot_queue=plot_queue)

                    # Plot the S-Curve histogram
                    scurve_th15_hist = chip_group.HistSCurve_th15[:].T
                    max_occ = n_injections * 5
                    p.plot_scurves(scurve_th15_hist, list(range(Vthreshold_start, Vthreshold_stop)), chipID, scan_parameter_name="Vthreshold", title='SCurves - PixelDAC 15', max_occ=max_occ, plot_queue=plot_queue)

                    # Plot the threshold distribution based on the S-Curve fits
                    hist_th15 = np.ma.masked_array(chip_group.ThresholdMap_th15[:], mask)
                    p.plot_distribution(hist_th15, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution - PixelDAC 15, chip %s' %chipID, suffix='threshold_distribution_th15', plot_queue=plot_queue)

                    # Plot the occupancy matrix
                    eq_masked = np.ma.masked_array(chip_group.EqualisationMap[:].T, mask)
                    p.plot_occupancy(eq_masked, title='Equalisation Map, chip %s' %chipID, z_max='median', z_label='PixelDAC', suffix='equalisation', plot_queue=plot_queue)

                    # Plot the equalisation bits histograms
                    p.plot_distribution(eq_masked, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution, chip %s' %chipID, x_axis_title='Pixel threshold', y_axis_title='# of hits', suffix='pixel_threshold_distribution', plot_queue=plot_queue)


if __name__ == "__main__":
    scan = EqualisationCharge()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()