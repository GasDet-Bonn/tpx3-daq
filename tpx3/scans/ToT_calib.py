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
from __future__ import absolute_import
from __future__ import division
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import math

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting
from six.moves import range

local_configuration = {
    # Scan parameters
    'mask_step'        : 64,
    'VTP_fine_start'   : 210 + 0,
    'VTP_fine_stop'    : 210 + 300,
    'n_injections'     : 1,
    'maskfile'        : './output_data/20200505_165149_mask.h5'
}


class ToTCalib(ScanBase):

    scan_id = "ToT_calib"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self, start_column = 0, stop_column = 256, VTP_fine_start=100, VTP_fine_stop=200, n_injections=100, mask_step=32, **kwargs):
        '''
        Testpulse scan main loop

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

        #self.chip.write_ctpr()  # ALL

        # Step 5: Set general config
        self.chip.configs["Op_mode"] = 0 # Change to ToT/ToA mode
        self.chip.write_general_config()

        # Step 6: Write to the test pulse registers
        # Step 6a: Write to period and phase tp registers
        data = self.chip.write_tp_period(3, 0)

        # Step 6b: Write to pulse number tp register
        self.chip.write_tp_pulsenumber(n_injections)
        #self.chip.write_tp_period(200,8)

        self.logger.info('Preparing injection masks...')

        mask_cmds = []
        pbar = tqdm(total=mask_step)
        for i in range(mask_step):
            mask_step_cmd = []

            self.chip.test_matrix[:, :] = self.chip.TP_OFF
            self.chip.mask_matrix[:, :] = self.chip.MASK_OFF
            
            self.chip.test_matrix[(i//(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step))),
                                  (i%(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step)))] = self.chip.TP_ON
            self.chip.mask_matrix[(i//(mask_step//int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step))),
                                  (i%(mask_ste/p/int(math.sqrt(mask_step))))::(mask_step//int(math.sqrt(mask_step)))] = self.chip.MASK_ON

            #self.chip.test_matrix[start_column:stop_column, i::mask_step] = self.chip.TP_ON
            #self.chip.mask_matrix[start_column:stop_column, i::mask_step] = self.chip.MASK_ON

            for i in range(256 // 4):
                mask_step_cmd.append(self.chip.write_pcr(list(range(4 * i, 4 * i + 4)), write=False))

            mask_step_cmd.append(self.chip.read_pixel_matrix_datadriven())

            mask_cmds.append(mask_step_cmd)
            pbar.update(1)
        pbar.close()

        cal_high_range = list(range(VTP_fine_start, VTP_fine_stop, 1))

        self.logger.info('Starting scan...')
        pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            self.chip.set_dac("VTP_fine", vcal)
            time.sleep(0.01)

            with self.readout(scan_param_id=scan_param_id):
                for i, mask_step_cmd in enumerate(mask_cmds):
                    self.chip.write_ctpr(list(range(i//(mask_step//int(math.sqrt(mask_step))), 256, mask_step//int(math.sqrt(mask_step)))))
                    self.chip.write(mask_step_cmd)
                    with self.shutter():
                        time.sleep(0.01)
                        pbar.update(1)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.01)
                time.sleep(0.01)
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
            totcurve = analysis.scurve_hist(hit_data, param_range)

            n_injections = [int(item[1]) for item in run_config if item[0] == 'n_injections'][0]
            VTP_fine_start = [int(item[1]) for item in run_config if item[0] == 'VTP_fine_start'][0]
            VTP_fine_stop = [int(item[1]) for item in run_config if item[0] == 'VTP_fine_stop'][0]

            param_range = list(range(VTP_fine_start, VTP_fine_stop))
            a2D, b2D, c2D, t2D, chi2ndf2D = analysis.fit_totcurves_multithread(totcurve, scan_param_range=param_range)

            h5_file.remove_node(h5_file.root.interpreted, recursive=True)

            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')

            h5_file.create_table(h5_file.root.interpreted, 'hit_data', hit_data, filters=tb.Filters(complib='zlib', complevel=5))

            h5_file.create_carray(h5_file.root.interpreted, name='HistSCurve', obj=totcurve)
            h5_file.create_carray(h5_file.root.interpreted, name='Chi2Map', obj=chi2ndf2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='aMap', obj=a2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='bMap', obj=b2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='cMap', obj=c2D.T)
            h5_file.create_carray(h5_file.root.interpreted, name='tMap', obj=t2D.T)

            pix_occ = np.bincount(hit_data['x'] * 256 + hit_data['y'], minlength=256 * 256).astype(np.uint32)
            hist_occ = np.reshape(pix_occ, (256, 256)).T
            h5_file.create_carray(h5_file.root.interpreted, name='HistOcc', obj=hist_occ)

    def plot(self):
        h5_filename = self.output_filename + '.h5'

        self.logger.info('Starting plotting...')
        with tb.open_file(h5_filename, 'r') as h5_file:

            # Q: Maybe Plotting should not know about the file?
            with plotting.Plotting(h5_filename) as p:

                VTP_fine_start = p.run_config['VTP_fine_start']
                VTP_fine_stop = p.run_config['VTP_fine_stop']
                VTP_coarse = p.dacs['VTP_coarse']
                n_injections = p.run_config['n_injections']

                p.plot_parameter_page()

                mask = h5_file.root.configuration.mask_matrix[:]

                occ_masked = np.ma.masked_array(h5_file.root.interpreted.HistOcc[:], mask)
                p.plot_occupancy(occ_masked, title='Integrated Occupancy', z_max='maximum', suffix='occupancy')

                thr_matrix = h5_file.root.configuration.thr_matrix[:],
                p.plot_distribution(thr_matrix, plot_range=np.arange(-0.5, 16.5, 1), title='TDAC distribution', x_axis_title='TDAC', y_axis_title='# of hits', suffix='tdac_distribution')

                scurve_hist = h5_file.root.interpreted.HistSCurve[:].T
                p.plot_scurves(scurve_hist, list(range(VTP_fine_start, VTP_fine_stop)), electron_axis=False, scan_parameter_name="VTP_fine", max_occ=250, ylabel='ToT Clock Cycles', title='ToT curves')

                hist = np.ma.masked_array(h5_file.root.interpreted.aMap[:], mask)
                p.plot_distribution(hist, plot_range=np.arange(0, 20, 0.1), x_axis_title='a', title='a distribution', suffix='a_distribution')

                hist = np.ma.masked_array(h5_file.root.interpreted.bMap[:], mask)
                p.plot_distribution(hist, plot_range=list(range(-5000, 0, 100)), x_axis_title='b', title='b distribution', suffix='b_distribution')

                hist = np.ma.masked_array(h5_file.root.interpreted.cMap[:], mask)
                p.plot_distribution(hist, plot_range=list(range(-10000, 0000, 200)), x_axis_title='c', title='c distribution', suffix='c_distribution')

                hist = np.ma.masked_array(h5_file.root.interpreted.tMap[:], mask)
                p.plot_distribution(hist, plot_range=list(range(200, 300, 2)), x_axis_title='t', title='t distribution', suffix='t_distribution')
                


if __name__ == "__main__":
    scan = ToTCalib()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()