#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script scans over different thresholds for one testpulse height
'''
from __future__ import print_function

from __future__ import absolute_import
from tqdm import tqdm
import numpy as np
import time
import tables as tb
import math

from tpx3.scan_base import ScanBase
import tpx3.analysis as analysis
import tpx3.plotting as plotting

local_configuration = {
    # Scan parameters
    'mask_step'        : 16,
    'Vthreshold_start' : 1500,
    'Vthreshold_stop'  : 2600,
    'n_injections'     : 100,
    'n_pulse_heights'  : 3,
    'maskfile'         : './output_data/20200511_103833_mask.h5'
}


class ThresholdCalib(ScanBase):

    scan_id = "threshold_calib"
    wafer_number = 0
    y_position = 0
    x_position = 'A'

    def scan(self,  start_column = 0, stop_column = 256, Vthreshold_start=1312, Vthreshold_stop=1471, n_injections=100, n_pulse_heights=5, mask_step=32, **kwargs):
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

        self.chip.write_ctpr()  # ALL

        # Step 5: Set general config
        self.chip.write_general_config()

        # Step 6: Write to the test pulse registers
        # Step 6a: Write to period and phase tp registers
        data = self.chip.write_tp_period(1, 0)

        # Step 6b: Write to pulse number tp register
        self.chip.write_tp_pulsenumber(n_injections)

        self.logger.info('Preparing injection masks...')

        mask_cmds = []
        pbar = tqdm(total=mask_step)
        for i in range(mask_step):
            mask_step_cmd = []

            self.chip.test_matrix[:, :] = self.chip.TP_OFF
            self.chip.mask_matrix[:, :] = self.chip.MASK_OFF

            #self.chip.test_matrix[start_column:stop_column, i::mask_step] = self.chip.TP_ON
            #self.chip.mask_matrix[start_column:stop_column, i::mask_step] = self.chip.MASK_ON

            self.chip.test_matrix[(i//(mask_step/int(math.sqrt(mask_step))))::(mask_step/int(math.sqrt(mask_step))),
                                  (i%(mask_step/int(math.sqrt(mask_step))))::(mask_step/int(math.sqrt(mask_step)))] = self.chip.TP_ON
            self.chip.mask_matrix[(i//(mask_step/int(math.sqrt(mask_step))))::(mask_step/int(math.sqrt(mask_step))),
                                  (i%(mask_step/int(math.sqrt(mask_step))))::(mask_step/int(math.sqrt(mask_step)))] = self.chip.MASK_ON

            self.chip.thr_matrix[:, :] = 0

            for i in range(256 / 4):
                mask_step_cmd.append(self.chip.write_pcr(range(4 * i, 4 * i + 4), write=False))

            mask_step_cmd.append(self.chip.read_pixel_matrix_datadriven())

            mask_cmds.append(mask_step_cmd)
            pbar.update(1)
        pbar.close()

        cal_high_range = range(0, (Vthreshold_stop-Vthreshold_start) * n_pulse_heights, 1)

        self.logger.info('Starting scan...')
        pbar = tqdm(total=len(mask_cmds) * len(cal_high_range))

        for scan_param_id, vcal in enumerate(cal_high_range):
            self.chip.set_dac("VTP_fine", 250 + (300 / n_pulse_heights) * (vcal / (Vthreshold_stop-Vthreshold_start)))

            vcal_step = vcal % (Vthreshold_stop-Vthreshold_start) + Vthreshold_start
            if(vcal_step <= 511):
                coarse_threshold = 0
                fine_threshold = vcal_step
            else:
                relative_fine_threshold = (vcal_step - 512) % 160
                coarse_threshold = (((vcal_step - 512) - relative_fine_threshold) / 160) + 1
                fine_threshold = relative_fine_threshold + 352
                #print("rel: %i coarse: %i fine: %i" % (relative_fine_threshold, coarse_threshold, fine_threshold))
            self.chip.set_dac("Vthreshold_coarse", coarse_threshold)
            self.chip.set_dac("Vthreshold_fine", fine_threshold)
            #print("ID: %i VTP_fine: %i coarse: %i fine: %i" % (scan_param_id, 200 + (300 / n_pulse_heights) * (vcal / (Vthreshold_stop-Vthreshold_start)), coarse_threshold, fine_threshold))
            time.sleep(0.001)

            with self.readout(scan_param_id=scan_param_id):
                for i, mask_step_cmd in enumerate(mask_cmds):
                    self.chip.write_ctpr(range(i//(mask_step/int(math.sqrt(mask_step))), 256, mask_step/int(math.sqrt(mask_step))))
                    self.chip.write(mask_step_cmd)
                    with self.shutter():
                        time.sleep(0.001)
                        pbar.update(1)
                    self.chip.stop_readout()
                    self.chip.reset_sequential()
                    time.sleep(0.001)
                time.sleep(0.001)
        pbar.close()

        self.logger.info('Scan finished')

    def analyze(self):
        h5_filename = self.output_filename + '.h5'
        #h5_filename = './output_data/20200512_141527_threshold_calib.h5'

        self.logger.info('Starting data analysis...')
        with tb.open_file(h5_filename, 'r+') as h5_file:
            raw_data = h5_file.root.raw_data[:]
            meta_data = h5_file.root.meta_data[:]
            run_config = h5_file.root.configuration.run_config[:]

            n_injections = [int(item[1]) for item in run_config if item[0] == 'n_injections'][0]
            n_pulse_heights = [int(item[1]) for item in run_config if item[0] == 'n_pulse_heights'][0]
            Vthreshold_start = [int(item[1]) for item in run_config if item[0] == 'Vthreshold_start'][0]
            Vthreshold_stop = [int(item[1]) for item in run_config if item[0] == 'Vthreshold_stop'][0]

            # TODO: TMP this should go to analysis function with chunking
            hit_data = analysis.interpret_raw_data(raw_data, meta_data)
            hit_data = hit_data[hit_data['data_header'] == 1]

            h5_file.create_group(h5_file.root, 'interpreted', 'Interpreted Data')
            h5_file.create_table(h5_file.root.interpreted, 'hit_data', hit_data, filters=tb.Filters(complib='zlib', complevel=5))

            for pulse_height in range(n_pulse_heights):
                param_range = np.unique(meta_data['scan_param_id'])
                #print(len(param_range))
                #print("pulse_height: %i Vthreshold_start: %i Vthreshold_stop: %i" % (pulse_height, Vthreshold_start, Vthreshold_stop))
                #print(pulse_height * (Vthreshold_stop - Vthreshold_start))
                #print((pulse_height + 1) * (Vthreshold_stop - Vthreshold_start))
                hit_data_step = hit_data[hit_data['scan_param_id'] >= (pulse_height * (Vthreshold_stop - Vthreshold_start))]
                hit_data_step = hit_data_step[hit_data_step['scan_param_id'] < ((pulse_height + 1) * (Vthreshold_stop - Vthreshold_start))]
                #print(hit_data_step)
                #for hit in hit_data_step:
                #    print(hit['scan_param_id'], hit['x'], hit['y'], hit['EventCounter'])
                param_range_step = np.unique(hit_data_step['scan_param_id'])
                #print(len(param_range_step))
                scurve = analysis.scurve_hist(hit_data_step, param_range_step)
                #print(scurve[128*256+128])

                param_range_step = range(Vthreshold_start, Vthreshold_stop)
                thr2D, sig2D, chi2ndf2D = analysis.fit_scurves_multithread(scurve, scan_param_range=param_range_step, n_injections=n_injections, invert_x=True)
                #print(thr2D)
                #quit()

                HistSCurve_name = 'HistSCurve_' + str(pulse_height)
                Chi2Map_name = 'Chi2Map_' + str(pulse_height)
                ThresholdMap_name = 'ThresholdMap_' + str(pulse_height)
                NoiseMap_name = 'NoiseMap_' + str(pulse_height)
                h5_file.create_carray(h5_file.root.interpreted, name=HistSCurve_name, obj=scurve)
                h5_file.create_carray(h5_file.root.interpreted, name=Chi2Map_name, obj=chi2ndf2D.T)
                h5_file.create_carray(h5_file.root.interpreted, name=ThresholdMap_name, obj=thr2D.T)
                h5_file.create_carray(h5_file.root.interpreted, name=NoiseMap_name, obj=sig2D.T)

                pix_occ = np.bincount(hit_data['x'] * 256 + hit_data['y'], minlength=256 * 256).astype(np.uint32)
                hist_occ = np.reshape(pix_occ, (256, 256)).T
                HistOcc_name = 'HistOcc_' + str(pulse_height)
                h5_file.create_carray(h5_file.root.interpreted, name=HistOcc_name, obj=hist_occ)

    def plot(self):
        h5_filename = self.output_filename + '.h5'
        #h5_filename = './output_data/20200512_141527_threshold_calib.h5'

        self.logger.info('Starting plotting...')
        with tb.open_file(h5_filename, 'r') as h5_file:

            # Q: Maybe Plotting should not know about the file?
            with plotting.Plotting(h5_filename) as p:

                Vthreshold_start = p.run_config['Vthreshold_start']
                Vthreshold_stop = p.run_config['Vthreshold_stop']
                n_injections = p.run_config['n_injections']
                n_pulse_heights = p.run_config['n_pulse_heights']

                p.plot_parameter_page()

                thr_matrix = h5_file.root.configuration.thr_matrix[:],
                p.plot_distribution(thr_matrix, plot_range=np.arange(-0.5, 16.5, 1), title='TDAC distribution', x_axis_title='TDAC', y_axis_title='# of hits', suffix='tdac_distribution')

                #for pulse_height in range(n_pulse_heights):
                mask = h5_file.root.configuration.mask_matrix[:]

                #scurve_hist_name = 'HistSCurve_' + str(pulse_height)
                #scurve_hist_path = 'h5_file.root.interpreted.' + scurve_hist_name + '[:].T'
                #scurve_hist = scurve_hist_path
                scurve_hist = h5_file.root.interpreted.HistSCurve_0[:].T
                max_occ = n_injections * 5
                p.plot_scurves(scurve_hist, range(Vthreshold_start, Vthreshold_stop), scan_parameter_name="Vthreshold", max_occ=max_occ)

                #chi2_sel_name = 'Chi2Map_' + str(pulse_height)
                #chi2_sel_path = 'h5_file.root.interpreted.' + chi2_sel_name + '[:]'
                #chi2_sel = chi2_sel_path > 0.  # Mask not converged fits (chi2 = 0)
                chi2_sel = h5_file.root.interpreted.Chi2Map_0[:] > 0.  # Mask not converged fits (chi2 = 0)
                mask[~chi2_sel] = True

                #ThresholdMap_name = 'ThresholdMap_' + str(pulse_height)
                #ThresholdMap_path = 'h5_file.root.interpreted.' + ThresholdMap_name + '[:]'
                #hist = np.ma.masked_array(ThresholdMap_path, mask)
                hist = np.ma.masked_array(h5_file.root.interpreted.ThresholdMap_0[:], mask)
                result_0 = p.plot_distribution(hist, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution', suffix='threshold_distribution')
                #p.plot_occupancy(hist, z_label='Threshold', title='Threshold', show_sum=False, suffix='threshold_map', z_min=Vthreshold_start, z_max=Vthreshold_stop)

                scurve_hist = h5_file.root.interpreted.HistSCurve_1[:].T
                max_occ = n_injections * 5
                p.plot_scurves(scurve_hist, range(Vthreshold_start, Vthreshold_stop), scan_parameter_name="Vthreshold", max_occ=max_occ)

                #chi2_sel_name = 'Chi2Map_' + str(pulse_height)
                #chi2_sel_path = 'h5_file.root.interpreted.' + chi2_sel_name + '[:]'
                #chi2_sel = chi2_sel_path > 0.  # Mask not converged fits (chi2 = 0)
                chi2_sel = h5_file.root.interpreted.Chi2Map_1[:] > 0.  # Mask not converged fits (chi2 = 0)
                mask[~chi2_sel] = True

                #ThresholdMap_name = 'ThresholdMap_' + str(pulse_height)
                #ThresholdMap_path = 'h5_file.root.interpreted.' + ThresholdMap_name + '[:]'
                #hist = np.ma.masked_array(ThresholdMap_path, mask)
                hist = np.ma.masked_array(h5_file.root.interpreted.ThresholdMap_1[:], mask)
                result_1 = p.plot_distribution(hist, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution', suffix='threshold_distribution')
                #p.plot_occupancy(hist, z_label='Threshold', title='Threshold', show_sum=False, suffix='threshold_map', z_min=Vthreshold_start, z_max=Vthreshold_stop)

                scurve_hist = h5_file.root.interpreted.HistSCurve_2[:].T
                max_occ = n_injections * 5
                p.plot_scurves(scurve_hist, range(Vthreshold_start, Vthreshold_stop), scan_parameter_name="Vthreshold", max_occ=max_occ)

                #chi2_sel_name = 'Chi2Map_' + str(pulse_height)
                #chi2_sel_path = 'h5_file.root.interpreted.' + chi2_sel_name + '[:]'
                #chi2_sel = chi2_sel_path > 0.  # Mask not converged fits (chi2 = 0)
                chi2_sel = h5_file.root.interpreted.Chi2Map_2[:] > 0.  # Mask not converged fits (chi2 = 0)
                mask[~chi2_sel] = True

                #ThresholdMap_name = 'ThresholdMap_' + str(pulse_height)
                #ThresholdMap_path = 'h5_file.root.interpreted.' + ThresholdMap_name + '[:]'
                #hist = np.ma.masked_array(ThresholdMap_path, mask)
                hist = np.ma.masked_array(h5_file.root.interpreted.ThresholdMap_2[:], mask)
                result_2 = p.plot_distribution(hist, plot_range=np.arange(Vthreshold_start-0.5, Vthreshold_stop-0.5, 1), x_axis_title='Vthreshold', title='Threshold distribution', suffix='threshold_distribution')
                #p.plot_occupancy(hist, z_label='Threshold', title='Threshold', show_sum=False, suffix='threshold_map', z_min=Vthreshold_start, z_max=Vthreshold_stop)

                print(result_0[1], result_0[2])
                print(result_1[1], result_1[2])
                print(result_2[1], result_2[2])

if __name__ == "__main__":
    scan = ThresholdCalib()
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
