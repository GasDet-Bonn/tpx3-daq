from online_monitor.receiver.receiver import Receiver
from zmq.utils import jsonapi
import numpy as np
import time

from matplotlib import cm

from PyQt5 import Qt
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.ptime as ptime
from pyqtgraph.dockarea import DockArea, Dock


from online_monitor.utils import utils


def generatePgColormap(cm_name):
    # https://github.com/pyqtgraph/pyqtgraph/issues/561
    pltMap = cm.get_cmap(cm_name)
    colors = pltMap.colors
    colors = [c + [1.] for c in colors]
    positions = np.linspace(0, 1, len(colors))
    pgMap = pg.ColorMap(positions, colors)
    return pgMap


class Tpx3(Receiver):

    def setup_receiver(self):
        # We want to change converter settings
        self.set_bidirectional_communication()

    def setup_top_dock(self):
        self.dock_status = Dock("Status", size=(800, 40))

        # Status dock on top
        cw = QtGui.QWidget()
        cw.setStyleSheet("QWidget {background-color:white}")
        layout = QtGui.QGridLayout()
        cw.setLayout(layout)
        self.rate_label = QtGui.QLabel("Readout Rate\n0 Hz")
        self.hit_rate_label = QtGui.QLabel("Hit Rate\n0 Hz")
        self.event_rate_label = QtGui.QLabel("Event Rate\n0 Hz")
        self.timestamp_label = QtGui.QLabel("Data Timestamp\n")
        self.plot_delay_label = QtGui.QLabel("Plot Delay\n")
        self.scan_parameter_label = QtGui.QLabel("Parameter ID\n")
        self.spin_box = Qt.QSpinBox(value=0)
        self.spin_box.setMaximum(1000000)
        self.spin_box.setSuffix(" Readouts")
        self.reset_button = QtGui.QPushButton('Reset')
        layout.addWidget(self.timestamp_label, 0, 0, 0, 1)
        layout.addWidget(self.plot_delay_label, 0, 1, 0, 1)
        layout.addWidget(self.rate_label, 0, 2, 0, 1)
        layout.addWidget(self.hit_rate_label, 0, 3, 0, 1)
        layout.addWidget(self.event_rate_label, 0, 4, 0, 1)
        layout.addWidget(self.scan_parameter_label, 0, 5, 0, 1)
        layout.addWidget(self.spin_box, 0, 6, 0, 1)
        layout.addWidget(self.reset_button, 0, 7, 0, 1)
        self.dock_status.addWidget(cw)

        # Connect widgets
        self.reset_button.clicked.connect(lambda: self.send_command('RESET'))
        self.spin_box.valueChanged.connect(lambda value: self.send_command(str(value)))

    def setup_plots(self, parent, name):
        dock_area = DockArea()
        parent.addTab(dock_area, name)

        # Docks
        dock_occupancy = Dock("Occupancy", size=(400, 400))
        dock_tot = Dock("Time over threshold values (TOT)", size=(200, 200))
        dock_hit_timing = Dock("Hit count histogram", size=(200, 200))

        dock_area.addDock(dock_occupancy, 'top')

        dock_area.addDock(dock_tot, 'right', dock_occupancy)
        dock_area.addDock(dock_hit_timing, 'bottom', dock_tot)

        dock_area.addDock(self.dock_status, 'top')

        # Different plot docks
        occupancy_graphics = pg.GraphicsLayoutWidget()
        occupancy_graphics.show()
        view = occupancy_graphics.addViewBox()
        view.invertY(True)
        self.occupancy_img = pg.ImageItem(border='w')
        # Set colormap from matplotlib
        lut = generatePgColormap("viridis").getLookupTable(0.0, 1.0, 256)

        self.occupancy_img.setLookupTable(lut, update=True)
        # view.addItem(self.occupancy_img)
        plot = pg.PlotWidget(viewBox=view, labels={'bottom': 'Column', 'left': 'Row'})
        plot.addItem(self.occupancy_img)

        dock_occupancy.addWidget(plot)

        tot_plot_widget = pg.PlotWidget(background="w")
        self.tot_plot = tot_plot_widget.plot(np.linspace(-0.5, 15.5, 17),
                                             np.zeros((16)), stepMode=True)
        tot_plot_widget.showGrid(y=True)
        dock_tot.addWidget(tot_plot_widget)

        hit_timing_widget = pg.PlotWidget()
        self.hist_hit_count = hit_timing_widget.plot(np.linspace(-0.5, 100.5, 101),
                                                      np.zeros((100)), stepMode=True)
        hit_timing_widget.showGrid(y=True)
        dock_hit_timing.addWidget(hit_timing_widget)

        self.plot_delay = 0

        # add tabbed 3D plot
        dock_3d = self.setup_3d_plot()
        dock_area.addDock(dock_3d, 'above', dock_occupancy)

    def setup_3d_plot(self):
        # Docks
        dock_3d = Dock("3D events", size=(400, 400))

        # Different plot docks
        graphics_3d = gl.GLViewWidget()
        graphics_3d.show()
        graphics_3d.setCameraPosition(distance=200)
        #view = graphics_3d.addViewBox()
        #view.invertY(True)
        self.img_3d = pg.ImageItem(border='w')
        # Set colormap from matplotlib
        lut = generatePgColormap("viridis").getLookupTable(0.0, 1.0, 256)

        self.img_3d.setLookupTable(lut, update=True)
        # view.addItem(self.occupancy_img)

        dock_3d.addWidget(graphics_3d)

        ## create three grids, add each to the view
        xgrid = gl.GLGridItem(antialias = True)
        xgrid.setSize(x=256.0, y=256.0, z=256.0)
        ygrid = gl.GLGridItem(antialias = True)
        ygrid.setSize(x=256.0, y=256.0, z=256.0)
        zgrid = gl.GLGridItem(antialias = True)
        zgrid.setSize(x=256.0, y=256.0, z=256.0)
        graphics_3d.addItem(xgrid)
        graphics_3d.addItem(ygrid)
        graphics_3d.addItem(zgrid)

        # TODO: make axis look reasonable
        axis_3d = gl.GLAxisItem()
        axis_3d.setSize(x = 256.0, y = 256.0, z = 256.0)
        graphics_3d.addItem(axis_3d)

        # rotate x and y grids to face the correct direction
        xgrid.rotate(90, 0, 1, 0)
        ygrid.rotate(90, 1, 0, 0)

        # translate each axis to the correct position
        # TODO: fix Z axis for good choice of TOA values!
        xgrid.translate(0.0, 128.0, 128.0)
        ygrid.translate(128.0, 0.0, 128.0)
        zgrid.translate(128.0, 128.0, 0.0)

        self.plot_3d = gl.GLScatterPlotItem(pos = np.zeros((0, 3),
                                                           dtype=np.uint32),
                                            color = (0.5, 1.0, 0.0, 1.0))
        graphics_3d.addItem(self.plot_3d)

        return dock_3d

    def setup_widgets(self, parent, name):
        self.setup_top_dock()

        self.setup_plots(parent, name)

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
            self.occupancy_img.setImage(data['occupancy'][:, :],
                                        autoDownsample=True)
            self.tot_plot.setData(x=np.linspace(-0.5, 15.5, 17),
                                  y=data['tot_hist'], fillLevel=0,
                                  brush=(0, 0, 255, 150))
            self.hist_hit_count.setData(x=np.linspace(-0.5, 100.5, 101),
                                         y=data['hist_hit_count'][:100],
                                         stepMode=True,
                                         fillLevel=0, brush=(0, 0, 255, 150))
        else:  # Meta data
            self._update_rate(data['meta_data']['fps'],
                              data['meta_data']['hps'],
                              data['meta_data']['total_hits'],
                              data['meta_data']['eps'],
                              data['meta_data']['total_events'])
            self.timestamp_label.setText(
                "Data Timestamp\n%s" % time.asctime(
                    time.localtime(data['meta_data']['timestamp_stop'])
                )
            )
            self.scan_parameter_label.setText(
                "Parameter ID\n%d" % data['meta_data']['scan_par_id']
            )
            now = ptime.time()
            self.plot_delay = self.plot_delay * 0.9 + (
                now - data['meta_data']['timestamp_stop']
            ) * 0.1
            self.plot_delay_label.setText(
                "Plot Delay\n%s" % 'not realtime' if abs(self.plot_delay) > 5
                else "Plot Delay\n%1.2f ms" % (self.plot_delay * 1.e3)
            )
