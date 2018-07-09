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
    'wait_time': 0.1
}


class NoiseTune(ScanBase):

    scan_id = "tune_noise"

    def scan(self, start_column=0, stop_column=256, wait_time=1.0, **kwargs):
        '''

        Parameters
        ----------

        '''

        self.chip.write_ctpr([])  # ALL

        # Step 5: Set general config
        self.chip.write_general_config()

        #TODO: Move to configuration
        Vthreshold_fine = 130
        Vthreshold_coarse = 8


        # TODO: Should be loaded from configuration and saved in rn_config
        self.chip.set_dac("VTP_coarse", 128)
        self.chip.set_dac("Vthreshold_fine", Vthreshold_fine)
        self.chip.set_dac("Vthreshold_coarse", Vthreshold_coarse)

        self.chip._configs["TP_en"] = 0
        self.chip._configs["Op_mode"] = 0
        self.chip.write_general_config()

        self.chip.read_pixel_matrix_datadriven()

        self.chip.thr_matrix[:, :] = 0
        self.chip.test_matrix[:, :] = self.chip.TP_OFF
        self.chip.mask_matrix[start_column:stop_column, :] = self.chip.MASK_ON

        def take_data():
            self.fifo_readout.reset_rx()
            self.fifo_readout.enable_rx(True)
            time.sleep(0.2)

            mask_step_cmd = []
            for i in range(256 / 4):
                mask_step_cmd.append(self.chip.write_pcr(range(4 * i, 4 * i + 4), write=False))
            mask_step_cmd.append(self.chip.read_pixel_matrix_datadriven())
            self.chip.write(mask_step_cmd)

            stop_cmd = []
            stop_cmd.append(self.chip.stop_readout(write=False))
            #stop_cmd.append(self.chip.set_dac("Vthreshold_coarse", 15, write=False))
            stop_cmd.append(self.chip.reset_sequential(write=False))

            with self.readout(scan_param_id=1, fill_buffer=True, clear_buffer=True):
                time.sleep(0.1)
                #self.chip.set_dac("Vthreshold_coarse", 6)
                time.sleep(0.01)
                with self.shutter():
                    time.sleep(wait_time)
                self.chip.write(stop_cmd)
                time.sleep(0.1)

            dqdata = self.fifo_readout.data
            raw_data = np.concatenate([item[0] for item in dqdata])
            error = (len(raw_data) % 2 != 0)

            hit_data = analysis.interpret_raw_data(raw_data)

            error |= (self.chip['RX'].LOST_DATA_COUNTER > 0)
            error |= (self.chip['RX'].DECODER_ERROR_COUNTER > 0)
            if error:
                self.logger.error('DATA ERROR')

            hit_data = hit_data[hit_data['data_header'] == 1]
            self.logger.info('raw_data = %d, hit_data = %d' % (len(raw_data), len(hit_data)))

            bc = np.bincount(hit_data['x'].astype(np.uint16) * 256 + hit_data['y'], minlength=256 * 256)
            hist_occ = np.reshape(bc, (256, 256))
            return hist_occ

        ## Find lowest global threshold (mask noisy pixel on te way)
        dis_pix_no = 0
        while 1:
            self.chip.set_dac("Vthreshold_fine", Vthreshold_fine)
            self.chip.set_dac("Vthreshold_coarse", Vthreshold_coarse)

            self.logger.info('Vthreshold_fine = %d' % (Vthreshold_fine,))

            occ = take_data()
            to_dis_p = (float(dis_pix_no + np.count_nonzero(occ)) / ((stop_column - start_column) * 256)) * 100.0

            if to_dis_p > 0.1:
                break

            disbaled_smt = False
            where_hit = np.where(occ > 0)
            for h in range(len(where_hit[0])):
                self.chip.mask_matrix[where_hit[0][h], where_hit[1][h]] = self.chip.MASK_OFF
                self.logger.info('Disable: col=%d row=%d' % (where_hit[0][h], where_hit[1][h]))
                disbaled_smt = True

            dis_pix_no = np.count_nonzero(self.chip.mask_matrix[start_column:stop_column, :])

            if disbaled_smt is False:
                Vthreshold_fine -= 1

            dis_pix_no_p = (float(dis_pix_no) / ((stop_column - start_column) * 256)) * 100.0

            self.logger.info('dis_pix_no = %d %.3f %%' % (dis_pix_no, dis_pix_no_p))

        self.chip.set_dac("Vthreshold_fine", Vthreshold_fine + 2)

        # ## Find lowest local threshold
        # ## Lower local threshold gradually and increse if noisy
        np.set_printoptions(linewidth=120)

        for tdac_set in range(16):

            step_inc = 32
            for step in range(step_inc):

                to_change = ~np.logical_or(self.chip.mask_matrix, self.chip.thr_matrix < tdac_set)
                mask_inc = np.zeros((256, 256), dtype=np.bool)
                mask_inc[:, step::step_inc] = True

                self.chip.thr_matrix[np.logical_and(to_change, mask_inc)] += 1

                while 1:
                    occ = take_data()

                    correct_smt = 0
                    for col in range(start_column, stop_column):
                        for row in range(256):
                            if occ[col, row]:
                                if self.chip.thr_matrix[col, row] >= tdac_set and  self.chip.thr_matrix[col, row] > 0:
                                    self.chip.thr_matrix[col, row] -= 1
                                    correct_smt += 1

                    tdac_dist = np.bincount(self.chip.thr_matrix[start_column:stop_column, :].flatten())
                    self.logger.info(str((tdac_set, step, Vthreshold_fine, correct_smt, tdac_dist)))

                    if step != step_inc - 1:
                        break

                    if correct_smt == 0:
                        break

        self.save_mask_matrix()
        self.save_thr_mask()
        #TODO: Save DACs?

if __name__ == "__main__":
    scan = NoiseTune()
    scan.start(**local_configuration)
