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

    scan_id      = "ToTCalib"
    wafer_number = 0
    y_position   = 0
    x_position   = 'A'

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

        for chip in self.chips[1:]:
            # Set general configuration registers of the Timepix3
            self.chips[0].write(chip.write_general_config(write=False))

            # Write to the test pulse registers of the Timepix3
            # Write to period and phase tp registers
            # If TP_Period is to short there is not enough time for discharging the capacitor
            # This effect becomes stronger if the Ikurm DAC is small
            self.chips[0].write(chip.write_tp_period(tp_period, 0, write=False))

            # Write to pulse number tp register - only inject once per pixel
            self.chips[0].write(chip.write_tp_pulsenumber(1, write=False))

        self.logger.info('Preparing injection masks...')
        if status != None:
            status.put("Preparing injection masks")

        # Create the masks for all steps
        mask_cmds = self.create_scan_masks(mask_step, progress = progress, append_datadriven = False)

        # Get the shutter sleep time
        sleep_time = self.get_shutter_sleep_time(tp_period = tp_period, n_injections = 1, TOT = True)

        # Start the scan
        self.logger.info('Starting scan...')
        if status != None:
            status.put("Starting scan")
        if status != None:
            status.put("iteration_symbol")
        cal_high_range = list(range(VTP_fine_start, VTP_fine_stop+1, 1))

        if progress == None:
            # Initialize progress bar
            pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))
        else:
            # Initialize counter for progress
            step_counter = 0

        scan_param_id = 0
        for vcal in cal_high_range:
            for chip in self.chips[1:]:
                # Set the fine testpulse DAC
                self.chips[0].write(chip.set_dac("VTP_fine", vcal, write=False))

            with self.readout(scan_param_id=scan_param_id):
                step = 0
                for mask_step_cmd in mask_cmds:
                    for chip in self.chips[1:]:
                        # Only activate testpulses for columns with active pixels
                        self.chips[0].write(chip.write_ctpr(list(range(step//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))), write=False))

                    # Write the pixel matrix for the current step plus the read_pixel_matrix_datadriven command
                    self.chips[0].write(mask_step_cmd)

                    for pulse in range(10):
                        # Open the shutter, take data and update the progress bar
                        for chip in self.chips[1:]:
                            self.chips[0].write(chip.read_pixel_matrix_datadriven(write=False))
                        with self.shutter():
                            time.sleep(sleep_time)
                        for chip in self.chips[1:]:
                            self.chips[0].write(chip.stop_readout(write=False))
                            self.chips[0].write(chip.reset_sequential(write=False))
                            time.sleep(0.001)
                    if progress == None:
                        # Update the progress bar
                        pbar.update(1)
                    else:
                        # Update the progress fraction and put it in the queue
                        step_counter += 1
                        fraction      = step_counter / (len(mask_cmds) * len(cal_high_range))
                        progress.put(fraction)
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
            meta_data      = h5_file.root.meta_data[:]
            run_config     = h5_file.root.configuration.run_config
            general_config = h5_file.root.configuration.generalConfig
            op_mode        = general_config.col('Op_mode')[0]
            vco            = general_config.col('Op_mode')[0]

            # 'Simulate' more chips
            #chip_IDs_new = [b'W18-K7',b'W18-K7',b'W18-K7',b'W18-K7',b'W18-K7', b'W18-K7',b'W18-K7', b'W18-K7']
            #for new_Id in range(8):
            #    h5_file.root.configuration.links.cols.chip_id[new_Id] = chip_IDs_new[new_Id]

            # Get link configuration
            #link_config = h5_file.root.configuration.links[:]
            #print(link_config)
            #chip_IDs    = link_config['chip_id']

            # Create dictionary of Chips and the links they are connected to
            #self.chip_links = {}
    
            #for link, ID in enumerate(chip_IDs):
            #    if ID not in self.chip_links:
            #        self.chip_links[ID] = [link]
            #    else:
            #        self.chip_links[ID].append(link)
            #print('Chip links: ' + str(self.chip_links))

            # Get the number of chips
            #self.num_of_chips = len(self.chip_links)
            #self.num_of_chips = len(self.chips[1:])
            # Create group to save all data and histograms to the HDF file
            try:
                h5_file.remove_node(h5_file.root.interpreted, recursive=True)
            except:
                pass

            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

            self.logger.info('Interpret raw data...')
            param_range = np.unique(meta_data['scan_param_id'])

            # Create arrays for interpreted data for all scan parameter IDs
            totcurves_means = np.zeros((self.num_of_chips, 256*256, len(param_range)), dtype=np.uint16)
            totcurves_hits  = np.zeros((self.num_of_chips, 256*256, len(param_range)), dtype=np.uint16)

            if progress == None:
                pbar = tqdm(total = len(param_range))
            else:
                step_counter = 0

            # Interpret data separately per scan parameter id to save RAM
            for param_id in param_range:
                start_index  = meta_data[meta_data['scan_param_id'] == param_id]
                stop_index   = meta_data[meta_data['scan_param_id'] == param_id]
                # Interpret the raw data (2x 32 bit to 1x 48 bit)
                raw_data_tmp = h5_file.root.raw_data[start_index['index_start'][0]:stop_index['index_stop'][-1]]
                hit_data_tmp = analysis.interpret_raw_data(raw_data_tmp, op_mode, vco, kwargs['chip_link'], progress = progress)

                #for chip in range(self.num_of_chips):
                for chip in self.chips[1:]:
                    # Get the index of current chip in regards to the chip_links dictionary. This is the index, where
                    # the hit_data of the chip is.
                    chip_num = [number for number, ID in enumerate(kwargs['chip_link']) if ID==chip.chipId_decoded][0]

                    # Select only data which is hit data
                    hit_data_chip = hit_data_tmp[chip_num][hit_data_tmp[chip_num]['data_header'] == 1]

                    # Create histograms for number of detected ToT clock cycles for individual testpulses
                    full_tmp, count_tmp = analysis.totcurve_hist(hit_data_chip)

                    # Put results of current scan parameter ID in overall arrays
                    totcurves_means[chip_num][:, param_id] = full_tmp
                    full_tmp                               = None
                    totcurves_hits[chip_num][:, param_id]  = count_tmp
                    count_tmp                              = None
                    hit_data_chip                          = None
                
                raw_data_tmp = None
                hit_data_tmp = None

                if progress == None:
                    pbar.update(1)
                else:
                    step_counter += 1
                    fraction      = step_counter / (len(param_range))
                    progress.put(fraction)

            if progress == None:
                pbar.close()

            meta_data = None

            #for chip in range(self.num_of_chips):
            for chip in self.chips[1:]:
                # Get the index of current chip in regards to the chip_links dictionary. This is the index, where
                # the hit_data of the chip is.
                chip_num = [number for number, ID in enumerate(kwargs['chip_link']) if ID==chip.chipId_decoded][0]
                # Get chipID in desirable formatting for HDF5 files (without '-')
                #chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                chipID = f'W{chip.wafer_number}_{chip.x_position}{chip.y_position}'
                
                # create group for current chip
                h5_file.create_group(h5_file.root.interpreted, name=chipID)

                # get group for current chip
                chip_group  = h5_file.root.interpreted._f_get_child(chipID)

                # Calculate the mean ToT per pixel per 110 injections
                totcurve = np.divide(totcurves_means[chip_num], 10, where = totcurves_hits[chip_num] > 0)
                totcurve = np.nan_to_num(totcurve)
                
                # Only use pixel which saw at least all pulses
                # Additional pulses are not part of the ToT sum (see analysis.totcurve_hist())
                totcurve[totcurves_hits[chip_num] < 10] = 0

                # Read needed configuration parameters
                VTP_fine_start = run_config.col('VTP_fine_start')[0]
                VTP_fine_stop  = run_config.col('VTP_fine_stop')[0]

                # Fit ToT-Curves to the histograms for all pixels
                param_range = list(range(VTP_fine_start, VTP_fine_stop+1))
                
                h5_file.create_carray(chip_group, name='HistToTCurve', obj=totcurve)
                h5_file.create_carray(chip_group, name='HistToTCurve_Full', obj=totcurves_means[chip_num])
                h5_file.create_carray(chip_group, name='HistToTCurve_Count', obj=totcurves_hits[chip_num])
                
                mean, popt, pcov = analysis.fit_totcurves_mean(totcurve, scan_param_range=param_range, progress = progress)

                totcurve = None

                h5_file.create_table(chip_group, 'mean_curve', mean)

                data_type = {'names': ['param', 'value', 'stddev'],
                            'formats': ['S1', 'float32', 'float32']}

                parameter_table           = np.recarray(4, dtype=data_type)
                parameter_table['param']  = ['a', 'b', 'c', 't']
                parameter_table['value']  = [popt[0], popt[1], popt[2], popt[3]]
                parameter_table['stddev'] = [np.sqrt(pcov[0][0]), np.sqrt(pcov[1][1]), np.sqrt(pcov[2][2]), np.sqrt(pcov[3][3])]

                h5_file.create_table(chip_group, 'fit_params', parameter_table)


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
                VTP_fine_start = p.run_config['VTP_fine_start'][0]
                VTP_fine_stop  = p.run_config['VTP_fine_stop'][0]
                VTP_coarse     = p.dacs['VTP_coarse'][0]

                # Plot a page with all parameters
                p.plot_parameter_page()

                #for chip in range(self.num_of_chips):
                for chip in self.chips[1:]:
                    # Get chipID in desirable formatting for HDF5 files (without '-')
                    #chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
                    chipID = f'W{chip.wafer_number}_{chip.x_position}{chip.y_position}'

                    # get group for current chip
                    chip_group = h5_file.root.interpreted._f_get_child(chipID)

                    # Plot the equalisation bits histograms
                    thr_matrix = eval(f'h5_file.root.configuration.thr_matrix_{chipID}[:]')
                    p.plot_distribution(thr_matrix, chipID, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution', x_axis_title='Pixel threshold', y_axis_title='# of hits', suffix='pixel_threshold_distribution', plot_queue=plot_queue)

                    # Plot the Hit-Curve histogram
                    ToT_hit_hist = chip_group.HistToTCurve_Count[:].T
                    p.plot_scurves(ToT_hit_hist.astype(int), chipID, list(range(VTP_fine_start, VTP_fine_stop+1)), electron_axis=False, scan_parameter_name="VTP_fine", max_occ=50, ylabel='Hits per pixel', title='Hit curves', plot_queue=plot_queue)
                    
                    # Plot the ToT-Curve histogram
                    ToT_hist = chip_group.HistToTCurve[:].T
                    p.plot_scurves(ToT_hist.astype(int), chipID, list(range(VTP_fine_start, VTP_fine_stop+1)), electron_axis=False, scan_parameter_name="VTP_fine", max_occ=250, ylabel='ToT Clock Cycles', title='ToT curves', plot_queue=plot_queue)

                    # Plot the mean ToT-Curve with fit
                    mean = chip_group.mean_curve[:]

                    fit_params = chip_group.fit_params[:]
                    a  = [float(item["value"]) for item in fit_params if item[0] == b'a'][0]
                    ac = [float(item["stddev"]) for item in fit_params if item[0] == b'a'][0]
                    b  = [float(item["value"]) for item in fit_params if item[0] == b'b'][0]
                    bc = [float(item["stddev"]) for item in fit_params if item[0] == b'b'][0]
                    c  = [float(item["value"]) for item in fit_params if item[0] == b'c'][0]
                    cc = [float(item["stddev"]) for item in fit_params if item[0] == b'c'][0]
                    t  = [float(item["value"]) for item in fit_params if item[0] == b't'][0]
                    tc = [float(item["stddev"]) for item in fit_params if item[0] == b't'][0]

                    mean['tot']
                    mean['tot_error']
                    points = np.linspace(t*1.001, len(mean['tot']), 500)
                    fit    = analysis.totcurve(points, a, b, c, t)

                    p.plot_two_functions(chipID, range(len(mean['tot'])), mean['tot'], range(len(mean['tot'])), mean['tot_error'], points, fit, y_plot_range = [0, np.amax(fit[1])], label_1 = 'mean ToT', label_2='fit with \na=(%.2f+/-%.2f), \nb=(%.2f+/-%.2f), \nc=(%.2f+/-%.2f), \nt=(%.2f+/-%.2f)'%(a, ac, b, bc, c, cc, t ,tc), x_axis_title='VTP [2.5 mV]', y_axis_title='ToT Clock Cycles [25 ns]', title='ToT fit', suffix='ToT fit', plot_queue=plot_queue )


if __name__ == "__main__":
    scan = ToTCalib()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()