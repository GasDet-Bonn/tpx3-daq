from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from http.client import FORBIDDEN
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import math
from scipy.optimize import curve_fit

#from tpx3.scan_base import ScanBase
import analysis as analysis
import plotting as plotting
#import tpx3.utils as utils
#from six.moves import range

def linear(x, a, b):
    return a*x + b

def totcurve(x, a, b, c, t):
    return a*x + b - c / (x-t)

'''
    Analyze the data of the scan
    If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
    If there is a status queue information about the status of the scan are put into it
'''
#h5_filename = self.output_filename + '.h5'
h5_filename = '/home/tpc/Timepix3/scans/hdf/ToTCalib_2023-03-08_21-48-40.h5'
chip_links = {'W18-K7': [0,1,2,3,4,5,6,7]}
'''
# Open the HDF5 which contains all data of the calibration
with tb.open_file(h5_filename, 'r+') as h5_file:
    
    # Read raw data, meta data and configuration parameters
    meta_data      = h5_file.root.meta_data[:]
    run_config     = h5_file.root.configuration.run_config
    general_config = h5_file.root.configuration.generalConfig
    op_mode        = general_config.col('Op_mode')[0]
    vco            = general_config.col('Op_mode')[0]
    
    try:
        h5_file.remove_node(h5_file.root.interpreted, recursive=True)
    except:
        pass
    
    h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

    param_range = np.unique(meta_data['scan_param_id'])

    # Create arrays for interpreted data for all scan parameter IDs
    totcurves_means = np.zeros((1, 256*256, len(param_range)), dtype=np.uint16)
    totcurves_hits  = np.zeros((1, 256*256, len(param_range)), dtype=np.uint16)

    pbar = tqdm(total = len(param_range))
    
    # Interpret data separately per scan parameter id to save RAM
    for param_id in param_range:
        start_index  = meta_data[meta_data['scan_param_id'] == param_id]
        stop_index   = meta_data[meta_data['scan_param_id'] == param_id]
        # Interpret the raw data (2x 32 bit to 1x 48 bit)
        raw_data_tmp = h5_file.root.raw_data[start_index['index_start'][0]:stop_index['index_stop'][-1]]
        hit_data_tmp = analysis.interpret_raw_data(raw_data_tmp, op_mode, vco, chip_links)

        #for chip in range(self.num_of_chips):
        for chip in ['W18-K7']:
            # Get the index of current chip in regards to the chip_links dictionary. This is the index, where
            # the hit_data of the chip is.
            chip_num = [number for number, ID in enumerate(chip_links) if ID==chip][0]

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

        pbar.update(1)
        
    pbar.close()

    meta_data = None
    
    #for chip in range(self.num_of_chips):
    for chip in ['W18-K7']:
        print('... in fitting ...')
        
        # Get the index of current chip in regards to the chip_links dictionary. This is the index, where
        # the hit_data of the chip is.
        #chip_num = [number for number, ID in enumerate(kwargs['chip_link']) if ID==chip.chipId_decoded][0]
        chip_num = 0
        # Get chipID in desirable formatting for HDF5 files (without '-')
        #chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
        #chipID = f'W{chip.wafer_number}_{chip.x_position}{chip.y_position}'
        chipID = 'W18_K7'
                
        # create group for current chip
        h5_file.create_group(h5_file.root.interpreted, name=chipID)

        # get group for current chip
        chip_group  = h5_file.root.interpreted._f_get_child(chipID)

        # Calculate the mean ToT per pixel per 110 injections
        tot_curve = np.divide(totcurves_means[chip_num], 10, where = totcurves_hits[chip_num] > 0)
        tot_curve = np.nan_to_num(tot_curve)
                
        # Only use pixel which saw at least all pulses
        # Additional pulses are not part of the ToT sum (see analysis.totcurve_hist())
        tot_curve[totcurves_hits[chip_num] < 10] = 0

        # Read needed configuration parameters
        VTP_fine_start = run_config.col('VTP_fine_start')[0]
        VTP_fine_stop  = run_config.col('VTP_fine_stop')[0]

        # Fit ToT-Curves to the histograms for all pixels
        param_range = list(range(VTP_fine_start, VTP_fine_stop+1))
                
        h5_file.create_carray(chip_group, name='HistToTCurve', obj=tot_curve)
        h5_file.create_carray(chip_group, name='HistToTCurve_Full', obj=totcurves_means[chip_num])
        h5_file.create_carray(chip_group, name='HistToTCurve_Count', obj=totcurves_hits[chip_num])
                
        #mean, popt, pcov = analysis.fit_totcurves_mean(totcurve, scan_param_range=param_range)

        
        ################################
        """
        Fit the the ToT curves for all pixels simultaneously, by only
        fitting the mean for each VTP_fine slice.
        """
        # Set data with no tot to nan to cut it later
        tot_curve[tot_curve == 0] = np.nan

        # Get mean and standard deviation for non nan data
        totcurve_mean = np.nanmean(tot_curve, axis=0)
        totcurve_std  = np.nanstd(tot_curve, axis=0)

        # Get the start value for t with data close to the start of the curve
        t_est = np.average(np.where((totcurve_mean > 0) & (totcurve_mean <= 5)))

        # Use only pulse height with at least 60% active pixels
        active_pixels                                  = np.count_nonzero(tot_curve > 0, axis=0)
        totcurve_mean[active_pixels < 0.4 * 256 * 256] = 0
        totcurve_std[active_pixels < 0.4 * 256 * 256]  = 0

        # use only data which contains tot data
        x     = np.where(totcurve_mean>0)[0]
        y     = totcurve_mean[totcurve_mean > 0]
        y_err = totcurve_std[totcurve_mean > 0]

        # fit with a linear function to get start values for a and b
        #popt, pcov  = curve_fit(f=linear, xdata=x, ydata=y)
        a           = 1.
        b           = -20.
        ac          = 0
        bc          = 0

        # fit whole function with the complete totcurve-function
        #p0 = [a, b, 200, t_est]
        p0 = [1., -20., 200., 20.]
        try:
            popt, pcov = curve_fit(f=totcurve, xdata=x, ydata=y, sigma = y_err, p0=p0, maxfev= 10000)
        except RuntimeError:  # fit failed
            popt = [a, b, 0, 0]
            pcov = [[pcov[0][0], pcov[0][1], 0, 0], [pcov[1][0], pcov[1][1], 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        except ValueError:  # fit failed
            popt = [a, b, 0, 0]
            pcov = [[pcov[0][0], pcov[0][1], 0, 0], [pcov[1][0], pcov[1][1], 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]

        # prepare data for fit and ToT mean for return
        data_type = {'names': ['tot', 'tot_error'],
                   'formats': ['float32', 'float32']}

        mean              = np.recarray(len(totcurve_mean), dtype=data_type)
        mean['tot']       = totcurve_mean
        mean['tot_error'] = totcurve_std
        ########################
        tot_curve = None

        h5_file.create_table(chip_group, 'mean_curve', mean)

        data_type = {'names': ['param', 'value', 'stddev'],
                            'formats': ['S1', 'float32', 'float32']}

        parameter_table           = np.recarray(4, dtype=data_type)
        parameter_table['param']  = ['a', 'b', 'c', 't']
        parameter_table['value']  = [popt[0], popt[1], popt[2], popt[3]]
        parameter_table['stddev'] = [np.sqrt(pcov[0][0]), np.sqrt(pcov[1][1]), np.sqrt(pcov[2][2]), np.sqrt(pcov[3][3])]

        h5_file.create_table(chip_group, 'fit_params', parameter_table)
'''
'''
    Plot data and histograms of the scan
    If there is a status queue information about the status of the scan are put into it
'''

