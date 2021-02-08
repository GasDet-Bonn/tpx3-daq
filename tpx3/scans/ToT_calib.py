#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script scans over different amounts of injected charge
    to find the corresponding number of ToT clock cycles
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
    'mask_step'        : 64,
    'VTP_fine_start'   : 210 + 0,
    'VTP_fine_stop'    : 210 + 300,
    'thrfile'        : './output_data/20200505_165149_mask.h5'
}


class ToTCalib(ScanBase):

    scan_id = "ToT_calib"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self, VTP_fine_start=210, VTP_fine_stop=511, mask_step=64, tp_period = 1, progress = None, status = None, **kwargs):
        '''
            Takes data for the ToT calibration in a range of testpulses
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
        if mask_step not in {4, 16, 64, 256}:
            raise ValueError("Value {} for mask_step is not in the allowed range (4, 16, 64, 256)".format(mask_step))

        # Set general configuration registers of the Timepix3
        self.chip.write_general_config()

        # Write to the test pulse registers of the Timepix3
        # Write to period and phase tp registers
        # If TP_Period is to short there is not enough time for discharging the capacitor
        # This effect becomes stronger if the Ikurm DAC is small
        data = self.chip.write_tp_period(tp_period, 0)

        # Write to pulse number tp register - only inject once per pixel
        self.chip.write_tp_pulsenumber(1)

        self.logger.info('Preparing injection masks...')
        if status != None:
            status.put("Preparing injection masks")

        # Create the masks for all steps
        mask_cmds = self.create_scan_masks(mask_step, progress = progress)

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
            # Initailize counter for progress
            step_counter = 0

        for scan_param_id, vcal in enumerate(cal_high_range):
            # Set the fine testpulse DAC
            self.chip.set_dac("VTP_fine", vcal)
            time.sleep(0.01)

            with self.readout(scan_param_id=scan_param_id):
                if status != None:
                    status.put("Scan iteration {} of {}".format(scan_param_id + 1, len(cal_high_range)))
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
                    time.sleep(0.01)
                time.sleep(0.01)

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

        # Open the HDF5 which contains all data of the calibration
        with tb.open_file(h5_filename, 'r+') as h5_file:
            # Read raw data, meta data and configuration parameters
            raw_data = h5_file.root.raw_data[:]
            meta_data = h5_file.root.meta_data[:]
            run_config = h5_file.root.configuration.run_config[:]
            general_config = h5_file.root.configuration.generalConfig[:]
            op_mode = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            vco = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

            # Create group to save all data and histograms to the HDF file
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

            # Create histograms for number of detected ToT clock cycles for individual testpulses
            totcurve = analysis.totcurve_hist(hit_data, param_range)
            hit_data = None

            # Read needed configuration parameters
            VTP_fine_start = [int(item[1]) for item in run_config if item[0] == b'VTP_fine_start'][0]
            VTP_fine_stop = [int(item[1]) for item in run_config if item[0] == b'VTP_fine_stop'][0]

            # Fit ToT-Curves to the histogramms for all pixels
            param_range = list(range(VTP_fine_start, VTP_fine_stop))
            a2D, b2D, c2D, t2D, chi2ndf2D = analysis.fit_totcurves_multithread(totcurve, scan_param_range=param_range, progress = progress)

            h5_file.create_carray(h5_file.root.interpreted, name='HistToTCurve', obj=totcurve)
            h5_file.create_carray(h5_file.root.interpreted, name='Chi2Map', obj=chi2ndf2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='aMap', obj=a2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='bMap', obj=b2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='cMap', obj=c2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='tMap', obj=t2D.T)

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
                VTP_fine_start = int(p.run_config[b'VTP_fine_start'])
                VTP_fine_stop = int(p.run_config[b'VTP_fine_stop'])
                VTP_coarse = int(p.dacs[b'VTP_coarse'])

                # Plot a page with all parameters
                p.plot_parameter_page()

                mask = h5_file.root.configuration.mask_matrix[:]

                # Plot the occupancy matrix
                occ_masked = np.ma.masked_array(h5_file.root.interpreted.HistOcc[:], mask)
                p.plot_occupancy(occ_masked, title='Integrated Occupancy', z_max='maximum', suffix='occupancy')

                # Plot the equalisation bits histograms
                thr_matrix = h5_file.root.configuration.thr_matrix[:],
                p.plot_distribution(thr_matrix, plot_range=np.arange(-0.5, 16.5, 1), title='TDAC distribution', x_axis_title='TDAC', y_axis_title='# of hits', suffix='tdac_distribution', plot_queue=plot_queue)

                # Plot the ToT-Curve histogram
                ToT_hist = h5_file.root.interpreted.HistToTCurve[:].T
                p.plot_scurves(ToT_hist, list(range(VTP_fine_start, VTP_fine_stop)), electron_axis=False, scan_parameter_name="VTP_fine", max_occ=250, ylabel='ToT Clock Cycles', title='ToT curves', plot_queue=plot_queue)

                # Plot the ToT-Curve fit parameter a histogram
                hist = np.ma.masked_array(h5_file.root.interpreted.aMap[:], mask)
                p.plot_distribution(hist, plot_range=np.arange(0, 20, 0.1), x_axis_title='a', title='a distribution', suffix='a_distribution', plot_queue=plot_queue)

                # Plot the ToT-Curve fit parameter b histogram
                hist = np.ma.masked_array(h5_file.root.interpreted.bMap[:], mask)
                p.plot_distribution(hist, plot_range=list(range(-5000, 0, 100)), x_axis_title='b', title='b distribution', suffix='b_distribution', plot_queue=plot_queue)

                # Plot the ToT-Curve fit parameter c histogram
                hist = np.ma.masked_array(h5_file.root.interpreted.cMap[:], mask)
                p.plot_distribution(hist, plot_range=list(range(-10000, 0000, 200)), x_axis_title='c', title='c distribution', suffix='c_distribution', plot_queue=plot_queue)

                # Plot the ToT-Curve fit parameter t histogram
                hist = np.ma.masked_array(h5_file.root.interpreted.tMap[:], mask)
                p.plot_distribution(hist, plot_range=list(range(200, 300, 2)), x_axis_title='t', title='t distribution', suffix='t_distribution', plot_queue=plot_queue)
                


if __name__ == "__main__":
    scan = ToTCalib()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()