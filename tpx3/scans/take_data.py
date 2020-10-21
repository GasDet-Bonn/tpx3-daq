#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs a run in ToT/ToA mode with data-driven readout
'''

from __future__ import print_function
from __future__ import absolute_import
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
            Takes data for run
        '''

        # Check if parameters are valid before starting the scan
        if scan_timeout < 0:
            raise ValueError("Value {} for scan_timeout must be equal or bigger than 0".format(scan_timeout))

        
        # Set the threshold of the chip
        Vthreshold_fine = 117
        Vthreshold_coarse = 8
        self.chip.set_dac("Vthreshold_fine", Vthreshold_fine)
        self.chip.set_dac("Vthreshold_coarse", Vthreshold_coarse)

        # Disable test pulses, set the mode to ToT/ToA and write the configuration to the Timepix3
        self.chip._configs["TP_en"] = 0
        self.chip._configs["Op_mode"] = 0
        self.chip.write_general_config()

        # Initialize data-driven readout
        self.chip.read_pixel_matrix_datadriven()

        # Start the run
        self.logger.info('Starting data taking...')

        # If there is a defined runtime crate a progress bar
        if scan_timeout != 0:
            pbar = tqdm(total=int(scan_timeout))

        start_time = time.time()

        with self.readout(scan_param_id=1):
            time.sleep(0.1)

            # Open the shutter and take data
            with self.shutter():
                self.stop_scan = False

                while not self.stop_scan:
                    try:
                        time.sleep(1)
                        how_long = int(time.time() - start_time)
                        
                        # If there is a defined runtime update the progress bar continiously until the time is over
                        if scan_timeout != 0:
                            pbar.n = how_long
                            pbar.refresh()
                            if how_long > scan_timeout:
                                self.stop_scan = True

                        # If the runtime is 0 show and update a time counter and run infinitely
                        else:
                            minutes, seconds = divmod(how_long, 60)
                            hours, minutes = divmod(minutes, 60)
                            print(f'Runtime: %d:%02d:%02d\r' % (hours, minutes, seconds), end="")

                    # react on keyboard interupt
                    except KeyboardInterrupt:
                        self.logger.info('Scan was stopped due to keyboard interrupt')
                        self.stop_scan = True


            time.sleep(0.1)

        if scan_timeout != 0:
            # Close the progress bar
            pbar.clear()

        self.logger.info('Scan finished')

if __name__ == "__main__":
    scan = DataTake()
    scan.start(**local_configuration)
