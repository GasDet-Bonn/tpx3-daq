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
import random

import matplotlib.backends.backend_pdf



class Preparation():    

    scan_id = "BeamAnalysisPreparation"
    
    """
        Convert existing hdf5 file which is allready analysed into the format necessary for reading it
        in the beam telescope analysis (@SiLab). It requires:
        - name/location of the hdf5 file with the data
        - trigger data: reqarray with two columns: trigger_id and timestamp
        - trigger width: # of max ToA difference for a hit to be assigned to the trigger
        - trigger offset: offset in ToA between trigger timestamp and toa to correct for
            imperfect synchronization
    """
    def convert_to_silab_format(self,file_name, trigger_data, output_file_name, trigger_width = 20, trigger_offset = -12355, no_save = False, max_hits = None):
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

            run_config = h5_file.root.configuration.run_config[:]
            chip_id = 'W'+str([row[1] for row in run_config if row[0]==b'chip_wafer'][0]).split("'")[1]+'-'+str([row[1] for row in run_config if row[0]==b'chip_x'][0]).split("'")[1]+str([row[1] for row in run_config if row[0]==b'chip_y'][0]).split("'")[1]
        
        if max_hits != None:
            hit_data = hit_data[:max_hits]

        hit_data.sort(order="TOA_Combined") # sort according to ToA_Combined in order to make trigger assignment easier and possible
        hits = np.recarray((hit_data.shape[0]), dtype=data_type)

        hits["column"] = [x+1 for x in hit_data['x']]
        hits["row"] = [y+1 for y in hit_data['y']]
        hits["frame"] = hit_data["TOA_Combined"]

        conversion = True

        # Testbeam 1
        if(chip_id == "W18-D8"):
            print("We have data from W18-D8.")
            a = 0.34
            b = 6.65
            c = 8812.12
            t = -83.82
        elif(chip_id == "W18-J6"):
            print("We have data from W18-J6.")
            a = 0.3
            b = 122.19
            c = 85672.8
            t = -431.79
        elif(chip_id == "W18-L9"):
            print("We have data from W18-L9.")
            a = 0.25
            b = 112.81
            c = 82640.67
            t = -448.07
        else:
            print("We have data from an unknown chip. No conversion ToT -> charge")
            conversion = False

        # Testbeam 2
        """if(chip_id == "W18-D8"):
            print("We have data from W18-D8.")
            a = 0.15
            b = 315.53
            c = 363259.81
            t = -987.80
        elif(chip_id == "W18-J6"):
            print("We have data from W18-J6.")
            a = 0.3
            b = 58.43
            c = 35030.73
            t = -266.66
        elif(chip_id == "W18-L9"):
            print("We have data from W18-L9.")
            a = 0.28
            b = 29.25
            c = 17100.57
            t = -185.60
        else:
            print("We have data from an unknown chip. No conversion ToT -> charge")
            conversion = False"""

        if conversion == True:
            hits["charge"] = [3*np.abs(100*0.005-(-(b-value*25-t*a)/(2*a)+np.sqrt(((b-value*25-t*a)/(2*a))**2-(value*25*t-b*t-c)/a))*2/2.5*0.0025)/1.602*10**4 for value in hit_data["TOT"]]
        else:
            hits["charge"] = hit_data["ToT"]
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
        if no_save == False:
            pbar = tqdm(total = trigger_data.shape[0])
        for i in range(trigger_data.shape[0]):
            curr_hit_data = first_hit_data_index
            while curr_hit_data < len(hit_data) and ((hit_data["TOA_Combined"][curr_hit_data]+trigger_offset) < (trigger_data["timestamp"][i]+trigger_width)):
                if np.abs((hit_data["TOA_Combined"][curr_hit_data].astype('int64')+trigger_offset) - trigger_data["timestamp"][i].astype('float64')) < trigger_width:
                    if assigned[curr_hit_data] == False:
                        hits["event_number"][curr_hit_data] = trigger_data["trigger_id"][i]
                        assigned[curr_hit_data] = True
                    else: #TODO: Evtl. doppelt zugeordnete Hits ganz rausschmeissen mit TLU?
                        # duplicate hit if necessary
                        hits_add["event_number"][curr_add] = trigger_data["trigger_id"][i]
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
            if no_save == False:
                pbar.update(1)
        if no_save == False:
            pbar.close()

        n = len(assigned)-np.sum(assigned)
        print("%d Hits were assigned to a trigger."%np.sum(assigned))
        print("%d Hits could not be assigned to a trigger. Throw them away."%(n))
        print("There were %d additional assignments."%(curr_add))
        hits = hits[assigned]

        """trigger_id = hits["event_number"][:]
        plt.hist(trigger_id, bins=int(np.amax(trigger_id)/50))
        plt.savefig("trigger_id.png")"""
        
        if no_save == False:
            hits = np.hstack((hits, hits_add[:curr_add]))
            hits.sort(order="event_number")
            with tb.open_file(output_file_name, mode='w', title=self.scan_id) as h5_file:
                h5_file.create_table(h5_file.root, 'Hits', hits, filters=tb.Filters(complib='zlib', complevel=5))

        return np.sum(assigned)


    """
        Convert existing hdf5 file which is allready analysed into the format necessary for reading it
        in the beam telescope analysis (@SiLab). The assignment is based on the mean ToA in each cluster.
        It requires:
        - name/location of the hdf5 file with the data
        - trigger data: reqarray with two columns: trigger_id and timestamp
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
        trigger_data.sort(order="timestamp")
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
            while curr_cluster < len(histtoa_mean) and (histtoa_mean[curr_cluster] < (trigger_data["timestamp"][i]+trigger_width)):
                if np.abs(histtoa_mean[curr_cluster] - trigger_data["timestamp"][i].astype('float64')) < trigger_width:
                    if assigned[curr_cluster] == False:
                        assigned[curr_cluster] = True
                    hits_add = hits[hitindex[curr_cluster]]
                    hits_add["event_number"] = np.full(hits_add.shape[0], trigger_data["trigger_id"][i])
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
        - trigger data: reqarray with two columns: trigger_id and timestamp
        - min_size: minimal size of a cluster to use it as a trigger seed
        - min_charge: minimal charge in a cluster to use it as a trigger seed
    """
    def generate_trigger_from_DUT1(self,filename, output_file_name, min_size = 0, min_charge = 0, trigger_width = 5):
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

        data_type = {'names': ['trigger_id', 'timestamp'],
            'formats': ['int64', 'float64']}
        trigger = np.recarray((np.sum(select)), dtype=data_type)
        trigger['timestamp'] = np.array(hist_toa_m,dtype=np.float64)[select]
        trigger.sort(order="timestamp")
        trigger['trigger_id'] = range(np.sum(select))

        histtoa = None
        histcha = None
        histch = None

        dif = np.empty(trigger.shape[0]-1)
        for i in range(trigger.shape[0]-1):
            dif[i] = trigger['timestamp'][i+1]-trigger['timestamp'][i]

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
    def assign_event_number_by_toa(self, filename, output_file_name, toa_width = 2000):

        print('Start Conversion to SiLab format with fixed event length...')
        hit_data = None
        first = True
        with tb.open_file(filename, 'r+') as h5_file:

            for group in h5_file.root.interpreted:
                if first == False:
                    hit_data = np.hstack((hit_data, group[:]))
                else:
                    hit_data = group[:]
                    first = False

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


    """
    read trigger data from h5 file and store in array
    """
    def read_trigger(self,file_name):
        print('Start Conversion to SiLab format...')
        trigger_data = None
        with tb.open_file(file_name, 'r+') as h5_file:
            first = True
            for group in h5_file.root.trigger:
                if first == False:
                    trigger_data = np.hstack((trigger_data, group[:]))
                else:
                    trigger_data = group[:]
                    first = False

        trigger_data.sort(order="timestamp")
        
        return trigger_data

    """
    Based on two data files of two Timepix3 planes with triggers, the relative clock difference 
    over time can be determined. Usefull to apply to data without tlu triggers.
    """
    def compare_trigger_timeshift(self, file_name_ref, file_name_trial, output_pdf):
        trigger_data = None
        with tb.open_file(file_name_ref, 'r+') as h5_file_ref: 
            first = True               
            for group in h5_file_ref.root.trigger:
                if first == False:
                    trigger_data_ref = np.hstack((trigger_data, group[:]))
                else:
                    trigger_data_ref = group[:]
                    first = False

        with tb.open_file(file_name_trial, 'r+') as h5_file_trial:
            first = True 
            for group in h5_file_trial.root.trigger:
                if first == False:
                    trigger_data_trial = np.hstack((trigger_data, group[:]))
                else:
                    trigger_data_trial = group[:]
                    first = False

        id_trial = trigger_data_trial["trigger_id"][:]
        id_ref = trigger_data_ref["trigger_id"][:]
        print(id_ref)
        print(id_trial)

        trigger_id = np.zeros(len(id_ref), dtype = np.int64)
        time_diff = np.zeros(len(id_ref), dtype = np.int64)

        ids, counts = np.unique(id_trial, return_counts=True)
        print(np.unique(counts, return_counts=True))

        for i in range(len(id_ref)):
            if id_ref[i] in id_trial:
                j = np.argwhere(id_trial == id_ref[i])[0][0]
                diff = np.int64(trigger_data_ref["timestamp"][i])-np.int64(trigger_data_trial["timestamp"][j])
                time_diff[i] = diff
                trigger_id[i] = id_ref[i]

        print(time_diff)

        time_diff = time_diff[trigger_id != 0]
        trigger_id = trigger_id[trigger_id != 0]

        print(np.amax(time_diff))

        plt.plot(trigger_id, time_diff,'ro', markersize=0.1)
        plt.xlabel("trigger_id")
        plt.ylabel("Difference in clock cycles")
        plt.title("Difference between the two detectors over the different trigger ids")
        plt.ylim((0,50000))
        output_pdf.savefig()
        plt.clf()

        plt.plot(id_ref, trigger_data_ref["timestamp"],'bo', markersize=0.1, label="Detektor A")
        plt.plot(id_trial, trigger_data_trial["timestamp"],'ro', markersize=0.1, label="Detektor B")
        plt.xlabel("trigger_id")
        plt.ylabel("timestamp")
        plt.title("Timestamp vs. Trigger id for the two detectors")
        plt.legend()
        output_pdf.savefig()
        plt.clf()

        plt.plot(id_ref, trigger_data_ref["timestamp"],'bo', markersize=0.1, label="Detektor A")
        plt.xlabel("trigger_id")
        plt.ylabel("timestamp")
        plt.legend()
        plt.title("Timestamp vs. Trigger id for detector A")
        #plt.ylim((0,5000))
        output_pdf.savefig()
        plt.clf()

        plt.plot(id_trial, trigger_data_trial["timestamp"],'ro', markersize=0.1, label="Detektor B")
        plt.xlabel("trigger_id")
        plt.ylabel("timestamp")
        plt.legend()
        plt.title("Timestamp vs. Trigger id for detector B")
        #plt.ylim((0,5000))
        output_pdf.savefig()
        plt.clf()

        plt.plot(id_ref[:-1], np.diff(trigger_data_ref["timestamp"]),'bo', markersize=0.1, label="Detektor A")
        plt.xlabel("trigger_id")
        plt.ylabel("timestamp")
        plt.legend()
        plt.title("Difference between two successing timestamps for detector A")
        plt.ylim((0,40000))
        output_pdf.savefig()
        plt.clf()

        plt.plot(id_trial[:-1], np.diff(trigger_data_trial["timestamp"]),'ro', markersize=0.1, label="Detektor B")
        plt.xlabel("trigger_id")
        plt.ylabel("timestamp")
        plt.legend()
        plt.title("Difference between two successing timestamps for detector B")
        plt.ylim((0,40000))
        output_pdf.savefig()
        plt.clf()

    """
    Function to determine the offset (and width) necessary to assign the trigger numbers to the data. The offset 
    between the trigger timestamp and the data timestamp is usually in the range of a -10000 (meaning the tlu 
    timestamp is later than it should be)
    """
    def get_offset(self, file_name, trigger_list, output_file_name, offset_min, offset_max, output_pdf):
        print("Calculate rough estimate for the offset between trigger and data.")
        with tb.open_file(file_name, 'r+') as h5_file:
            run_config = h5_file.root.configuration.run_config[:]
            chip_id = 'W'+str([row[1] for row in run_config if row[0]==b'chip_wafer'][0]).split("'")[1]+'-'+str([row[1] for row in run_config if row[0]==b'chip_x'][0]).split("'")[1]+str([row[1] for row in run_config if row[0]==b'chip_y'][0]).split("'")[1]
        
        # Calculate a first estimate for the offset between trigger and data, using a rather broad width for the search
        # window
        assigned_list = []
        stepsize = 5000
        iteration_array = np.arange(offset_min, offset_max+2500, 5000)
        pbar = tqdm(total = len(iteration_array))
        for i in iteration_array:
            sys.stdout = open(os.devnull, 'w')
            assigned_list.append(prep.convert_to_silab_format(file_name, trigger_list, output_file_name,trigger_offset = i, trigger_width = stepsize*2, no_save = True))
            sys.stdout = sys.__stdout__
            pbar.update()
        pbar.close()
        assigned_max = np.amax(assigned_list)
        index_high = np.where(assigned_list>assigned_max*0.9)[0]
        offset_coarse = (iteration_array[index_high[0]]+iteration_array[index_high[-1]])/2
        
        # plot the results
        print("Result: "+str(offset_coarse))
        plt.axvline(x=offset_coarse, label="fine offset at %d"%(offset_coarse))
        plt.plot(iteration_array,assigned_list)
        plt.title("Rough offset search for detector "+chip_id+", trigger width = 5000")
        plt.legend()
        output_pdf.savefig()
        plt.close()

        # repeat the search with a smaller window width around the rough estimate for the offset calculated before
        assigned_list = []
        iteration_array = np.arange(int(offset_coarse-2500), int(offset_coarse+2500), 100)
        print("Calculate final estimate for the offset between trigger and data.")
        pbar = tqdm(total=len(iteration_array))
        for i in iteration_array:
            sys.stdout = open(os.devnull, 'w')
            assigned_list.append(prep.convert_to_silab_format(file_name, trigger_list, output_file_name,trigger_offset = i, trigger_width = 100, no_save = True))
            sys.stdout = sys.__stdout__
            pbar.update()
        pbar.close()
        max_value = np.amax(assigned_list)
        index_high = np.where(assigned_list>max_value*0.9)[0]
        offset_fine = (iteration_array[index_high[0]]+iteration_array[index_high[-1]])/2
        plt.axvline(x=offset_fine, label="fine offset at %d"%(offset_fine))
        plt.plot(iteration_array,assigned_list)
        plt.title("Fine offset search for detector "+chip_id+", trigger width = 100")
        plt.legend()
        output_pdf.savefig()
        print("Result: "+str(offset_fine))

        # possibility to also determine the optimal width. It proved however to be quite efficient to just
        # use a width of 100 for reasonable low rates. This was thus commented out (and anyway not working perfectly)
        """assigned_list = np.array(assigned_list)[iteration_array>offset_fine]
        iteration_array = np.array(iteration_array)[iteration_array>offset_fine]
        index_high = np.where(assigned_list>=max_value*0.9)[0]
        index_low = np.where(assigned_list<=max_value*0.1)[0]
        width = iteration_array[index_low[0]]-iteration_array[index_high[-1]]
        print("Trigger width: "+str(width))
        offset_fine = offset_coarse"""
        width = 100
        return offset_fine, width

    """
    Based on the original analysis file and the (newly) created DUT file, histograms comparing the amount of available
    triggers and triggers to which data was assigned are drawn. Very usefull for debugging.
    """
    def check_trigger_assignment(self, trigger_list, input_file, orig_file, output_pdf):
        with tb.open_file(orig_file, 'r+') as h5_file:
            run_config = h5_file.root.configuration.run_config[:]
            chip_id = 'W'+str([row[1] for row in run_config if row[0]==b'chip_wafer'][0]).split("'")[1]+'-'+str([row[1] for row in run_config if row[0]==b'chip_x'][0]).split("'")[1]+str([row[1] for row in run_config if row[0]==b'chip_y'][0]).split("'")[1]

        with tb.open_file(input_file, "r") as h5_file:
            hits = h5_file.root.Hits[:]

        trigger_used = np.unique(hits["event_number"])
        fig = plt.figure()
        plt.hist(trigger_list["trigger_id"], bins = 500, range=(np.amin(trigger_list["trigger_id"]),np.amax(trigger_list["trigger_id"])), alpha = 0.5, label = "existing triggers")
        plt.hist(trigger_used, bins = 500, range=(np.amin(trigger_used),np.amax(trigger_used)), alpha = 0.5, label = "assigned triggers")
        plt.legend()
        plt.xlabel("Event number")
        plt.ylabel("#")
        plt.title("Comparison between available and assigned triggers in detector "+chip_id)
        output_pdf.savefig()
        plt.close()

        fig = plt.figure()
        plt.hist(hits["frame"], bins = 500, range=(np.amin(hits["frame"]),np.amax(hits["frame"])), alpha = 0.5)
        plt.legend()
        plt.xlabel("ToA Combined")
        plt.ylabel("#")
        output_pdf.savefig()
        plt.close()

        fig = plt.figure()
        plt.hist(trigger_used, bins = 100, range=(436000,437000), alpha = 0.5)
        plt.legend()
        plt.xlabel("Assigned triggers")
        plt.ylabel("#")
        output_pdf.savefig()
        plt.close()


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
    parser.add_argument('--tlu', 
                        action='store_true',
                        help='Generate events from TLU trigger data')
    args_dict = vars(parser.parse_args())

    file_names = args_dict['filenames_string'].split(";")
    for i in range(len(file_names)):
        if file_names[i].startswith("data_take"):
            file_names[i] = file_names[i].replace("data_take","analysis")
    datafiles = [args_dict['inputfolder']+filename for filename in file_names]
    toa_split = args_dict["toa"]
    tlu = args_dict["tlu"]

    # output pdf for plots
    pdf = matplotlib.backends.backend_pdf.PdfPages(datafiles[0].replace("analysis","prep").replace(".h5",".pdf"))

    prep = Preparation()

    # analyze and plot
    if tlu == False: # no tlu data, generate trigger from first TPX3 plane
        if toa_split==False:
            trigger_list = prep.generate_trigger_from_DUT1(datafiles[0], output_file_name=datafiles[0][:-3]+"_DUT0.h5")
            for i in range(1, len(datafiles)):
                prep.convert_to_silab_format(datafiles[i], trigger_list, output_file_name=datafiles[i][:-3]+"_DUT"+str(i)+".h5")
            print("# triggers found: %d"%(trigger_list.shape[0]))
            print("last trigger timestamp = %d"%(trigger_list["timestamp"][-1]))
        else:
            for i in range(len(datafiles)):
                prep.assign_event_number_by_toa(datafiles[i],datafiles[i][:-3]+"_toa_DUT"+str(i)+".h5")
    else: # tlu data, use for triggering
        for i in range(0, len(datafiles)):
            trigger_list = prep.read_trigger(datafiles[i])
            offset, width = prep.get_offset(datafiles[i], trigger_list, output_file_name=datafiles[i][:-3]+"_DUT"+str(i)+".h5", offset_min = -30000, offset_max = 00000, output_pdf = pdf)
            prep.convert_to_silab_format(datafiles[i], trigger_list, output_file_name=datafiles[i][:-3]+"_DUT"+str(i)+".h5", trigger_offset=offset, trigger_width = width)
            prep.check_trigger_assignment(trigger_list, datafiles[i].replace(".h5", "_DUT0.h5"), orig_file = datafiles[i], output_pdf = pdf)

    pdf.close()
