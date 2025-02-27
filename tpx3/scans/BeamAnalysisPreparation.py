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

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

from numba import njit

import sys
import os
import argparse



class BeamAnalysisPreparation():    

    scan_id = "BeamAnalysisPreparation"

    """
        Convert existing hdf5 file which is allready analysed into the format necessary for reading it
        in the beam telescope analysis (@SiLab). It requires:
        - name/location of the hdf5 file with the data
        - trigger data: reqarray with two columns: trigger_number and trigger_timestamp
        - trigger width: # of max ToA difference for a hit to be assigned to the trigger
        - trigger offset: offset in ToA between trigger timestamp and toa to correct for
            imperfect synchronization
    """
    def convert_to_silab_format(self,file_name, trigger_data, output_file_name, trigger_width = 5, trigger_offset = 0):
        print('Start Conversion to SiLab format...')
        hit_data = None
        with tb.open_file(file_name, 'r+') as h5_file:
            data_type = {'names': ['event_number', 'frame', 'column', 'row', 'charge'],
               'formats': ['int64', 'uint64', 'uint16',  'uint16', 'float32']}

            first = True
            for group in h5_file.root.interpreted:
                if first == False:
                    hit_data = np.hstack((hit_data, group[:]))
                else:
                    hit_data = group[:]
                    first = False

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
        pbar = tqdm(total = trigger_data.shape[0])
        for i in range(trigger_data.shape[0]):
            curr_hit_data = first_hit_data_index
            while curr_hit_data < len(hit_data) and (hit_data["TOA_Combined"][curr_hit_data] < (trigger_data["trigger_timestamp"][i]+trigger_width)):
                if np.abs(hit_data["TOA_Combined"][curr_hit_data].astype('int64') - trigger_data["trigger_timestamp"][i].astype('float')) < trigger_width:
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
            pbar.update(1)
        pbar.close()

        n = len(assigned)-np.sum(assigned)
        print("%d Hits could not be assigned to a trigger. Throw them away."%(n))
        print("There were %d additional assignments."%(curr_add))
        hits = hits[assigned]

        hits = np.hstack((hits, hits_add[:curr_add]))
        hits.sort(order="frame")


        with tb.open_file(output_file_name, mode='w', title=self.scan_id) as h5_file:
            h5_file.create_table(h5_file.root, 'Hits', hits, filters=tb.Filters(complib='zlib', complevel=5))


    """
        Convert existing hdf5 file which is allready analysed into the format necessary for reading it
        in the beam telescope analysis (@SiLab). The assignment is based on the mean ToA in each cluster.
        It requires:
        - name/location of the hdf5 file with the data
        - trigger data: reqarray with two columns: trigger_number and trigger_timestamp
        - trigger width: # of max ToA difference for a hit to be assigned to the trigger
        - trigger offset: offset in ToA between trigger timestamp and toa to correct for
            imperfect synchronization
    """
    def convert_to_silab_format_cluster_based(self,file_name, trigger_data, output_file_name, trigger_width = 5, trigger_offset = 0):
        print('Start Conversion to SiLab format...')
        hit_data = None
        with tb.open_file(file_name, 'r+') as h5_file:
            data_type = {'names': ['event_number', 'frame', 'column', 'row', 'charge'],
               'formats': ['int64', 'uint64', 'uint16',  'uint16', 'float32']}

            first = True
            for group in h5_file.root.interpreted:
                if first == False:
                    hit_data = np.hstack((hit_data, group[:]))
                else:
                    hit_data = group[:]
                    first = False

            first = True
            for group in h5_file.root.reconstruction:
                if first == False:
                    histtoa = np.concatenate((histtoa, group.TOA[:]), axis = 0)
                    hitindex = np.concatenate((hitindex, group.hit_index[:]), axis = 0)
                else:
                    histtoa = np.array(group.TOA[:],dtype=object)
                    hitindex = np.array(group.hit_index[:],dtype=object)
                    first = False

        histtoa_mean = [np.mean(toa) for toa in histtoa] 

        hit_data.sort(order="TOA_Combined") # sort according to ToA_Combined in order to make trigger assignment easier and possible
        trigger_data.sort(order="trigger_timestamp")
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

        ind = np.argsort(histtoa_mean)
        histtoa_mean.sort()
        hitindex = np.take_along_axis(hitindex, ind, axis=0)

        assigned = np.full(len(histtoa_mean), False)
        first = True

        hits_trigger = np.recarray((hit_data.shape[0]), dtype=data_type)

        # assign triggers
        hits_index = 0
        first_cluster_index = 0
        curr_add = 0
        curr_first_ind = 0
        pbar = tqdm(total = trigger_data.shape[0])
        for i in range(trigger_data.shape[0]):
            curr_cluster = first_cluster_index
            while curr_cluster < len(histtoa_mean) and (histtoa_mean[curr_cluster] < (trigger_data["trigger_timestamp"][i]+trigger_width)):
                if np.abs(histtoa_mean[curr_cluster] - trigger_data["trigger_timestamp"][i].astype('float')) < trigger_width:
                    if assigned[curr_cluster] == False:
                        assigned[curr_cluster] = True
                    hits_add = hits[hitindex[curr_cluster]]
                    hits_add["event_number"] = np.full(hits_add.shape[0], trigger_data["trigger_number"][i])
                    len_add = hits_add.shape[0]
                    if not (len_add+curr_first_ind)<hits_trigger.shape[0]:
                        hits_trigger = np.hstack((hits_trigger, np.recarray((hit_data.shape[0]), dtype=data_type)))
                    hits_trigger[curr_first_ind:curr_first_ind+len_add] = hits_add
                    curr_first_ind += len_add
                    curr_add += 1
                else:
                    first_cluster_index = curr_cluster
                curr_cluster += 1
                #print(str(curr_cluster)+"/"+str(len(histtoa_mean)))
            pbar.update(1)
        pbar.close()
        hits_trigger = hits_trigger[:curr_first_ind]
            

        n = len(assigned)-np.sum(assigned)
        print("%d Clusters could not be assigned to a trigger. Throw them away."%(n))
        #hits = hits[assigned]


        with tb.open_file(output_file_name, mode='w', title=self.scan_id) as h5_file:
            h5_file.create_table(h5_file.root, 'Hits', hits_trigger, filters=tb.Filters(complib='zlib', complevel=5))


    """
        Convert existing hdf5 file which is allready analysed into the format necessary for reading it
        in the beam telescope analysis (@SiLab). The input file is used to generate a table of triggers.
        The mean ToA of each cluster is taken as trigger timestamp and the number is assigned consecutively
        It requires:
        - name/location of the hdf5 file with the data
        - trigger data: reqarray with two columns: trigger_number and trigger_timestamp
        - min_size: minimal size of a cluster to use it as a trigger seed
        - min_charge: minimal charge in a cluster to use it as a trigger seed
    """
    def generate_trigger_from_DUT1(self,filename, output_file_name, min_size = 2, min_charge = 0, trigger_width = 5):
        hist_size = []
        first = True
        with tb.open_file(filename, 'r+') as h5_file:
            for group in h5_file.root.reconstruction:
                hist_size = np.concatenate((hist_size, group.hits[:]), axis = None)
                if first == False:
                    histcha = np.concatenate((histcha, group.TOT[:]), axis = 0)
                    histtoa = np.concatenate((histtoa, group.TOA[:]), axis = 0)
                    hitindex = np.concatenate((hitindex, group.hit_index[:]), axis = 0)
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
            'formats': ['int64', 'float']}
        trigger = np.recarray((np.sum(select)), dtype=data_type)
        trigger['trigger_timestamp'] = np.array(hist_toa_m,dtype=float)[select]
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

        print('Start Conversion to SiLab format for trigger plane...')
        hit_data = None
        with tb.open_file(filename, 'r+') as h5_file:
            data_type = {'names': ['event_number', 'frame', 'column', 'row', 'charge'],
               'formats': ['int64', 'uint64', 'uint16',  'uint16', 'float32']}

            first = True
            for group in h5_file.root.interpreted:
                if first == False:
                    hit_data = np.hstack((hit_data, group[:]))
                else:
                    hit_data = group[:]
                    first = False

        hit_data.sort(order="hit_index")

        hits = np.recarray((hit_data.shape[0]), dtype=data_type)

        select_index = np.full(hits.shape[0], False)

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

        for i, array in enumerate(hitindex[select]):
            for index in array:
                hits["event_number"][index] = i
                select_index[index] = True
                if hits["event_number"][index] == 0:
                        print("Event number still 0.")

        #print(hits)

        num_unassigned = hits.shape[0]-np.sum(select_index)
        print(str(num_unassigned)+" hits did not pass the requirements on the clusters and were thus removed from the data.")
        hits = hits[select_index]

        hits.sort(order="event_number")

        if np.any(hits["column"]<1):
            print("COLUMN PROBLEM")
        if np.any(hits["row"]<1):
            print("ROW PROBLEM")

        with tb.open_file(output_file_name, mode='w', title=self.scan_id) as h5_file:
            h5_file.create_table(h5_file.root, 'Hits', hits, filters=tb.Filters(complib='zlib', complevel=5))

        return trigger

    """
        Convert existing hdf5 file which is allready analysed into the format necessary for reading it
        in the beam telescope analysis (@SiLab). The event number is assigned consecutively for ToA intervals
        of fixed length.
        It requires:
        - name/location of the hdf5 file with the data
        - toa_width: width of the ToA-interval that is assigned the same event number
    """
    def assign_event_number_by_toa(self, filename, output_file_name, toa_width = 200000):

        print('Start Conversion to SiLab format with fixed event length...')
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


