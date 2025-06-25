from __future__ import absolute_import
from __future__ import division
from re import X
import numpy as np
import logging
import math
import os
import yaml
from six.moves import range

from UI.GUI.converter.transceiver import Transceiver
from UI.GUI.converter import utils
from zmq.utils import jsonapi

import tpx3.analysis as analysis
from numba.tests.npyufunc.test_ufunc import dtype

logger = logging.getLogger('Online_Interpreter')

_lfsr_10_lut = np.zeros((2 ** 10), dtype=np.uint16)

def init_lfsr_10_lut():
    """
    Generates a 10bit LFSR according to Manual v1.9 page 19
    """
    lfsr = 1023
    dummy = 0
    for i in range(2 ** 10):
        _lfsr_10_lut[lfsr] = i
        dummy = lfsr >> 9
        lfsr = (lfsr << 1) & 0b1111111111
        lfsr += ((lfsr & 0b10000000) >> 7) ^ dummy
    _lfsr_10_lut[2 ** 10 - 1] = 0

init_lfsr_10_lut()

def _interpret_raw_data(data):
    pixel = np.uint32(data >> np.uint32(28)) & np.uint32(0b111)
    super_pixel = np.uint32(data >> np.uint32(31)) & np.uint32(0x3f)
    right_col = pixel > 3
    eoc = np.uint32(data >> np.uint32(37)) & np.uint32(0x7f)

    header = (data >> np.uint32(47))
    x = (eoc * 2 + right_col * 1)
    y = ((super_pixel * 4) + (pixel - right_col * 4))
    tot = _lfsr_10_lut[(data >> np.uint32(4)) & np.uint32(0x3ff)]

    return header, x, y, tot

