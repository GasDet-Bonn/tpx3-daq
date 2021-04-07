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

from tqdm import tqdm
import numpy as np
import time
import tables as tb
import math

from numpy.lib.recfunctions import merge_arrays

import matplotlib.pyplot as plt
import matplotlib.colors as colors

import logging
import six

#from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

from numba import njit

import sys
import os
import argparse

local_configuration = {
    # Scan parameters
    'mask_step'        : 64,
    'VTP_fine_start'   : 190 + 0,
    'VTP_fine_stop'    : 210 + 300,
    'n_injections'     : 1,
    #'maskfile'        : './output_data/20200918_170800_mask.h5'
}


class DataAnalysis():

    scan_id = "DataAnalysis"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    """ a bit advanced clustering algorithm. Clusters hits in one chunk and if possible also with hits in the next chunk"""
    def cluster(self, data, radius, dt, progress = None):
        cluster_nr = 0
        data_type = [('cluster_nr','uint64'), ('hits','int'), ('centerX','int'), ('centerY','int'), ('sumTOT','int'), ('sumCharge','int'), ('x','object'), ('y','object'), ('TOA','object'), ('TOT','object'), ('EventCounter','object'), ('chunk_start_time','double'), ('TOA_Extension','object'), ('hit_index','object')]

        start_times = np.unique(data['chunk_start_time'])
        # create empty recarray which is big enough to contain one cluster per pixel (maximum possible number of clusters)
        cluster_data = np.recarray(data.shape[0], dtype=data_type)
        data.sort(order="TOA_Combined")

        s=0
        n=0

        if progress == None:
            pbar = tqdm(total = len(start_times))
        else:
            step_counter = 0
    
        for i in range(len(start_times)):
            # as long as there are still hits in frame:
            current_hit = 0
            # get the data for this and the next frame, as well as an index list for all the hits in these frames (aka chunks)
            # the index lists are later used to check whether a hit is allready assigned to a cluster
            # special cases have to be treated for the first and last frame and for runs consisting of only one frame (unlikely)
            if i == len(start_times)-1:
                if i == 0:
                    frame = data[data['chunk_start_time'] == start_times[i]]
                    frame_next = []
                    event_index = np.arange(frame.shape[0])
                    event_index_next = []
                else:
                    event_index = event_index_next
                    frame = frame_next
                    frame_next = []
                    event_index_next = []
            else:
                if i == 0:
                    frame = data[data['chunk_start_time'] == start_times[i]]
                    frame_next = data[data['chunk_start_time'] == start_times[i+1]]
                    event_index = np.arange(frame.shape[0])
                    event_index_next = np.arange(frame_next.shape[0])
                else:
                    # take last next frame and corresponding index list as current frame. Important in the case that hits from this frame
                    # were allready assigned to the last
                    event_index = event_index_next
                    frame = frame_next
                    frame_next = data[data['chunk_start_time'] == start_times[i+1]]
                    event_index_next = np.arange(frame_next.shape[0])

            while len(event_index):
                # start new cluster with first hit in frame as current pixel
                cluster_data['cluster_nr'][cluster_nr] = cluster_nr
                cluster_data['chunk_start_time'][cluster_nr] = start_times[i]
                x_list = [frame['x'][event_index[0]]]
                y_list = [frame['y'][event_index[0]]]
                toa_list=[frame['TOA_Combined'][event_index[0]]]
                tot_list = [frame['TOT'][event_index[0]]]
                event_list = [frame['EventCounter'][event_index[0]]]
                extension_list = [frame['TOA_Extension'][event_index[0]]]
                hit_index_list = [frame['hit_index'][event_index[0]]]
                event_index = event_index[1:] # remove first hit from index list
                j = 0
                current = 0
                # did not reach end of cluster
                while current < len(x_list):
                    stop = False
                    k = 0
                    # append all hits within cluster radius to current pixel and delete from frame
                    while k < len(event_index):
                        j = event_index[k]
                        # check whether next hit in frame fits by TOA. As the data is sorted, we can stop looking if not
                        if np.abs(frame['TOA_Combined'][j].astype('int64')-toa_list[current])>dt:
                            s += k
                            n+=1
                            # pass on to check whether maybe another hit in the next chunk fits
                            stop = True
                            # if there is no next chunk: just abort
                            if not len(frame_next):
                                break
                        # if it fits in time, check whether it also fits in space
                        elif np.abs(frame['x'][j].astype('int64')-x_list[current])<=radius and np.abs(frame['y'][j].astype('int64')-y_list[current])<=radius:
                            x_list.append(frame['x'][j])
                            y_list.append(frame['y'][j])
                            toa_list.append(frame['TOA_Combined'][j])
                            tot_list.append(frame['TOT'][j])
                            event_list.append(frame['EventCounter'][j])
                            extension_list.append(frame['TOA_Extension'][j])
                            hit_index_list.append(frame['hit_index'][j])
                            event_index = np.delete(event_index,k,axis=0)
                        # if the hit does not fit in space go on to the next one
                        else:
                            k+=1
                        # check in the next frame whether there is a suiting hit. As we shift inside the frames, it might be that the first
                        # hit in the next frame is before the last in the currect frame
                        #if (k == len(event_index) or stop == True) and (frame_next!=None):
                        if (k == len(event_index) or stop == True) and len(frame_next):
                            f = 0
                            # append all hits within cluster radius to current pixel and delete from frame
                            while f < len(event_index_next):
                                n = event_index_next[f]
                                # stop if TOA does not fit, as is is impossible to shift over two chunks
                                if np.abs(frame_next['TOA_Combined'][n].astype('int64')-toa_list[current])>dt:
                                    s += k+f
                                    n+=1
                                    break
                                # check whether it fits in space and add to cluster if so
                                if np.abs(frame_next['x'][n].astype('int64')-x_list[current])<=radius and np.abs(frame_next['y'][n].astype('int64')-y_list[current])<=radius:
                                    x_list.append(frame_next['x'][n])
                                    y_list.append(frame_next['y'][n])
                                    toa_list.append(frame_next['TOA_Combined'][n])
                                    tot_list.append(frame_next['TOT'][n])
                                    event_list.append(frame_next['EventCounter'][n])
                                    extension_list.append(frame_next['TOA_Extension'][n])
                                    hit_index_list.append(frame_next['hit_index'][n])
                                    event_index_next = np.delete(event_index_next,f,axis=0)
                                # if the hit does not fit go on to the next one
                                else:
                                    f+=1
                            # break k-loop when done looking in next frame
                            break
                    # change current pixel to next one
                    current+=1
                
                # save cluster data
                cluster_data['x'][cluster_nr] = x_list
                cluster_data['y'][cluster_nr] = y_list
                cluster_data['TOA'][cluster_nr] = toa_list
                cluster_data['TOT'][cluster_nr] = tot_list
                cluster_data['EventCounter'][cluster_nr] = event_list
                cluster_data['TOA_Extension'][cluster_nr] = extension_list
                cluster_data['hit_index'][cluster_nr] = hit_index_list
                cluster_data['hits'][cluster_nr] = len(x_list)
                cluster_data['centerX'][cluster_nr] = sum(x_list)/len(x_list)
                cluster_data['centerY'][cluster_nr] = sum(y_list)/len(y_list)
                cluster_data['sumTOT'][cluster_nr] = sum(tot_list)
                cluster_nr+=1
            if progress == None:
                pbar.update(1)
            else:
                step_counter += 1
                fraction = step_counter / (len(split[:-1]))
                progress.put(fraction)

        # cut to the number of actual clusters (remove empty rows) and return
        if progress == None:
            pbar.close()
        if n!=0:
            self.logger.info("Average looking size "+str(s/n))
        self.logger.info("Done with clustering.")
        return cluster_data[:cluster_nr]


    def analyze(self, file_name, big = False, cluster_radius = 1.1, cluster_dt = 10, progress = None):

        big = args_dict["big"]

        self.logger.info('Starting data analysis of '+str(file_name)+' ...')
        #if file_name != "":
        self.h5_filename = file_name
        file_extension = file_name.split('/')[-1]
        with tb.open_file(self.h5_filename, 'r+') as h5_file:
            meta_data = h5_file.root.meta_data[:]
            run_config = h5_file.root.configuration.run_config[:]
            general_config = h5_file.root.configuration.generalConfig[:]
            op_mode = [row[1] for row in general_config if row[0]==b'Op_mode'][0]
            #vco = [row[1] for row in general_config if row[0]==b'Fast_Io_en'][0]
            vco = False            
    
            # create structures to write the hit_data and cluster data in
            try:
                h5_file.remove_node(h5_file.root.interpreted, recursive=True)
                print("Node interpreted allready there")
            except:
                print("Create node interpreted")

            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

            try:
                h5_file.remove_node(h5_file.root.reconstruction, recursive=True)
                print("Node reconstrution allready there")
            except:
                print("Create node reconstrution")

            h5_file.create_group(h5_file.root, 'reconstruction', 'Reconstructed Data')

            # for large data_sets we might want to split it into smaller parts to speed up analysis and save RAM
            if big == True:
                # customize number of meta data chunks to be analyzed at once here
                chunk_length = 1000
                meta_length = len(meta_data)

                # array of indices of the meta_data chunks each package of chunks begins with
                iteration_array = range(0, meta_length, chunk_length)
            # for smaller data we just analyse everything at once -> only one set    chunks, involving all data
            else:
                iteration_array = [0]

            cluster_sum = 0
            hit_sum = 0

            hit_index = 0
            # iterate over all sets of chunks
            for num, i in enumerate(iteration_array):
                # Split meta_data
                if big == False: # take all data
                    self.logger.info("Start analysis of part 1/1")
                    meta_data_tmp = meta_data[:]
                elif i < meta_length-chunk_length: # take all data in chunks
                    self.logger.info("Start analysis of part %d/%d" % (num+1,math.ceil(meta_length/chunk_length)))
                    meta_data_tmp = meta_data[i:i+chunk_length]
                else: # take all data until the end
                    self.logger.info("Start analysis of part %d/%d" % (num+1,math.ceil(meta_length/chunk_length)))
                    meta_data_tmp = meta_data[i:]
                # get raw_data
                raw_data_tmp = h5_file.root.raw_data[meta_data_tmp['index_start'][0]:meta_data_tmp['index_stop'][-1]]
                # shift indices in meta_data to start a zero
                start = meta_data_tmp['index_start'][0]
                meta_data_tmp['index_start'] = meta_data_tmp['index_start']-start
                meta_data_tmp['index_stop'] = meta_data_tmp['index_stop']-start
                # analyze data
                hit_data_tmp = analysis.interpret_raw_data(raw_data_tmp, op_mode, vco, meta_data_tmp, split_fine=True)
                hit_data_tmp = hit_data_tmp[hit_data_tmp['data_header'] == 1]
                hit_data_tmp['hit_index'] = range(hit_index,hit_index+hit_data_tmp.shape[0])
                hit_index += hit_data_tmp.shape[0]

                # cluster data
                self.logger.info("Start clustering...")
                cluster_data = self.cluster(hit_data_tmp, cluster_radius, cluster_dt)
                self.logger.info("Done with clustering")

                # save hit_data
                h5_file.create_table(h5_file.root.interpreted, 'hit_data_'+str(num), hit_data_tmp, filters=tb.Filters(complib='zlib', complevel=5))

                # create group for cluster data
                group = h5_file.create_group(h5_file.root.reconstruction, 'run_'+str(num), 'Cluster Data of Chunk '+str(num))

                # write cluster data into h5 file
                self.logger.info("Start writing into h5 file...")
                vlarray = h5_file.create_vlarray(group, 'x', tb.Int32Atom(shape=()), "x-values", filters=tb.Filters(complib='zlib', complevel=5))
                for i in range(cluster_data.shape[0]):
                    vlarray.append(cluster_data['x'][i])

                vlarray = h5_file.create_vlarray(group, 'y', tb.Int32Atom(shape=()), "y-values", filters=tb.Filters(complib='zlib', complevel=5))
                for i in range(cluster_data.shape[0]):
                    vlarray.append(cluster_data['y'][i])

                vlarray = h5_file.create_vlarray(group, 'TOA', tb.Int64Atom(shape=()), "TOA-values", filters=tb.Filters(complib='zlib', complevel=5))
                for i in range(cluster_data.shape[0]):
                    vlarray.append(cluster_data['TOA'][i])

                vlarray = h5_file.create_vlarray(group, 'TOT', tb.Int32Atom(shape=()), "TOT-values", filters=tb.Filters(complib='zlib', complevel=5))
                for i in range(cluster_data.shape[0]):
                    vlarray.append(cluster_data['TOT'][i])

                vlarray = h5_file.create_vlarray(group, 'EventCounter', tb.Int32Atom(shape=()), "EventCounter-values", filters=tb.Filters(complib='zlib', complevel=5))
                for i in range(cluster_data.shape[0]):
                    vlarray.append(cluster_data['EventCounter'][i])

                vlarray = h5_file.create_vlarray(group, 'TOA_Extension', tb.Int64Atom(shape=()), "TOA_Extension-values", filters=tb.Filters(complib='zlib', complevel=5))
                for i in range(cluster_data.shape[0]):
                    vlarray.append(cluster_data['TOA_Extension'][i])

                vlarray = h5_file.create_vlarray(group, 'hit_index', tb.Int64Atom(shape=()), "hit_index-values", filters=tb.Filters(complib='zlib', complevel=5))
                for i in range(cluster_data.shape[0]):
                    vlarray.append(cluster_data['hit_index'][i])

                vlarray = h5_file.create_array(group, 'cluster_nr', cluster_data['cluster_nr'], "cluster_nr-values")
                
                h5_file.create_array(group, 'chunk_start_time', cluster_data['chunk_start_time'], "chunk_start_time-values")

                h5_file.create_array(group, 'hits', cluster_data['hits'], "size of cluster")

                h5_file.create_array(group, 'centerX', cluster_data['centerX'], "mean of the x values")

                h5_file.create_array(group, 'centerY', cluster_data['centerY'], "mean of the y values")

                h5_file.create_array(group, 'sumTOT', cluster_data['sumTOT'], "sum of the ToT in the cluster")

                # print out cluster information
                print("# cluster in chunk: "+str(len(cluster_data['hits'])))
                if len(cluster_data['hits']) != 0:
                    print("average size: "+str(np.mean(cluster_data['hits'])))
                print("total hits in chunk: "+str(np.sum(cluster_data['hits'])))

                cluster_sum += len(cluster_data['hits'])
                hit_sum += np.sum(cluster_data['hits'])
            
            # print out final information on clustering
            print("# cluster in total: "+str(cluster_sum))
            print("# hits in total: "+str(hit_sum))


    def plot(self,file_name):
        '''
            Plot data and histograms of the data taking
        '''

        self.logger.info('Starting plotting...')
        with tb.open_file(file_name, 'r+') as h5_file:
            with plotting.Plotting(file_name) as p:
                p.plot_parameter_page()

                hit_data_x = np.empty(0, dtype = np.uint32)
                hit_data_y = np.empty(0, dtype = np.uint32)
                tot = np.empty(0, dtype = np.uint32)
                toa = np.empty(0, dtype = np.uint32)
                toa_comb = np.empty(0, dtype = np.uint64)

                # iterate over all hit_data groups in the hdf5 file and build arrays for the histograms
                for group in h5_file.root.interpreted:
                    hit_data = group[:]
                    hit_data_x = np.concatenate((hit_data_x, hit_data['x']), axis = None)
                    hit_data_y = np.concatenate((hit_data_y, hit_data['y']), axis = None)
                    tot = np.concatenate((tot, hit_data['TOT']), axis = None)
                    toa = np.concatenate((toa, hit_data['TOA']), axis = None)
                    toa_comb = np.concatenate((toa_comb, hit_data['TOA_Combined']), axis = None)

                # Plot general hit properties

                # Plot the occupancy matrix
                pix_occ = np.bincount(hit_data_x * 256 + hit_data_y, minlength=256 * 256).astype(np.uint32)
                hist_occ = np.reshape(pix_occ, (256, 256)).T
                p.plot_occupancy(hist_occ, title='Integrated Occupancy', z_max='maximum', suffix='occupancy')

                # Plot the ToT-Curve histogram
                p.plot_distribution(tot, plot_range = np.arange(np.amin(tot)-0.5, np.median(tot) * 7, 5), x_axis_title='ToT', title='ToT distribution', suffix='ToT_distribution', fit=False)

                # Plot the ToA-Curve histogram
                p.plot_distribution(toa, plot_range = np.arange(np.amin(toa)-0.5, np.amax(toa), 100), x_axis_title='ToA', title='ToA distribution', suffix='ToA_distribution', fit=False)

                # Plot the ToA_Combined-Curve histogram
                p.plot_distribution(toa_comb, plot_range = np.arange(np.amin(toa_comb), np.amax(toa_comb), (np.amax(toa_comb)-np.amin(toa_comb))//100), x_axis_title='ToA_Combined', title='ToA_Combined distribution', suffix='ToA_Combined_distribution', fit=False)

                hist_size = np.empty(0, dtype=np.uint32)
                hist_sum = np.empty(0, dtype=np.uint32)
                first = True

                # iterate over all run_* groups in the hdf5 file and build arrays for the histograms
                for group in h5_file.root.reconstruction:
                    hist_size = np.concatenate((hist_size, group.hits[:]), axis = None)
                    hist_sum = np.concatenate((hist_sum, group.sumTOT[:]), axis = None)
                    if first == False:
                        histcha = np.concatenate((histcha, group.TOT[:]), axis = 0)
                        histtoa = np.concatenate((histcha, group.TOA[:]), axis = 0)
                    else:
                        histcha = np.array(group.TOT[:],dtype=object)
                        histtoa = np.array(group.TOA[:],dtype=object)
                        first = False

                # Plot cluster properties

                num_cluster = len(hist_size)

                # Plot the Cluster Size
                p.plot_distribution(hist_size, plot_range = np.arange(-0.5, np.median(hist_size)*7+0.5, 1), x_axis_title='Cluster Size', y_axis_title='# of clusters', title='Size distribution'+r' ($\Sigma$ = {0})'.format(num_cluster), suffix='Size_distribution', fit=False)

                # Plot the Cluster ToT
                p.plot_distribution(hist_sum, plot_range = np.arange(np.amin(hist_sum)-0.5, np.median(hist_sum) *7, 5), x_axis_title='Cluster ToT', y_axis_title='# of clusters', title='Cluster ToT distribution', suffix='Cluster_toT_distribution', fit=False)

                # Plot the Cluster ToT for all clusters with more than one pixel
                histm1 = hist_sum[hist_size!=1]
                p.plot_distribution(histm1, plot_range = np.arange(np.amin(hist_sum)-0.5, np.median(hist_sum) *7, 5), x_axis_title='Cluster ToT for clusters with more than one pixel', y_axis_title='# of clusters', title='Cluster ToT distribution for clusters with more than one pixel', suffix='Cluster_toT_distribution', fit=False)

                # Plot the Cluster ToT for all clusters with one pixel
                histe1 = hist_sum[hist_size==1]
                p.plot_distribution(histe1, plot_range = np.arange(np.amin(hist_sum)-0.5, np.median(hist_sum) *7, 5), x_axis_title='Cluster ToT for clusters with one pixel', y_axis_title='# of clusters', title='Cluster ToT distribution for clusters with one pixel', suffix='Cluster_toT_distribution for clusters with one pixel', fit=False)

                # K7
                #a = 10.17
                #b = -4307.6
                #c = -52649.2
                #t = 268.85
                # I7 THR=800
                #a = 8.8
                #b = -3910.2
                #c = -66090.6
                #t = 258.61
                # I7 THR=1000
                a = 8.0
                b = -2964.3
                c = -46339.0
                t = 206.31
                # I7 THR=1100
                #a = 7.4
                #b = -2288.9
                #c = -7204.0
                #t = 236.44
                histch = np.zeros(len(histcha))
                for i,el in enumerate(histcha):
                    for value in  el:
                        histch[i] += 3*np.abs(100*0.005-(-(b-value*25-t*a)/(2*a)+np.sqrt(((b-value*25-t*a)/(2*a))**2-(value*25*t-b*t-c)/a))*2/2.5*0.0025)/1.602*10**4

                #p.plot_distribution(histch, plot_range = np.arange(np.amin(histch)-0.5, np.median(histch) *7, 500), x_axis_title='Number of electrons per cluster', y_axis_title='# of clusters', title='Number of electrons per cluster', suffix='Number of electrons per cluster', fit=False)

                p.plot_distribution(histch, plot_range = np.arange(0, 48000, 500), x_axis_title='Number of electrons per cluster', y_axis_title='# of clusters', title='Number of electrons per cluster', suffix='Number of electrons per cluster', fit=False)


                histchm1 = histch[hist_size!=1]
                p.plot_distribution(histchm1, plot_range = np.arange(np.amin(histch)-0.5, np.median(histch) *7, 500), x_axis_title='Number of electrons per cluster for clusters with more than one pixel', y_axis_title='# of clusters', title='Number of electrons per cluster for clusters with more than one pixel', suffix='Number of electrons per cluster for clusters with more than one pixel', fit=False)


                histche1 = histch[hist_size==1]
                p.plot_distribution(histche1, plot_range = np.arange(np.amin(histch)-0.5, np.median(histch) *7, 500), x_axis_title='Number of electrons per cluster for clusters with only one pixel', y_axis_title='# of clusters', title='Number of electrons per cluster for clusters with only one pixel', suffix='Number of electrons per cluster for clusters with only one pixel', fit=False)

                histche2 = histch[hist_size==2]
                p.plot_distribution(histche2, plot_range = np.arange(np.amin(histch)-0.5, np.median(histch) *7, 500), x_axis_title='Number of electrons per cluster for clusters with two pixel', y_axis_title='# of clusters', title='Number of electrons per cluster for clusters with two pixel', suffix='Number of electrons per cluster for clusters with only one pixel', fit=False)

                histche3 = histch[hist_size==3]
                p.plot_distribution(histche3, plot_range = np.arange(np.amin(histch)-0.5, np.median(histch) *7, 500), x_axis_title='Number of electrons per cluster for clusters with three pixel', y_axis_title='# of clusters', title='Number of electrons per cluster for clusters with three pixel', suffix='Number of electrons per cluster for clusters with only one pixel', fit=False)

                histche4 = histch[hist_size==4]
                p.plot_distribution(histche4, plot_range = np.arange(np.amin(histch)-0.5, np.median(histch) *7, 500), x_axis_title='Number of electrons per cluster for clusters with four pixel', y_axis_title='# of clusters', title='Number of electrons per cluster for clusters with four pixel', suffix='Number of electrons per cluster for clusters with only one pixel', fit=False)

                # Plot the charge for all pixels
                hist = np.empty(len(tot))
                for i,value in enumerate(tot):
                    hist[i] = 3*np.abs(100*0.005-(-(b-value*25-t*a)/(2*a)+np.sqrt(((b-value*25-t*a)/(2*a))**2-(value*25*t-b*t-c)/a))*2/2.5*0.0025)/1.602*10**4
                p.plot_distribution(hist, plot_range = np.arange(0-0.5, np.median(hist) *7, 500), x_axis_title='Number of electrons per pixel', y_axis_title='# of pixels', title='Number of electrons per pixel', suffix='Number of electrons per pixel', fit=False)

                # plot the ToA spread in the clusters
                hist_spread = np.empty(len(toa_comb))
                ind = 0
                for i,el in enumerate(histtoa):
                    m = np.mean(el)
                    for value in  el:
                        hist_spread[ind] = value-m
                        ind += 1
                p.plot_distribution(hist_spread, plot_range = np.arange(-10.25, 10.25, 0.5), x_axis_title='Deviation from mean ToA of cluster', y_axis_title='# of pixels', title='Deviation from mean ToA of cluster', suffix='Deviation from mean ToA of cluster', fit=False)



    def convert_to_silab_format(self,file_name, trigger_data, trigger_width = 5, trigger_offset = 0):
        self.logger.info('Start Conversion to SiLab format...')
        output_file_name = file_name[:-3] + "_converted.h5"
        hit_data = None
        with tb.open_file(file_name, 'r+') as h5_file:
            data_type = {'names': ['event_number', 'frame', 'column', 'row', 'charge'],
               'formats': ['int64', 'uint64', 'uint16',  'uint16', 'float32']}

            for group in h5_file.root.interpreted:
                if hit_data:
                    hit_data = np.hstack((hit_data, group[:]))
                else:
                    hit_data = group[:]

        hit_data.sort(order="TOA_Combined") # sort according to ToA_Combined in order to make trigger assignment easier and possible
        hits = np.recarray((hit_data.shape[0]), dtype=data_type)

        hits["column"] = [x+1 for x in hit_data['x']]
        hits["row"] = [y+1 for y in hit_data['y']]
        hits["frame"] = hit_data["TOA_Combined"]

        # K7
        #a = 10.17
        #b = -4307.6
        #c = -52649.2
        #t = 268.85
        # I7 THR=800
        #a = 8.8
        #b = -3910.2
        #c = -66090.6
        #t = 258.61
        # I7 THR=1000
        a = 8.0
        b = -2964.3
        c = -46339.0
        t = 206.31
        # I7 THR=1100
        #a = 7.4
        #b = -2288.9
        #c = -7204.0
        #t = 236.44
        hits["charge"] = [3*np.abs(100*0.005-(-(b-value*25-t*a)/(2*a)+np.sqrt(((b-value*25-t*a)/(2*a))**2-(value*25*t-b*t-c)/a))*2/2.5*0.0025)/1.602*10**4 for value in hit_data["TOT"]]
        hits["frame"] = hit_data["TOA_Combined"]

        print("last data timestamp = %d"%(hit_data["TOA_Combined"][-1]))

        if np.any(hits["column"]<1):
            print("COLUMN PROBLEM")
        if np.any(hits["row"]<1):
            print("ROW PROBLEM")

        assigned = np.full(hit_data.shape[0], False)
        hits_add = np.recarray((hit_data.shape[0]), dtype=data_type)
        # assign triggers

        hits_index = 0
        first_hit_data_index = 0
        curr_add = 0
        for i in range(trigger_data.shape[0]):
            curr_hit_data = first_hit_data_index
            while curr_hit_data < len(hit_data) and (hit_data["TOA_Combined"][curr_hit_data] < (trigger_data["trigger_timestamp"][i]+trigger_width)):
                if np.abs(hit_data["TOA_Combined"][curr_hit_data].astype('int64') - trigger_data["trigger_timestamp"][i].astype('float64')) < trigger_width:
                    if assigned[curr_hit_data] == False:
                        hits["event_number"][curr_hit_data] = trigger_data["trigger_number"][i]
                        assigned[curr_hit_data] = True
                    else: #TODO: Evtl. doppelt zugeordnete Hits ganz rausschmeissen mit TLU?
                        # duplicate hit if necessary
                        hits_add["event_number"][curr_add] = trigger_data["trigger_number"][i]
                        hits_add["frame"][curr_add] = hits["frame"][curr_hit_data]
                        hits_add["row"][curr_add] = hits["row"][curr_hit_data]
                        hits_add["column"][curr_add] = hits["column"][curr_hit_data]
                        hits_add["charge"][curr_add] = hits["charge"][curr_hit_data]
                        curr_add += 1
                        if curr_add == len(hits_add):
                            hits_add2 = np.recarray((hit_data.shape[0]), dtype=data_type)
                            hits_add = np.hstack((hits_add, hits_add2))
                else:
                    first_hit_data_index = curr_hit_data
                curr_hit_data += 1

        n = len(assigned)-np.sum(assigned)
        print("%d Hits could not be assigned to a trigger. Throw them away?"%(n))
        print("There were %d additional assignments."%(curr_add))
        
        hits = np.hstack((hits, hits_add[:curr_add]))
        hits.sort(order="frame")

        
        with tb.open_file(output_file_name, mode='w', title=self.scan_id) as h5_file:
            h5_file.create_table(h5_file.root, 'Hits', hits, filters=tb.Filters(complib='zlib', complevel=5))

    def generate_trigger_from_DUT1(self,filename, min_size = 0, min_charge = 0):
        hist_size = []
        first = True
        with tb.open_file(filename, 'r+') as h5_file:
            for group in h5_file.root.reconstruction:
                hist_size = np.concatenate((hist_size, group.hits[:]), axis = None)
                if first == False:
                    histcha = np.concatenate((histcha, group.TOT[:]), axis = 0)
                    histtoa = np.concatenate((histtoa, group.TOA[:]), axis = 0)
                    hitindex = np.concatenate((histtoa, group.hit_index[:]), axis = 0)
                else:
                    histcha = np.array(group.TOT[:],dtype=object)
                    histtoa = np.array(group.TOA[:],dtype=object)
                    hitindex = np.array(group.hit_index[:],dtype=object)
                    first = False


        # K7
        #a = 10.17
        #b = -4307.6
        #c = -52649.2
        #t = 268.85
        # I7 THR=800
        #a = 8.8
        #b = -3910.2
        #c = -66090.6
        #t = 258.61
        # I7 THR=1000
        a = 8.0
        b = -2964.3
        c = -46339.0
        t = 206.31
        # I7 THR=1100
        #a = 7.4
        #b = -2288.9
        #c = -7204.0
        #t = 236.44
        # calculate total cluster charge
        histch = np.zeros(len(histcha))
        for i,el in enumerate(histcha):
            for value in  el:
                histch[i] += 3*np.abs(100*0.005-(-(b-value*25-t*a)/(2*a)+np.sqrt(((b-value*25-t*a)/(2*a))**2-(value*25*t-b*t-c)/a))*2/2.5*0.0025)/1.602*10**4

        # calculate mean ToA_Combined
        hist_toa_m = [np.mean(toa) for toa in histtoa] 

        # make table for triggers
        select = (hist_size >= min_size) & (histch >= min_charge)

        data_type = {'names': ['trigger_number', 'trigger_timestamp'],
            'formats': ['int64', 'float64']}
        trigger = np.recarray((np.sum(select)), dtype=data_type)
        trigger['trigger_timestamp'] = np.array(hist_toa_m,dtype=np.uint64)[select]
        trigger.sort(order="trigger_timestamp")
        trigger['trigger_number'] = range(np.sum(select))

        histtoa = None
        histcha = None
        histch = None

        dif = np.empty(trigger.shape[0]-1)
        for i in range(trigger.shape[0]-1):
            dif[i] = trigger['trigger_timestamp'][i+1]-trigger['trigger_timestamp'][i]

        plt.hist(dif, range=(np.amin(dif)-0.25, 30+0.25), bins = 50)
        plt.savefig("spread_clusters.png")

        self.logger.info('Start Conversion to SiLab format for trigger plane...')
        output_file_name = filename[:-3] + "_converted.h5"
        hit_data = None
        with tb.open_file(filename, 'r+') as h5_file:
            data_type = {'names': ['event_number', 'frame', 'column', 'row', 'charge'],
               'formats': ['int64', 'uint64', 'uint16',  'uint16', 'float32']}

            for group in h5_file.root.interpreted:
                if hit_data:
                    hit_data = np.hstack((hit_data, group[:]))
                else:
                    hit_data = group[:]

        hit_data.sort(order="hit_index")

        hits = np.recarray((hit_data.shape[0]), dtype=data_type)

        #hits["event_number"] = np.full(hit_data.shape[0])
        #hits["event_number"] = [math.floor(n/1000) for n in range(hit_data.shape[0])]
        hits["column"] = [x+1 for x in hit_data['x']]
        hits["row"] = [y+1 for y in hit_data['y']]
        hits["frame"] = hit_data["TOA_Combined"]

        # K7
        #a = 10.17
        #b = -4307.6
        #c = -52649.2
        #t = 268.85
        # I7 THR=800
        #a = 8.8
        #b = -3910.2
        #c = -66090.6
        #t = 258.61
        # I7 THR=1000
        a = 8.0
        b = -2964.3
        c = -46339.0
        t = 206.31
        # I7 THR=1100
        #a = 7.4
        #b = -2288.9
        #c = -7204.0
        #t = 236.44
        hits["charge"] = [3*np.abs(100*0.005-(-(b-value*25-t*a)/(2*a)+np.sqrt(((b-value*25-t*a)/(2*a))**2-(value*25*t-b*t-c)/a))*2/2.5*0.0025)/1.602*10**4 for value in hit_data["TOT"]]
        hits["frame"] = hit_data["TOA_Combined"]

        for i, idx in enumerate(hitindex):
            for l in idx:
                #hits["event_number"][hit_data["hit_index"]==l] = i
                hits["event_number"][l] = i

        hits.sort(order="event_number")

        if np.any(hits["column"]<1):
            print("COLUMN PROBLEM")
        if np.any(hits["row"]<1):
            print("ROW PROBLEM")

        with tb.open_file(output_file_name, mode='w', title=self.scan_id) as h5_file:
            h5_file.create_table(h5_file.root, 'Hits', hits, filters=tb.Filters(complib='zlib', complevel=5))

        return trigger

    def assign_event_number_by_toa(self,filename, toa_width = 10000):

        self.logger.info('Start Conversion to SiLab format with fixed event length...')
        output_file_name = filename[:-3] + "_converted_toa.h5"
        hit_data = None
        with tb.open_file(filename, 'r+') as h5_file:

            for group in h5_file.root.interpreted:
                if hit_data:
                    hit_data = np.hstack((hit_data, group[:]))
                else:
                    hit_data = group[:]

        hit_data.sort(order="hit_index")

        data_type = {'names': ['event_number', 'frame', 'column', 'row', 'charge'],
               'formats': ['int64', 'uint64', 'uint16',  'uint16', 'float32']}

        hits = np.recarray((hit_data.shape[0]), dtype=data_type)

        hits["column"] = [x+1 for x in hit_data['x']]
        hits["row"] = [y+1 for y in hit_data['y']]
        hits["frame"] = hit_data["TOA_Combined"]

        # K7
        #a = 10.17
        #b = -4307.6
        #c = -52649.2
        #t = 268.85
        # I7 THR=800
        #a = 8.8
        #b = -3910.2
        #c = -66090.6
        #t = 258.61
        # I7 THR=1000
        a = 8.0
        b = -2964.3
        c = -46339.0
        t = 206.31
        # I7 THR=1100
        #a = 7.4
        #b = -2288.9
        #c = -7204.0
        #t = 236.44
        hits["charge"] = [3*np.abs(100*0.005-(-(b-value*25-t*a)/(2*a)+np.sqrt(((b-value*25-t*a)/(2*a))**2-(value*25*t-b*t-c)/a))*2/2.5*0.0025)/1.602*10**4 for value in hit_data["TOT"]]
        hits["frame"] = hit_data["TOA_Combined"]

        hits["event_number"] = np.floor(hits["frame"]/toa_width)

        hits.sort(order="event_number")

        if np.any(hits["column"]<1):
            print("COLUMN PROBLEM")
        if np.any(hits["row"]<1):
            print("ROW PROBLEM")

        with tb.open_file(output_file_name, mode='w', title=self.scan_id) as h5_file:
            h5_file.create_table(h5_file.root, 'Hits', hits, filters=tb.Filters(complib='zlib', complevel=5))

    def set_directory(self,sub_dir=None):
        # Get the user directory
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        if not os.path.exists(user_path):
            os.makedirs(user_path)
        
        # Store runs in '~/Timepix3/data' and other scans in '~/Timepix3/scans'
        if self.scan_id == "data_take":
            scan_path = os.path.join(user_path, 'data')
        else:
            scan_path = os.path.join(user_path, 'scans')

        if not os.path.exists(scan_path):
            os.makedirs(scan_path)

        # Setup the output_data directory
        if sub_dir:
            self.working_dir = os.path.join(scan_path, sub_dir)
            if not os.path.exists(self.working_dir):
                os.makedirs(self.working_dir)
        else:
            self.working_dir = scan_path

    def make_files(self):
        # Create the filename for the HDF5 file and the logger by combining timestamp and run_name
        self.timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.run_name = self.scan_id + '_' + self.timestamp
        output_path = os.path.join(self.working_dir, 'hdf')
        self.output_filename = os.path.join(output_path, self.run_name)

        # Setup the logger and the logfile
        self.logger = logging.getLogger("DataAnalysis")
        self.logger.setLevel(logging.INFO)
        self.setup_logfile()
        self.logger.info('Initializing %s...', self.__class__.__name__)

    def setup_logfile(self):
        '''
            Setup the logfile
        '''
        output_path = os.path.join(self.working_dir, 'logs')
        logger_filename = os.path.join(output_path, self.run_name)
        self.fh = logging.FileHandler(logger_filename + '.log')
        self.fh.setLevel(logging.INFO)
        self.fh.setFormatter(logging.Formatter("%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s"))
        for lg in six.itervalues(logging.Logger.manager.loggerDict):
            if isinstance(lg, logging.Logger):
                lg.addHandler(self.fh)

        return self.fh
            



if __name__ == "__main__":
    # get command line arguments
    parser = argparse.ArgumentParser(description='Script to analyse Timepix3 data')
    parser.add_argument('filename', 
                        metavar='datafile', 
                        help='Name of the file to be analysed')
    parser.add_argument('--big',
                        action='store_true',
                        help="Use this if your data is to big to analyse efficiently in one chunk")
    args_dict = vars(parser.parse_args())
    file_name = args_dict['filename']
    # convert file name to path
    if file_name.endswith('h5'):
        print('OK, thanks.')
    else:
        print("Please choose a correct data file")
    user_path = '~'
    user_path = os.path.expanduser(user_path)
    user_path = os.path.join(user_path, 'Timepix3')
    user_path = os.path.join(user_path, 'data')
    user_path = os.path.join(user_path, 'hdf')
    datafile = user_path + os.sep +file_name
    if not os.path.isfile(datafile): 
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'scans')
        user_path = os.path.join(user_path, 'hdf')
        datafile = user_path + os.sep +file_name
    # analyze and plot
    plotter = DataAnalysis()
    plotter.set_directory()
    plotter.make_files()
    #plotter.analyze(datafile, args_dict)
    #plotter.plot(datafile)
    #plotter.convert_to_silab_format(datafile)
    trigger_list = plotter.generate_trigger_from_DUT1(datafile)
    plotter.assign_event_number_by_toa(datafile)
    #print("# triggers found: %d"%(trigger_list.shape[0]))
    #print("last trigger timestamp = %d"%(trigger_list["trigger_timestamp"][-1]))
    #plotter.convert_to_silab_format(datafile, trigger_list)

