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

h5_filename = '/home/tpc/Timepix3/scans/hdf/NoiseScan_2022-05-24_12-04-59.h5'

#self.logger.info('Starting data analysis...')
#        if status != None:
#            status.put("Performing data analysis")



# Open the HDF5 which contains all data of the scan
with tb.open_file(h5_filename, 'r+') as h5_file:
    # remove analised data 
    #h5_file.root.interpreted._f_remove(recursive=True)
    h5_file.root.interpreted_test._f_remove(recursive=True)
    
    # Read raw data, meta data and configuration parameters
    raw_data        = h5_file.root.raw_data[:]
    meta_data       = h5_file.root.meta_data[:]
    run_config      = h5_file.root.configuration.run_config[:]
    general_config  = h5_file.root.configuration.generalConfig[:]
    op_mode = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
    vco = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]

    link_config = h5_file.root.configuration.links[:]
    print(link_config)
    chip_IDs = link_config['chip_id']
    #chip_IDs_new = [b'W12-C7',b'W12-C7',b'W13-D8',b'W13-D8',b'W14-E9', b'W14-E9',b'W15-C5', b'W15-C5']
    #for new_Id in range(8):
    #    h5_file.root.configuration.links.cols.chip_id[new_Id] = chip_IDs_new[new_Id]
    #print(h5_file.root.configuration.links[:]['chip_id'])
    #print(h5_file.root.configuration.links)

    #chip_IDs_links = link_config['chip_id']
    
    chip_links = {}
    
    for link, ID in enumerate(chip_IDs):
        if ID not in chip_links:
            chip_links[ID] = [link]
        else:
            chip_links[ID].append(link)
    print(chip_links)

    link_number = 3
    for link, chipID in enumerate(chip_links):
        if link_number in chip_links[chipID]:
            print(link, chipID)

    num_of_chips = len(chip_links)

    pix_occ  = [[]]*num_of_chips
    hist_occ = [[]]*num_of_chips

    print(pix_occ, hist_occ)
    print(len(pix_occ), len(hist_occ))
    
    # Create a group to save all data and histograms to the HDF file
    h5_file.create_group(h5_file.root, 'interpreted_test', 'Interpreted Data')

    #self.logger.info('Interpret raw data...')
    # Interpret the raw data (2x 32 bit to 1x 48 bit)
    hit_data = analysis.interpret_raw_data(raw_data, op_mode, vco, chip_links,meta_data)
    #print(hit_data[0][:3])
    raw_data = None
    param_range = np.unique(meta_data['scan_param_id'])
    #print('parameter range: ' + str(param_range))
    # Read needed configuration parameters
    Vthreshold_start = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_start'][0]
    Vthreshold_stop  = [int(item[1]) for item in run_config if item[0] == b'Vthreshold_stop'][0]
    
    # create tables and histograms for each chip
    for chip in range(num_of_chips):
        chipID = str([ID for number, ID in enumerate(chip_links) if chip == number])[3:-2]
        print(chipID)
        #chip_ID_format = chipID[:3] +str('_') + chipID[-2:]
        
        h5_file.create_group(h5_file.root.interpreted_test, chipID)
        child = h5_file.root.interpreted_test._f_get_child(chipID)
        #print(h5_file.root.interpreted_test._v_children[-1])
        # Select only data which is hit data
        hit_data_chip = hit_data[chip][hit_data[chip]['data_header'] == 1]
        #print(hit_data_chip[:3])
        #print('Size: ' + str(len(hit_data_chip)))
        
        #h5_file.create_table(h5_file.root.interpreted_test, 'hit_data_%s' %chipID, hit_data_chip, filters=tb.Filters(complib='zlib', complevel=5))
        h5_file.create_table(child, 'hit_data', hit_data_chip, filters=tb.Filters(complib='zlib', complevel=5))
        
        pix_occ  = np.bincount(hit_data_chip['x'] * 256 + hit_data_chip['y'], minlength=256 * 256).astype(np.uint32)
        hist_occ = np.reshape(pix_occ, (256, 256)).T
        h5_file.create_carray(child, name='HistOcc', obj=hist_occ)

        meta_data   = None
        pix_occ     = None
        hist_occ    = None

        # Create histograms for number of active pixels and number of hits for individual thresholds
        noise_curve_pixel, noise_curve_hits = analysis.noise_pixel_count(hit_data_chip, param_range, Vthreshold_start)
        h5_file.create_carray(child, name='NoiseCurvePixel', obj=noise_curve_pixel)
        h5_file.create_carray(child, name='NoiseCurveHits', obj=noise_curve_hits)
    #print(h5_file.root.interpreted_test._v_children)
'''
    Plot data and histograms of the scan
    If there is a status queue information about the status of the scan are put into it
'''

#h5_filename = self.output_filename + '.h5'

#self.logger.info('Starting plotting...')
#if status != None:
#    status.put("Create Plots")
with tb.open_file(h5_filename, 'r+') as h5_file:

    with plotting.Plotting(h5_filename) as p:

        # Read needed configuration parameters
        Vthreshold_start = int(p.run_config[b'Vthreshold_start'])
        Vthreshold_stop = int(p.run_config[b'Vthreshold_stop'])

        # Plot a page with all parameters
        p.plot_parameter_page()

        mask = h5_file.root.configuration.mask_matrix[:].T

        # Plot the equalisation bits histograms
        thr_matrix = h5_file.root.configuration.thr_matrix[:],
        p.plot_distribution(thr_matrix, plot_range=np.arange(-0.5, 16.5, 1), title='Pixel threshold distribution', x_axis_title='Pixel threshold', y_axis_title='# of hits', suffix='pixel_threshold_distribution', plot_queue=None)
                
        for chip in range(num_of_chips):
            chipID = str([ID for number, ID in enumerate(chip_links) if number == chip])[3:-2]
            child  = h5_file.root.interpreted_test._f_get_child(chipID)

            noise_curve_pixel = child.NoiseCurvePixel[:]
            print(noise_curve_pixel[noise_curve_pixel > 0])
            p._plot_1d_hist(hist = noise_curve_pixel, plot_range = list(range(Vthreshold_start, Vthreshold_stop+1)), title='Noise pixel per threshold, chip = %s' %chipID, suffix='noise_pixel_per_threshold', x_axis_title='Threshold', y_axis_title='Number of active pixels', log_y=True, plot_queue=None)

            # Plot the noise hits histogram
            noise_curve_hits = child.NoiseCurveHits[:]
            print(noise_curve_hits[noise_curve_hits > 0])
            p._plot_1d_hist(hist = noise_curve_hits, plot_range = list(range(Vthreshold_start, Vthreshold_stop+1)), title='Noise hits per threshold, chip = %s' %chipID, suffix='noise_pixel_per_threshold', x_axis_title='Threshold', y_axis_title='Total number of hits', log_y=True, plot_queue=None)
                