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

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

local_configuration = {
    # Scan parameters
    'mask_step'        : 32,
    'VTP_fine_start'   : 256 + 0,
    'VTP_fine_stop'    : 256 + 140,
    'n_injections'     : 100,
    #'maskfile'        : './output_data/?_mask.h5'
}


scan_id = "threshold_scan"

def analyze(self, filename):
    h5_filename = filename + '.h5'

    self.logger.info('Starting data analysis...')
    with tb.open_file(h5_filename, 'r+') as h5_file:
        raw_data = h5_file.root.raw_data[:]
        meta_data = h5_file.root.meta_data[:]
        run_config = h5_file.root.configuration.run_config[:]

        op_mode = [int(item[1]) for item in run_config if item[0] == 'op_mode'][0]
        VCO_mode = [int(item[1]) for item in run_config if item[0] == 'VCO_mode'][0]

        # TODO: TMP this should go to analysis function with chunking
        hit_data = analysis.interpret_raw_data(raw_data, meta_data, op_mode, VCO_mode)

        print hit_data[0:10]


if __name__ == "__main__":

    import sys

    analyze(sys.argv[1])
