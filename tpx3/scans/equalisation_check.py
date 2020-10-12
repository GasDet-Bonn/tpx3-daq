#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script performs a threshold scan with an equalised matrix and noise
    to valitate the equalisation.
'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import os

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

from tables.exceptions import NoSuchNodeError

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'Vthreshold_start' : 1000,
    'Vthreshold_stop'  : 1350,
    'maskfile'         : './output_data/20191107_162600_mask.h5'
}


class Equalisation_Check(ScanBase):

    scan_id = "Equalisation_Check"
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
        pbar = tqdm(total=mask_step)
        for j in range(mask_step):
            mask_step_cmd = []

            self.chip.test_matrix[:, :] = self.chip.TP_OFF
            self.chip.mask_matrix[:, :] = self.chip.MASK_OFF
            self.chip.mask_matrix[start_column:stop_column, j::mask_step] = self.chip.MASK_ON

            for i in range(256 // 4):
                mask_step_cmd.append(self.chip.write_pcr(range(4 * i, 4 * i + 4), write=False))

            mask_step_cmd.append(self.chip.read_pixel_matrix_datadriven())

            mask_cmds.append(mask_step_cmd)
            pbar.update(1)
        pbar.close()

        cal_high_range = range(Vthreshold_start, Vthreshold_stop, 1)

        self.logger.info('Starting scan...')
        pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            if(vcal <= 511):
                coarse_threshold = 0
                fine_threshold = vcal
            else:
                relative_fine_threshold = (vcal - 512) % 160
                coarse_threshold = (((vcal - 512) - relative_fine_threshold) // 160) + 1
                fine_threshold = relative_fine_threshold + 352
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

        self.logger.info('Scan finished')

    def analyze(self):
        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting data analysis...')
        with tb.open_file(h5_filename, 'r+') as h5_file:
            raw_data = h5_file.root.raw_data[:]
            meta_data = h5_file.root.meta_data[:]
            run_config = h5_file.root.configuration.run_config[:]

            # TODO: TMP this should go to analysis function with chunking
            self.logger.info('Interpret raw data...')
            hit_data = analysis.interpret_raw_data(raw_data, meta_data)
            print(hit_data)
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == 'Vthreshold_start'][0]
            Vthreshold_stop = [int(item[1]) for item in run_config if item[0] == 'Vthreshold_stop'][0]

            hit_data = hit_data[hit_data['data_header'] == 1]
            print(hit_data)
            param_range = np.unique(meta_data['scan_param_id'])
            
            self.logger.info('Get the global threshold distributions for all pixels...')
            scurve = analysis.scurve_hist(hit_data, param_range)
            self.logger.info('Calculate the mean of the global threshold distributions for all pixels...')
            vths = analysis.vths(scurve, param_range, Vthreshold_start)

            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

            h5_file.create_table(h5_file.root.interpreted, 'hit_data', hit_data, filters=tb.Filters(complib='zlib', complevel=5))
            h5_file.create_carray(h5_file.root.interpreted, name='HitDistribution', obj=scurve)
            h5_file.create_carray(h5_file.root.interpreted, name='PixelThresholdMap', obj=vths.T)

    def plot(self):
        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting plotting...')
        with tb.open_file(h5_filename, 'r') as h5_file:

            # Q: Maybe Plotting should not know about the file?
            with plotting.Plotting(h5_filename) as p:

                Vthreshold_start = p.run_config['Vthreshold_start']
                Vthreshold_stop = p.run_config['Vthreshold_stop']

                p.plot_parameter_page()

                mask = h5_file.root.configuration.mask_matrix[:]

                thr_matrix = h5_file.root.configuration.thr_matrix[:],
                p.plot_distribution(thr_matrix, plot_range=np.arange(-0.5, 16.5, 1), title='TDAC distribution', x_axis_title='TDAC', y_axis_title='# of hits', suffix='tdac_distribution')

                vth_hist = h5_file.root.interpreted.HitDistribution[:].T
                p.plot_scurves(vth_hist, range(Vthreshold_start, Vthreshold_stop), scan_parameter_name="Vthreshold")

                vths = h5_file.root.interpreted.PixelThresholdMap[:]
                p.plot_occupancy(vths, z_label='Threshold', title='Threshold', show_sum=False, suffix='threshold_map', z_min=Vthreshold_start, z_max=Vthreshold_stop)
                p.plot_distribution(vths, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution', suffix='threshold_distribution')


if __name__ == "__main__":
    scan = Equalisation_Check()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()