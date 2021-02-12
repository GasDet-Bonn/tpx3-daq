#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    Script to convert raw data
'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
import numpy as np
from basil.utils.BitLogic import BitLogic
import logging
from tqdm import tqdm
import multiprocessing as mp
from functools import partial
from scipy.optimize import curve_fit
from scipy.special import erf
from numba import njit, prange
import math
from six.moves import range
import sys

logger = logging.getLogger('Analysis')

_lfsr_4_lut = np.zeros((2 ** 4), dtype=np.uint16)
_lfsr_10_lut = np.zeros((2 ** 10), dtype=np.uint16)
_lfsr_14_lut = np.zeros((2 ** 14), dtype=np.uint16)
_gray_14_lut = np.zeros((2 ** 14), dtype=np.uint16)

@njit(parallel = True)
def scurve_hist(hit_data, param_range):
    scurves = np.zeros((256*256, len(param_range)), dtype=np.uint16)

    for i in prange(hit_data.shape[0]):
        x = hit_data['x'][i]
        y = hit_data['y'][i]
        p = hit_data['scan_param_id'][i]
        c = hit_data['EventCounter'][i]
        scurves[x*256+y,p] += c

    return scurves

@njit
def totcurve_hist(hit_data, param_range):
    totcurves = np.zeros((256*256, len(param_range)), dtype=np.uint16)

    for i in range(hit_data.shape[0]):
        x = hit_data['x'][i]
        y = hit_data['y'][i]
        p = hit_data['scan_param_id'][i]
        c = hit_data['TOT'][i]
        totcurves[x*256+y,p] += c

    return totcurves

@njit
def noise_pixel_count(hit_data, param_range, Vthreshold_start):
    noise_curve = np.zeros(len(param_range) + Vthreshold_start, dtype=np.uint16)
    pixel_list = np.zeros((256*256, Vthreshold_start + len(param_range)), dtype=np.uint16)

    for i in range(hit_data.shape[0]):
        x = hit_data['x'][i]
        y = hit_data['y'][i]
        p = hit_data['scan_param_id'][i]
        if pixel_list[x * 256 + y, p + Vthreshold_start] == 0:
            noise_curve[p + Vthreshold_start] += 1
        pixel_list[x * 256 + y, p + Vthreshold_start] += 1

    return noise_curve

def vths(scurves, param_range, Vthreshold_start):
    vths = np.zeros((256, 256), dtype=np.uint16)
    for x in range(256):
        for y in range(256):
            sum_of_hits = 0
            weighted_sum_of_hits = 0
            for i in range(len(param_range)):
                sum_of_hits += scurves[x*256+y, i]
                weighted_sum_of_hits += scurves[x*256+y, i] * i
            if(sum_of_hits > 0):
                vths[x, y] = Vthreshold_start + weighted_sum_of_hits / (sum_of_hits * 1.0)
    return vths

def vth_hist(vths, Vthreshold_stop):
    hist = np.zeros(Vthreshold_stop, dtype=np.uint16)
    for x in range(256):
        for y in range(256):
            if int(vths[x, y]) >= Vthreshold_stop:
                logger.info("Scan for pixel %d / %d failed, calculated threshold = %f" % (x, y, vths[x,y]))
            elif int(vths[x, y]) < 0:
                logger.info("Scan for pixel %d / %d failed, calculated threshold = %f" % (x, y, vths[x,y]))
            else:
                hist[int(vths[x, y])] += 1
    return hist

def eq_matrix(hist_th0, hist_th15, vths_th0, Vthreshold_start, Vthreshold_stop):
    matrix = np.zeros((256, 256), dtype=np.uint8)
    means = th_means(hist_th0, hist_th15, Vthreshold_start, Vthreshold_stop)
    eq_step_size = int((means[1] - means[0]) / 16)
    eq_distance = (vths_th0 - means[0]) / eq_step_size

    matrix = 8 - eq_distance

    filter_0 = eq_distance >= 8
    matrix[filter_0] = 0

    filter_15 = eq_distance <= -8
    matrix[filter_15] = 15

    return matrix.astype(np.uint8)

def pixeldac_opt(hist_th0, hist_th15, pixeldac, last_pixeldac, last_delta, Vthreshold_start, Vthreshold_stop):
    means = th_means(hist_th0, hist_th15, Vthreshold_start, Vthreshold_stop)
    delta = means[4]
    rms_delta = means[5]
    pixeldac_ratio = (last_pixeldac - pixeldac)/(last_delta - delta)
    if pixeldac == last_pixeldac:
        new_pixeldac = pixeldac / 2.
    elif delta == last_delta:
        new_pixeldac = pixeldac
    else:
        new_pixeldac = pixeldac + pixeldac_ratio * rms_delta - pixeldac_ratio * delta

    return (new_pixeldac, delta, rms_delta)

