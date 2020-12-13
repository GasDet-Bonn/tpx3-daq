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
import signal
import sys

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

local_configuration = {
    # Scan parameters
    'scan_timeout' : 60*60,
    #'thrfile'     : './output_data/20180707_222224_mask.h5'
}


class DataTake(ScanBase):

    scan_id = "data_take"

    def handle_exit(sig, frame):
        raise(SystemExit)

    signal.signal(signal.SIGTERM, handle_exit)

    def scan(self, scan_timeout=60.0, progress = None, status = None, **kwargs):
        '''
            Takes data for run. A runtime in secondes can be defined. scan_timeout 0 is interpreted as infinite
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
        '''

        # Check if parameters are valid before starting the scan
        if scan_timeout < 0:
            raise ValueError("Value {} for scan_timeout must be equal or bigger than 0".format(scan_timeout))

        system_exit = False

        # Disable test pulses, set the mode to ToT/ToA and write the configuration to the Timepix3
        self.chip._configs["TP_en"] = 0
        self.chip._configs["Op_mode"] = 0
        self.chip.write_general_config()

        # Initialize data-driven readout
        self.chip.read_pixel_matrix_datadriven()

        # Start the run
        self.logger.info('Starting data taking...')
        if status != None:
            status.put("Starting run")
        if status != None:
            status.put("iteration_symbol")

        # If there is a defined runtime crate a progress bar
        if scan_timeout != 0 and progress == None:
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
                            if progress == None:
                                # Update the progress bar
                                pbar.n = how_long
                                pbar.refresh()
                            else:
                                # Update the progress fraction and put it in the queue
                                fraction = how_long / scan_timeout
                                progress.put(fraction)
                            if how_long > scan_timeout:
                                self.stop_scan = True

                        # If the runtime is 0 show and update a time counter and run infinitely
                        minutes, seconds = divmod(how_long, 60)
                        hours, minutes = divmod(minutes, 60)
                        if scan_timeout == 0 and status == None:
                            print(f'Runtime: %d:%02d:%02d\r' % (hours, minutes, seconds), end="")
                        elif status != None:
                            status.put('Run since: %d:%02d:%02d' % (hours, minutes, seconds))

                    # react on keyboard interupt
                    except KeyboardInterrupt:
                        self.logger.info('Scan was stopped due to keyboard interrupt')
                        self.stop_scan = True
                    except SystemExit:
                        self.logger.info('Scan was stopped due to system exit')
                        self.stop_scan = True
                        system_exit = True

            self.chip['PULSE_GEN'].reset()

        if scan_timeout != 0 and progress == None:
            # Close the progress bar
            pbar.clear()

        if status != None:
            status.put("iteration_finish_symbol")

        self.logger.info('Scan finished')

        if system_exit == True:
            raise SystemExit

if __name__ == "__main__":
    scan = DataTake()
    scan.start(**local_configuration)