#h5_filename = self.output_filename + '.h5'

with tb.open_file(h5_filename, 'r+') as h5_file:
    with plotting.Plotting(h5_filename) as p:
        print('...in plotting...')
        # Read needed configuration parameters
        VTP_fine_start = p.run_config['VTP_fine_start'][0]
        VTP_fine_stop  = p.run_config['VTP_fine_stop'][0]
        VTP_coarse     = p.dacs['VTP_coarse'][0]

        # Plot a page with all parameters
        p.plot_parameter_page()

        #for chip in range(self.num_of_chips):
        for chip in ['W18-K7']:
            # Get chipID in desirable formatting for HDF5 files (without '-')
            #chipID = str([ID for number, ID in enumerate(self.chip_links) if chip == number])[3:-2]
            chipID = 'W18_K7'

            # get group for current chip
            chip_group = h5_file.root.interpreted._f_get_child(chipID)

            # Plot the equalisation bits histograms
            thr_matrix = eval(f'h5_file.root.configuration.thr_matrix_{chipID}[:]')
            p.plot_distribution(thr_matrix, chip, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution', x_axis_title='Pixel threshold', y_axis_title='# of pixels', suffix='pixel_threshold_distribution', plot_queue=None)

            # Plot the Hit-Curve histogram
            ToT_hit_hist = chip_group.HistToTCurve_Count[:].T
            p.plot_scurves(ToT_hit_hist.astype(int), chip, list(range(VTP_fine_start, VTP_fine_stop+1)), electron_axis=False, scan_parameter_name="VTP_fine", max_occ=50, ylabel='Hits per pixel', title='Hit curves', plot_queue=None)
                    
            # Plot the ToT-Curve histogram
            ToT_hist = chip_group.HistToTCurve[:].T
            p.plot_scurves(ToT_hist.astype(int), chip, list(range(VTP_fine_start, VTP_fine_stop+1)), electron_axis=False, scan_parameter_name="VTP_fine", max_occ=250, ylabel='ToT Clock Cycles', title='ToT curves', plot_queue=None)

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
            fit    = totcurve(points, a, b, c, t)

            p.plot_two_functions(chip, range(len(mean['tot'])), mean['tot'], range(len(mean['tot'])), mean['tot_error'], points, fit, y_plot_range = [0, np.amax(fit[1])], label_1 = 'mean ToT', label_2='fit with \na=(%.2f+/-%.2f), \nb=(%.2f+/-%.2f), \nc=(%.2f+/-%.2f), \nt=(%.2f+/-%.2f)'%(a, ac, b, bc, c, cc, t ,tc), x_axis_title='VTP [2.5 mV]', y_axis_title='ToT Clock Cycles [25 ns]', title='ToT fit', suffix='ToT fit', plot_queue=None)