def th_means(hist_th0, hist_th15, Vthreshold_start, Vthreshold_stop):
    sum_th0 = 0
    entries_th0 = 0.
    sum_th15 = 0
    entries_th15 = 0.
    active_pixels_th0 = 0.
    active_pixels_th15 = 0.
    for i in range(Vthreshold_start, Vthreshold_stop):
        sum_th0 += hist_th0[i]
        entries_th0 += hist_th0[i] / 100. * i
        sum_th15 += hist_th15[i]
        entries_th15 += hist_th15[i] / 100. * i
    mean_th0 = entries_th0 / (sum_th0 / 100.)
    mean_th15 = entries_th15 / (sum_th15 / 100.)
    sum_mean_difference_th0 = 0.
    sum_mean_difference_th15 = 0.
    for i in range(Vthreshold_start, Vthreshold_stop):
        sum_mean_difference_th0 += math.pow(i - mean_th0, 2) * hist_th0[i] / 100.
        sum_mean_difference_th15 += math.pow(i - mean_th15, 2) * hist_th15[i] / 100.
        active_pixels_th0 += hist_th0[i] / 100.
        active_pixels_th15 += hist_th15[i] / 100.
    var_th0 = sum_mean_difference_th0 / (active_pixels_th0 - 1)
    var_th15 = sum_mean_difference_th15 / (active_pixels_th15 - 1)
    rms_th0 = np.sqrt(var_th0)
    rms_th15 = np.sqrt(var_th15)
    delta = mean_th15 - mean_th0
    rms_delta = 3.3 * rms_th15 + 3.3 * rms_th0

    return (mean_th0, mean_th15, rms_th0, rms_th15, delta, rms_delta)


def _interpret_raw_data(data, op_mode = 0, vco = False, ToA_Extension = None):
    data_type = {'names': ['data_header', 'header', 'x',     'y',     'TOA',    'TOT',    'EventCounter', 'HitCounter', 'FTOA',  'scan_param_id', 'chunk_start_time', 'iTOT',   'TOA_Extension', 'TOA_Combined'],
               'formats': ['uint8',       'uint8',  'uint8', 'uint8', 'uint16', 'uint16', 'uint16',       'uint8',      'uint8', 'uint16',        'float',            'uint16', 'uint64',        'uint64']}

    pix_data = np.recarray((data.shape[0]), dtype=data_type)

    n47 = np.uint64(47)
    n44 = np.uint64(44)
    n28 = np.uint64(28)
    n14 = np.uint(14)
    n4 = np.uint64(4)

    n3ff = np.uint64(0x3ff)
    n3fff = np.uint64(0x3fff)
    nf = np.uint64(0xf)

    pixel = (data >> n28) & np.uint64(0b111)
    super_pixel = (data >> np.uint64(28 + 3)) & np.uint64(0x3f)
    right_col = pixel > 3
    eoc = (data >> np.uint64(28 + 9)) & np.uint64(0x7f)

    pix_data['data_header'] = data >> n47
    pix_data['header'] = data >> n44
    pix_data['y'] = (super_pixel * 4) + (pixel - right_col * 4)
    pix_data['x'] = eoc * 2 + right_col * 1
    if(vco == False):
        pix_data['HitCounter'] = _lfsr_4_lut[data & nf]
        pix_data['FTOA'] = np.zeros(len(data))
    else:
        pix_data['HitCounter'] = np.zeros(len(data))
        pix_data['FTOA'] = data & nf

    # ToA and ToT mode
    if op_mode == 0b00:
        pix_data['TOT'] = _lfsr_10_lut[(data >> n4) & n3ff]
        pix_data['TOA'] = _gray_14_lut[(data >> n14) & n3fff]
        pix_data['EventCounter'] = np.zeros(len(data))
        if len(ToA_Extension):
            pix_data['TOA_Extension'] = ToA_Extension & 0xFFFFFFFFFFFF # remove header marking it as timestamp
            pix_data['TOA_Combined'] = (ToA_Extension & 0xFFFFFFFFC000) + pix_data['TOA']
        else:
            pix_data['TOA_Extension'] = np.zeros(len(data))
            pix_data['TOA_Combined'] = np.zeros(len(data))
    elif op_mode == 0b01: # ToA
        pix_data['TOA'] = _gray_14_lut[(data >> n14) & n3fff]
        pix_data['EventCounter'] = np.zeros(len(data))
        pix_data['TOT'] = np.zeros(len(data))
        if len(ToA_Extension):
            pix_data['TOA_Extension'] = ToA_Extension & 0xFFFFFFFFFFFF # remove header marking it as timestamp
            pix_data['TOA_Combined'] = (ToA_Extension & 0xFFFFFFFFC000) + pix_data['TOA']
        else:
            pix_data['TOA_Extension'] = np.zeros(len(data))
            pix_data['TOA_Combined'] = np.zeros(len(data))
    else: # Event and iToT
        pix_data['iTOT'] = _lfsr_14_lut[(data >> n14) & n3fff]
        pix_data['EventCounter'] = _lfsr_10_lut[(data >> n4) & n3ff]
        pix_data['TOT'] = np.zeros(len(data))
        pix_data['TOA'] = np.zeros(len(data))
        pix_data['TOA_Extension'] = np.zeros(len(data))
        pix_data['TOA_Combined'] = np.zeros(len(data))

    return pix_data

"""
Corrects for missing packages in the raw_data of the data
"""
def save_and_correct(raw_data, indices):
    # split into packages, which should be package0 and 1
    package0 = raw_data[1::2]
    package0 = (package0 & 0x01000000) >> 24
    package1 = raw_data[0::2]
    package1 = (package1 & 0x01000000) >> 24
    # package 0 should have a 0 here, check where this is not the case
    ones = np.where(package0 == 1)[0]
    # found an error -> missing package somewhere
    if len(ones) != 0:
        first = ones[0]
        # delete package belonging to the missing one
        if first == 0:
            raw_data = np.delete(raw_data, 0, axis = 0)
            indices = np.delete(indices, 0, axis = 0)
            #logger.info("Deleted package at index "+str(0))
        elif package1[first] == 1:
            raw_data = np.delete(raw_data, 2*first+1, axis = 0)
            indices = np.delete(indices, 2*first+1, axis = 0)
            #logger.info("Deleted package at index "+str(2*first+1))
        else:
            raw_data = np.delete(raw_data, 2*(first-1)+1, axis = 0)
            indices = np.delete(indices, 2*(first-1)+1, axis = 0)
            #logger.info("Deleted package at index "+str(2*(first-1)+1))

        # call recursively until everything is as it should
        raw_data, indices, num = save_and_correct(raw_data,indices)
        num += 1
    # everything is fine, return
    else:
        num = 0

    return raw_data, indices, num

