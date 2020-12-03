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
from numba import njit
import math
from six.moves import range

logger = logging.getLogger('Analysis')

_lfsr_10_lut = np.zeros((2 ** 10), dtype=np.uint16)

from numba import njit

@njit
def scurve_hist(hit_data, param_range):
    scurves = np.zeros((256*256, len(param_range)), dtype=np.uint16)

    for i in range(hit_data.shape[0]):
        x = hit_data['x'][i]
        y = hit_data['y'][i]
        p = hit_data['scan_param_id'][i]
        c = hit_data['EventCounter'][i]
        scurves[x*256+y,p] += c

    return scurves

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
                logger.info("Scan for pixel %d / %d failed" % (x, y))
            else:
                hist[int(vths[x, y])] += 1
    return hist

def eq_matrix(hist_th0, hist_th15, vths_th0, Vthreshold_start, Vthreshold_stop):
    matrix = np.zeros((256, 256), dtype=np.uint8)
    means = th_means(hist_th0, hist_th15, Vthreshold_start, Vthreshold_stop)
    eq_step_size = int((means[1] - means[0]) / 16)

    for x in range(256):
        for y in range(256):
            eq_distance = (vths_th0[x, y] - means[0]) / eq_step_size
            if eq_distance >= 8:
                matrix[x, y] = 0
            elif eq_distance <= -8:
                matrix[x, y] = 15
            else:
                matrix[x, y] = int(8 - eq_distance)

    return matrix

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


#TODO: This is bad should be njit
def _interpret_raw_data(data):

    # TODO: fix types
    data_type = {'names': ['data_header', 'header', 'x', 'y', 'TOA', 'TOT', 'EventCounter', 'HitCounter', 'EoC', 'CTPR', 'scan_param_id','chunk_start_time'],
               'formats': ['uint8', 'uint8', 'uint16', 'uint16', 'uint8', 'uint8', 'uint16', 'uint8', 'uint8', 'uint8', 'uint16', 'double']}

    pix_data = np.recarray((data.shape[0]), dtype=data_type)

    n47 = np.uint64(47)
    n44 = np.uint64(44)
    n28 = np.uint64(28)
    n36 = np.uint64(36)
    n4 = np.uint64(4)

    nff = np.uint64(0xff)
    n3ff = np.uint64(0x3ff)
    nf = np.uint64(0xf)

    pixel = (data >> n28) & np.uint64(0b111)
    super_pixel = (data >> np.uint64(28 + 3)) & np.uint64(0x3f)
    right_col = pixel > 3
    eoc = (data >> np.uint64(28 + 9)) & np.uint64(0x7f)

    pix_data['data_header'] = data >> n47
    pix_data['header'] = data >> n44
    pix_data['y'] = (super_pixel * 4) + (pixel - right_col * 4)
    pix_data['x'] = eoc * 2 + right_col * 1
    pix_data['HitCounter'] = data & nf
    pix_data['EventCounter'] = _lfsr_10_lut[(data >> n4) & n3ff] # at the moment in ToA and ToT mode this gives you ToT
    # TODO

    return pix_data

def raw_data_to_dut(raw_data):
    '''
    Transform to 48 bit format -> fast decode_fpga
    '''

    #assert len(raw_data) % 2 == 0, "Missing one 32bit subword of a 48bit package"  # This could be smarter
    if len(raw_data) % 2 != 0:
        logger.error("Missing one 32bit subword of a 48bit package!")
        return np.empty(0, dtype=np.uint64)

    nwords = len(raw_data) // 2

    # make a list of the header elements giving the link from where the data was received (h)
    h = (raw_data & 0x1E000000) >> 25
    # and a list of the data (k)
    k = (raw_data & 0xffffff)
    data_words = np.empty(0, dtype=np.uint64) # empty list element to store the final data_words
    # make a single list containing the data from each link
    for i in range(8):
        k_i = k[h == i] # gives a list of all data for the specific link number
        if len(k_i) % 2 != 0: # did we receive all packages?
            logger.error("Missing package(s) from Link " + str(i))
        # initialize list with the needed length for temporal storage
        data_words_i = np.empty((k_i.shape[0] // 2), dtype=np.uint64)
        data_words_i[:] = k_i[1::2].view('>u4')
        data_words_i = (data_words_i << 16) + (k_i[0::2].view('>u4') >> 8)
        # append all data from this link to the list of all data
        data_words = np.append(data_words,data_words_i)

    return data_words

def interpret_raw_data(raw_data, meta_data=[], chunk_start_time=None, split_fine=False):
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
            for i in range(len(split[:-1])):
                # print param[i], stops[i], len(split[i]), split[i]

                # sends split[i] (i.e. part of data that is currently treated) recursively
                # to this function. Get pixel_data back (splitted in a readable way, not packages any more)
                int_pix_data = interpret_raw_data(split[i])
                # reattach param_id TODO: good idea to also give timestamp here!
                int_pix_data['scan_param_id'][:] = param[i]
                # append data we got back to return array or create new if this is the fist bunch of data treated
                if len(ret):
                    ret = np.hstack((ret, int_pix_data))
                else:
                    ret = int_pix_data
        # case used for clustering: split further into the time frames defined through one row in meta_data
        else:
            for l in range(meta_data.shape[0]):
                index_start = meta_data['index_start'][l]
                index_stop = meta_data['index_stop'][l]
                if index_start<index_stop:
                    int_pix_data = interpret_raw_data(raw_data[index_start:index_stop])
                    # reattach timestamp
                    int_pix_data['chunk_start_time'] = meta_data['timestamp_start'][l]
                    # append data we got back to return array or create new if this is the fist bunch of data treated
                    if len(ret):
                        ret = np.hstack((ret, int_pix_data))
                    else:
                        ret = int_pix_data
    else:

        #it can be chunked and multithreaded here
        data_words = raw_data_to_dut(raw_data)
        ret = _interpret_raw_data(data_words)

    return ret


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
    for col in range(_scurves.shape[0]):
        for row in range(_scurves.shape[1]):
            if _scurves[col][row] > n_injections:
                _scurves[col][row] = n_injections
            else:
                _scurves[col][row] = scurves[col][row]
    
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

    result_list = imap_bar(partialfit_scurve, scurves.tolist(), progress = progress)
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
init_lfsr_10_lut()

if __name__ == "__main__":
    pass
