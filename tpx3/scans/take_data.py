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

    def init_chip_data_taking(self, reset=False, **kwargs):

        if reset:
            # call the init procedure for the whole chip again
            self.init_chip(reset, **kwargs)

        self.chip.write_ctpr([])  # ALL

        # Step 5: Set general config
        self.chip.write_general_config()

        Vthreshold_fine = 80
        Vthreshold_coarse = 8

        # TODO: Should be loaded from configuration and saved in rn_config
        self.chip.set_dac("VTP_coarse", 128)
        self.chip.set_dac("Vthreshold_fine", Vthreshold_fine)
        self.chip.set_dac("Vthreshold_coarse", Vthreshold_coarse)

        self.chip._configs["TP_en"] = 0
        self.chip._configs["Op_mode"] = 0
        self.chip.write_general_config()

        self.chip.read_pixel_matrix_datadriven()

    def stop_readout(self):
        """
        Convenience proc to stop a readout in order to reset the chip.
        Disables the fifo readout and resets it. Then sends the
        stop command to the chip.
        """

        self.fifo_readout.enable_rx(False)
        self.fifo_readout.reset_rx()

        stop_cmd = []
        stop_cmd.append(self.chip.stop_readout(write=False))
        stop_cmd.append(self.chip.reset_sequential(write=False))
        self.chip.write(stop_cmd)

    def scanImpl(self, start_time, pbar, scan_timeout=60.0):
        """
        The function actually implementing the scan procedure.
        Inputs:
            - scan_timeout = the length of the scan
        Outputs:
            - return False, if the chip should be reset and the scanning
              restarted.
              True, if the data taking ended successfully.
        """
        result = False
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
                        result = True
                    if self.reset_chip == True:
                        self.logger.warning('Too many RX errors encountered. '
                                            'Will try to reset the chip.')
                        self.stop_scan = True
                        self.reset_chip = False
                        result = False
                except KeyboardInterrupt:  # react on keyboard interupt
                    self.logger.info('Scan was stopped due to keyboard interrupt')
                    self.stop_scan = True
                    result = True

        print("Returning from scanImpl with ", result)
        return result

    def scan(self, scan_timeout=60.0, **kwargs):
        '''

        Parameters
        ----------

        '''

        self.init_chip_data_taking(**kwargs)

        self.logger.info('Starting data taking...')
        pbar = tqdm(total=int(scan_timeout))  # [s]

        start_time = time.time()

        with self.readout(scan_param_id=1):
            time.sleep(0.1)

            # call scanImpl until it returns True, indicating
            # a successful data scan (instead of resetting the chip
            while not self.scanImpl(start_time, pbar, scan_timeout):
                # else we received many errors, so reset chip

                # stoppping the readout
                self.logger.warning("After > 255 RX errors (probably noisy pixel) ",
                                    ", stop readout, reset chip and RX then restart.")
                self.stop_readout()

                time.sleep(0.3)
                self.init_chip_data_taking(reset=True, **kwargs)
                self.chip['FIFO'].reset()
                self.fifo_readout.clear_buffer()
                # restart the readout thread
                time.sleep(0.3)

            time.sleep(0.1)

        pbar.clear()

        self.logger.info('Scan finished')

if __name__ == "__main__":
    scan = DataTake()
    scan.start(**local_configuration)
