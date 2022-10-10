#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script scans over different thresholds and counts the active pixels based on noise
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
    'Vthreshold_start' : 1335,
    'Vthreshold_stop'  : 1700,
    #'thrfile'        : './output_data/equal_?.h5'
}


class NoiseScan(ScanBase):

    scan_id      = "NoiseScan"
    wafer_number = 0
    y_position   = 0
    x_position   = 'A'

    def scan(self, Vthreshold_start=0, Vthreshold_stop=2911, shutter=0.01, progress = None, status = None, **kwargs):
        '''
            Takes data for threshold scan in a range of thresholds.
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

        # Disable test pulses, set the mode to ToT/ToA and write the configuration to the Timepix3
        # Every object needs the same configurations for correct analysis right now
        for chip in self.chips:
            chip._configs["TP_en"] = 0

        # Set general configuration registers of the Timepix3
        self.chips[0].write_general_config()
        for chip in self.chips[1:]:
            self.chips[0].write(chip.write_general_config(write=False))

        self.logger.info('Preparing injection masks...')
        if status != None:
            status.put("Preparing injection masks")

        mask_step = 1
        if self.chip_links == 8:
            mask_step = 1
        elif self.chip_links < 8 and self.chip_links >= 4:
            mask_step = 2
        elif self.chip_links < 4 and self.chip_links >= 2:
            mask_step = 4
        else:
            mask_step = 8

        # Create the masks for all steps
        mask_cmds = self.create_noise_scan_masks(mask_step)

        # Start the scan
        self.logger.info('Starting scan...')
        if status != None:
            status.put("Starting scan")
        if status != None:
            status.put("iteration_symbol")
        thresholds = utils.create_threshold_list(utils.get_coarse_jumps(Vthreshold_start, Vthreshold_stop))
        #print('Thresholds: ' + str(thresholds))

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds) * len(thresholds))
        else:
            # Initialize counter for progress
            step_counter = 0

        scan_param_id = 0
        for threshold in thresholds:
            # Set the threshold
            for chip in self.chips[1:]:
                self.chips[0].write(chip.set_dac("Vthreshold_coarse", int(threshold[0]), write=False))
                self.chips[0].write(chip.set_dac("Vthreshold_fine", int(threshold[1]), write=False))

            for mask_step_cmd in mask_cmds:
                # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
                self.chips[0].write(mask_step_cmd)

                with self.readout(scan_param_id=scan_param_id):
                    time.sleep(0.001)

                    # Open the shutter, take data and update the progress bar
                    with self.shutter():
                        time.sleep(shutter)
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
                        time.sleep(0.025)
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
            # Read raw data, meta data and configuration parameters
            raw_data       = h5_file.root.raw_data[:]
            meta_data      = h5_file.root.meta_data[:]
            run_config     = h5_file.root.configuration.run_config
            general_config = h5_file.root.configuration.generalConfig
            # op_mode and vco should be the same for all chips for the same scan
            op_mode        = general_config.col('Op_mode')[0]
            vco            = general_config.col('Fast_Io_en')[0]
            
            # 'Simulate' more chips
            #chip_IDs_new = [b'W12-C7',b'W12-C7',b'W13-D8',b'W13-D8',b'W14-E9', b'W14-E9',b'W15-C5', b'W15-C5']
            #for new_Id in range(8):
            #    h5_file.root.configuration.links.cols.chip_id[new_Id] = chip_IDs_new[new_Id]

            #chip_IDs_links = link_config['chip_id']

            # Get link configuration
            #link_config = h5_file.root.configuration.links[:]
            #chip_IDs    = link_config['chip_id']

            # Create dictionary of chips and the links they are connected to
            #self.chip_links = {}
            #self.chip_links = chip_link
            #for link, ID in enumerate(chip_IDs):
            #    if ID not in self.chip_links:
            #        self.chip_links[ID] = [link]
            #    else:
            #        self.chip_links[ID].append(link)
            
            pix_occ  = []
            hist_occ = []

            # Create a group to save all data and histograms to the HDF file
            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

            self.logger.info('Interpret raw data...')
            # Interpret the raw data (2x 32 bit to 1x 48 bit)
            hit_data = analysis.interpret_raw_data(raw_data, op_mode, vco, kwargs['chip_link'], meta_data, progress = progress)
            raw_data = None

            param_range = np.unique(meta_data['scan_param_id'])
            
            # Read needed configuration parameters
            # Vthreshold_start and Vthreshold_stop should be the same for all chips
            Vthreshold_start = run_config.col('Vthreshold_start')[0]
            Vthreshold_stop  = run_config.col('Vthreshold_stop')[0]

            # for now create tables and histograms for each chip
            # for chip in range(self.num_of_chips):
            for chip in self.chips[1:]:
                # Get the index of current chip in regards to the chip_links dictionary. This is the index, where
                # the hit_data of the chip is.
                # chip_num = [number for number, ID in enumerate(self.chip_links) if ID.decode()==chip.chipId_decoded][0]
                chip_num = [number for number, ID in enumerate(kwargs['chip_link']) if ID == chip.chipId_decoded][0]
                
                # Get chipID in desirable formatting for HDF5 files (without '-')
                # chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                chipID = f'W{chip.wafer_number}_{chip.x_position}{chip.y_position}'

                # Create group for current chip
                h5_file.create_group(h5_file.root.interpreted, name = chipID)
                # Get the group as an object
                chip_group = h5_file.root.interpreted._f_get_child(chipID)

                # Select only data which is hit data
                hit_data_chip = hit_data[chip_num][hit_data[chip_num]['data_header'] == 1]
                
                h5_file.create_table(chip_group, 'hit_data', hit_data_chip, filters=tb.Filters(complib='zlib', complevel=5))
                pix_occ  = np.bincount(hit_data_chip['x'] * 256 + hit_data_chip['y'], minlength=256 * 256).astype(np.uint32)
                hist_occ = np.reshape(pix_occ, (256, 256)).T
                h5_file.create_carray(chip_group, name='HistOcc', obj=hist_occ)

                #meta_data   = None
                pix_occ     = None
                hist_occ    = None

                # Create histograms for number of active pixels and number of hits for individual thresholds
                noise_curve_pixel, noise_curve_hits = analysis.noise_pixel_count(hit_data_chip, param_range, Vthreshold_start)
                h5_file.create_carray(chip_group, name='NoiseCurvePixel', obj=noise_curve_pixel)
                h5_file.create_carray(chip_group, name='NoiseCurveHits', obj=noise_curve_hits)

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
                Vthreshold_start = p.run_config['Vthreshold_start'][0]
                Vthreshold_stop  = p.run_config['Vthreshold_stop'][0]
                
                # Plot a page with all parameters
                p.plot_parameter_page()

                #for chip in range(self.num_of_chips):
                for chip in self.chips[1:]:
                    # Get chipID in desirable formatting for HDF5 files (with '_' instead of '-')
                    #chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                    chipID = f'W{chip.wafer_number}_{chip.x_position}{chip.y_position}'
                    # Get the group of the chip in the HDF5-file
                    chip_group  = h5_file.root.interpreted._f_get_child(chipID)
                    
                    # Plot the equalisation bits histograms
                    thr_matrix_call = eval(f'h5_file.root.configuration.thr_matrix_{chipID}[:]')
                    thr_matrix = thr_matrix_call
                    p.plot_distribution(thr_matrix, chipID, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution', x_axis_title='Pixel threshold', y_axis_title='# of hits', suffix='pixel_threshold_distribution', plot_queue=plot_queue)
                
                    # Plot noise pixels histogram
                    noise_curve_pixel = chip_group.NoiseCurvePixel[:]
                    p._plot_1d_hist(noise_curve_pixel, chipID, plot_range = list(range(Vthreshold_start, Vthreshold_stop+1)), title='Noise pixel per threshold', suffix='noise_pixel_per_threshold', x_axis_title='Threshold', y_axis_title='Number of active pixels', log_y=True, plot_queue=plot_queue)

                    # Plot noise hits histogram
                    noise_curve_hits = chip_group.NoiseCurveHits[:]
                    p._plot_1d_hist(noise_curve_hits, chipID, plot_range = list(range(Vthreshold_start, Vthreshold_stop+1)), title='Noise hits per threshold', suffix='noise_pixel_per_threshold', x_axis_title='Threshold', y_axis_title='Total number of hits', log_y=True, plot_queue=plot_queue)


if __name__ == "__main__":
    scan = NoiseScan()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