"""
Corrects for missing packages in the raw_data of the FPGA Timestamps
"""
def save_and_correct_timer(raw_data, indices):
    # split timer packages
    package1 = raw_data[1::2]
    package1 = (package1 & 0x01000000) >> 24
    package0 = raw_data[0::2]
    package0 = (package0 & 0x01000000) >> 24
    #package1 should have a 1 at this position; find where this is not the case
    ones = np.where(package1 == 0)[0]
    # if we found an error: correct
    if len(ones) != 0:
        first = ones[0]
        # delete the package that belongs to the missing package
        if first == 0:
            raw_data = np.delete(raw_data, 0, axis = 0)
            indices = np.delete(indices, 0, axis = 0)
            #logger.info("Deleted package at index "+str(0))
        elif package0[first] == 0:
            raw_data = np.delete(raw_data, 2*first+1, axis = 0)
            indices = np.delete(indices, 2*first+1, axis = 0)
            #logger.info("Deleted package at index "+str(2*first+1))
        else:
            raw_data = np.delete(raw_data, 2*(first-1)+1, axis = 0)
            indices = np.delete(indices, 2*(first-1)+1, axis = 0)
            #logger.info("Deleted package at index "+str(2*(first-1)+1))

        # call recursively on the resulting new raw_data until everything is fine
        raw_data, indices, num = save_and_correct_timer(raw_data,indices)
        num += 1 # counting variable
    #if everything is alright: wounderfull, return!
    else:
        num = 0

    return raw_data, indices, num


