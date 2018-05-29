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

from tqdm import tqdm
import numpy as np
import time
import tables as tb

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
#from tpx3.analysis import plotting



local_configuration = {
    # Scan parameters
    'maskfile'          : 'auto',

    'VTP_fine_start'   : 256,
    'VTP_fine_stop'    : 400,
    }


class ThresholdScan(ScanBase):
    scan_id = "threshold_scan"


    def scan(self, VTP_fine_start=100, VTP_fine_stop=200, n_injections=100, **kwargs):
        '''
        Threshold scan main loop

        Parameters
        ----------

        VTP_fine_start : int
            TODO
        VTP_fine_stop : int
            TODO

        '''



        #
        # ALL this should be set in set_configuration?
        #


        # choose the pixel for which to do an SCurve
        x_pixel = 128
        y_pixel = 128
        self.chip.set_pixel_pcr(x_pixel, y_pixel, self.chip.TP_ON, 7, self.chip.MASK_ON)
        # Step 3b: Write PCR to chip
        for i in range(256):
            self.chip.write_pcr([i])

        # Step 5: Set general config
        self.chip.write_general_config()

        # Step 6: Write to the test pulse registers
        # Step 6a: Write to period and phase tp registers
        data = self.chip.write_tp_period(1, 0)

        # Step 6b: Write to pulse number tp register
        self.chip.write_tp_pulsenumber(n_injections)

        self.chip.write_ctpr([128])

        self.chip.set_dac("VTP_coarse", 128)
        self.chip.set_dac("Vthreshold_fine", 256)
        self.chip.set_dac("Vthreshold_coarse", 8)
        self.chip.read_pixel_matrix_datadriven()

        cal_high_range = range(VTP_fine_start, VTP_fine_stop, 1)

        #self.logger.info('Preparing injection masks...')
        #mask_data = self.prepare_injection_masks(start_column, stop_column, start_row, stop_row, mask_step)
        mask_data = [1];

        self.logger.info('Starting scan...')
        pbar = tqdm(total=len(mask_data)*len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            self.chip.set_dac("VTP_fine", vcal)

            time.sleep(0.1)
            with self.readout(scan_param_id=scan_param_id):
                for mask in mask_data:
                    with self.shutter():
                        time.sleep(0.1)
                        pbar.update(1)
                    time.sleep(0.1)
        pbar.close()

        self.logger.info('Scan finished')

    def analyze(self):


        h5_filename = self.output_filename + '.h5'
        #h5_filename = '/home/tomek/git/tpx3-daq/tpx3/scans/output_data/20180529_194045_threshold_scan.h5'

        # TODO: TMP this should go to analysis function
        with tb.open_file(h5_filename, 'r+') as in_file_h5:
            raw_data = in_file_h5.root.raw_data[:]
            meta_data = in_file_h5.root.meta_data[:]

            hit_data = analysis.interpret_raw_data(raw_data, meta_data)
            hit_data = hit_data[hit_data['data_header']==1]

            param_range = np.unique(meta_data['scan_param_id'])
            scurve = np.zeros((256*256, len(param_range)), dtype=np.uint16)

            sscan = []
            for i in param_range:
                hits = np.where(hit_data['scan_param_id'] == i)
                ev = 0
                for h in hits:
                    if len(h):
                        ev += hit_data['EventCounter'][h[0]]

                scurve[0][i] = ev

            print(scurve[0])
            thr2D, sig2D, chi2ndf2D = analysis.fit_scurves_multithread(scurve, scan_param_range=param_range, n_injections=100)
            print(thr2D[0][0], sig2D[0][0])

if __name__ == "__main__":
    scan = ThresholdScan()
    scan.start(**local_configuration)
    scan.analyze()
