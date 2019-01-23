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
import numpy as np
from basil.utils.BitLogic import BitLogic
import logging
from tqdm import tqdm
import multiprocessing as mp
from functools import partial
from scipy.optimize import curve_fit
from scipy.special import erf
from numba import njit
from six.moves import range

logger = logging.getLogger('Analysis')

_lfsr_10_lut = np.zeros((2 ** 10), dtype=np.uint16)

from numba import njit

# Causes that the division in Python 2.7 behaves as in Python 3
from __future__ import division

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

#TODO: This is bad should be njit
def _interpret_raw_data(data):

    # TODO: fix types
    data_type = {'names': ['data_header', 'header', 'x', 'y', 'TOA', 'TOT', 'EventCounter', 'HitCounter', 'EoC', 'CTPR', 'scan_param_id'],
               'formats': ['uint8', 'uint8', 'uint16', 'uint16', 'uint8', 'uint8', 'uint16', 'uint8', 'uint8', 'uint8', 'uint16']}

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
    pix_data['EventCounter'] = _lfsr_10_lut[(data >> n4) & n3ff]
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

    data_words = np.empty((raw_data.shape[0] // 2), dtype=np.uint64)
    k = (raw_data & 0xffffff)
    data_words[:] = k[1::2].view('>u4')
    data_words = (data_words << 16) + (k[0::2].view('>u4') >> 8)

    return data_words

def interpret_raw_data(raw_data, meta_data=[]):
    '''
    Chunk the data based on scan_param and interpret
    '''
    ret = []

    if len(meta_data):
        param, index = np.unique(meta_data['scan_param_id'], return_index=True)
        index = index[1:]
        index = np.append(index, meta_data.shape[0])
        index = index - 1
        stops = meta_data['index_stop'][index]
        split = np.split(raw_data, stops)
        for i in range(len(split[:-1])):
            # print(param[i], stops[i], len(split[i]), split[i])
            int_pix_data = interpret_raw_data(split[i])
            int_pix_data['scan_param_id'][:] = param[i]
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
    d = np.diff(x)[0]  # Delta x
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


def imap_bar(func, args, n_processes=None):
    ''' Apply function (func) to interable (args) with progressbar
    '''
    p = mp.Pool(n_processes)
    res_list = []
    pbar = tqdm(total=len(args))
    for _, res in enumerate(p.imap(func, args)):
        pbar.update()
        res_list.append(res)
    pbar.close()
    p.close()
    p.join()
    return res_list


def fit_scurves_multithread(scurves, scan_param_range,
                            n_injections=None, invert_x=False):
    scurves = np.ma.masked_array(scurves)
    scan_param_range = np.array(scan_param_range)

    # Calculate noise median for fit start value
    logger.info("Calculate S-curve fit start parameters")
    sigmas = []
    for curve in tqdm(scurves):
        # FIXME: n_injections is not defined, can this happen?
        if not n_injections:
            raise RuntimeError('Number of injections not defined. Please report to developers at https://gitlab.cern.ch/silab/bdaq53/issues')
            n_injections = curve.max()
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
    sigma_0 = np.median(sigmas)

    logger.info("Start S-curve fit on %d CPU core(s)", mp.cpu_count())

    partialfit_scurve = partial(fit_scurve,
                                scan_param_range=scan_param_range,
                                n_injections=n_injections,
                                sigma_0=sigma_0,
                                invert_x=invert_x)

    result_list = imap_bar(partialfit_scurve, scurves.tolist())
    result_array = np.array(result_list)
    logger.info("S-curve fit finished")

    thr = result_array[:, 0]
    sig = result_array[:, 1]
    chi2ndf = result_array[:, 2]

    thr2D = np.reshape(thr, (256, 256))
    sig2D = np.reshape(sig, (256, 256))
    chi2ndf2D = np.reshape(chi2ndf, (256, 256))
    return thr2D, sig2D, chi2ndf2D


# init LUTs
init_lfsr_10_lut()

if __name__ == "__main__":
    pass
