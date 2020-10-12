#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs an equalisation of pixels based on a threshold scan
    with noise.
'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import os
import math

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

from tables.exceptions import NoSuchNodeError
from six.moves import range

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'Vthreshold_start' : 1000,
    'Vthreshold_stop'  : 1350
}


class Equalisation(ScanBase):

    scan_id = "Equalisation"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self,  start_column = 0, stop_column = 256, Vthreshold_start=1312, Vthreshold_stop=1471, mask_step=32, **kwargs):
        '''
        Threshold scan main loop

        Parameters
        ----------

        Vthreshold_fine_start : int
            TODO
        Vthreshold_fine_stop : int
            TODO

        '''

        #
        # ALL this should be set in set_configuration?
        #

        # Step 5: Set general config
        self.chip.write_general_config()

        # Step 6: Write to the test pulse registers
        # Step 6a: Write to period and phase tp registers
        data = self.chip.write_tp_period(1, 0)

        #TODO: Should be loaded from configuration and saved in rn_config

        self.logger.info('Preparing injection masks...')

        mask_cmds = []
        mask_cmds2 = []
        pbar = tqdm(total=mask_step)
        for j in range(mask_step):
            mask_step_cmd = []
            mask_step_cmd2 = []

            self.chip.test_matrix[:, :] = self.chip.TP_OFF
            self.chip.mask_matrix[:, :] = self.chip.MASK_OFF
            
            self.chip.test_matrix[(j//(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step))),
                                  (j%(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step)))] = self.chip.TP_ON
            self.chip.mask_matrix[(j//(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step))),
                                  (j%(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step)))] = self.chip.MASK_ON
            
            #self.chip.mask_matrix[start_column:stop_column, j::mask_step] = self.chip.MASK_ON
            
            self.chip.thr_matrix[:, :] = 0

            for i in range(256 // 4):
                mask_step_cmd.append(self.chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))

            self.chip.thr_matrix[:, :] = 15

            for i in range(256 // 4):
                mask_step_cmd2.append(self.chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))

            mask_step_cmd.append(self.chip.read_pixel_matrix_datadriven())
            mask_step_cmd2.append(self.chip.read_pixel_matrix_datadriven())

            mask_cmds.append(mask_step_cmd)
            mask_cmds2.append(mask_step_cmd2)
            pbar.update(1)
        pbar.close()

        cal_high_range = list(range(Vthreshold_start, Vthreshold_stop, 1))

        self.logger.info('Starting scan for THR = 0...')
        pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            if(vcal <= 511):
                coarse_threshold = 0
                fine_threshold = vcal
            else:
                relative_fine_threshold = (vcal - 512) % 160
                coarse_threshold = (((vcal - 512) - relative_fine_threshold) // 160) + 1
                fine_threshold = relative_fine_threshold + 352
                #print("rel: %i coarse: %i fine: %i" % (relative_fine_threshold, coarse_threshold, fine_threshold))
            self.chip.set_dac("Vthreshold_coarse", coarse_threshold)
            self.chip.set_dac("Vthreshold_fine", fine_threshold)
            time.sleep(0.001)

            with self.readout(scan_param_id=scan_param_id):
                for mask_step_cmd in mask_cmds:
                    self.chip.write(mask_step_cmd)
                    with self.shutter():
                        time.sleep(0.01)
                        pbar.update(1)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)
        pbar.close()

        self.logger.info('Starting scan for THR = 15...')
        pbar = tqdm(total=len(mask_cmds2) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            if(vcal <= 511):
                coarse_threshold = 0
                fine_threshold = vcal
            else:
                relative_fine_threshold = (vcal - 512) % 160
                coarse_threshold = (((vcal - 512) - relative_fine_threshold) // 160) + 1
                fine_threshold = relative_fine_threshold + 352
                #print("rel: %i coarse: %i fine: %i" % (relative_fine_threshold, coarse_threshold, fine_threshold))
            self.chip.set_dac("Vthreshold_coarse", coarse_threshold)
            self.chip.set_dac("Vthreshold_fine", fine_threshold)
            time.sleep(0.001)

            with self.readout(scan_param_id=scan_param_id + len(cal_high_range)):
                for mask_step_cmd in mask_cmds2:
                    self.chip.write(mask_step_cmd)
                    with self.shutter():
                        time.sleep(0.01)
                        pbar.update(1)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)
        pbar.close()

        self.logger.info('Scan finished')

    def analyze(self):
        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting data analysis...')
        with tb.open_file(h5_filename, 'r+') as h5_file:
            raw_data = h5_file.root.raw_data[:]
            meta_data = h5_file.root.meta_data[:]
            run_config = h5_file.root.configuration.run_config[:]

            # TODO: TMP this should go to analysis function with chunking
            #print('haeder1\t header2\t y\t x\t Hits\t Counter')
            self.logger.info('Interpret raw data...')
            hit_data = analysis.interpret_raw_data(raw_data, meta_data)
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == 'Vthreshold_start'][0]
            Vthreshold_stop = [int(item[1]) for item in run_config if item[0] == 'Vthreshold_stop'][0]

            hit_data = hit_data[hit_data['data_header'] == 1]
            param_range = np.unique(meta_data['scan_param_id'])
            hit_data_th0 = hit_data[hit_data['scan_param_id'] < len(param_range) // 2]
            param_range_th0 = np.unique(hit_data_th0['scan_param_id'])
            hit_data_th15 = hit_data[hit_data['scan_param_id'] >= len(param_range) // 2]
            param_range_th15 = np.unique(hit_data_th15['scan_param_id'])
            
            self.logger.info('Get the global threshold distributions for all pixels...')
            scurve_th0 = analysis.scurve_hist(hit_data_th0, param_range_th0)
            scurve_th15 = analysis.scurve_hist(hit_data_th15, param_range_th15)
            self.logger.info('Calculate the mean of the global threshold distributions for all pixels...')
            vths_th0 = analysis.vths(scurve_th0, param_range_th0, Vthreshold_start)
            vths_th15 = analysis.vths(scurve_th15, param_range_th15, Vthreshold_start)
            self.logger.info('Get the cumulated global threshold distributions...')
            hist_th0 = analysis.vth_hist(vths_th0, Vthreshold_stop)
            hist_th15 = analysis.vth_hist(vths_th15, Vthreshold_stop)

            self.logger.info('Calculate the equalisation matrix...')
            eq_matrix = analysis.eq_matrix(hist_th0, hist_th15, vths_th0, Vthreshold_start, Vthreshold_stop)
            mask_matrix = np.zeros((256, 256), dtype=np.bool)
            mask_matrix[:, :] = 0

            self.logger.info('Writing mask_matrix to file...')
            maskfile = os.path.join(self.working_dir, self.timestamp + '_mask.h5')

            with tb.open_file(maskfile, 'a') as out_file:
                try:
                    out_file.remove_node(out_file.root.mask_matrix)
                except NoSuchNodeError:
                    self.logger.debug('Specified maskfile does not include a mask_matrix yet!')

                out_file.create_carray(out_file.root,
                                    name='mask_matrix',
                                    title='Matrix mask',
                                    obj=mask_matrix)
                self.logger.info('Closing mask file: %s' % (maskfile))

            self.logger.info('Writing equalisation matrix to file...')
            with tb.open_file(maskfile, 'a') as out_file:
                try:
                    out_file.remove_node(out_file.root.thr_matrix)
                except NoSuchNodeError:
                    self.logger.debug('Specified maskfile does not include a thr_mask yet!')

                out_file.create_carray(out_file.root,
                                        name='thr_matrix',
                                        title='Matrix Threshold',
                                        obj=eq_matrix)
                self.logger.info('Closing equalisation matrix file: %s' % (maskfile))


if __name__ == "__main__":
    scan = Equalisation()
    scan.start(**local_configuration)
    scan.analyze()