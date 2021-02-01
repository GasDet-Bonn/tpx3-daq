#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# Based on: https://github.com/SiLab-Bonn/online_monitor
# ------------------------------------------------------------
#

import os
import logging
import argparse
import yaml
import json
import ast
import base64
import sys
import numpy as np
from importlib import import_module #imports a module
import struct
from array import array
import pickle as pickle
from importlib.machinery import SourceFileLoader

from UI.GUI.converter import settings

def frombytes(v, b):  # Python 2/3 compatibility function for array.tobytes function
    return v.frombytes(b)
def tobytes(v):
    return v.tobytes()

# create config dict from yaml text file
def parse_config_file(config_file, expect_receiver=False):
    with open(config_file, 'r') as in_config_file:
        configuration = yaml.safe_load(in_config_file)
        if expect_receiver:
            try:
                configuration['receiver']
            except KeyError:
                logging.warning('No receiver specified, thus no data '
                                'can be plotted. Change %s!', config_file)
        return configuration

def setup_logging(loglevel):  # set logging level of this module
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level)

def simple_enc(data=None, meta={}):

    data_buffer = array('B', [])

    if data is not None:
        meta['data_meta'] = {'dtype': data.dtype, 'shape': data.shape}
        frombytes(data_buffer, data.tobytes())

    meta_json = pickle.dumps(meta)
    meta_json_buffer = array('B', [])
    frombytes(meta_json_buffer, meta_json)

    meta_len = len(meta_json)

    meta_len_byte = struct.unpack("4B", struct.pack("I", meta_len))

    data_buffer.extend(meta_json_buffer)
    data_buffer.extend(meta_len_byte)

    return tobytes(data_buffer)

def simple_dec(data_buffer):

    len_buffer = data_buffer[-4:]
    length = struct.unpack("I", len_buffer)[0]

    meta = pickle.loads(data_buffer[-4 - length:-4])

    if 'data_meta' in meta:
        dtype = meta['data_meta']['dtype']
        shape = meta['data_meta']['shape']
        data = np.frombuffer(data_buffer[:-4 - length], dtype).reshape(shape)
    else:
        data = None

    return data, meta