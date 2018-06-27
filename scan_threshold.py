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
    'VTP_fine_start'   : 256,
    'VTP_fine_stop'    : 256 + 140,
    'n_injections'     : 100,
}


class ThresholdScan(ScanBase):

    scan_id = "threshold_scan"

    def scan(self, VTP_fine_start=100, VTP_fine_stop=200, n_injections=100, mask_step=8, **kwargs):
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

        self.chip.write_ctpr()  # ALL

        # Step 5: Set general config
        self.chip.write_general_config()

        # Step 6: Write to the test pulse registers
        # Step 6a: Write to period and phase tp registers
        data = self.chip.write_tp_period(1, 0)

        # Step 6b: Write to pulse number tp register
        self.chip.write_tp_pulsenumber(n_injections)

        #TODO: Should be loaded from configuration and saved in rn_config
        self.chip.set_dac("VTP_coarse", 128)
        self.chip.set_dac("Vthreshold_fine", 220)
        self.chip.set_dac("Vthreshold_coarse", 8)

        self.chip.read_pixel_matrix_datadriven()

        self.logger.info('Preparing injection masks...')

        start_column = 0
        stop_column = 256

        #TODO: should be loaded from file/configuration
        self.chip.thr_matrix[:, :] = 15
        self.chip.mask_matrix[start_column:stop_column, :] = self.chip.MASK_ON

        mask_cmds = []
        pbar = tqdm(total=mask_step)
        for i in range(mask_step):
            mask_step_cmd = []

            self.chip.test_matrix[:, :] = self.chip.TP_OFF
            # self.chip.test_matrix[start_column:stop_column,i*mask_step:i*mask_step+mask_step] = self.chip.TP_ON
            self.chip.test_matrix[start_column:stop_column, i::mask_step] = self.chip.TP_ON

            for i in range(256 / 4):
                mask_step_cmd.append(self.chip.write_pcr(range(4 * i, 4 * i + 4), write=False))

            mask_step_cmd.append(self.chip.read_pixel_matrix_datadriven())

            mask_cmds.append(mask_step_cmd)
            pbar.update(1)
        pbar.close()

        cal_high_range = range(VTP_fine_start, VTP_fine_stop, 1)

        self.logger.info('Starting scan...')
        pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            self.chip.set_dac("VTP_fine", vcal)
            time.sleep(0.001)

            with self.readout(scan_param_id=scan_param_id):
                for mask_step_cmd in mask_cmds:
                    self.chip.write(mask_step_cmd)
                    with self.shutter():
                        time.sleep(0.001)
                        pbar.update(1)
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
            hit_data = analysis.interpret_raw_data(raw_data, meta_data)
            hit_data = hit_data[hit_data['data_header'] == 1]
            param_range = np.unique(meta_data['scan_param_id'])
            scurve = analysis.scurve_hist(hit_data, param_range)

            n_injections = [int(item[1]) for item in run_config if item[0] == 'n_injections'][0]
            VTP_fine_start = [int(item[1]) for item in run_config if item[0] == 'VTP_fine_start'][0]
            VTP_fine_stop = [int(item[1]) for item in run_config if item[0] == 'VTP_fine_stop'][0]

            param_range = range(VTP_fine_start, VTP_fine_stop)
            thr2D, sig2D, chi2ndf2D = analysis.fit_scurves_multithread(scurve, scan_param_range=param_range, n_injections=n_injections)

            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

            h5_file.create_table(h5_file.root.interpreted, 'hit_data', hit_data, filters=tb.Filters(complib='zlib', complevel=5))

            h5_file.create_carray(h5_file.root.interpreted, name='HistSCurve', obj=scurve)
            h5_file.create_carray(h5_file.root.interpreted, name='Chi2Map', obj=chi2ndf2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='ThresholdMap', obj=thr2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='NoiseMap', obj=sig2D.T)

            hist_occ = np.reshape(np.sum(scurve, axis=1), (256, 256)).T
            h5_file.create_carray(h5_file.root.interpreted, name='HistOcc', obj=hist_occ)

    def plot(self):
        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting plotting...')
        with tb.open_file(h5_filename, 'r') as h5_file:

            # Q: Maybe Plotting should not know about the file?
            with plotting.Plotting(h5_filename) as p:

                VTP_fine_start = p.run_config['VTP_fine_start']
                VTP_fine_stop = p.run_config['VTP_fine_stop']
                n_injections = p.run_config['n_injections']

                p.plot_parameter_page()

                mask = ~h5_file.root.configuration.mask_matrix[:]

                occ_masked = np.ma.masked_array(h5_file.root.interpreted.HistOcc[:], mask)
                p.plot_occupancy(occ_masked, title='Integrated Occupancy', z_max='median', suffix='occupancy')

                thr_matrix = h5_file.root.configuration.thr_matrix[:],
                p.plot_distribution(thr_matrix, plot_range=range(0, 16), title='TDAC distribution', x_axis_title='TDAC', y_axis_title='# of hits', suffix='tdac_distribution')

                scurve_hist = h5_file.root.interpreted.HistSCurve[:].T
                max_occ = n_injections + 10
                p.plot_scurves(scurve_hist, range(VTP_fine_start, VTP_fine_stop), scan_parameter_name="VTP_fine", max_occ=max_occ)

                chi2_sel = h5_file.root.interpreted.Chi2Map[:] > 0.  # Mask not converged fits (chi2 = 0)
                mask[~chi2_sel] = True

                hist = np.ma.masked_array(h5_file.root.interpreted.ThresholdMap[:], mask)
                p.plot_distribution(hist, plot_range=range(VTP_fine_start, VTP_fine_stop), x_axis_title='VTP_fine', title='Threshold distribution', suffix='threshold_distribution')

                p.plot_occupancy(hist, z_label='Threshold', title='Threshold', show_sum=False, suffix='threshold_map', z_min=VTP_fine_start, z_max=VTP_fine_stop)

                hist = np.ma.masked_array(h5_file.root.interpreted.NoiseMap[:], mask)
                p.plot_distribution(hist, plot_range=np.arange(0.1, 4, 0.1), title='Noise distribution', suffix='noise_distribution')
                p.plot_occupancy(hist, z_label='Noise', title='Noise', show_sum=False, suffix='noise_map', z_min=0.1, z_max=4.0)


if __name__ == "__main__":
    scan = ThresholdScan()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
