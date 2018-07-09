#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script ...
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
    'scan_timeout' : 60*60,
    #'maskfile'     : './output_data/20180707_222224_mask.h5'
}


class DataTake(ScanBase):

    scan_id = "data_take"

    def scan(self, scan_timeout=60.0, **kwargs):
        '''

        Parameters
        ----------

        '''


        self.chip.write_ctpr([])  # ALL

        # Step 5: Set general config
        self.chip.write_general_config()

        Vthreshold_fine = 117
        Vthreshold_coarse = 8


        # TODO: Should be loaded from configuration and saved in rn_config
        self.chip.set_dac("VTP_coarse", 128)
        self.chip.set_dac("Vthreshold_fine", Vthreshold_fine)
        self.chip.set_dac("Vthreshold_coarse", Vthreshold_coarse)

        self.chip._configs["TP_en"] = 0
        self.chip._configs["Op_mode"] = 0
        self.chip.write_general_config()

        self.chip.read_pixel_matrix_datadriven()

        self.logger.info('Starting data taking...')
        pbar = tqdm(total=int(scan_timeout))  # [s]

        start_time = time.time()

        with self.readout(scan_param_id=1):
            time.sleep(0.1)
            with self.shutter():
                self.stop_scan = False

                while not self.stop_scan:
                    try:
                        time.sleep(1)
                        how_long = int(time.time() - start_time)
                        pbar.n = how_long
                        pbar.refresh()
                        if how_long > scan_timeout:
                            self.stop_scan = True

                    except KeyboardInterrupt:  # react on keyboard interupt
                        self.logger.info('Scan was stopped due to keyboard interrupt')
                        self.stop_scan = True


            time.sleep(0.1)

        pbar.clear()

        self.logger.info('Scan finished')

if __name__ == "__main__":
    scan = DataTake()
    scan.start(**local_configuration)
