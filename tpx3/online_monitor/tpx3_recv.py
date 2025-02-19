from __future__ import absolute_import
from online_monitor.receiver.receiver import Receiver
from zmq.utils import jsonapi
import numpy as np
import time
import copy

from matplotlib import cm

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from pyqtgraph.dockarea import DockArea, Dock


from online_monitor.utils import utils


def generateColorMapLut(cm_name):
    # https://github.com/pyqtgraph/pyqtgraph/issues/561
    colormap = copy.copy(cm.get_cmap(cm_name))
    colormap._init()
    lut = (colormap._lut[:-3] * 255).astype(np.uint8)
    return lut


class Tpx3(Receiver):

    def setup_receiver(self):
        # We want to change converter settings
        self.set_bidirectional_communication()

    def setup_widgets(self, parent, name):
        dock_area = DockArea()
        parent.addTab(dock_area, name)

        # Docks
        dock_occcupancy = Dock("Occupancy", size=(400, 400))
        dock_tot = Dock("Time over threshold values (TOT)", size=(200, 200))
        dock_hit_timing = Dock("Hit count histogram", size=(200, 200))
        dock_status = Dock("Status", size=(800, 40))

        dock_area.addDock(dock_occcupancy, 'top')

        dock_area.addDock(dock_tot, 'right', dock_occcupancy)
        dock_area.addDock(dock_hit_timing, 'bottom', dock_tot)

        dock_area.addDock(dock_status, 'top')

        # Status dock on top
        cw = QtWidgets.QWidget()
        cw.setStyleSheet("QWidget {background-color:white}")
        layout = QtWidgets.QGridLayout()
        cw.setLayout(layout)
        self.rate_label = QtWidgets.QLabel("Readout Rate\n0 Hz")
        self.hit_rate_label = QtWidgets.QLabel("Hit Rate\n0 Hz")
        self.event_rate_label = QtWidgets.QLabel("Event Rate\n0 Hz")
        self.timestamp_label = QtWidgets.QLabel("Data Timestamp\n")
        self.plot_delay_label = QtWidgets.QLabel("Plot Delay\n")
        self.scan_parameter_label = QtWidgets.QLabel("Parameter ID\n")
        self.spin_box = QtWidgets.QSpinBox(value=0)
        self.spin_box.setMaximum(1000000)
        self.spin_box.setSuffix(" Readouts")
        self.reset_button = QtWidgets.QPushButton('Reset')
        layout.addWidget(self.timestamp_label, 0, 0, 0, 1)
        layout.addWidget(self.plot_delay_label, 0, 1, 0, 1)
        layout.addWidget(self.rate_label, 0, 2, 0, 1)
        layout.addWidget(self.hit_rate_label, 0, 3, 0, 1)
        layout.addWidget(self.event_rate_label, 0, 4, 0, 1)
        layout.addWidget(self.scan_parameter_label, 0, 5, 0, 1)
        layout.addWidget(self.spin_box, 0, 6, 0, 1)
        layout.addWidget(self.reset_button, 0, 7, 0, 1)
        dock_status.addWidget(cw)

        # Connect widgets
        self.reset_button.clicked.connect(lambda: self.send_command('RESET'))
        self.spin_box.valueChanged.connect(lambda value: self.send_command(str(value)))

        # Different plot docks
        occupancy_graphics = pg.GraphicsLayoutWidget()
        occupancy_graphics.show()
        view = occupancy_graphics.addViewBox()
        self.occupancy_img = pg.ImageItem(border='w')
        # Set colormap from matplotlib
        lut = generateColorMapLut("viridis")

        self.occupancy_img.setLookupTable(lut, update=True)
        # view.addItem(self.occupancy_img)
        plot = pg.PlotWidget(viewBox=view, labels={'bottom': 'Column', 'left': 'Row'})
        plot.addItem(self.occupancy_img)

        dock_occcupancy.addWidget(plot)

        tot_plot_widget = pg.PlotWidget(background="w")
        self.tot_plot = tot_plot_widget.plot(np.linspace(-0.5, 15.5, 17),
                                             np.zeros((16)), stepMode=True)
        tot_plot_widget.showGrid(y=True)
        dock_tot.addWidget(tot_plot_widget)

        hit_timing_widget = pg.PlotWidget()
        self.hist_hit_count = hit_timing_widget.plot(np.linspace(-0.5, 1000.5, 1001),
                                                      np.zeros((1000)), stepMode=True)
        hit_timing_widget.showGrid(y=True)
        dock_hit_timing.addWidget(hit_timing_widget)

        self.plot_delay = 0

    def deserialize_data(self, data):
        datar, meta = utils.simple_dec(data)
        if 'occupancies' in meta:
            meta['occupancies'] = datar
        return meta

    def _update_rate(self, fps, hps, recent_total_hits, eps, recent_total_events):
            self.rate_label.setText("Readout Rate\n%d Hz" % fps)
            if self.spin_box.value() == 0:  # show number of hits, all hits are integrated
                self.hit_rate_label.setText("Total Hits\n%d" % int(recent_total_hits))
            else:
                self.hit_rate_label.setText("Hit Rate\n%d Hz" % int(hps))
            if self.spin_box.value() == 0:  # show number of events
                self.event_rate_label.setText("Total Events\n%d" % int(recent_total_events))
            else:
                self.event_rate_label.setText("Event Rate\n%d Hz" % int(eps))

    def handle_data(self, data):
        if 'meta_data' not in data:  # Histograms
            self.occupancy_img.setImage(image = data['occupancy'][:, :],
                                        autoDownsample = True)
            self.tot_plot.setData(x=np.linspace(-0.5, 1024.5, 1025),
                                  y=data['tot_hist'], fillLevel=0,
                                  brush=(0, 0, 255, 150))
            self.hist_hit_count.setData(x=np.linspace(-0.5, 1000.5, 101),
                                         y=data['hist_hit_count'][:100],
                                         stepMode=True,
                                         fillLevel=0, brush=(0, 0, 255, 150))
        else:  # Meta data
            self._update_rate(data['meta_data']['fps'],
                              data['meta_data']['hps'],
                              data['meta_data']['total_hits'],
                              data['meta_data']['eps'],
                              data['meta_data']['total_events'])
            self.timestamp_label.setText("Data Timestamp\n%s" % time.asctime(time.localtime(data['meta_data']['timestamp_stop'])))
            self.scan_parameter_label.setText("Parameter ID\n%d" % data['meta_data']['scan_par_id'])
            now = time.time()
            self.plot_delay = self.plot_delay * 0.9 + (now - data['meta_data']['timestamp_stop']) * 0.1
            self.plot_delay_label.setText("Plot Delay\n%s" % 'not realtime' if abs(self.plot_delay) > 5 else "Plot Delay\n%1.2f ms" % (self.plot_delay * 1.e3))

