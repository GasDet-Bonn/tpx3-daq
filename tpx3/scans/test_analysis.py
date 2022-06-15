from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from cgitb import enable
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import math
import os

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting
import tpx3.utils as utils
from six.moves import range
import faulthandler
faulthandler.enable()

'''
    Analyze the data of the scan
    If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
    If there is a status queue information about the status of the scan are put into it
'''

#h5_filename = '/home/tpc/Timepix3/scans/hdf/NoiseScan_2022-05-24_12-04-59.h5'
#h5_filename = '/home/tpc/Timepix3/scans/hdf/ThresholdScan_2022-05-31_18-35-18.h5'
#h5_filename = '/home/tpc/Timepix3/scans/hdf/ThresholdScan_2022-06-02_16-11-35.h5'
#h5_filename = '/home/tpc/Timepix3/scans/hdf/ThresholdCalib_2022-06-03_11-12-55.h5'
h5_filename = '/home/tpc/Timepix3/scans/hdf/EqualisationCharge_2022-06-09_11-25-36.h5'
#self.logger.info('Starting data analysis...')
#        if status != None:
#            status.put("Performing data analysis")



# Open the HDF5 which contains all data of the scan
with tb.open_file(h5_filename, 'r+') as h5_file:
    # remove analised data 
    h5_file.root.interpreted._f_remove(recursive=True)
    #h5_file.root.interpreted_test._f_remove(recursive=True)
    
    # Read raw data, meta data and configuration parameters
    #raw_data        = h5_file.root.raw_data[:]
    meta_data       = h5_file.root.meta_data[:]
    run_config      = h5_file.root.configuration.run_config[:]
    general_config  = h5_file.root.configuration.generalConfig[:]
    op_mode         = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
    vco             = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]
    
    #chip_IDs_new = [b'W12-C1',b'W12-C2',b'W12-C3',b'W12-C4',b'W12-C5', b'W12-C6',b'W12-C7', b'W12-C8']
    chip_IDs_new = [b'W18-K7',b'W18-K7',b'W17-K6',b'W17-K6',b'W16-K5', b'W16-K5',b'W15-K4', b'W15-K4']
    for new_Id in range(8):
        h5_file.root.configuration.links.cols.chip_id[new_Id] = chip_IDs_new[new_Id]
    #print(h5_file.root.configuration.links[:]['chip_id'])
    #print(h5_file.root.configuration.links)
    link_config = h5_file.root.configuration.links[:]
    print(link_config)
    chip_IDs = link_config['chip_id']
    #chip_IDs_links = link_config['chip_id']
    
    chip_links = {}
    
    for link, ID in enumerate(chip_IDs):
        if ID not in chip_links:
            chip_links[ID] = [link]
        else:
            chip_links[ID].append(link)
    print(chip_links)

    #link_number = 3
    #for link, chipID in enumerate(chip_links):
    #    if link_number in chip_links[chipID]:
    #        print(link, chipID)

    num_of_chips = len(chip_links)

    # Create group to save all data and histograms to the HDF file
    h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

    #self.logger.info('Interpret raw data...')

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

    #self.logger.info('THR = 0')
    #THR = 0
    raw_data_thr0 = h5_file.root.raw_data[:meta_data_th0['index_stop'][-1]]
    hit_data_thr0 = analysis.interpret_raw_data(raw_data_thr0, op_mode, vco, chip_links, meta_data_th0, progress = None)
    #group_child = h5_file.root.interpreted._f_get_child('W18-K7')
    #hit_data_thr0 = group_child.hit_data_th0[:]
    #h5_file.create_table(h5_file.root.interpreted, 'hit_data_th0', hit_data_thr0, filters=tb.Filters(complib='zlib', complevel=5))
    #raw_data_thr0 = None

    #self.logger.info('THR = 15')
    #THR = 15
    raw_data_thr15 = h5_file.root.raw_data[meta_data_th0['index_stop'][-1]:]
    hit_data_thr15 = analysis.interpret_raw_data(raw_data_thr15, op_mode, vco, chip_links, meta_data_th15, progress = None)
    #hit_data_thr15 = group_child.hit_data_th15[:]
    #h5_file.create_table(h5_file.root.interpreted, 'hit_data_th15', hit_data_thr15, filters=tb.Filters(complib='zlib', complevel=5))
    #raw_data_thr15 = None

    # Read needed configuration parameters
    Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
    Vthreshold_stop  = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]
    n_injections     = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]
    chip_wafer       = [int(item[1]) for item in run_config if item[0] == b'chip_wafer'][0]
    chip_x           = [item[1].decode() for item in run_config if item[0] == b'chip_x'][0]
    chip_y           = [int(item[1]) for item in run_config if item[0] == b'chip_y'][0]

    for chip in range(num_of_chips):
        # get chipID of current chip
        chipID = str([ID for number, ID in enumerate(chip_links) if chip == number])[3:-2]
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
        #self.logger.info('Get the global threshold distributions for all pixels...')
        scurve_th0     = analysis.scurve_hist(hit_data_thr0_chip, np.arange(len(param_range) // 2))
        #hit_data_thr0  = None
        scurve_th15    = analysis.scurve_hist(hit_data_thr15_chip, np.arange(len(param_range) // 2, len(param_range)))
        #hit_data_thr15 = None

        # Fit S-Curves to the histograms for all pixels
        #self.logger.info('Fit the scurves for all pixels...')
        thr2D_th0, sig2D_th0, chi2ndf2D_th0 = analysis.fit_scurves_multithread(scurve_th0, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop + 1)), n_injections=n_injections, invert_x=False, progress = None)
        h5_file.create_carray(chip_group, name='HistSCurve_th0', obj=scurve_th0)
        h5_file.create_carray(chip_group, name='ThresholdMap_th0', obj=thr2D_th0.T)
        #scurve_th0 = None
        thr2D_th15, sig2D_th15, chi2ndf2D_th15 = analysis.fit_scurves_multithread(scurve_th15, scan_param_range=list(range(Vthreshold_start, Vthreshold_stop + 1)), n_injections=n_injections, invert_x=False, progress = None)
        h5_file.create_carray(chip_group, name='HistSCurve_th15', obj=scurve_th15)
        h5_file.create_carray(chip_group, name='ThresholdMap_th15', obj=thr2D_th15.T)
        #scurve_th15 = None

        # Put the threshold distribution based on the fit results in two histograms
        #self.logger.info('Get the cumulated global threshold distributions...')
        hist_th0  = analysis.vth_hist(thr2D_th0, Vthreshold_stop)
        hist_th15 = analysis.vth_hist(thr2D_th15, Vthreshold_stop)

        # Use the threshold histograms and one threshold distribution to calculate the equalisation
        #self.logger.info('Calculate the equalisation matrix...')
        eq_matrix = analysis.eq_matrix(hist_th0, hist_th15, thr2D_th0, Vthreshold_start, Vthreshold_stop)
        h5_file.create_carray(chip_group, name='EqualisationMap', obj=eq_matrix)

        # Don't mask any pixels in the mask file
        #mask_matrix = np.zeros((256, 256), dtype=bool)
        #mask_matrix[:, :] = 0

        # Write the equalisation matrix to a new HDF5 file
        #self.save_thr_mask(eq_matrix, chip_wafer, chip_x ,chip_y)
        #self.save_thr_mask(eq_matrix, chipID[:3], chipID[4], chipID[5])
        #if result_path != None:
        #    result_path.put(self.thrfile)


'''
    Plot data and histograms of the scan
    If there is a status queue information about the status of the scan are put into it
'''


#h5_filename = self.output_filename + '.h5'

#self.logger.info('Starting plotting...')
#if status != None:
#    status.put("Create Plots")

with tb.open_file(h5_filename, 'r+') as h5_file:
    #run_config      = h5_file.root.configuration.run_config[:]
    #general_config  = h5_file.root.configuration.generalConfig[:]
    #op_mode         = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
    #vco             = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]
    # 'Simulate' more chips
    #chip_IDs_new = [b'W18-K7',b'W18-K7',b'W17-D8',b'W17-D8',b'W14-E9', b'W14-E9',b'W15-C5', b'W15-C5']
    #chip_IDs_new = [b'W18-K7',b'W18-K7',b'W18-K7',b'W18-K7',b'W18-K7', b'W18-K7',b'W18-K7', b'W18-K7']
    #for new_Id in range(8):
    #    h5_file.root.configuration.links.cols.chip_id[new_Id] = chip_IDs_new[new_Id]

    link_config = h5_file.root.configuration.links[:]
    chip_IDs = link_config['chip_id']
    chip_links = {}
    
    for link, ID in enumerate(chip_IDs):
        if ID not in chip_links:
            chip_links[ID] = [link]
        else:
            chip_links[ID].append(link)
    print(chip_links)

    num_of_chips = len(chip_links)
    #n_injections = [int(item[1]) for item in run_config if item[0] == b'n_injections'][0]

    with plotting.Plotting(h5_filename) as p:

        #run_config_call   = ('.run_config_' + str(iteration))
        # Read needed configuration parameters
        #iterations       = int(p.run_config[b"n_pulse_heights"])
        Vthreshold_start = int(p.run_config[b"Vthreshold_start"])
        Vthreshold_stop  = int(p.run_config[b"Vthreshold_stop"])
        n_injections     = int(p.run_config[b"n_injections"])

        # Plot a page with all parameters
        print('Plot parameter page...')
        p.plot_parameter_page()
        print('Done!')

        mask = h5_file.root.configuration.mask_matrix[:].T

        # create a group for the calibration results
        #h5_file.create_group(h5_file.root, 'calibration', 'Threshold calibration results')

        for chip in range(num_of_chips):
            # get chipID of current chip
            chipID = str([ID for number, ID in enumerate(chip_links) if chip == number])[3:-2]
            print(chip, chipID)

            # get group for current chip
            chip_group  = h5_file.root.interpreted._f_get_child(chipID)

            # Plot the S-Curve histogram
            scurve_th0_hist = chip_group.HistSCurve_th0[:].T
            max_occ = n_injections * 5
            p.plot_scurves(scurve_th0_hist, list(range(Vthreshold_start, Vthreshold_stop)), chipID, scan_parameter_name="Vthreshold", title='SCurves - PixelDAC 0', max_occ=max_occ, plot_queue=None)

            # Plot the threshold distribution based on the S-Curve fits
            hist_th0 = np.ma.masked_array(chip_group.ThresholdMap_th0[:], mask)
            p.plot_distribution(hist_th0, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution - PixelDAC 0, chip %s' %chipID, suffix='threshold_distribution_th0', plot_queue=None)

            # Plot the S-Curve histogram
            scurve_th15_hist = chip_group.HistSCurve_th15[:].T
            max_occ = n_injections * 5
            p.plot_scurves(scurve_th15_hist, list(range(Vthreshold_start, Vthreshold_stop)), chipID, scan_parameter_name="Vthreshold", title='SCurves - PixelDAC 15', max_occ=max_occ, plot_queue=None)

            # Plot the threshold distribution based on the S-Curve fits
            hist_th15 = np.ma.masked_array(chip_group.ThresholdMap_th15[:], mask)
            p.plot_distribution(hist_th15, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution - PixelDAC 15, chip %s' %chipID, suffix='threshold_distribution_th15', plot_queue=None)

            # Plot the occupancy matrix
            eq_masked = np.ma.masked_array(chip_group.EqualisationMap[:].T, mask)
            p.plot_occupancy(eq_masked, title='Equalisation Map, chip %s' %chipID, z_max='median', z_label='PixelDAC', suffix='equalisation', plot_queue=None)

            # Plot the equalisation bits histograms
            p.plot_distribution(eq_masked, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution, chip %s' %chipID, x_axis_title='Pixel threshold', y_axis_title='# of hits', suffix='pixel_threshold_distribution', plot_queue=None)