if __name__ == "__main__":
    # get command line arguments
    parser = argparse.ArgumentParser(description='Script to analyse Timepix3 data')
    parser.add_argument('inputfolder',
                        metavar='inputfolder',
                        help='Input folder')
    parser.add_argument('filenames_string',
                        metavar='datafiles',
                        help='Name of the files to be analysed')
    parser.add_argument('--toa',
                        action='store_true',
                        help='Use this to generate events as equally long toa frames')
    args_dict = vars(parser.parse_args())

    file_names = args_dict['filenames_string'].split(";")
    datafiles = [args_dict['inputfolder']+filename for filename in file_names]
    toa_split = args_dict["toa"]

    # analyze and plot
    prep = BeamAnalysisPreparation()
    if toa_split==False:
        trigger_list = prep.generate_trigger_from_DUT1(datafiles[0], output_file_name=datafiles[0][:-3]+"_DUT0.h5")
        for i in range(1, len(datafiles)):
            #prep.convert_to_silab_format(datafiles[i], trigger_list, output_file_name=datafiles[i][:-3]+"_DUT"+str(i)+".h5")
            prep.convert_to_silab_format_cluster_based(datafiles[i], trigger_list, output_file_name=datafiles[i][:-3]+"_DUT"+str(i)+".h5")
        print("# triggers found: %d"%(trigger_list.shape[0]))
        print("last trigger timestamp = %d"%(trigger_list["trigger_timestamp"][-1]))
    else:
        for i in range(len(datafiles)):
            prep.assign_event_number_by_toa(datafiles[i],datafiles[i][:-3]+"_toa_DUT"+str(i)+".h5")