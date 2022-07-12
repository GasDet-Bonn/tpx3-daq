#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script scans over different amounts of injected charge
    to find the effective threshold of the enabled pixels.
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
from six.moves import range

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'VTP_fine_start'   : 256 + 0,
    'VTP_fine_stop'    : 256 + 140,
    'n_injections'     : 100,
    #'thrfile'        : './output_data/?_mask.h5'
}


class TestpulseScan(ScanBase):

    scan_id      = "TestpulseScan"
    wafer_number = 0
    y_position   = 0
    x_position   = 'A'

    def scan(self, VTP_fine_start = 100, VTP_fine_stop = 200, n_injections = 100, tp_period = 1, mask_step = 16, progress = None, status = None, **kwargs):
        '''
            Takes data for testpulse scan over a range of testpulses with a defined number of pulses per iteration
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
        '''

        # Check if parameters are valid before starting the scan
        if VTP_fine_start < 0 or VTP_fine_start > 511:
            raise ValueError("Value {} for VTP_fine_start is not in the allowed range (0-511)".format(VTP_fine_start))
        if VTP_fine_stop < 0 or VTP_fine_stop > 511:
            raise ValueError("Value {} for VTP_fine_stop is not in the allowed range (0-511)".format(VTP_fine_stop))
        if VTP_fine_stop <= VTP_fine_start:
            raise ValueError("Value for VTP_fine_stop must be bigger than value for VTP_fine_start")
        if n_injections < 1 or n_injections > 65535:
            raise ValueError("Value {} for n_injections is not in the allowed range (1-65535)".format(n_injections))
        if mask_step not in {4, 16, 64, 256}:
            raise ValueError("Value {} for mask_step is not in the allowed range (4, 16, 64, 256)".format(mask_step))

        # Set general configuration registers of the Timepix3
        #self.chips[0].write_general_config()
        for chip in self.chips[1:]:
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

        # Get the shutter sleep time
        sleep_time = self.get_shutter_sleep_time(tp_period = tp_period, n_injections = n_injections)

        # Start the scan
        self.logger.info('Starting scan...')
        if status != None:
            status.put("Starting scan")
        if status != None:
            status.put("iteration_symbol")
        cal_high_range = list(range(VTP_fine_start, VTP_fine_stop, 1))

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))
        else:
            # Initialize counter for progress
            step_counter = 0

        scan_param_id = 0
        for vcal in cal_high_range:
            # Set the fine testpulse DAC
            for chip in self.chips[1:]:
                self.chips[0].write(chip.set_dac("VTP_fine", vcal, write=False))

            with self.readout(scan_param_id=scan_param_id):
                step = 0
                for mask_step_cmd in mask_cmds:
                    # Only activate testpulses for columns with active pixels
                    for chip in self.chips[1:]:
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
                            fraction = step_counter / (len(mask_cmds) * len(cal_high_range))
                            progress.put(fraction)
                    for chip in self.chips[1:]:
                        self.chips[0].write(chip.stop_readout(write=False))
                        time.sleep(0.001)
                    step += 1
                for chip in self.chips[1:]:
                    self.chips[0].write(chip.reset_sequential(write=False))
                    time.sleep(0.001)
            scan_param_id +=1

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
            # Read raw data, meta data and configuration parameters
            raw_data        = h5_file.root.raw_data[:]
            meta_data       = h5_file.root.meta_data[:]
            run_config      = h5_file.root.configuration.run_config[:]
            general_config  = h5_file.root.configuration.generalConfig[:]
            op_mode         = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            vco             = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

            # 'Simulate' more chips
            #chip_IDs_new = [b'W12-C7',b'W12-C7',b'W13-D8',b'W13-D8',b'W14-E9', b'W14-E9',b'W15-C5', b'W15-C5']
            #for new_Id in range(8):
            #    h5_file.root.configuration.links.cols.chip_id[new_Id] = chip_IDs_new[new_Id]
            #print(h5_file.root.configuration.links[:]['chip_id'])
            #print(h5_file.root.configuration.links)

            #chip_IDs_links = link_config['chip_id']

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
            print(self.chip_links)

            # Sanity check
            link_number = 3
            for link, chipID in enumerate(self.chip_links):
                if link_number in self.chip_links[chipID]:
                    print(link, chipID)

            # Get the number of chips
            self.num_of_chips = len(self.chip_links)

            # Create a group to save all data and histograms to the HDF file
            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

            self.logger.info('Interpret raw data...')
            # Interpret the raw data (2x 32 bit to 1x 48 bit)
            hit_data = analysis.interpret_raw_data(raw_data, op_mode, vco, self.chip_links, meta_data, progress = progress)
            raw_data = None
            #param_range   = np.unique(meta_data['scan_param_id'])
            # Read needed configuration parameters
            n_injections    = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]
            VTP_fine_start  = [int(item[1]) for item in run_config if item[0] == b'VTP_fine_start'][0]
            VTP_fine_stop   = [int(item[1]) for item in run_config if item[0] == b'VTP_fine_stop'][0]
                
            for chip in range(self.num_of_chips):
                
                # Get current chipID
                chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                print(chipID)
                #chip_ID_format = chipID[:3] +str('_') + chipID[-2:]

                # Create group for current chip
                h5_file.create_group(h5_file.root.interpreted, name=chipID)

                # Get current group
                chip_group = h5_file.root.interpreted._f_get_child(chipID)

                # Select only data which is hit data
                hit_data_chip = hit_data[chip][hit_data[chip]['data_header'] == 1]
                h5_file.create_table(chip_group, 'hit_data', hit_data_chip, filters=tb.Filters(complib='zlib', complevel=5))
                pix_occ       = np.bincount(hit_data_chip['x'] * 256 + hit_data_chip['y'], minlength=256 * 256).astype(np.uint32)
                hist_occ      = np.reshape(pix_occ, (256, 256)).T
                h5_file.create_carray(chip_group, name='HistOcc', obj=hist_occ)
                param_range   = np.unique(meta_data['scan_param_id'])
                #meta_data     = None
                pix_occ       = None
                hist_occ      = None

                # Create histograms for number of detected hits for individual testpulses
                scurve      = analysis.scurve_hist(hit_data_chip, param_range)
                #hit_data    = None

                # Read needed configuration parameters
                #n_injections    = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]
                #VTP_fine_start  = [int(item[1]) for item in run_config if item[0] == b'VTP_fine_start'][0]
                #VTP_fine_stop   = [int(item[1]) for item in run_config if item[0] == b'VTP_fine_stop'][0]

                # Fit S-Curves to the histograms for all pixels
                param_range             = list(range(VTP_fine_start, VTP_fine_stop))
                thr2D, sig2D, chi2ndf2D = analysis.fit_scurves_multithread(scurve, scan_param_range=param_range, n_injections=n_injections, progress = progress, invert_x=False)

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
            with plotting.Plotting(h5_filename) as p:

                # Read needed configuration parameters
                VTP_fine_start  = int(p.run_config[b'VTP_fine_start'])
                VTP_fine_stop   = int(p.run_config[b'VTP_fine_stop'])
                n_injections    = int(p.run_config[b'n_injections'])

                # Plot a page with all parameters
                p.plot_parameter_page()

                # Plot the equalisation bits histograms
                thr_matrix = h5_file.root.configuration.thr_matrix[:],
                p.plot_distribution(thr_matrix, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution', x_axis_title='Pixel threshold', y_axis_title='# of hits', suffix='pixel_threshold_distribution', plot_queue=plot_queue)

                #mask_scurve = h5_file.root.configuration.mask_matrix[:].T

                for chip in range(self.num_of_chips):

                    # Get current chipID
                    chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                    print(chipID)

                    # Get group for current chip
                    chip_group = h5_file.root.interpreted._f_get_child(chipID)
                    # TODO: Maybe we get different masks for different chips
                    mask = h5_file.root.configuration.mask_matrix[:].T

                    # Plot the occupancy matrix
                    occ_masked  = np.ma.masked_array(chip_group.HistOcc[:], mask)
                    p.plot_occupancy(occ_masked, title='Integrated Occupancy, chip %s' %chipID, z_max='median', suffix='occupancy', plot_queue=plot_queue)

                    # Plot the S-Curve histogram, put title for plot
                    scurve_hist = chip_group.HistSCurve[:].T
                    max_occ     = n_injections + 10
                    p.plot_scurves(scurve_hist, list(range(VTP_fine_start, VTP_fine_stop)), chipID, scan_parameter_name="VTP_fine", max_occ=max_occ, plot_queue=plot_queue)

                    # Do not plot pixels with converged S-Curve fits, Chi2Map together with ThresholdMap
                    chi2_sel        = chip_group.Chi2Map[:] > 0.
                    mask[~chi2_sel] = True

                    # Plot the threshold distribution based on the S-Curve fits
                    hist    = np.ma.masked_array(chip_group.ThresholdMap[:], mask)
                    p.plot_distribution(hist, plot_range=np.arange(VTP_fine_start-0.5, VTP_fine_stop-0.5, 1), x_axis_title='VTP_fine', title='Threshold distribution, chip %s' %chipID, suffix='threshold_distribution', plot_queue=plot_queue)

                    # Plot the occupancy
                    p.plot_occupancy(hist, z_label='Threshold', title='Threshold, chip %s' %chipID, show_sum=False, suffix='threshold_map', z_min=VTP_fine_start, z_max=VTP_fine_stop, plot_queue=plot_queue)

                    # Plot the noise map
                    hist    = np.ma.masked_array(chip_group.NoiseMap[:], mask)
                    p.plot_distribution(hist, plot_range=np.arange(0.1, 4, 0.1), title='Noise distribution, chip %s' %chipID, suffix='noise_distribution', plot_queue=plot_queue)
                    p.plot_occupancy(hist, z_label='Noise', title='Noise, chip %s' %chipID, show_sum=False, suffix='noise_map', z_min=0.1, z_max=4.0, plot_queue=plot_queue)


if __name__ == "__main__":
    scan = TestpulseScan()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()