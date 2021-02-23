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
from six.moves import range

local_configuration = {
    # Scan parameters
    'Vthreshold_start' : 1450,
    'Vthreshold_stop'  : 1700,
    #'thrfile'        : './output_data/equal_?.h5'
}


class NoiseScan(ScanBase):

    scan_id = "noise_scan"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self, Vthreshold_start=0, Vthreshold_stop=2911, progress = None, status = None, **kwargs):
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
        self.chip._configs["TP_en"] = 0
        self.chip.write_general_config()

        # Start the scan
        self.logger.info('Starting scan...')
        if status != None:
            status.put("Starting scan")
        if status != None:
            status.put("iteration_symbol")
        cal_high_range = list(range(Vthreshold_start, Vthreshold_stop, 1))

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(cal_high_range))
        else:
            # Initailize counter for progress
            step_counter = 0

        scan_param_id = 0
        for vcal in cal_high_range:
            # Initialize data-driven readout
            self.chip.read_pixel_matrix_datadriven()

            # Set the threshold
            self.chip.set_threshold(vcal)

            with self.readout(scan_param_id=scan_param_id):
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
                time.sleep(0.001)
            self.chip.reset_sequential()
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
            raw_data = h5_file.root.raw_data[:]
            meta_data = h5_file.root.meta_data[:]
            run_config = h5_file.root.configuration.run_config[:]
            general_config = h5_file.root.configuration.generalConfig[:]
            op_mode = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            vco = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

            # Create a group to save all data and histograms to the HDF file
            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

            self.logger.info('Interpret raw data...')
            # Interpret the raw data (2x 32 bit to 1x 48 bit)
            hit_data = analysis.interpret_raw_data(raw_data, op_mode, vco, meta_data, progress = progress)
            raw_data = None

            # Select only data which is hit data
            hit_data = hit_data[hit_data['data_header'] == 1]
            h5_file.create_table(h5_file.root.interpreted, 'hit_data', hit_data, filters=tb.Filters(complib='zlib', complevel=5))
            pix_occ = np.bincount(hit_data['x'] * 256 + hit_data['y'], minlength=256 * 256).astype(np.uint32)
            hist_occ = np.reshape(pix_occ, (256, 256)).T
            h5_file.create_carray(h5_file.root.interpreted, name='HistOcc', obj=hist_occ)
            param_range = np.unique(meta_data['scan_param_id'])
            meta_data = None
            pix_occ = None
            hist_occ = None

            # Read needed configuration parameters
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
            Vthreshold_stop = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]

            # Create histograms for number of active pixels for individual thresholds
            noise_curve = analysis.noise_pixel_count(hit_data, param_range, Vthreshold_start)
            h5_file.create_carray(h5_file.root.interpreted, name='NoiseCurve', obj=noise_curve)

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

                # Plot a page with all parameters
                p.plot_parameter_page()

                mask = h5_file.root.configuration.mask_matrix[:]

                # Plot the equalisation bits histograms
                thr_matrix = h5_file.root.configuration.thr_matrix[:],
                p.plot_distribution(thr_matrix, plot_range=np.arange(-0.5, 16.5, 1), title='TDAC distribution', x_axis_title='TDAC', y_axis_title='# of hits', suffix='tdac_distribution', plot_queue=plot_queue)

                # Plot the noise pixels histogram
                noise_curve = h5_file.root.interpreted.NoiseCurve[:]
                p._plot_1d_hist(hist = noise_curve, plot_range = list(range(Vthreshold_start, Vthreshold_stop)), x_axis_title='Threshold', y_axis_title='Number of active pixels', plot_queue=plot_queue)


if __name__ == "__main__":
    scan = NoiseScan()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
