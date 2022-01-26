#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    Plotting class
'''

from __future__ import absolute_import
from __future__ import division
import zlib  # workaround for segmentation fault on tables import
import numpy as np
import math
import logging
import shutil
import os
import matplotlib
import ast
import copy

import tables as tb
import matplotlib.pyplot as plt

from collections import OrderedDict
from scipy.optimize import curve_fit
from scipy.stats import norm
from matplotlib.figure import Figure
from matplotlib.artist import setp
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import colors, cm
from matplotlib.backends.backend_pdf import PdfPages
import six
from six.moves import range

#import bdaq53.analysis.analysis_utils as au

logging.basicConfig(
    format="%(asctime)s - [%(name)-8s] - %(levelname)-7s %(message)s")
loglevel = logging.INFO


ELECTRON_CONVERSION = {'slope': 10.02, 'offset': 64}   # [slope] = Electrons / Delta VCAL; [offset] = Electrons
TITLE_COLOR = '#07529a'
OVERTEXT_COLOR = '#07529a'


class ConfigDict(dict):
    ''' Dictionary with different key data types:
        str / int / float depending on value
    '''

    def __init__(self, *args):
        super(ConfigDict, self).__init__(*args)

    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        return self._type_cast_value(key, val)

    def get(self, k, d=None):
        val = dict.get(self, k, d)
        return self._type_cast_value(k, val)

    def _type_cast_value(self, key, val):
        try:
            return ast.literal_eval(val)
        except (ValueError, SyntaxError):  # fallback to return a string
            return val

class Plotting(object):
    def __init__(self, analyzed_data_file, pdf_file=None, level='draft', qualitative=False, internal=False, save_single_pdf=False, save_png=False, iteration = None):
        self.logger = logging.getLogger('Plotting')
        self.logger.setLevel(loglevel)

        self.plot_cnt = 0
        self.save_single_pdf = save_single_pdf
        self.save_png = save_png
        self.level = level
        self.qualitative = qualitative
        self.internal = internal
        self.clustered = False
        self.skip_plotting = False

        if pdf_file is None:
            path, name = os.path.split(analyzed_data_file)
            path = os.path.dirname(path)
            self.filename = os.path.join(path, name.split('.')[0] + '.pdf')
        else:
            self.filename = pdf_file
        self.out_file = PdfPages(self.filename)

        try:
            if isinstance(analyzed_data_file, str):
                in_file = tb.open_file(analyzed_data_file, 'r+')
                root = in_file.root
            else:
                root = analyzed_data_file
        except IOError:
            self.logger.warning('Interpreted data file does not exist!')
            self.skip_plotting = True
            return

        if iteration == None:
            self.run_config = ConfigDict(root.configuration.run_config[:])
        else:
            run_config_call = ('root.' + 'configuration.run_config_' + str(iteration) + '[:]')
            self.run_config = ConfigDict(eval(run_config_call))
        

        try:
            if iteration == None:
                self.dacs = ConfigDict(root.configuration.dacs[:])
            else:
                dacs_call = ('root.' + 'configuration.dacs_' + str(iteration) + '[:]')
                self.dacs = ConfigDict(eval(dacs_call))
        except tb.NoSuchNodeError:
            self.dacs = {}

        try:
            in_file.close()
        except:
            pass


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.out_file is not None and isinstance(self.out_file, PdfPages):
            self.logger.info('Closing output PDF file: %s', str(self.out_file._file.fh.name))
            self.out_file.close()
            shutil.copyfile(self.filename, os.path.join(os.path.split(self.filename)[0], 'last_scan.pdf'))

    ''' User callable plotting functions '''

    def _save_plots(self, fig, suffix=None, tight=False, plot_queue=None):
        increase_count = False
        bbox_inches = 'tight' if tight else ''
        if suffix is None:
            suffix = str(self.plot_cnt)

        if plot_queue != None:
            figure = fig, suffix
            plot_queue.put(figure)

        if not self.out_file:
            fig.show()
        else:
            self.out_file.savefig(fig, bbox_inches=bbox_inches)
        if self.save_png:
            fig.savefig(self.filename[:-4] + '_' +
                        suffix + '.png', bbox_inches=bbox_inches)
            increase_count = True
        if self.save_single_pdf:
            fig.savefig(self.filename[:-4] + '_' +
                        suffix + '.pdf', bbox_inches=bbox_inches)
            increase_count = True
        if increase_count:
            self.plot_cnt += 1

    def _gauss(self, x, *p):
        amplitude, mu, sigma = p
        return amplitude * np.exp(- (x - mu)**2.0 / (2.0 * sigma**2.0))

    def _lin(self, x, *p):
        m, b = p
        return m * x + b

    def _add_text(self, fig):
        fig.subplots_adjust(top=0.85)
        y_coord = 0.92
        if self.qualitative:
            fig.text(0.1, y_coord, 'Timepix3 qualitative',
                     fontsize=12, color=OVERTEXT_COLOR, transform=fig.transFigure)
            if self.run_config['chip_wafer'] is not None:
                fig.text(0.7, y_coord, 'Chip: W%s-%s%s',
                         (self.run_config['chip_wafer'].decode(), self.run_config['chip_x'].decode(), self.run_config['chip_y'].decode()), fontsize=12, color=OVERTEXT_COLOR, transform=fig.transFigure)
        else:
            fig.text(0.1, y_coord, 'Timepix3 %s' %
                     (self.level), fontsize=12, color=OVERTEXT_COLOR, transform=fig.transFigure)
            if self.run_config[b'chip_wafer'] is not None:
                fig.text(0.7, y_coord, 'Chip: W%s-%s%s' %
                         (self.run_config[b'chip_wafer'].decode(), self.run_config[b'chip_x'].decode(), self.run_config[b'chip_y'].decode()), fontsize=12, color=OVERTEXT_COLOR, transform=fig.transFigure)
        if self.internal:
            fig.text(0.1, 1, 'Timepix3 Internal', fontsize=16, color='r', rotation=45, bbox=dict(
                boxstyle='round', facecolor='white', edgecolor='red', alpha=0.7), transform=fig.transFigure)

    def _convert_to_e(self, dac, use_offset=True):
        if use_offset:
            return dac * ELECTRON_CONVERSION['slope'] + ELECTRON_CONVERSION['offset']
        else:
            return dac * ELECTRON_CONVERSION['slope']

    def _add_electron_axis(self, fig, ax, use_electron_offset=True):
        fig.subplots_adjust(top=0.75)
        ax.title.set_position([.5, 1.15])

        fig.canvas.draw()
        ax2 = ax.twiny()

        xticks = []
        for x in ax.xaxis.get_majorticklabels():
            try:
                xticks.append(int(self._convert_to_e(float(x.get_text()), use_offset=use_electron_offset)))  # it crashes sometimes for last value depending on scale (return empty string)
            except:
                pass

        ax2.set_xticklabels(xticks)

        l = ax.get_xlim()
        l2 = ax2.get_xlim()

        def f(x): return l2[0] + (x - l[0]) / (l[1] - l[0]) * (l2[1] - l2[0])
        ticks = f(ax.get_xticks())
        ax2.xaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))

#         ax2.set_xlabel(r'Electrons ($x \cdot %1.2f \; \frac{e^-}{\Delta VCAL} + %1.2f \; e^-$)' % (ELECTRON_CONVERSION['slope'], ELECTRON_CONVERSION['offset']), labelpad=7)
        ax2.set_xlabel('Electrons', labelpad=7)

    def plot_parameter_page(self):
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.axis('off')

        scan_id = self.run_config[b'scan_id'].decode()
        run_name = self.run_config[b'run_name'].decode()
        chip_wafer = self.run_config[b'chip_wafer'].decode()
        chip_x = self.run_config[b'chip_x'].decode()
        chip_y = self.run_config[b'chip_y'].decode()
        sw_ver = self.run_config[b'software_version'].decode()
        board_name = self.run_config[b'board_name'].decode()
        fw_ver = self.run_config[b'firmware_version'].decode()

        if self.level != '':
            text = 'This is a tpx3-daq %s for chip W%s-%s%s.\nRun name: %s' % (
                scan_id, chip_wafer, chip_x, chip_y, run_name)
        else:
            text = 'This is a tpx3-daq %s for chip W%s-%s%s.\nRun name: %s' % (
                scan_id, chip_wafer, chip_x, chip_y, run_name)
        ax.text(0.01, 1, text, fontsize=10)
        ax.text(0.7, 0.02, 'Software version: %s \nReadout board: %s \nFirmware version: %s' % (sw_ver, board_name, fw_ver), fontsize=6)

        ax.text(0.01, 0.02, r'Have a good day!', fontsize=6)

        if b'thrfile' in list(self.run_config.keys()) and self.run_config[b'thrfile'] is not None and not self.run_config[b'thrfile'] == b'None':
            ax.text(0.01, -0.05, 'Equalisation:\n%s' %
                    (self.run_config[b'thrfile']).decode(), fontsize=6)

        if b'maskfile' in list(self.run_config.keys()) and self.run_config[b'maskfile'] is not None and not self.run_config[b'maskfile'] == b'None':
            ax.text(0.01, -0.11, 'Maskfile:\n%s' %
                    (self.run_config[b'maskfile']).decode(), fontsize=6)

        tb_dict = OrderedDict(sorted(self.dacs.items()))
        for key, value in six.iteritems(self.run_config):
            if key in [b'scan_id', b'run_name', b'chip_wafer', b'chip_x', b'chip_y', b'software_version', b'board_name', b'firmware_version', b'disable', b'thrfile', b'maskfile']:
                continue
            tb_dict[key] = int(value)

        tb_list = []
        for i in range(0, len(list(tb_dict.keys())), 3):
            try:
                key1 = list(tb_dict.keys())[i]
                value1 = tb_dict[key1]
                try:
                    key2 = list(tb_dict.keys())[i + 1]
                    value2 = tb_dict[key2]
                except:
                    key2 = b''
                    value2 = ''
                try:
                    key3 = list(tb_dict.keys())[i + 2]
                    value3 = tb_dict[key3]
                except:
                    key3 = b''
                    value3 = ''
                tb_list.append(
                    [key1.decode(), value1, '', key2.decode(), value2, '', key3.decode(), value3])
            except:
                pass

        widths = [0.2, 0.12, 0.1, 0.2, 0.12, 0.1, 0.2, 0.12]
        labels = ['Parameter', 'Value', '', 'Parameter',
                  'Value', '', 'Parameter', 'Value']
        table = ax.table(cellText=tb_list, colWidths=widths,
                         colLabels=labels, cellLoc='left', loc='center')
        table.scale(0.8, 0.8)

        for key, cell in table.get_celld().items():
            row, col = key
            if row == 0:
                cell.set_color('#ffb300')
                cell.set_edgecolor('Black')
                cell.set_fontsize(8)
            if col in [2, 5]:
                cell.set_fill(False)
                cell.visible_edges = 'vertical'
                cell.set_fontsize(8)
            if col in [1, 4, 7]:
                cell._loc = 'center'
                cell.set_fontsize(8)                

        self._save_plots(fig, suffix='parameter_page')

    def _plot_2d_scatter(self, data, title=None, x_axis_title=None, y_axis_title=None, invert_x=False, invert_y=False, log_y=False, color='b', suffix=None, plot_queue=None):
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        ax.plot(data[0], data[1], 'o', color=color)

        if title is not None:
            ax.set_title(title)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        ax.grid()

        if invert_x:
            ax.invert_xaxis()
        if invert_y:
            ax.invert_yaxis()
        if log_y:
            ax.set_yscale('log')

        if self.qualitative:
            ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
            ax.yaxis.set_major_formatter(plt.NullFormatter())
            ax.yaxis.set_minor_formatter(plt.NullFormatter())

        self._save_plots(fig, suffix=suffix, plot_queue=plot_queue)

    def _plot_1d_hist(self, hist, yerr=None, title=None, x_axis_title=None, y_axis_title=None, x_ticks=None, color='r',
                      plot_range=None, log_y=False, suffix=None, plot_queue=None):
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        hist = np.array(hist)
        if plot_range is None:
            plot_range = list(range(0, len(hist)))
        plot_range = np.array(plot_range)
        plot_range = plot_range[plot_range < len(hist)]
        if yerr is not None:
            ax.bar(x=plot_range, height=hist[plot_range],
                   color=color, align='center', yerr=yerr)
        else:
            ax.bar(x=plot_range,
                   height=hist[plot_range], color=color, align='center')
        ax.set_xlim((min(plot_range) - 0.5, max(plot_range) + 0.5))

        ax.set_title(title, color=TITLE_COLOR)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        if x_ticks is not None:
            ax.set_xticks(plot_range)
            ax.set_xticklabels(x_ticks)
            ax.tick_params(which='both', labelsize=8)
        if np.allclose(hist, 0.0):
            ax.set_ylim((0, 1))
        else:
            if log_y:
                ax.set_yscale('log')
                ax.set_ylim((1e-1, np.amax(hist) * 2))
        ax.grid(True)

        if self.qualitative:
            ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
            ax.yaxis.set_major_formatter(plt.NullFormatter())
            ax.yaxis.set_minor_formatter(plt.NullFormatter())

        self._save_plots(fig, suffix=suffix, plot_queue=plot_queue)

    def _plot_tot(self, hist, title=None):
        if title is None:
            if self.qualitative:
                title = 'Time-over-Threshold distribution'
            else:
                title = ('Time-over-Threshold distribution' +
                         r' ($\Sigma$ = %d)' % (np.sum(hist)))
        self._plot_1d_hist(hist=hist, title=title, log_y=True, plot_range=list(range(
            0, 16)), x_axis_title='ToT code', y_axis_title='# of hits', color='b', suffix='tot')

    def _plot_relative_bcid(self, hist, title=None):
        if title is None:
            if self.qualitative:
                title = 'Relative BCID'
            else:
                title = ('Relative BCID' + r' ($\Sigma$ = %d)' %
                         (np.sum(hist)))
        self._plot_1d_hist(hist=hist, title=title, log_y=True, plot_range=list(range(
            0, 32)), x_axis_title='Relative BCID [25 ns]', y_axis_title='# of hits', suffix='rel_bcid')

    def _plot_event_status(self, hist, title=None):
        self._plot_1d_hist(hist=hist,
                           title=('Event status' + r' ($\Sigma$ = %d)' %
                                  (np.sum(hist))) if title is None else title,
                           log_y=True,
                           plot_range=list(range(0, 10)),
                           x_ticks=('User K\noccured', 'Ext\ntrigger', 'TDC\nword', 'BCID\nerror', 'TRG ID\nerror',
                                    'TDC\nambig.', 'Event\nTruncated', 'Unknown\nword', 'Wrong\nstructure', 'Ext. Trig.\nerror'),
                           color='g', y_axis_title='Number of events', suffix='event_status')

    def _plot_bcid_error(self, hist, title=None):
        self._plot_1d_hist(hist=hist,
                           title=('BCID error' + r' ($\Sigma$ = %d)' %
                                  (np.sum(hist))) if title is None else title,
                           log_y=True,
                           plot_range=list(range(0, 32)),
                           x_axis_title='Trigger ID',
                           y_axis_title='Number of event header', color='g',
                           suffix='bcid_error')

    def _plot_cl_size(self, hist):
        ''' Create 1D cluster size plot w/wo log y-scale '''
        self._plot_1d_hist(hist=hist, title='Cluster size',
                           log_y=False, plot_range=list(range(0, 10)),
                           x_axis_title='Cluster size',
                           y_axis_title='# of hits', suffix='cluster_size')
        self._plot_1d_hist(hist=hist, title='Cluster size (log)',
                           log_y=True, plot_range=list(range(0, 100)),
                           x_axis_title='Cluster size',
                           y_axis_title='# of hits', suffix='cluster_size_log')

    def _plot_cl_tot(self, hist):
        ''' Create 1D cluster size plot w/wo log y-scale '''
        self._plot_1d_hist(hist=hist, title='Cluster ToT',
                           log_y=False, plot_range=list(range(0, 96)),
                           x_axis_title='Cluster ToT [25 ns]',
                           y_axis_title='# of hits', suffix='cluster_tot')

    def _plot_cl_shape(self, hist, plot_queue=None):
        ''' Create a histogram with selected cluster shapes '''
        x = np.arange(12)
        fig = Figure()
        _ = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        selected_clusters = hist[[1, 3, 5, 6, 9, 13, 14, 7, 11, 19, 261, 15]]
        ax.bar(x, selected_clusters, align='center')
        ax.xaxis.set_ticks(x)
        fig.subplots_adjust(bottom=0.2)
        ax.set_xticklabels([u"\u2004\u2596",
                            # 2 hit cluster, horizontal
                            u"\u2597\u2009\u2596",
                            # 2 hit cluster, vertical
                            u"\u2004\u2596\n\u2004\u2598",
                            u"\u259e",  # 2 hit cluster
                            u"\u259a",  # 2 hit cluster
                            u"\u2599",  # 3 hit cluster, L
                            u"\u259f",  # 3 hit cluster
                            u"\u259b",  # 3 hit cluster
                            u"\u259c",  # 3 hit cluster
                            # 3 hit cluster, horizontal
                            u"\u2004\u2596\u2596\u2596",
                            # 3 hit cluster, vertical
                            u"\u2004\u2596\n\u2004\u2596\n\u2004\u2596",
                            # 4 hit cluster
                            u"\u2597\u2009\u2596\n\u259d\u2009\u2598"])
        ax.set_title('Cluster shapes', color=TITLE_COLOR)
        ax.set_xlabel('Cluster shape')
        ax.set_ylabel('# of hits')
        ax.grid(True)
        ax.set_yscale('log')
        ax.set_ylim(ymin=1e-1)

        if self.qualitative:
            ax.yaxis.set_major_formatter(plt.NullFormatter())
            ax.yaxis.set_minor_formatter(plt.NullFormatter())

        self._save_plots(fig, suffix='cluster_shape', plot_queue=plot_queue)

    def plot_occupancy(self, hist, electron_axis=False, use_electron_offset=True, title='Occupancy', z_label='# of hits', z_min=None, z_max=None, show_sum=True, suffix=None, plot_queue=None):
        if z_max == 'median':
            z_max = 2 * np.ma.median(hist)
        elif z_max == 'maximum' or z_max is None:
            z_max = np.ma.max(hist)

        if z_max < 1 or hist.all() is np.ma.masked:
            z_max = 1.0

        if z_min is None:
            z_min = np.ma.min(hist)
        if z_min == z_max or hist.all() is np.ma.masked:
            z_min = 0

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        ax.set_adjustable('box')
        extent = [0.5, 256.5, 256.5, 0.5]
        bounds = np.linspace(start=z_min, stop=z_max, num=255, endpoint=True)
        cmap = copy.copy(cm.get_cmap('plasma'))
        cmap.set_bad('w', 1.0)
        norm = colors.BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(hist, interpolation='none', aspect='equal', cmap=cmap,
                       norm=norm, extent=extent)  # TODO: use pcolor or pcolormesh
        ax.set_ylim((256.5, 0.5))
        ax.set_xlim((0.5, 256.5))
        if self.qualitative or not show_sum:
            ax.set_title(title, color=TITLE_COLOR)
        else:
            ax.set_title(title + r' ($\Sigma$ = {0})'.format(
                (0 if hist.all() is np.ma.masked else np.ma.sum(hist))), color=TITLE_COLOR)
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')

        divider = make_axes_locatable(ax)
        if electron_axis:
            pad = 1.0
        else:
            pad = 0.6
        cax = divider.append_axes("bottom", size="5%", pad=pad)
        cb = fig.colorbar(im, cax=cax, ticks=np.linspace(
            start=z_min, stop=z_max, num=10, endpoint=True), orientation='horizontal')
        cax.set_xticklabels([int(round(float(x.get_text())))
                            for x in cax.xaxis.get_majorticklabels()])
        cb.set_label(z_label)

        if electron_axis:
            fig.canvas.draw()
            ax2 = cb.ax.twiny()

            pos = ax2.get_position()
            pos.y1 = 0.14
            ax2.set_position(pos)

            for spine in ax2.spines.values():
                spine.set_visible(False)

            xticks = [int(round(self._convert_to_e(float(x.get_text()), use_offset=use_electron_offset)))
                      for x in cax.xaxis.get_majorticklabels()]
            ax2.set_xticklabels(xticks)
#
            l = cax.get_xlim()
            l2 = ax2.get_xlim()

            def f(x): return l2[0] + (x - l[0]) / \
                (l[1] - l[0]) * (l2[1] - l2[0])
            ticks = f(cax.get_xticks())
            ax2.xaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))

#             ax2.set_xlabel(r'%s [Electrons ($x \cdot %1.2f \; \frac{e^-}{\Delta VCAL} + %1.2f \; e^-$)]' % (z_label, ELECTRON_CONVERSION['slope'], ELECTRON_CONVERSION['offset']), labelpad=7)
            ax2.set_xlabel('%s [Electrons]' % (z_label), labelpad=7)
            cb.set_label(r'%s [$\Delta$ VCAL]' % z_label)

        if self.qualitative:
            ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
            ax.yaxis.set_major_formatter(plt.NullFormatter())
            ax.yaxis.set_minor_formatter(plt.NullFormatter())
            cb.formatter = plt.NullFormatter()
            cb.update_ticks()

        self._save_plots(fig, suffix=suffix, plot_queue=plot_queue)

    def _create_2d_pixel_hist(self, fig, ax, hist2d, title=None, x_axis_title=None, y_axis_title=None, z_min=0, z_max=None, cmap=None):
        extent = [0.5, 400.5, 192.5, 0.5]
        if z_max is None:
            if hist2d.all() is np.ma.masked:  # check if masked array is fully masked
                z_max = 1.0
            else:
                z_max = 2 * np.ma.median(hist2d)
        bounds = np.linspace(start=z_min, stop=z_max, num=255, endpoint=True)
        if cmap is None:
            cmap = copy.copy(cm.get_cmap('coolwarm'))
        cmap.set_bad('w', 1.0)
        norm = colors.BoundaryNorm(bounds, cmap.N)
        im = ax.imshow(hist2d, interpolation='none', aspect="auto", cmap=cmap, norm=norm, extent=extent)
        if title is not None:
            ax.set_title(title)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        fig.colorbar(im, boundaries=bounds, cmap=cmap, norm=norm, ticks=np.linspace(start=0, stop=z_max, num=9, endpoint=True), cax=cax)

    def _plot_three_way(self, hist, title, filename=None, x_axis_title=None, minimum=None, maximum=None, bins=101, cmap=None, plot_queue=None):  # the famous 3 way plot (enhanced)
        if cmap is None:
            if maximum == 'median' or maximum is None:
                cmap = copy.copy(cm.get_cmap('coolwarm'))
            else:
                cmap = copy.copy(cm.get_cmap('cool'))
        # TODO: set color for bad pixels
        # set nan to special value
        # masked_array = np.ma.array (a, mask=np.isnan(a))
        # cmap = matplotlib.cm.jet
        # cmap.set_bad('w',1.0)
        # ax.imshow(masked_array, interpolation='none', cmap=cmap)
        hist = np.ma.masked_invalid(hist)
        if minimum is None:
            minimum = 0.0
        elif minimum == 'minimum':
            minimum = np.ma.min(hist)
        if maximum == 'median' or maximum is None:
            maximum = 2 * np.ma.median(hist)
        elif maximum == 'maximum':
            maximum = np.ma.max(hist)
        if maximum < 1 or hist.all() is np.ma.masked:
            maximum = 1.0

        x_axis_title = '' if x_axis_title is None else x_axis_title
        fig = Figure()
        FigureCanvas(fig)
        fig.patch.set_facecolor('white')
        ax1 = fig.add_subplot(311)
        self._create_2d_pixel_hist(fig, ax1, hist, title=title, x_axis_title="column", y_axis_title="row", z_min=minimum if minimum else 0, z_max=maximum, cmap=cmap)
        ax2 = fig.add_subplot(312)
        self._create_1d_hist(ax2, hist, bins=bins, x_axis_title=x_axis_title, y_axis_title="#", x_min=minimum, x_max=maximum)
        ax3 = fig.add_subplot(313)
        self._create_pixel_scatter_plot(ax3, hist, x_axis_title="channel=row + column*192", y_axis_title=x_axis_title, y_min=minimum, y_max=maximum)
        fig.tight_layout()
        self._save_plots(fig, suffix='threeway', plot_queue=plot_queue)

    def _create_1d_hist(self, ax, hist, title=None, x_axis_title=None, y_axis_title=None, bins=101, x_min=None, x_max=None):
        if x_min is None:
            x_min = 0.0
        if x_max is None:
            if hist.all() is np.ma.masked:  # check if masked array is fully masked
                x_max = 1.0
            else:
                x_max = hist.max()
        hist_bins = int(x_max - x_min) + 1 if bins is None else bins
        if hist_bins > 1:
            bin_width = (x_max - x_min) / (hist_bins - 1)
        else:
            bin_width = 1.0
        hist_range = (x_min - bin_width / 2, x_max + bin_width / 2)
    #     if masked_hist.dtype.kind in 'ui':
    #         masked_hist[masked_hist.mask] = np.iinfo(masked_hist.dtype).max
    #     elif masked_hist.dtype.kind in 'f':
    #         masked_hist[masked_hist.mask] = np.finfo(masked_hist.dtype).max
    #     else:
    #         raise TypeError('Inappropriate type %s' % masked_hist.dtype)
        masked_hist_compressed = np.ma.masked_invalid(np.ma.masked_array(hist)).compressed()
        if masked_hist_compressed.size == 0:
            ax.plot([])
        else:
            _, _, _ = ax.hist(x=masked_hist_compressed, bins=hist_bins, range=hist_range, align='mid')  # re-bin to 1d histogram, x argument needs to be 1D
        # BUG: np.ma.compressed(np.ma.masked_array(hist, copy=True)) (2D) is not equal to np.ma.masked_array(hist, copy=True).compressed() (1D) if hist is ndarray
        ax.set_xlim(hist_range)  # overwrite xlim
        if hist.all() is np.ma.masked:  # or np.allclose(hist, 0.0):
            ax.set_ylim((0, 1))
            ax.set_xlim((-0.5, +0.5))
        elif masked_hist_compressed.size == 0:  # or np.allclose(hist, 0.0):
            ax.set_ylim((0, 1))
        # create histogram without masked elements, higher precision when calculating gauss
    #     h_1d, h_bins = np.histogram(np.ma.masked_array(hist, copy=True).compressed(), bins=hist_bins, range=hist_range)
        if title is not None:
            ax.set_title(title)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
    #     bin_centres = (h_bins[:-1] + h_bins[1:]) / 2
    #     amplitude = np.amax(h_1d)

        # defining gauss fit function
    #     def gauss(x, *p):
    #         amplitude, mu, sigma = p
    #         return amplitude * np.exp(- (x - mu)**2.0 / (2.0 * sigma**2.0))
    #         mu, sigma = p
    #         return 1.0 / (sigma * np.sqrt(2.0 * np.pi)) * np.exp(- (x - mu)**2.0 / (2.0 * sigma**2.0))
    #
    #     def chi_square(observed_values, expected_values):
    #         return (chisquare(observed_values, f_exp=expected_values))[0]
    #         # manual calculation
    #         chisquare = 0
    #         for observed, expected in itertools.izip(list(observed_values), list(expected_values)):
    #             chisquare += (float(observed) - float(expected))**2.0 / float(expected)
    #         return chisquare

    #     p0 = (amplitude, mean, rms)  # p0 is the initial guess for the fitting coefficients (A, mu and sigma above)
    #     try:
    #         coeff, _ = curve_fit(gauss, bin_centres, h_1d, p0=p0)
    #     except (TypeError, RuntimeError), e:
    #         logging.info('Normal distribution fit failed, %s', e)
    #     else:
        xmin, xmax = ax.get_xlim()
        points = np.linspace(xmin, xmax, 500)
    #     hist_fit = gauss(points, *coeff)
        param = norm.fit(masked_hist_compressed)
    #     points = np.linspace(norm.ppf(0.01, loc=param[0], scale=param[1]), norm.ppf(0.99, loc=param[0], scale=param[1]), 100)
        pdf_fitted = norm.pdf(points, loc=param[0], scale=param[1]) * (len(masked_hist_compressed) * bin_width)
        ax.plot(points, pdf_fitted, "r--", label='Normal distribution')
    #     ax.plot(points, hist_fit, "g-", label='Normal distribution')
        try:
            median = np.median(masked_hist_compressed)
        except IndexError:
            logging.warning('Cannot create 1D histogram named %s', title)
            return
        ax.axvline(x=median, color="g")
    #     chi2, pval = chisquare(masked_hist_compressed)
    #     _, p_val = mstats.normaltest(masked_hist_compressed)
    #     textright = '$\mu=%.2f$\n$\sigma=%.2f$\n$\chi^{2}=%.2f$' % (coeff[1], coeff[2], chi2)
    #     props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    #     ax.text(0.85, 0.9, textright, transform=ax.transAxes, fontsize=8, verticalalignment='top', bbox=props)

        textleft = '$\Sigma=%d$\n$\mathrm{mean\,\mu=%.2f}$\n$\mathrm{std\,\sigma=%.2f}$\n$\mathrm{median=%.2f}$' % (len(masked_hist_compressed), param[0], param[1], median)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.9, textleft, transform=ax.transAxes, fontsize=8, verticalalignment='top', bbox=props)


    def plot_fancy_occupancy(self, hist, z_max=None, plot_queue=None):
        if z_max == 'median':
            z_max = 2 * np.ma.median(hist)
        elif z_max == 'maximum' or z_max is None:
            z_max = np.ma.max(hist)
        if z_max < 1 or hist.all() is np.ma.masked:
            z_max = 1.0

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        extent = [0.5, 400.5, 192.5, 0.5]
        bounds = np.linspace(start=0, stop=z_max, num=255, endpoint=True)
        if z_max == 'median':
            cmap = copy.copy(cm.get_cmap('coolwarm'))
        else:
            cmap = copy.copy(cm.get_cmap('cool'))
        cmap.set_bad('w', 1.0)
        norm = colors.BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(hist, interpolation='none', aspect='auto', cmap=cmap, norm=norm, extent=extent)  # TODO: use pcolor or pcolormesh
        ax.set_ylim((192.5, 0.5))
        ax.set_xlim((0.5, 400.5))
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')

        # create new axes on the right and on the top of the current axes
        # The first argument of the new_vertical(new_horizontal) method is
        # the height (width) of the axes to be created in inches.
        divider = make_axes_locatable(ax)
        axHistx = divider.append_axes("top", 1.2, pad=0.2, sharex=ax)
        axHisty = divider.append_axes("right", 1.2, pad=0.2, sharey=ax)

        cax = divider.append_axes("right", size="5%", pad=0.1)
        cb = fig.colorbar(im, cax=cax, ticks=np.linspace(start=0, stop=z_max, num=9, endpoint=True))
        cb.set_label("#")
        # make some labels invisible
        setp(axHistx.get_xticklabels() + axHisty.get_yticklabels(), visible=False)
        hight = np.ma.sum(hist, axis=0)

        axHistx.bar(x=list(range(1, 401)), height=hight, align='center', linewidth=0)
        axHistx.set_xlim((0.5, 400.5))
        if hist.all() is np.ma.masked:
            axHistx.set_ylim((0, 1))
        axHistx.locator_params(axis='y', nbins=3)
        axHistx.ticklabel_format(style='sci', scilimits=(0, 4), axis='y')
        axHistx.set_ylabel('#')
        width = np.ma.sum(hist, axis=1)

        axHisty.barh(y=list(range(1, 193)), width=width, align='center', linewidth=0)
        axHisty.set_ylim((192.5, 0.5))
        if hist.all() is np.ma.masked:
            axHisty.set_xlim((0, 1))
        axHisty.locator_params(axis='x', nbins=3)
        axHisty.ticklabel_format(style='sci', scilimits=(0, 4), axis='x')
        axHisty.set_xlabel('#')

        self._save_plots(fig, suffix='fancy_occupancy', plot_queue=plot_queue)

    def plot_scurves(self, scurves, scan_parameters, electron_axis=False, scan_parameter_name=None, title='S-curves', ylabel='Occupancy', max_occ=None, plot_queue=None):

        if max_occ is None:
            max_occ = np.max(scurves) + 5

        x_bins = np.arange(min(scan_parameters) - 1, max(scan_parameters) + 1)
        y_bins = np.arange(-0.5, max_occ + 0.5)
        n_pixel = 256 * 256

        param_count = scurves.shape[0]
        hist = np.empty([param_count, max_occ], dtype=np.uint32)

        scurves[scurves>=max_occ] = max_occ-1

        for param in range(param_count):
            hist[param] = np.bincount(scurves[param, :], minlength=max_occ)

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        fig.patch.set_facecolor('white')
        cmap = copy.copy(cm.get_cmap('cool'))
        if np.allclose(hist, 0.0) or hist.max() <= 1:
            z_max = 1.0
        else:
            z_max = hist.max()
        # for small z use linear scale, otherwise log scale
        if z_max <= 10.0:
            bounds = np.linspace(start=0.0, stop=z_max, num=255, endpoint=True)
            norm = colors.BoundaryNorm(bounds, cmap.N)
        else:
            bounds = np.linspace(start=1.0, stop=z_max, num=255, endpoint=True)
            norm = colors.LogNorm()

        im = ax.pcolormesh(x_bins, y_bins, hist.T, norm=norm, rasterized=True)

        if z_max <= 10.0:
            cb = fig.colorbar(im, ticks=np.linspace(start=0.0, stop=z_max, num=min(
                11, math.ceil(z_max) + 1), endpoint=True), fraction=0.04, pad=0.05)
        else:
            cb = fig.colorbar(im, fraction=0.04, pad=0.05)
        cb.set_label("# of pixels")
        ax.set_title(title + ' for %d pixel(s)' % (n_pixel), color=TITLE_COLOR)
        if scan_parameter_name is None:
            ax.set_xlabel('Scan parameter')
        else:
            ax.set_xlabel(scan_parameter_name)
        ax.set_ylabel(ylabel)

        if electron_axis:
            self._add_electron_axis(fig, ax)

        if self.qualitative:
            ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
            ax.yaxis.set_major_formatter(plt.NullFormatter())
            ax.yaxis.set_minor_formatter(plt.NullFormatter())
            cb.formatter = plt.NullFormatter()
            cb.update_ticks()

        self._save_plots(fig, suffix='scurves', plot_queue=plot_queue)

    def plot_distribution(self, data, fit=True, plot_range=None, x_axis_title=None, electron_axis=False, use_electron_offset=True, y_axis_title='# of hits', title=None, suffix=None, plot_queue=None):

        if plot_range is None:
            diff = np.amax(data) - np.amin(data)
            if (np.amax(data)) > np.median(data) * 5:
                plot_range = np.arange(
                    np.amin(data), np.median(data) * 5, diff / 100.)
            else:
                plot_range = np.arange(np.amin(data), np.amax(
                    data) + diff / 100., diff / 100.)

        tick_size = np.diff(plot_range)[0]

        hist, bins = np.histogram(np.ravel(data), bins=plot_range)

        bin_centres = (bins[:-1] + bins[1:]) / 2.0

        p0 = (np.amax(hist), np.mean(bins),
              (max(plot_range) - min(plot_range)) / 3)

        if fit == True:
            try:
                coeff, cov = curve_fit(self._gauss, bin_centres, hist, p0=p0)
            except:
                coeff = None
                self.logger.warning('Gauss fit failed!')
        else:
            coeff = None

        if coeff is not None:
            points = np.linspace(min(plot_range), max(plot_range), 500)
            gau = self._gauss(points, *coeff)
            errors = np.sqrt(np.diag(cov))

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        ax.bar(bins[:-1], hist, width=tick_size, align='edge')
        if coeff is not None:
            ax.plot(points, gau, "r-", label='Normal distribution')

        ax.set_xlim((min(plot_range), max(plot_range)))
        ax.set_title(title, color=TITLE_COLOR)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        ax.grid(True)

        if coeff is not None and not self.qualitative:
            if coeff[1] < 10:
                if electron_axis:
                    textright = '$\mu=%.1f\;\Delta$VCAL\n$\;\,\,=%.0f \; e^-$\n\n$\sigma=%.1f\;\Delta$VCAL\n$\;\,\,=%.0f \; e^-$' % (
                        abs(coeff[1]), self._convert_to_e(abs(coeff[1]), use_offset=use_electron_offset), abs(coeff[2]), self._convert_to_e(abs(coeff[2]), use_offset=False))
                else:
                    textright = '$\mu=%.1f \pm %.1f$\n$\sigma=%.1f \pm %.1f$' % (abs(coeff[1]), abs(errors[1]), abs(coeff[2]), abs(errors[2]))
            else:
                if electron_axis:
                    textright = '$\mu=%.0f\;\Delta$VCAL\n$\;\,\,=%.0f \; e^-$\n\n$\sigma=%.0f\;\Delta$VCAL\n$\;\,\,=%.0f \; e^-$' % (
                        abs(coeff[1]), self._convert_to_e(abs(coeff[1]), use_offset=use_electron_offset), abs(coeff[2]), self._convert_to_e(abs(coeff[2]), use_offset=False))
                else:
                    textright = '$\mu=%.2f \pm %.2f$\n$\sigma=%.2f \pm %.2f$' % (abs(coeff[1]), abs(errors[1]), abs(coeff[2]), abs(errors[2]))
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.05, 0.9, textright, transform=ax.transAxes,
                    fontsize=8, verticalalignment='top', bbox=props)

        if electron_axis:
            self._add_electron_axis(fig, ax, use_electron_offset=use_electron_offset)

        if self.qualitative:
            ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
            ax.yaxis.set_major_formatter(plt.NullFormatter())
            ax.yaxis.set_minor_formatter(plt.NullFormatter())

        self._save_plots(fig, suffix=suffix, plot_queue=plot_queue)

        if coeff is not None:
            return coeff, errors

    def plot_datapoints(self, x, y, x_err = None, y_err = None, x_plot_range = None, y_plot_range = None, x_axis_title=None, y_axis_title=None, title=None, suffix=None, plot_queue=None):
        m = (y[len(y)-1]-y[0])/(x[len(x)-1]-x[0])
        b = y[0] - m * x[0]
        p0 = (m, b)
        try:
            coeff, cov = curve_fit(self._lin, x, y, sigma = y_err, p0=p0)
        except:
            coeff = None
            self.logger.warning('Linear fit failed!')

        if coeff is not None:
            errors = np.sqrt(np.diag(cov))
            points = np.linspace(min(x_plot_range), max(x_plot_range), 500)
            lin = self._lin(points, *coeff)

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        ax.errorbar(x, y, y_err, x_err, ls = 'None', marker = 'x', ms = 4)
        if coeff is not None:
            ax.plot(points, lin, "r-", label='Linear fit')

        ax.set_xlim((min(x_plot_range), max(x_plot_range)))
        ax.set_ylim((min(y_plot_range), max(y_plot_range)))
        ax.set_title(title, color=TITLE_COLOR)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        ax.grid(True)

        if coeff is not None and not self.qualitative:
            textright = '$m=%.3f \pm %.3f$\n$n=%.1f \pm %.1f$' % (abs(coeff[0]), abs(errors[0]), abs(coeff[1]), abs(errors[0]))
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.05, 0.9, textright, transform=ax.transAxes,
                    fontsize=8, verticalalignment='top', bbox=props)

        self._save_plots(fig, suffix=suffix, plot_queue=plot_queue)

        if coeff is not None:
            return coeff, errors

    def plot_stacked_threshold(self, data, tdac_mask, plot_range=None, electron_axis=False, x_axis_title=None, y_axis_title=None,
                                title=None, suffix=None, min_tdac=0, max_tdac=15, range_tdac=16, plot_queue=None):
        start_column = self.run_config['start_column']
        stop_column = self.run_config['stop_column']
        data = data[:, start_column:stop_column]

        if plot_range is None:
            diff = np.amax(data) - np.amin(data)
            if (np.amax(data)) > np.median(data) * 5:
                plot_range = np.arange(
                    np.amin(data), np.median(data) * 5, diff / 100.)
            else:
                plot_range = np.arange(np.amin(data), np.amax(
                    data) + diff / 100., diff / 100.)

        tick_size = plot_range[1] - plot_range[0]

        hist, bins = np.histogram(np.ravel(data), bins=plot_range)

        bin_centres = (bins[:-1] + bins[1:]) / 2
        p0 = (np.amax(hist), np.mean(bins),
              (max(plot_range) - min(plot_range)) / 3)

        try:
            coeff, _ = curve_fit(self._gauss, bin_centres, hist, p0=p0)
        except:
            coeff = None
            self.logger.warning('Gauss fit failed!')

        if coeff is not None:
            points = np.linspace(min(plot_range), max(plot_range), 500)
            gau = self._gauss(points, *coeff)

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        cmap = copy.copy(cm.get_cmap('viridis', (range_tdac - 1)))
        # create dicts for tdac data
        data_thres_tdac = {}
        hist_tdac = {}
        tdac_bar = {}

        tdac_map = tdac_mask[:, start_column:stop_column]

        # select threshold data for different tdac values according to tdac map
        for tdac in range(range_tdac):
            data_thres_tdac[tdac] = data[tdac_map == tdac - abs(min_tdac)]
            # histogram threshold data for each tdac
            hist_tdac[tdac], _ = np.histogram(
                np.ravel(data_thres_tdac[tdac]), bins=bins)

            if tdac == 0:
                tdac_bar[tdac] = ax.bar(bins[:-1], hist_tdac[tdac], width=tick_size,
                                        align='edge', color=cmap(.9 / range_tdac * tdac), edgecolor='white')
            elif tdac == 1:
                tdac_bar[tdac] = ax.bar(bins[:-1], hist_tdac[tdac], bottom=hist_tdac[0], width=tick_size,
                                        align='edge', color=cmap(1. / range_tdac * tdac), edgecolor='white')
            else:
                tdac_bar[tdac] = ax.bar(bins[:-1], hist_tdac[tdac], bottom=np.sum([hist_tdac[i] for i in range(
                    tdac)], axis=0), width=tick_size, align='edge', color=cmap(1. / range_tdac * tdac), edgecolor='white')

        fig.subplots_adjust(right=0.85)
        cax = fig.add_axes([0.89, 0.11, 0.02, 0.645])
        sm = plt.cm.ScalarMappable(
            cmap=cmap, norm=colors.Normalize(vmin=min_tdac, vmax=max_tdac))
        sm.set_array([])
        cb = fig.colorbar(sm, cax=cax, ticks=np.linspace(
            start=min_tdac, stop=max_tdac, num=range_tdac, endpoint=True))
        cb.set_label('TDAC')

        if coeff is not None:
            ax.plot(points, gau, "r-", label='Normal distribution')

        ax.set_xlim((min(plot_range), max(plot_range)))
        ax.set_title(title, color=TITLE_COLOR)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        ax.grid(True)

        if coeff is not None and not self.qualitative:
            if electron_axis:
                textright = '$\mu=%.0f\;\Delta$VCAL\n$\;\,\,=%.0f \; e^-$\n\n$\sigma=%.0f\;\Delta$VCAL\n$\;\,\,=%.0f \; e^-$' % (
                    abs(coeff[1]), self._convert_to_e(abs(coeff[1])), abs(coeff[2]), self._convert_to_e(abs(coeff[2]), use_offset=False))
            else:
                textright = '$\mu=%.0f$\n$\sigma=%.0f$' % (abs(coeff[1]), abs(coeff[2]))
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.05, 0.9, textright, transform=ax.transAxes,
                    fontsize=8, verticalalignment='top', bbox=props)

        if electron_axis:
            self._add_electron_axis(fig, ax)

        if self.qualitative:
            ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
            ax.yaxis.set_major_formatter(plt.NullFormatter())
            ax.yaxis.set_minor_formatter(plt.NullFormatter())

        self._save_plots(fig, suffix=suffix, plot_queue=plot_queue)

    def plot_two_functions(self, x1, y1, x1_err, y1_err, x2, y2, label_1 = "data", label_2 = "fit", x_plot_range=None, y_plot_range = None, x_axis_title=None, y_axis_title=None, title=None, suffix=None, plot_queue=None):
        """
            Plot two functions (1 = data function, 2 = fit of data function)
        """
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        self._add_text(fig)

        ax.errorbar(x1, y1, y1_err, label = label_1, ls = 'None', marker = '.', ms = 4, alpha = 0.8, zorder=0)
        ax.plot(x2, y2, label = label_2, alpha=0.8, zorder=1)

        ax.set_ylim(0, 1.5*max(y1))

        if title:
            ax.set_title(title, color=TITLE_COLOR)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        ax.grid(True)
        ax.legend()

        self._save_plots(fig, suffix=suffix, plot_queue=plot_queue)


if __name__ == "__main__":
    pass

