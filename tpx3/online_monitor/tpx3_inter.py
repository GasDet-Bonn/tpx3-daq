import numpy as np
import logging

from online_monitor.converter.transceiver import Transceiver
from online_monitor.utils import utils
from zmq.utils import jsonapi

import tpx3.analysis as analysis
from numba.tests.npyufunc.test_ufunc import dtype

class Tpx3(Transceiver):

    def setup_transceiver(self):
        ''' Called at the beginning

            We want to be able to change the histogrammmer settings
            thus bidirectional communication needed
        '''
        self.set_bidirectional_communication()

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
                        raw_data = np.frombuffer(buffer(data),
                                                 dtype=dtype).reshape(shape)
                        return raw_data
                    # KeyError happens if meta data read is omitted
                    # ValueError if np.frombuffer fails due to wrong shape
                    except (KeyError, ValueError):
                        return None
            except AttributeError:  # Happens if first data is not meta data
                return None

    def _interpret_meta_data(self, data):
        ''' Meta data interpratation is deducing timings '''

        meta_data = data[0][1]['meta_data']
        ts_now = float(meta_data['timestamp_stop'])

        # Calculate readout per second with smoothing
        recent_fps = 1.0 / (ts_now - self.ts_last_readout)
        self.fps = self.fps * 0.95 + recent_fps * 0.05

        # Calulate hits per second with smoothing
        recent_hps = self.hits_last_readout * recent_fps
        self.hps = self.hps * 0.95 + recent_hps * 0.05

        # Calulate hits per second with smoothing
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

        raw_data = data[0][1]
        hit_data = analysis.interpret_raw_data(data[0][1])
        hit_data = hit_data[hit_data['data_header'] == 1]

        pix_occ = np.bincount(hit_data['x'] * 256 + hit_data['y'], minlength=256*256).astype(np.uint32)
        hist_occ = np.reshape(pix_occ, (256, 256))


        hit_count = np.count_nonzero(hist_occ.flat)
        self.total_hits += len(hit_data)
        self.readout += 1

        if hit_count > 1: #cut noise
            self.hist_hit_count[hit_count] += 1
            self.hist_occ += hist_occ


        #TODO: self.hist_tot ...
        interpreted_data = {
            #'hits': hit_data,
            'occupancy': self.hist_occ,
            'tot_hist': self.hist_tot,
            'hist_hit_count': self.hist_hit_count,
            'hist_event_status': []
        }

        if self.int_readouts != 0:  # = 0 for infinite integration
            if self.readout % self.int_readouts == 0:
                self.reset_hists()

        return [interpreted_data]

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

        self.hist_occ = np.zeros((256,256), dtype=np.uint32)
        self.hist_tot = np.zeros((16), dtype=np.uint32)
        self.hist_hit_count = np.zeros((256*256), dtype=np.uint32) #