def raw_data_to_dut_old(raw_data, indices):
    '''
    2x 32 bit to 1x 47 bit
    '''
    raw_data, indices, num = save_and_correct(raw_data, indices)
    if num != 0:
        logger.info("Deleted "+str(num)+" link packages!")
    if len(raw_data) % 2 != 0:
        leftoverpackage = raw_data[-1]
        raw_data = raw_data[:-1]
        indices = indices[:-1]
        logger.info("One link package left over at the end! Try to integrate in next chunk...")
    else:
        leftoverpackage = None
    data_words = np.empty((raw_data.shape[0] // 2), dtype=np.uint64)
    k = (raw_data & 0xffffff)
    data_words[:] = k[1::2].view('>u4')
    data_words = (data_words << 16) + (k[0::2].view('>u4') >> 8)
    package0 = raw_data[1::2]
    package1 = raw_data[0::2]
    return data_words, indices, package0, package1, leftoverpackage

def raw_data_to_dut(raw_data, last_timestamp, next_to_last_timestamp, chunk_nr=0, leftoverpackage=[]):
    # reintegrate leftover package if present
    if len(leftoverpackage):
        logger.info("Integrate package(s) in chunk nr. "+str(chunk_nr))
        for m in range(len(leftoverpackage)-1,-1,-1):
            raw_data = np.insert(raw_data,0,leftoverpackage[m],axis= 0)
        leftoverpackage = []

    # make arrays for results and debugging values    
    data_combined = np.zeros(raw_data.shape[0], dtype=np.uint64)
    index_combined = np.zeros(raw_data.shape[0], dtype=np.uint64)
    data0 = np.zeros(raw_data.shape[0], dtype=np.uint64)
    data1 = np.zeros(raw_data.shape[0], dtype=np.uint64)

    # Get FPGA Timestamps and combine them to the full 48 bit timestamp
    timestamp_filter = (raw_data & 0xF0000000) >> 28 == 0b0101

    if np.sum(timestamp_filter):
        timestamps_raw = raw_data[timestamp_filter]
        timestamps_indices = np.where(timestamp_filter)[0]

        if len(timestamps_raw)%2!=0:
            logger.error("Missing one 32bit subword of the 2 timer packages! Chunk nr. "+str(chunk_nr)+", chunk length = "+str(len(timestamps_raw)))
            
            try:
                timestamps_raw, timestamps_indices, num = save_and_correct_timer(timestamps_raw, timestamps_indices)
                if num != 0:
                    logger.info("Deleted "+str(num)+" timer packages!")
            except RecursionError:
                logger.error("Unable to correct the timestamp data of chunk nr. "+str(chunk_nr))
            if len(timestamps_raw) % 2 != 0:
                leftoverpackage.append(timestamps_raw[-1])
                timestamps_raw = timestamps_raw[:-1]
                timestamps_indices = timestamps_indices[:-1]
                logger.info("One left over timer package! Try to integrate in next chunk...")
            timestamps_combined = np.empty((timestamps_raw.shape[0] // 2), dtype=np.uint64)
            k = (timestamps_raw & 0xFFFFFF)
            timestamps_combined[:] = k[0::2]
            timestamps_combined = (timestamps_combined << 24) + (k[1::2])
            timestamps_combined = timestamps_combined | 0b0101 << 48
            timestamps_combined_indices = timestamps_indices[0::2]
        else:
            timestamps_combined = np.empty((timestamps_raw.shape[0] // 2), dtype=np.uint64)
            k = (timestamps_raw & 0xFFFFFF)
            timestamps_combined[:] = k[0::2]
            timestamps_combined = (timestamps_combined << 24) + (k[1::2])
            timestamps_combined = timestamps_combined | 0b0101 << 48
            timestamps_combined_indices = timestamps_indices[0::2]

        # Put the FPGA timestamps in a new array on their initial positions
        np.put(data_combined, timestamps_combined_indices, timestamps_combined)
        np.put(index_combined, timestamps_combined_indices, timestamps_combined_indices)

        links = 8
        chunk_len = 0
        # Get link-sorted data packages and combine the 32 bit words
        for link in range(links):
            link_filter = (raw_data & 0xfe000000) >> 25 == link
            chunk_len+=np.sum(link_filter)
            if np.sum(link_filter) == 0:
                continue
            if np.sum(link_filter) % 2 != 0:
                logger.error("Missing one 32bit subword of the 2 link packages in link {}!".format(link)+" Chunk nr. "+str(chunk_nr)+ ", length "+str(np.sum(link_filter))+" correcting...")
                #logger.info("len(link_filter) before correction: "+str(len(link_filter)))
                #continue
            link_raw_data = raw_data[link_filter]
            link_indices = np.where(link_filter)[0]
            link_combined,link_indices,package0,package1,leftoverpackage_pot = raw_data_to_dut_old(link_raw_data,link_indices)
            if leftoverpackage_pot!=None:
                leftoverpackage.append(leftoverpackage_pot)
            #if len(link_filter) % 2 != 0: 
                #logger.info("len after correction: ",len(link_combined)*2)
            if len(link_indices) % 2 != 0:
                logger.error("Missing one 32bit subword of the 2 link packages in link {}!".format(link)+" Chunk nr. "+str(chunk_nr)+" after correction.")
                continue
            link_combined_indices = link_indices[0::2]
            link_combined_indices2 = link_indices[1::2]
            # Put the chip data in the new array on their initial positions
            np.put(data_combined, link_combined_indices, link_combined)
            np.put(data0, link_combined_indices, package0)
            np.put(data1, link_combined_indices, package1)

        # Delete array elements with no data - as all data is combined half of the array should be 0
        data0 = np.delete(data0, data_combined == 0)
        data1 = np.delete(data1, data_combined == 0)
        data_combined = np.delete(data_combined, data_combined == 0)

        # Split the array into smaller arrays starting with a fpga timestamp
        timestamp_combined_filter = (data_combined & 0xF000000000000) >> 48 == 0b0101
        timestamp_combined_indices = np.where(timestamp_combined_filter)[0]

        # to create an additional empty array element in timestamp_splits at the beginning, for insertion of last timestamps
        try:
            if timestamp_combined_indices[0] != 0:
                timestamp_combined_indices = np.insert(timestamp_combined_indices,0,0,axis= 0)
        except IndexError:
            pass

        #timestamp_splits = np.zeros(timestamp_combined_filter.shape[0], dtype='object')
        timestamp_splits = np.split(data_combined, timestamp_combined_indices)
        data0_splits = np.split(data0, timestamp_combined_indices)
        data1_splits = np.split(data1, timestamp_combined_indices)

        # attach last and next to last_timestamp if necessary
        minus = 0
        if len(timestamp_splits) > 1 and len(timestamp_splits[1]) > 0 and ((int(timestamp_splits[1][0]) & 0xF000000000000) >> 48 != 0b0101):
            timestamp_splits[1] = np.insert(timestamp_splits[1],0,np.uint64(last_timestamp),axis=0)
            timestamp_splits[0] = np.insert(timestamp_splits[0],0,next_to_last_timestamp,axis=0)
            data0_splits[1] = np.insert(data0_splits[1],0,0,axis=0)
            data0_splits[0] = np.insert(data0_splits[0],0,0,axis=0)
            data1_splits[1] = np.insert(data1_splits[1],0,0,axis=0)
            data1_splits[0] = np.insert(data1_splits[0],0,0,axis=0)
            minus = 2
        else:
            # only insert last timestamp
            timestamp_splits[0] = np.insert(timestamp_splits[0],0,last_timestamp,axis=0)
            data0_splits[0] = np.insert(data0_splits[0],0,0,axis=0)
            data1_splits[0] = np.insert(data1_splits[0],0,0,axis=0)
            minus = 1
        
        # Check for packages that are shifted by more than 1 wrt the extension. Keep for future debugging
        num = 0
        wrong_hits = 0
        for j in range(len(timestamp_splits)):
            for l in range(1,len(timestamp_splits[j])):
                if timestamp_splits[j][l]!=0:
                    if not int((((int(timestamp_splits[j][0]) & 0x3000) >> 12) - ((int(_gray_14_lut[(int(timestamp_splits[j][l]) >> 14) & 0x3fff]) & 0x3000) >> 12))) in [1,0,-3]:
                        print("Chunk length: ",len(timestamp_splits)-1)
                        diff = int(-(((int(timestamp_splits[j][0]) & 0x3000) >> 12) - ((int(_gray_14_lut[(int(timestamp_splits[j][l]) >> 14) & 0x3fff]) & 0x3000) >> 12)))
                        #diff = (diff+3)%3
                        data = int(timestamp_splits[j][l])
                        pixel = (data >> 28) & 0b111
                        super_pixel = (data >> 31) & 0x3f
                        right_col = pixel > 3
                        eoc = (data >> 37) & 0x7f

                        y = (super_pixel * 4) + (pixel - right_col * 4)
                        x = eoc * 2 + right_col * 1
                        logger.info("Found Hit, that is delayed by more than 1 w.r.t. the extension, i.e. by "+str(diff)+" Chunk nr. "+str(chunk_nr))
                        logger.info("Information to this hit: ToA="+str(_gray_14_lut[(int(timestamp_splits[j][l]) >> 14) & 0x3fff])+", ToT="+str(_lfsr_10_lut[(int(timestamp_splits[j][l]) >> 4) & 0x3ff])+", x="+str(x)+", y="+str(y))
                        logger.info("Paket 0: "+bin(int(data0_splits[j][l]) & 0x1ffffff))
                        logger.info("Paket 1: "+bin(int(data1_splits[j][l]) & 0x1ffffff))
                        wrong_hits += 1
            num += len(timestamp_splits[j])

        # Iterate over the smaller arrays and put chip data with wrong fpga overlap in the previous array
        #for i in range(len(timestamp_splits)-1,0,-1):
        for i in range(1,len(timestamp_splits)):
            if len(timestamp_splits[i]) < 2:
                continue
            iteration_toas = timestamp_splits[i][1:]
            old_toa_filter = (((int(timestamp_splits[i][0]) & 0x3000) >> 12) != ((_gray_14_lut[(iteration_toas >> 14) & 0x3fff] & 0x3000) >> 12))
            if sum(old_toa_filter) == 0:
                continue
            old_toas = iteration_toas[old_toa_filter]
            old_toas_indices = np.where(old_toa_filter)[0]
            timestamp_splits[i-1] = np.append(timestamp_splits[i-1], old_toas)
            timestamp_splits[i] = np.delete(timestamp_splits[i], old_toas_indices+1)
            
        try:
            last = timestamp_splits[-1][0]
        except IndexError:
            last = 0
        try:
            nlast = timestamp_splits[-2][0]
        except IndexError:
            nlast = 0

        # Delete all arrays which only contain a fpga [timestamp]
        output = list(filter(lambda x: len(x) > 1 , timestamp_splits))

        if len(output) == 0:
            return np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.uint64), 0, 0, []

        timestamps = np.concatenate([np.full((len(el)-1),el[0],dtype=np.uint64) for el in output])
        data_words = np.concatenate([el[1:] for el in output])

        """if wrong_hits/len(data_words) > 0.2:
            logger.error("Removed Chunk nr. "+str(chunk_nr)+" from data due to too many iregularities.")
            return np.empty(0,dtype=np.uint64),np.empty(0,dtype=np.uint64),last,nlast"""
    
    else:
        links = 8
        chunk_len = 0
        # Get link-sorted data packages and combine the 32 bit words
        for link in range(links):
            link_filter = (raw_data & 0xfe000000) >> 25 == link
            chunk_len+=np.sum(link_filter)
            if np.sum(link_filter) == 0:
                continue
            if np.sum(link_filter) % 2 != 0:
                logger.error("Missing one 32bit subword of the 2 link packages in link {}!".format(link)+" Chunk nr. "+str(chunk_nr)+ ", length "+str(np.sum(link_filter))+" correcting...")
                #logger.info("len(link_filter) before correction: "+str(len(link_filter)))
                #continue
            link_raw_data = raw_data[link_filter]
            link_indices = np.where(link_filter)[0]
            link_combined,link_indices,package0,package1,leftoverpackage_pot = raw_data_to_dut_old(link_raw_data,link_indices)
            if leftoverpackage_pot!=None:
                leftoverpackage.append(leftoverpackage_pot)
            #if len(link_filter) % 2 != 0: 
                #logger.info("len after correction: ",len(link_combined)*2)
            if len(link_indices) % 2 != 0:
                logger.error("Missing one 32bit subword of the 2 link packages in link {}!".format(link)+" Chunk nr. "+str(chunk_nr)+" after correction.")
                continue
            link_combined_indices = link_indices[0::2]
            link_combined_indices2 = link_indices[1::2]
            # Put the chip data in the new array on their initial positions
            np.put(data_combined, link_combined_indices, link_combined)
            np.put(data0, link_combined_indices, package0)
            np.put(data1, link_combined_indices, package1)

        # Delete array elements with no data - as all data is combined half of the array should be 0
        data0 = np.delete(data0, data_combined == 0)
        data1 = np.delete(data1, data_combined == 0)
        data_combined = np.delete(data_combined, data_combined == 0)

        data_words = data_combined
        timestamps = np.empty(0,dtype=np.uint64)
        last = 0
        nlast = 0
        leftoverpackage = []

    return data_words, timestamps, last, nlast, leftoverpackage

def interpret_raw_data(raw_data, op_mode, vco, meta_data=[], chunk_start_time=None, split_fine=False, last_timestamp = 0, next_to_last_timestamp = 0, intern =False, chunk_nr = 0, leftoverpackage = [], progress = None):
    '''
    Chunk the data based on scan_param and interpret
    '''
    ret = []

    if len(meta_data):
        # standard case: only split into bunches which have the same param_id
        if split_fine == False:
            # param = list of all occuring scan_param_ids
            # index = positions of first occurence of each scan_param_ids
            param, index = np.unique(meta_data['scan_param_id'], return_index=True)
            # remove first entry
            index = index[1:]
            # append entry with total number of rows in meta_data
            index = np.append(index, meta_data.shape[0])
            # substract one from each element; the indices are now marking the last element with a
            # specific scan_param_id (if they are not recuring).
            index = index - 1
            # make list of the entries in 'index_stop' at the positions stored in index
            stops = meta_data['index_stop'][index]
            # split raw_data according to these positions into sets that all consist of entries which belong to one scan_id
            split = np.split(raw_data, stops)
            # remove the last element (WHY?) and process each chunk individually
            if progress == None:
                pbar = tqdm(total = len(split[:-1]))
            else:
                step_counter = 0
            for i in range(len(split[:-1])):
                # print param[i], stops[i], len(split[i]), split[i]
                # sends split[i] (i.e. part of data that is currently treated) recursively
                # to this function. Get pixel_data back (splitted in a readable way, not packages any more)
                int_pix_data, last_timestamp, next_to_last_timestamp, leftoverpackage = interpret_raw_data(split[i], op_mode, vco, last_timestamp = last_timestamp, intern = True)
                # reattach param_id TODO: good idea to also give timestamp here!
                int_pix_data['scan_param_id'][:] = param[i]
                # append data we got back to return array or create new if this is the fist bunch of data treated
                if len(ret):
                    ret = np.hstack((ret, int_pix_data))
                else:
                    ret = int_pix_data
                if progress == None:
                    pbar.update(1)
                else:
                    step_counter += 1
                    fraction = step_counter / (len(split[:-1]))
                    progress.put(fraction)
            if progress == None:
                pbar.close()
        # case used for clustering: split further into the time frames defined through one row in meta_data
        else:
            if progress == None:
                pbar = tqdm(total = meta_data.shape[0])
            else:
                step_counter = 0
            for l in range(meta_data.shape[0]):
                index_start = meta_data['index_start'][l]
                index_stop = meta_data['index_stop'][l]
                if index_start<index_stop:
                    int_pix_data, last_timestamp, next_to_last_timestamp, leftoverpackage = interpret_raw_data(raw_data[index_start:index_stop], op_mode, vco, last_timestamp = last_timestamp, next_to_last_timestamp = next_to_last_timestamp, intern = True, chunk_nr = l, leftoverpackage = leftoverpackage)
                    # reattach timestamp
                    int_pix_data['chunk_start_time'][:] = meta_data['timestamp_start'][l]
                    # append data we got back to return array or create new if this is the fist bunch of data treated
                    if len(ret):
                        ret = np.hstack((ret, int_pix_data))
                    else:
                        ret = int_pix_data
                    if progress == None:
                        pbar.update(1)
                    else:
                        step_counter += 1
                        fraction = step_counter / (meta_data.shape[0])
                        progress.put(fraction)
            if progress == None:
                pbar.close()
    else:
        #it can be chunked and multithreaded here
        data_words, timestamp, last_timestamp, next_to_last_timestamp,leftoverpackage  = raw_data_to_dut(raw_data, last_timestamp, next_to_last_timestamp, chunk_nr = chunk_nr, leftoverpackage=leftoverpackage)
        ret = _interpret_raw_data(data_words, op_mode, vco, timestamp)

    if intern == True:
        return ret, last_timestamp, next_to_last_timestamp, leftoverpackage
    else:
        return ret

def init_lfsr_4_lut():
        """
        Generates a 4bit LFSR according to Manual v1.9 page 19
        """
        lfsr = BitLogic(4)
        lfsr[3:0] = 0xF
        dummy = 0
        for i in range(2**4):
            _lfsr_4_lut[BitLogic.tovalue(lfsr)] = i
            dummy = lfsr[3]
            lfsr[3] = lfsr[2]
            lfsr[2] = lfsr[1]
            lfsr[1] = lfsr[0]
            lfsr[0] = lfsr[3] ^ dummy
        _lfsr_4_lut[2 ** 4 - 1] = 0


def init_lfsr_10_lut():
    """
    Generates a 10bit LFSR according to Manual v1.9 page 19
    """

    lfsr = BitLogic(10)
    lfsr[7:0] = 0xFF
    lfsr[9:8] = 0b11
    dummy = 0
    for i in range(2 ** 10):
        _lfsr_10_lut[BitLogic.tovalue(lfsr)] = i
        dummy = lfsr[9]
        lfsr[9] = lfsr[8]
        lfsr[8] = lfsr[7]
        lfsr[7] = lfsr[6]
        lfsr[6] = lfsr[5]
        lfsr[5] = lfsr[4]
        lfsr[4] = lfsr[3]
        lfsr[3] = lfsr[2]
        lfsr[2] = lfsr[1]
        lfsr[1] = lfsr[0]
        lfsr[0] = lfsr[7] ^ dummy
    _lfsr_10_lut[2 ** 10 - 1] = 0

def init_lfsr_14_lut():
    """
    Generates a 14bit LFSR according to Manual v1.9 page 19
    """
    lfsr = BitLogic(14)
    lfsr[7:0] = 0xFF
    lfsr[13:8] = 63
    dummy = 0
    for i in range(2**14):
        _lfsr_14_lut[BitLogic.tovalue(lfsr)] = i
        dummy = lfsr[13]
        lfsr[13] = lfsr[12]
        lfsr[12] = lfsr[11]
        lfsr[11] = lfsr[10]
        lfsr[10] = lfsr[9]
        lfsr[9] = lfsr[8]
        lfsr[8] = lfsr[7]
        lfsr[7] = lfsr[6]
        lfsr[6] = lfsr[5]
        lfsr[5] = lfsr[4]
        lfsr[4] = lfsr[3]
        lfsr[3] = lfsr[2]
        lfsr[2] = lfsr[1]
        lfsr[1] = lfsr[0]
        lfsr[0] = lfsr[2] ^ dummy ^ lfsr[12] ^ lfsr[13]
    _lfsr_14_lut[2 ** 14 - 1] = 0

def init_gray_14_lut():
    """
    Generates a 14bit gray according to Manual v1.9 page 19
    """
    for j in range(2**14):
        encoded_value = BitLogic(14) #48
        encoded_value[13:0]=j #47
        gray_decrypt_v = BitLogic(14) #48
        gray_decrypt_v[13]=encoded_value[13] #47
        for i in range (12, -1, -1): #46
            gray_decrypt_v[i]=gray_decrypt_v[i+1]^encoded_value[i]
        _gray_14_lut[j] = gray_decrypt_v.tovalue()

def scurve(x, A, mu, sigma):
    return 0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A


def zcurve(x, A, mu, sigma):
    return -0.5 * A * erf((x - mu) / (np.sqrt(2) * sigma)) + 0.5 * A

def totcurve(x, a, b, c, t):
    return a*x + b - c / (x-t)


def get_threshold(x, y, n_injections, invert_x=False):
    ''' Fit less approximation of threshold from s-curve.

        From: https://doi.org/10.1016/j.nima.2013.10.022

        Parameters
        ----------
        x, y : numpy array like
            Data in x and y
        n_injections: integer
            Number of injections
    '''

    # Sum over last dimension to support 1D and 2D hists
    M = y.sum(axis=len(y.shape) - 1)  # is total number of hits
    d = np.diff(x)[0]  # Delta x = step size in x
    if not np.all(np.diff(x) == d):
        raise NotImplementedError('Threshold can only be calculated for equidistant x values!')
    if invert_x:
        return x.min() + (d * M).astype(np.float) / n_injections
    return x.max() - (d * M).astype(np.float) / n_injections


def get_noise(x, y, n_injections, invert_x=False):
    ''' Fit less approximation of noise from s-curve.

        From: https://doi.org/10.1016/j.nima.2013.10.022

        Parameters
        ----------
        x, y : numpy array like
            Data in x and y
        n_injections: integer
            Number of injections
    '''

    mu = get_threshold(x, y, n_injections, invert_x)
    d = np.abs(np.diff(x)[0])

    if invert_x:
        mu1 = y[x > mu].sum()
        mu2 = (n_injections - y[x < mu]).sum()
    else:
        mu1 = y[x < mu].sum()
        mu2 = (n_injections - y[x > mu]).sum()

    return d * (mu1 + mu2).astype(np.float) / n_injections * np.sqrt(np.pi / 2.)


def fit_scurve(scurve_data, scan_param_range, n_injections, sigma_0, invert_x):
    '''
        Fit one pixel data with Scurve.
        Has to be global function for the multiprocessing module.

        Returns:
            (mu, sigma, chi2/ndf)
    '''

    scurve_data = np.array(scurve_data, dtype=np.float)

    # Deselect masked values (== nan)
    x = scan_param_range[~np.isnan(scurve_data)]
    y = scurve_data[~np.isnan(scurve_data)]

    # Only fit data that is fittable
    if np.all(y == 0) or np.all(np.isnan(y)) or x.shape[0] < 3:
        return (0., 0., 0.)
    if y.max() < 0.2 * n_injections:
        return (0., 0., 0.)

    # Calculate data errors, Binomial errors
    yerr = np.sqrt(y * (1. - y.astype(np.float) / n_injections))
    # Set minimum error != 0, needed for fit minimizers
    # Set arbitrarly to error of 0.5 injections
    min_err = np.sqrt(0.5 - 0.5 / n_injections)
    yerr[yerr < min_err] = min_err
    # Additional hits not following fit model set high error
    sel_bad = y > n_injections
    yerr[sel_bad] = (y - n_injections)[sel_bad]

    # Calculate threshold start value:
    mu = get_threshold(x=x, y=y,
                       n_injections=n_injections,
                       invert_x=invert_x)

    # Set fit start values
    p0 = [n_injections, mu, sigma_0]

    try:
        if invert_x:
            popt = curve_fit(f=zcurve, xdata=x,
                             ydata=y, p0=p0, sigma=yerr,
                             absolute_sigma=True if np.any(yerr) else False)[0]
            chi2 = np.sum((y - zcurve(x, *popt)) ** 2)
        else:
            popt = curve_fit(f=scurve, xdata=x,
                             ydata=y, p0=p0, sigma=yerr,
                             absolute_sigma=True if np.any(yerr) else False,
                             method='lm')[0]
            chi2 = np.sum((y - scurve(x, *popt)) ** 2)
    except RuntimeError:  # fit failed
        return (0., 0., 0.)

    # Treat data that does not follow an S-Curve, every fit result is possible here but not meaningful
    max_threshold = x.max() + 5. * np.abs(popt[2])
    min_threshold = x.min() - 5. * np.abs(popt[2])
    if popt[2] <= 0 or not min_threshold < popt[1] < max_threshold:
        return (0., 0., 0.)

    return (popt[1], popt[2], chi2 / (y.shape[0] - 3 - 1))


def imap_bar(func, args, n_processes=None, progress = None):
    '''
        Apply function (func) to interable (args) with progressbar based on tqdm or 'progress'
        in case of a GUI
    '''
    p = mp.Pool(n_processes)
    res_list = []

    if progress == None:
        pbar = tqdm(total=len(args))
    else:
        step_counter = 0

    for _, res in enumerate(p.imap(func, args)):
        if progress == None:
            pbar.update(1)
        else:
            step_counter += 1
            fraction = step_counter / len(args)
            progress.put(fraction)
        res_list.append(res)

    if progress == None:
        pbar.close()
    
    p.close()
    p.join()
    return res_list


def fit_scurves_multithread(scurves, scan_param_range,
                            n_injections, invert_x=False, progress = None):
    _scurves = np.zeros((256*256, len(scan_param_range)), dtype=np.uint16)
    
    # Set all values above n_injections to n_injections. This is necessary, as the noise peak can lead to problems in the scurve fits.
    # As we are only interested in the position of the scurve (which lays below n_injections) this should not cause a problem.
    logger.info("Cut S-curves to %i hits for S-curve fit", n_injections)
    pulse_check = scurves > n_injections
    _scurves[pulse_check] = n_injections
    _scurves[np.invert(pulse_check)] = scurves[np.invert(pulse_check)]
    
    _scurves = np.ma.masked_array(_scurves)
    scan_param_range = np.array(scan_param_range)

    # Calculate noise median for fit start value
    logger.info("Calculate S-curve fit start parameters")
    sigmas = []

    if progress == None:
        pbar = tqdm(total=_scurves.shape[0] * _scurves.shape[1])
    else:
        step_counter = 0

    for curve in _scurves:
        # Calculate from pixels with valid data (maximum = n_injections)
        if curve.max() == n_injections:
            if np.all(curve.mask == np.ma.nomask):
                x = scan_param_range
            else:
                x = scan_param_range[~curve.mask]

            y = curve

            sigma = get_noise(x=x,
                              y=y.compressed(),
                              n_injections=n_injections,
                              invert_x=invert_x)
            sigmas.append(sigma)

            if progress == None:
                pbar.update(1)
            else:
                step_counter += 1
                fraction = step_counter / (_scurves.shape[0] * _scurves.shape[1])
                progress.put(fraction)

    if progress == None:
        pbar.close()

    sigma_0 = np.median(sigmas)

    logger.info("Start S-curve fit on %d CPU core(s)", mp.cpu_count())

    partialfit_scurve = partial(fit_scurve,
                                scan_param_range=scan_param_range,
                                n_injections=n_injections,
                                sigma_0=sigma_0,
                                invert_x=invert_x)

    result_list = imap_bar(partialfit_scurve, _scurves.tolist(), progress = progress)
    result_array = np.array(result_list)
    logger.info("S-curve fit finished")

    thr = result_array[:, 0]
    sig = result_array[:, 1]
    chi2ndf = result_array[:, 2]

    thr2D = np.reshape(thr, (256, 256))
    sig2D = np.reshape(sig, (256, 256))
    chi2ndf2D = np.reshape(chi2ndf, (256, 256))
    return thr2D, sig2D, chi2ndf2D


def fit_ToT(tot_data, scan_param_range):
    '''
        Fit one pixel data with totcurve.
        Has to be global function for the multiprocessing module.

        Returns:
            (a, b, c, t, chi2/ndf)
    '''

    tot_data = np.array(tot_data, dtype=np.float)

    # Deselect masked values (== nan)
    x = ((scan_param_range[~np.isnan(tot_data)])/2)*2.5
    y = (tot_data[~np.isnan(tot_data)])*25

    # Only fit data that is fittable
    if np.all(y == 0) or np.all(np.isnan(y)) or x.shape[0] < 3:
        return (0., 0., 0., 0., 0.)

    p0 = [10, -1300, 13000, 230]

    try:
        popt = curve_fit(f=totcurve, xdata=x, ydata=y, p0=p0)[0]
        chi2 = np.sum((y - totcurve(x, *popt)) ** 2)
    except RuntimeError:  # fit failed
        return (0., 0., 0., 0., 0.)

    return (popt[0], popt[1], popt[2], popt[3], chi2 / (y.shape[0] - 3 - 1))


def fit_totcurves_multithread(totcurves, scan_param_range, progress = None):
    totcurves = np.ma.masked_array(totcurves)
    scan_param_range = np.array(scan_param_range)

    logger.info("Start ToT-curve fit on %d CPU core(s)", mp.cpu_count())

    partialfit_totcurves = partial(fit_ToT, scan_param_range=scan_param_range)

    result_list = imap_bar(partialfit_totcurves, totcurves.tolist(), progress = progress)
    result_array = np.array(result_list)
    logger.info("ToT-curve fit finished")

    a = result_array[:, 0]
    b = result_array[:, 1]
    c = result_array[:, 2]
    t = result_array[:, 3]
    chi2ndf = result_array[:, 4]

    a2D = np.reshape(a, (256, 256))
    b2D = np.reshape(b, (256, 256))
    c2D = np.reshape(c, (256, 256))
    t2D = np.reshape(t, (256, 256))
    chi2ndf2D = np.reshape(chi2ndf, (256, 256))
    return a2D, b2D, c2D, t2D, chi2ndf2D


# init LUTs
init_lfsr_4_lut()
init_lfsr_10_lut()
init_lfsr_14_lut()
init_gray_14_lut()

if __name__ == "__main__":
    pass