def raw_data_to_dut(raw_data, chip_links, chips):
    '''
    Transform to 48 bit format -> fast decode_fpga
    '''
    if len(raw_data) % 2 != 0:
        return np.empty(0, dtype=np.uint64)

    # make a list of the header elements giving the link from where the data was received (h)
    h = (raw_data & 0xFE000000) >> 25
    # and a list of the data (k)
    k = (raw_data & 0xffffff)
    data_words = [np.empty(0, dtype=np.uint64)]*chips # empty list element to store the final data_words
    # make a single list containing the data from each link
    # write data to array which belongs to a chip via chip_links dictionary
    for i in range(24):
        
        for link, chip in enumerate(chip_links):
            if chip == None:
                continue
            if i in chip_links[chip]:
                current_chip = link
                break
        
        k_i = k[h == i] # gives a list of all data for the specific link number
        # initialize list with the needed length for temporal storage
        data_words_i = np.empty((k_i.shape[0] // 2), dtype=np.uint64)
        data_words_i2 = np.empty((k_i.shape[0] // 2), dtype=np.uint64)
        data_words_i[:] = k_i[1::2].view('>u4')
        try:
            data_words_i2[:] = k_i[0::2].view('>u4')
        except:
            data_words_i2[:] = k_i[0::2].view('>u4')[0:-1]
        data_words_i = (data_words_i << 16) + (data_words_i2 >> 8)
        # append all data from this link to the list of all data
        data_words[current_chip] = np.append(data_words[current_chip],data_words_i)

    return data_words

def interpret_raw_data(raw_data, chip_links, chips):
    '''
    Chunk the data based on scan_param and interpret
    '''
    header = [[]]*chips
    x      = [[]]*chips
    y      = [[]]*chips
    tot    = [[]]*chips

    data_words = raw_data_to_dut(raw_data, chip_links, chips)
    if len(data_words) == 0:
        return header, x, y, tot
    for chip in range(chips):
        header[chip], x[chip], y[chip], tot[chip] = _interpret_raw_data(data_words[chip])

    return header, x, y, tot

class Tpx3(Transceiver):
    def setup_interpretation(self):
        ''' Objects defined here are available in interpretation process '''
        utils.setup_logging(self.loglevel)

        self.chunk_size = self.config.get('chunk_size', 1000000)

        # Init result hists
        self.reset_hists()

        # Number of readouts to integrate
        self.int_readouts = 0

        # Variables for meta data time calculations
        self.ts_last_readout = 0.  # Time stamp last readout
        self.hits_last_readout = 0.  # Number of hits
        self.events_last_readout = 0.  # Number of events in last chunk
        self.fps = 0.  # Readouts per second
        self.hps = 0.  # Hits per second
        self.eps = 0.  # Events per second
        self.ext_trg_num = -1  # external trigger number

    def deserialize_data(self, data):
        ''' Inverse of Bdaq53 serialization '''
        try:
            self.meta_data = jsonapi.loads(data)
            return {'meta_data': self.meta_data}
        except ValueError:  # Is raw data
            try:
                dtype = self.meta_data.pop('dtype')
                shape = self.meta_data.pop('shape')
                if self.meta_data:
                    try:
                        raw_data = np.frombuffer(memoryview(data),
                                                 dtype=dtype).reshape(shape)
                        return raw_data
                    # KeyError happens if meta data read is omitted
                    # ValueError if np.frombuffer fails due to wrong shape
                    except (KeyError, ValueError):
                        return None
            except AttributeError:  # Happens if first data is not meta data
                return None

    def _interpret_meta_data(self, data):
        ''' Meta data interpretation is deducing timings '''

        meta_data = data[0][1]['meta_data']
        ts_now = float(meta_data['timestamp_stop'])

        # Calculate readout per second with smoothing
        recent_fps = 1.0 / (ts_now - self.ts_last_readout)
        self.fps = self.fps * 0.95 + recent_fps * 0.05

        # Calculate hits per second with smoothing
        recent_hps = self.hits_last_readout * recent_fps
        self.hps = self.hps * 0.95 + recent_hps * 0.05

        # Calculate hits per second with smoothing
        recent_eps = self.events_last_readout * recent_fps
        self.eps = self.eps * 0.95 + recent_eps * 0.05

        self.ts_last_readout = ts_now

        # Add info to meta data
        data[0][1]['meta_data'].update(
            {'fps': self.fps,
             'hps': self.hps,
             'total_hits': self.total_hits,
             'eps': self.eps,
             'total_events': self.total_events})
        return [data[0][1]]

    def interpret_data(self, data):
        ''' Called for every chunk received '''

        if isinstance(data[0][1], dict):  # Meta data
            return self._interpret_meta_data(data)

        chips = sum(1 for key in self.chip_links if key is not None)
        header, x, y, tot = interpret_raw_data(data[0][1], self.chip_links, chips)
        hits = [[]]*chips
        
        if len(x) > 0:
            for chip in range(chips):
                if len(x[chip]) == 0:
                    continue
                x[chip]    = x[chip][header[chip] == 1]
                y[chip]    = y[chip][header[chip] == 1]
                tot[chip]  = tot[chip][header[chip] == 1]
                hits[chip] = x[chip], y[chip], tot[chip]

        total_temp = 0 

        for header_list in range(chips):
            if len(header[header_list]) == 0:
                continue
            total_temp = len(header[header_list]==1) 

        self.total_hits += total_temp
        self.readout += 1
        self.total_events = self.readout  # ???

        if self.int_readouts != 0:  # = 0 for infinite integration
            if self.readout % self.int_readouts == 0:
                self.reset_hists()

        while self.symbol_pipe.poll(timeout = 0.0):
            self.run_data_queue_symbol = self.symbol_pipe.recv()

        if self.run_data_queue_symbol:
            self.data_queue.put(hits)

    def serialize_data(self, data):
        ''' Serialize data from interpretation '''
        if 'hits' in data:
            hits_data = data['hits']
            data['hits'] = None
            return utils.simple_enc(hits_data, data)
        else:
            return utils.simple_enc(None, data)

    def handle_command(self, command):
        ''' Received commands from GUI receiver '''
        if command[0] == 'RESET':
            self.reset_hists()
        else:
            self.int_readouts = int(command[0])

    def reset_hists(self):
        ''' Reset the histograms '''
        self.total_hits = 0
        self.total_events = 0
        # Readout number
        self.readout = 0

        self.hist_occ = np.zeros((256,256), dtype=float)
        self.hist_tot = np.zeros((1024), dtype=float)
        self.hist_hit_count = np.zeros((256*256), dtype=float)
