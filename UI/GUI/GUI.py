import gi
gi.require_version('Gtk', '3.0')
import os
import time
import cairo
from shutil import copy
from datetime import datetime, timedelta
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, GLib
import matplotlib.cm as cm
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import (FigureCanvasGTK3Agg as FigureCanvas)
import numpy as np
from multiprocessing import Process, Queue, Pipe

from UI.GUI.PlotWidget import plotwidget
from UI.tpx3_logger import file_logger, TPX3_datalogger, mask_logger
from UI.CLI.tpx3_cli import TPX3_multiprocess_start
import tpx3.utils as utils
from UI.GUI.converter import utils as conv_utils
from UI.GUI.converter.converter_manager import ConverterManager
from UI.GUI.sim_producer.producer_sim_manager import ProducerSimManager


class GUI_Plot1(Gtk.Window):
    def __init__(self, data_queue, startet_from = 'GUI', plottype = None, integration_length = None, color_depth = None, colorsteps = None):
        self.active = 'False'
        Gtk.Window.__init__(self, title = 'Plot')
        self.connect('delete-event', self.window_destroy)

        self.set_default_size(400, 400)
        self.started_from = startet_from 
        self.Tag = None

        self.box = Gtk.Box(spacing = 6, orientation = Gtk.Orientation.HORIZONTAL)
        self.add(self.box)

        self.plotwidget = plotwidget(data_queue = data_queue)
        self.plotbox = Gtk.EventBox()
        self.plotbox.add(self.plotwidget.canvas)
        self.plotbox.connect('button_press_event', self.plot_right_clicked)
        self.box.pack_start(self.plotbox, True, True, 0)


        self.box.grid = Gtk.Grid()
        self.box.add(self.box.grid)
        self.box.grid.set_row_spacing(10)
        self.box.grid.set_column_spacing(10)

        self.Stopbutton = Gtk.Button(label = 'Occ_Plot')
        self.Stopbutton.connect('clicked', self.on_Stopbutton_clicked)
        self.Slowbutton = Gtk.Button(label = 'Slow')
        self.Slowbutton.connect('clicked', self.on_Slowbutton_clicked)
        self.Fastbutton = Gtk.Button(label = 'Fast Plot')
        self.Fastbutton.connect('clicked', self.on_Fastbutton_clicked)
        self.box.grid.attach(self.Stopbutton, 0, 0, 1, 1)
        self.box.grid.attach(self.Slowbutton, 0, 1, 1, 1)
        self.box.grid.attach(self.Fastbutton, 0, 2, 1, 1)

        if self.started_from == 'GUI':
            self.plotwidget.set_plottype(TPX3_datalogger.read_value('plottype'))
            self.plotwidget.set_occupancy_length(TPX3_datalogger.read_value('integration_length'))
            self.plotwidget.set_color_depth(TPX3_datalogger.read_value('color_depth'))
            self.plotwidget.set_color_steps(TPX3_datalogger.read_value('colorsteps'))

            if TPX3_datalogger.read_value('plottype') == 'normal':
                self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(TPX3_datalogger.read_value('colorsteps')))
                self.Tag = GLib.idle_add(self.plotwidget.update_plot)
            elif TPX3_datalogger.read_value('plottype') == 'occupancy':
                self.plotwidget.change_colormap(colormap = cm.viridis, vmax = TPX3_datalogger.read_value('color_depth'))
                self.plotwidget.reset_occupancy()
                self.Tag = GLib.idle_add(self.plotwidget.update_occupancy_plot)

        if self.started_from == 'CLI':
            self.plotwidget.set_plottype(plottype)
            self.plotwidget.set_occupancy_length(integration_length)
            self.plotwidget.set_color_depth(color_depth)
            self.plotwidget.set_color_steps(colorsteps)

            if plottype == 'normal':
                self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(colorsteps))
                self.Tag = GLib.idle_add(self.plotwidget.update_plot)
            elif plottype == 'occupancy':
                self.plotwidget.change_colormap(colormap = cm.viridis, vmax = color_depth)
                self.plotwidget.reset_occupancy()
                self.Tag = GLib.idle_add(self.plotwidget.update_occupancy_plot)

        self.show_all()

    def on_Stopbutton_clicked(self, widget):
        GLib.source_remove(self.Tag)
        self.plotwidget.set_plottype('occupancy')
        self.plotwidget.change_colormap(colormap = cm.viridis, vmax = self.plotwidget.get_iteration_depth('occupancy.color'))
        self.plotwidget.reset_occupancy()
        self.Tag = GLib.idle_add(self.plotwidget.update_occupancy_plot)

    def on_Slowbutton_clicked(self, widget):
        GLib.source_remove(self.Tag)
        self.plotwidget.set_plottype('normal')
        self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(self.plotwidget.get_iteration_depth('normal')))
        self.Tag = GLib.timeout_add(500, self.plotwidget.update_plot)

    def on_Fastbutton_clicked(self, widget):
        GLib.source_remove(self.Tag)
        self.plotwidget.set_plottype('normal')
        self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(self.plotwidget.get_iteration_depth('normal')))
        self.Tag = GLib.idle_add(self.plotwidget.update_plot)

    def plot_right_clicked(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            subw = GUI_Plot_settings(self.plotwidget)

    def stop_idle_job(self):
        GLib.source_remove(self.Tag)

    def window_destroy(self, event, widget):
        if self.started_from == 'GUI':
            TPX3_datalogger.write_value(name = 'plottype', value = self.plotwidget.get_plottype())
            TPX3_datalogger.write_value(name = 'colorsteps', value = self.plotwidget.get_iteration_depth('normal'))
            TPX3_datalogger.write_value(name = 'integration_length', value = self.plotwidget.get_iteration_depth('occupancy'))
            TPX3_datalogger.write_value(name = 'color_depth', value = self.plotwidget.get_iteration_depth('occupancy.color'))
        if self.started_from == 'CLI':
            print('plottype=' + str(self.plotwidget.get_plottype()) + 
                    ' colorsteps=' + str(self.plotwidget.get_iteration_depth('normal')) + 
                    ' integration_length=' + str(self.plotwidget.get_iteration_depth('occupancy')) + 
                    ' color_depth=' + str(self.plotwidget.get_iteration_depth('occupancy.color')))
        GLib.source_remove(self.Tag)
        if self.started_from == 'GUI':
            GUI.closed_plot1()
        self.destroy()

class GUI_Plot_settings(Gtk.Window):
    def __init__(self,plotwidget):
        Gtk.Window.__init__(self, title = 'Plot Settings')
        self.connect('delete-event', self.window_destroy)

        color_depth = 1

        self.plotwidget = plotwidget

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        self.add(grid)

        if self.plotwidget.get_plottype() == 'normal':
            nIteration = self.plotwidget.get_iteration_depth('normal')

        elif self.plotwidget.get_plottype() == 'occupancy':
            nIteration = self.plotwidget.get_iteration_depth('occupancy')
            color_depth = self.plotwidget.get_iteration_depth('occupancy.color')

        self.OKbutton = Gtk.Button(label = 'OK')
        self.OKbutton.connect('clicked', self.on_OKbutton_clicked)

        #Plot depth
        plot_depth_label = Gtk.Label()
        plot_depth_label.set_text('Plot Depth')
        self.plot_depth_value = nIteration
        plot_depth_adj = Gtk.Adjustment()
        plot_depth_adj.configure(nIteration, 0, 1000, 1, 0, 0)
        self.plot_depth = Gtk.SpinButton(adjustment = plot_depth_adj, climb_rate = 1, digits = 0)
        self.plot_depth.set_value(self.plot_depth_value) 
        self.plot_depth.connect('value-changed', self.plot_depth_set)

        #color depth
        color_depth_label = Gtk.Label()
        color_depth_label.set_text('Color Depth')
        self.color_depth_value = color_depth
        color_depth_adj = Gtk.Adjustment()
        color_depth_adj.configure(color_depth, 0, 255, 1, 0, 0)
        self.color_depth = Gtk.SpinButton(adjustment = color_depth_adj, climb_rate = 1, digits = 0)
        self.color_depth.set_value(self.color_depth_value) 
        self.color_depth.connect('value-changed', self.color_depth_set)

        grid.attach(plot_depth_label, 0, 0, 3, 1)
        grid.attach(self.plot_depth, 0, 1, 3, 1)
        grid.attach(color_depth_label, 0, 2, 3, 1)
        grid.attach(self.color_depth, 0, 3, 3, 1)
        grid.attach(self.OKbutton, 3, 4, 1, 1)

        self.show_all()

        if self.plotwidget.get_plottype() == 'normal':
            color_depth_label.hide()
            self.color_depth.hide()

    def plot_depth_set(self, event):
        self.plot_depth_value = self.plot_depth.get_value_as_int()

    def color_depth_set(self, event):
        self.color_depth_value = self.color_depth.get_value_as_int()

    def on_OKbutton_clicked(self, widget):
        self.plot_depth_value = self.plot_depth.get_value_as_int()
        self.color_depth_value = self.color_depth.get_value_as_int()
        if self.plotwidget.get_plottype() == 'normal':
            self.plotwidget.change_colormap(colormap = self.plotwidget.fading_colormap(self.plot_depth_value))
            self.destroy()

        elif self.plotwidget.get_plottype() == 'occupancy':
            self.plotwidget.change_colormap(colormap = cm.viridis, vmax = self.color_depth_value)
            self.plotwidget.set_occupancy_length(self.plot_depth_value)
            self.plotwidget.reset_occupancy()
            self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_ToT_Calib(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'ToT Calibration')
        self.connect('delete-event', self.window_destroy)

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text('')

        #other process running
        self.other_process = Gtk.Label()
        self.other_process.set_text('')

        #Testpuls range label
        Testpulse_range_label = Gtk.Label()
        Testpulse_range_label.set_text('Testpulse range')

        #default values
        self.Testpulse_range_start_value = 200
        self.Testpulse_range_stop_value = 500

        #Testpulse_range_start
        Testpulse_range_start_adj = Gtk.Adjustment()
        Testpulse_range_start_adj.configure(200, 0, self.Testpulse_range_stop_value, 1, 0, 0)
        self.Testpulse_range_start = Gtk.SpinButton(adjustment = Testpulse_range_start_adj, climb_rate = 1, digits = 0)
        self.Testpulse_range_start.set_value(self.Testpulse_range_start_value) 
        self.Testpulse_range_start.connect('value-changed', self.Testpulse_range_start_set)
        Testpulse_range_start_label = Gtk.Label()
        Testpulse_range_start_label.set_text('Start ')

        #Testpulse_range_stop
        Testpulse_range_stop_adj = Gtk.Adjustment()
        Testpulse_range_stop_adj.configure(500, self.Testpulse_range_start_value, 511, 1, 0, 0)
        self.Testpulse_range_stop = Gtk.SpinButton(adjustment = Testpulse_range_stop_adj, climb_rate = 1, digits = 0)
        self.Testpulse_range_stop.set_value(self.Testpulse_range_stop_value) 
        self.Testpulse_range_stop.connect('value-changed', self.Testpulse_range_stop_set)
        Testpulse_range_stop_label = Gtk.Label()
        Testpulse_range_stop_label.set_text('Stop ')

        #Buttons for number of iteration
        self.Number_of_Iterations = 64
        Iterationbutton1 = Gtk.RadioButton.new_with_label_from_widget(None, '4')
        Iterationbutton2 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '16')
        Iterationbutton3 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '64')
        Iterationbutton4 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '256')
        Iterationbutton3.set_active(True)
        Iterationbutton1.connect('toggled', self.on_Iterationbutton_toggled, '4')
        Iterationbutton2.connect('toggled', self.on_Iterationbutton_toggled, '16')
        Iterationbutton3.connect('toggled', self.on_Iterationbutton_toggled, '64')
        Iterationbutton4.connect('toggled', self.on_Iterationbutton_toggled, '256')
        Number_of_iteration_label = Gtk.Label()
        Number_of_iteration_label.set_text('Number of iterations')

        #Startbutton
        self.Startbutton = Gtk.Button(label = 'Start')
        self.Startbutton.connect('clicked', self.on_Startbutton_clicked)


        grid.attach(Testpulse_range_label, 0, 0, 6, 1)
        grid.attach(Testpulse_range_start_label, 0, 1, 1, 1)
        grid.attach(self.Testpulse_range_start, 1, 1, 2, 1)
        grid.attach(Testpulse_range_stop_label, 3, 1, 1, 1)
        grid.attach(self.Testpulse_range_stop, 4, 1, 2, 1)
        grid.attach(Number_of_iteration_label, 1, 2, 4, 1)
        grid.attach(Iterationbutton1, 1, 3, 1, 1)
        grid.attach(Iterationbutton2, 2, 3, 1, 1)
        grid.attach(Iterationbutton3, 3, 3, 1, 1)
        grid.attach(Iterationbutton4, 4, 3, 1, 1)
        grid.attach(Space, 0, 4, 1, 1)
        grid.attach(self.other_process, 0, 5, 4, 1)
        grid.attach(self.Startbutton, 4, 5, 2, 1)

        self.show_all()

    def Testpulse_range_start_set(self, event):
        self.Testpulse_range_start_value = self.Testpulse_range_start.get_value_as_int()
        temp_Testpulse_range_stop_value = self.Testpulse_range_stop.get_value_as_int()
        new_adjustment_start = Gtk.Adjustment()
        new_adjustment_start.configure(200, self.Testpulse_range_start_value, 511, 1, 0, 0)
        self.Testpulse_range_stop.disconnect_by_func(self.Testpulse_range_stop_set)
        self.Testpulse_range_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Testpulse_range_stop.set_value(temp_Testpulse_range_stop_value)
        self.Testpulse_range_stop.connect('value-changed', self.Testpulse_range_stop_set)

    def Testpulse_range_stop_set(self, event):
        self.Testpulse_range_stop_value = self.Testpulse_range_stop.get_value_as_int()
        temp_Testpulse_range_start_value = self.Testpulse_range_start.get_value_as_int()
        new_adjustment_stop = Gtk.Adjustment()
        new_adjustment_stop.configure(200, 0, self.Testpulse_range_stop_value, 1, 0, 0)
        self.Testpulse_range_start.disconnect_by_func(self.Testpulse_range_start_set)
        self.Testpulse_range_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Testpulse_range_start.set_value(temp_Testpulse_range_start_value)
        self.Testpulse_range_start.connect('value-changed', self.Testpulse_range_start_set)

    def on_Iterationbutton_toggled(self, button, name):
        self.Number_of_Iterations = int(name)

    def on_Startbutton_clicked(self, widget):
        if GUI.get_process_alive():
            self.other_process.set_text('Other process running')
            return
        elif GUI.get_simulation_alive():
            self.other_process.set_text('Simulation running')
            return

        GUI.Status_window_call(function = 'ToT_Calib', 
                                lowerTHL = self.Testpulse_range_start_value, 
                                upperTHL = self.Testpulse_range_stop_value, 
                                iterations = self.Number_of_Iterations)
        new_process = TPX3_multiprocess_start.process_call(function = 'ToTCalib', 
                                                            VTP_fine_start = self.Testpulse_range_start_value, 
                                                            VTP_fine_stop = self.Testpulse_range_stop_value, 
                                                            mask_step = self.Number_of_Iterations, 
                                                            tp_period = TPX3_datalogger.read_value(name = 'TP_Period'), 
                                                            thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                            maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                            progress = GUI.get_progress_value_queue(), 
                                                            status = GUI.get_status_queue(), 
                                                            plot_queue = GUI.plot_queue)
        GUI.set_running_process(running_process = new_process)
        GUI.set_quit_scan_label()

        self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Threshold_Scan(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Threshold Scan')
        self.connect('delete-event', self.window_destroy)


        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text("")

        Threshold_label = Gtk.Label()
        Threshold_label.set_text('Threshold')

        #other process running
        self.other_process = Gtk.Label()
        self.other_process.set_text('')

        #Threshold_start
        self.Threshold_start_value = 1400
        Threshold_start_adj = Gtk.Adjustment()
        Threshold_start_adj.configure(1400, 0, 2911, 1, 0, 0)
        self.Threshold_start = Gtk.SpinButton(adjustment = Threshold_start_adj, climb_rate = 1, digits = 0)
        self.Threshold_start.set_value(self.Threshold_start_value) 
        self.Threshold_start.connect('value-changed', self.Threshold_start_set)
        Threshold_start_label = Gtk.Label()
        Threshold_start_label.set_text('Start ')

        #Threshold_stop
        self.Threshold_stop_value = 2900
        Threshold_stop_adj = Gtk.Adjustment()
        Threshold_stop_adj.configure(2900, 0, 2911, 1, 0, 0)
        self.Threshold_stop = Gtk.SpinButton(adjustment = Threshold_stop_adj, climb_rate = 1, digits = 0)
        self.Threshold_stop.set_value(self.Threshold_stop_value) 
        self.Threshold_stop.connect('value-changed', self.Threshold_stop_set)
        Threshold_stop_label = Gtk.Label()
        Threshold_stop_label.set_text('Stop ')

        #n_injections
        self.n_injections_value = 100
        n_injections_adj = Gtk.Adjustment()
        n_injections_adj.configure(100, 1, 65535, 1, 0, 0)
        self.n_injections = Gtk.SpinButton(adjustment = n_injections_adj, climb_rate = 1, digits = 0)
        self.n_injections.set_value(self.n_injections_value) 
        self.n_injections.connect('value-changed', self.n_injections_set)
        n_injections_label = Gtk.Label()
        n_injections_label.set_text('Number of injections ')

        #Buttons for number of iteration
        Iterationbutton1 = Gtk.RadioButton.new_with_label_from_widget(None, '4')
        Iterationbutton2 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '16')
        Iterationbutton3 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '64')
        Iterationbutton4 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '256')
        Iterationbutton2.set_active(True)
        Iterationbutton1.connect('toggled', self.on_Iterationbutton_toggled, '4')
        Iterationbutton2.connect('toggled', self.on_Iterationbutton_toggled, '16')
        Iterationbutton3.connect('toggled', self.on_Iterationbutton_toggled, '64')
        Iterationbutton4.connect('toggled', self.on_Iterationbutton_toggled, '256')

        Number_of_iteration_label = Gtk.Label()
        Number_of_iteration_label.set_text('Number of iterations')
        self.Number_of_Iterations = 16

        #Startbutton
        self.Startbutton = Gtk.Button(label = 'Start')
        self.Startbutton.connect('clicked', self.on_Startbutton_clicked)

        grid.attach(Threshold_label, 0, 0, 6, 1)
        grid.attach(Threshold_start_label, 0, 1, 1, 1)
        grid.attach(self.Threshold_start, 1, 1, 2, 1)
        grid.attach(Threshold_stop_label, 3, 1, 1, 1)
        grid.attach(self.Threshold_stop, 4, 1, 2, 1)
        grid.attach(n_injections_label, 2, 2, 2, 1)
        grid.attach(self.n_injections, 2, 3, 2, 1)
        grid.attach(Number_of_iteration_label, 1, 4, 4, 1)
        grid.attach(Iterationbutton1, 1, 5, 1, 1)
        grid.attach(Iterationbutton2, 2, 5, 1, 1)
        grid.attach(Iterationbutton3, 3, 5, 1, 1)
        grid.attach(Iterationbutton4, 4, 5, 1, 1)
        grid.attach(Space, 0, 6, 1, 1)
        grid.attach(self.other_process, 0, 7, 4, 1)
        grid.attach(self.Startbutton, 4, 7, 2, 1)

        self.show_all()

    def Threshold_start_set(self, event):
        self.Threshold_start_value = self.Threshold_start.get_value_as_int()
        temp_Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        new_adjustment_start = Gtk.Adjustment()
        new_adjustment_start.configure(200, self.Threshold_start_value,2911, 1, 0, 0)
        self.Threshold_stop.disconnect_by_func(self.Threshold_stop_set)
        self.Threshold_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Threshold_stop.set_value(temp_Threshold_stop_value)
        self.Threshold_stop.connect('value-changed', self.Threshold_stop_set)

    def Threshold_stop_set(self, event):
        self.Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        temp_Threshold_start_value = self.Threshold_start.get_value_as_int()
        new_adjustment_stop = Gtk.Adjustment()
        new_adjustment_stop.configure(200, 0, self.Threshold_stop_value, 1, 0, 0)
        self.Threshold_start.disconnect_by_func(self.Threshold_start_set)
        self.Threshold_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Threshold_start.set_value(temp_Threshold_start_value)
        self.Threshold_start.connect('value-changed', self.Threshold_start_set)

    def n_injections_set(self, event):
        self.n_injections_value = self.n_injections.get_value_as_int()

    def on_Iterationbutton_toggled(self, button, name):
        self.Number_of_Iterations = int(name)

    def on_Startbutton_clicked(self, widget):
        if GUI.get_process_alive():
            self.other_process.set_text('Other process running')
            return
        elif GUI.get_simulation_alive():
            self.other_process.set_text('Simulation running')
            return
        GUI.Status_window_call(function = 'ThresholdScan', 
                                lowerTHL = self.Threshold_start_value, 
                                upperTHL = self.Threshold_stop_value, 
                                iterations = self.Number_of_Iterations, 
                                n_injections = self.n_injections_value)
        new_process = TPX3_multiprocess_start.process_call(function = 'ThresholdScan', 
                                                            Vthreshold_start = self.Threshold_start_value, 
                                                            Vthreshold_stop = self.Threshold_stop_value, 
                                                            n_injections = self.n_injections_value, 
                                                            mask_step = self.Number_of_Iterations, 
                                                            tp_period = TPX3_datalogger.read_value(name = 'TP_Period'), 
                                                            thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                            maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                            progress = GUI.get_progress_value_queue(), 
                                                            status = GUI.get_status_queue(), 
                                                            plot_queue = GUI.plot_queue)
        GUI.set_running_process(running_process = new_process)
        GUI.set_quit_scan_label()

        self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Threshold_Calib(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Threshold Calibration')
        self.connect('delete-event', self.window_destroy)

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text('')

        Threshold_label = Gtk.Label()
        Threshold_label.set_text('Threshold')

        #other process running
        self.other_process = Gtk.Label()
        self.other_process.set_text('')

        #Threshold_start
        self.Threshold_start_value = 1400
        Threshold_start_adj = Gtk.Adjustment()
        Threshold_start_adj.configure(1400, 0, 2911, 1, 0, 0)
        self.Threshold_start = Gtk.SpinButton(adjustment = Threshold_start_adj, climb_rate = 1, digits = 0)
        self.Threshold_start.set_value(self.Threshold_start_value) 
        self.Threshold_start.connect('value-changed', self.Threshold_start_set)
        Threshold_start_label = Gtk.Label()
        Threshold_start_label.set_text('Start ')

        #Threshold_stop
        self.Threshold_stop_value = 2900
        Threshold_stop_adj = Gtk.Adjustment()
        Threshold_stop_adj.configure(2900, 0, 2911, 1, 0, 0)
        self.Threshold_stop = Gtk.SpinButton(adjustment = Threshold_stop_adj, climb_rate = 1, digits = 0)
        self.Threshold_stop.set_value(self.Threshold_stop_value) 
        self.Threshold_stop.connect('value-changed', self.Threshold_stop_set)
        Threshold_stop_label = Gtk.Label()
        Threshold_stop_label.set_text('Stop ')

        #n_injections
        self.n_injections_value = 100
        n_injections_adj = Gtk.Adjustment()
        n_injections_adj.configure(100, 1, 65535, 1, 0, 0)
        self.n_injections = Gtk.SpinButton(adjustment = n_injections_adj, climb_rate = 1, digits = 0)
        self.n_injections.set_value(self.n_injections_value) 
        self.n_injections.connect('value-changed', self.n_injections_set)
        n_injections_label = Gtk.Label()
        n_injections_label.set_text('Number of injections ')

        #Buttons for number of iteration
        Iterationbutton1 = Gtk.RadioButton.new_with_label_from_widget(None, '4')
        Iterationbutton2 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '16')
        Iterationbutton3 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '64')
        Iterationbutton4 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '256')
        Iterationbutton2.set_active(True)
        Iterationbutton1.connect('toggled', self.on_Iterationbutton_toggled, '4')
        Iterationbutton2.connect('toggled', self.on_Iterationbutton_toggled, '16')
        Iterationbutton3.connect('toggled', self.on_Iterationbutton_toggled, '64')
        Iterationbutton4.connect('toggled', self.on_Iterationbutton_toggled, '256')

        Number_of_iteration_label = Gtk.Label()
        Number_of_iteration_label.set_text('Number of iterations')
        self.Number_of_Iterations = 16

        #n_pulse_heights
        self.n_pulse_heights_value = 4
        n_pulse_heights_adj = Gtk.Adjustment()
        n_pulse_heights_adj.configure(4, 2, 100, 1, 0, 0)
        self.n_pulse_heights = Gtk.SpinButton(adjustment = n_pulse_heights_adj, climb_rate = 1, digits = 0)
        self.n_pulse_heights.set_value(self.n_pulse_heights_value) 
        self.n_pulse_heights.connect('value-changed', self.n_pulse_heights_set)
        n_pulse_heights_label = Gtk.Label()
        n_pulse_heights_label.set_text('Pulse height steps ')

        #Startbutton
        self.Startbutton = Gtk.Button(label = 'Start')
        self.Startbutton.connect('clicked', self.on_Startbutton_clicked)

        grid.attach(Threshold_label, 0, 0, 6, 1)
        grid.attach(Threshold_start_label, 0, 1, 1, 1)
        grid.attach(self.Threshold_start, 1, 1, 2, 1)
        grid.attach(Threshold_stop_label, 3, 1, 1, 1)
        grid.attach(self.Threshold_stop, 4, 1, 2, 1)
        grid.attach(n_injections_label, 2, 2, 2, 1)
        grid.attach(self.n_injections, 2, 3, 2, 1)
        grid.attach(Number_of_iteration_label, 1, 4, 4, 1)
        grid.attach(Iterationbutton1, 1, 5, 1, 1)
        grid.attach(Iterationbutton2, 2, 5, 1, 1)
        grid.attach(Iterationbutton3, 3, 5, 1, 1)
        grid.attach(Iterationbutton4, 4, 5, 1, 1)
        grid.attach(n_pulse_heights_label, 2, 6, 2, 1)
        grid.attach(self.n_pulse_heights, 2, 7, 2, 1)
        grid.attach(Space, 0, 8, 1, 1)
        grid.attach(self.other_process, 0, 9, 4, 1)
        grid.attach(self.Startbutton, 4, 9, 2, 1)

        self.show_all()

    def Threshold_start_set(self, event):
        self.Threshold_start_value = self.Threshold_start.get_value_as_int()
        temp_Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        new_adjustment_start = Gtk.Adjustment()
        new_adjustment_start.configure(200, self.Threshold_start_value, 2911, 1, 0, 0)
        self.Threshold_stop.disconnect_by_func(self.Threshold_stop_set)
        self.Threshold_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Threshold_stop.set_value(temp_Threshold_stop_value)
        self.Threshold_stop.connect('value-changed', self.Threshold_stop_set)

    def Threshold_stop_set(self, event):
        self.Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        temp_Threshold_start_value = self.Threshold_start.get_value_as_int()
        new_adjustment_stop = Gtk.Adjustment()
        new_adjustment_stop.configure(200, 0, self.Threshold_stop_value, 1, 0, 0)
        self.Threshold_start.disconnect_by_func(self.Threshold_start_set)
        self.Threshold_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Threshold_start.set_value(temp_Threshold_start_value)
        self.Threshold_start.connect('value-changed', self.Threshold_start_set)

    def n_injections_set(self, event):
        self.n_injections_value = self.n_injections.get_value_as_int()

    def on_Iterationbutton_toggled(self, button, name):
        self.Number_of_Iterations = int(name)

    def n_pulse_heights_set(self, event):
        self.n_pulse_heights_value = self.n_pulse_heights.get_value_as_int()

    def on_Startbutton_clicked(self, widget):
        if GUI.get_process_alive():
            self.other_process.set_text('Other process running')
            return
        elif GUI.get_simulation_alive():
            self.other_process.set_text('Simulation running')
            return

        GUI.Status_window_call(function = 'ThresholdCalib', 
                                lowerTHL = self.Threshold_start_value, 
                                upperTHL = self.Threshold_stop_value, 
                                iterations = self.Number_of_Iterations, 
                                n_injections = self.n_injections_value, 
                                n_pulse_heights = self.n_pulse_heights_value)
        new_process = TPX3_multiprocess_start.process_call(function = 'ThresholdCalib', 
                                                            iteration = 0, 
                                                            Vthreshold_start = self.Threshold_start_value, 
                                                            Vthreshold_stop = self.Threshold_stop_value, 
                                                            n_injections = self.n_injections_value, 
                                                            mask_step = self.Number_of_Iterations, 
                                                            tp_period = TPX3_datalogger.read_value(name = 'TP_Period'), 
                                                            n_pulse_heights = self.n_pulse_heights_value, 
                                                            thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                            maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                            progress = GUI.get_progress_value_queue(), 
                                                            status = GUI.get_status_queue(), 
                                                            plot_queue = GUI.plot_queue)
        GUI.set_running_process(running_process = new_process)
        GUI.set_quit_scan_label()

        self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Testpulse_Scan(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Testpulse Scan')
        self.connect('delete-event', self.window_destroy)

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text('')

        Testpulse_range_label = Gtk.Label()
        Testpulse_range_label.set_text('Testpulse range')

        #other process running
        self.other_process = Gtk.Label()
        self.other_process.set_text('')

        #Testpulse_range_start
        self.Testpulse_range_start_value = 200
        Testpulse_range_start_adj = Gtk.Adjustment()
        Testpulse_range_start_adj.configure(200, 0, 511, 1, 0, 0)
        self.Testpulse_range_start = Gtk.SpinButton(adjustment = Testpulse_range_start_adj, climb_rate = 1, digits = 0)
        self.Testpulse_range_start.set_value(self.Testpulse_range_start_value) 
        self.Testpulse_range_start.connect('value-changed', self.Testpulse_range_start_set)
        Testpulse_range_start_label = Gtk.Label()
        Testpulse_range_start_label.set_text('Start ')

        #Testpulse_range_stop
        self.Testpulse_range_stop_value = 500
        Testpulse_range_stop_adj = Gtk.Adjustment()
        Testpulse_range_stop_adj.configure(500, 0, 511, 1, 0, 0)
        self.Testpulse_range_stop = Gtk.SpinButton(adjustment = Testpulse_range_stop_adj, climb_rate = 1, digits = 0)
        self.Testpulse_range_stop.set_value(self.Testpulse_range_stop_value) 
        self.Testpulse_range_stop.connect('value-changed', self.Testpulse_range_stop_set)
        Testpulse_range_stop_label = Gtk.Label()
        Testpulse_range_stop_label.set_text('Stop ')

        #n_injections
        self.n_injections_value = 100
        n_injections_adj = Gtk.Adjustment()
        n_injections_adj.configure(100, 1, 65535, 1, 0, 0)
        self.n_injections = Gtk.SpinButton(adjustment = n_injections_adj, climb_rate = 1, digits = 0)
        self.n_injections.set_value(self.n_injections_value) 
        self.n_injections.connect('value-changed', self.n_injections_set)
        n_injections_label = Gtk.Label()
        n_injections_label.set_text('Number of injections ')

        #Buttons for number of iteration
        Iterationbutton1 = Gtk.RadioButton.new_with_label_from_widget(None, '4')
        Iterationbutton2 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '16')
        Iterationbutton3 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '64')
        Iterationbutton4 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '256')
        Iterationbutton2.set_active(True)
        Iterationbutton1.connect('toggled', self.on_Iterationbutton_toggled, '4')
        Iterationbutton2.connect('toggled', self.on_Iterationbutton_toggled, '16')
        Iterationbutton3.connect('toggled', self.on_Iterationbutton_toggled, '64')
        Iterationbutton4.connect('toggled', self.on_Iterationbutton_toggled, '256')

        Number_of_iteration_label = Gtk.Label()
        Number_of_iteration_label.set_text('Number of iterations')
        self.Number_of_Iterations = 16

        #Startbutton
        self.Startbutton = Gtk.Button(label = 'Start')
        self.Startbutton.connect('clicked', self.on_Startbutton_clicked)

        grid.attach(Testpulse_range_label, 0, 0, 6, 1)
        grid.attach(Testpulse_range_start_label, 0, 1, 1, 1)
        grid.attach(self.Testpulse_range_start, 1, 1, 2, 1)
        grid.attach(Testpulse_range_stop_label, 3, 1, 1, 1)
        grid.attach(self.Testpulse_range_stop, 4, 1, 2, 1)
        grid.attach(n_injections_label, 2, 2, 2, 1)
        grid.attach(self.n_injections, 2, 3, 2, 1)
        grid.attach(Number_of_iteration_label, 1, 4, 4, 1)
        grid.attach(Iterationbutton1, 1, 5, 1, 1)
        grid.attach(Iterationbutton2, 2, 5, 1, 1)
        grid.attach(Iterationbutton3, 3, 5, 1, 1)
        grid.attach(Iterationbutton4, 4, 5, 1, 1)
        grid.attach(Space, 0, 6, 1, 1)
        grid.attach(self.other_process, 0, 7, 4, 1)
        grid.attach(self.Startbutton, 4, 7, 2, 1)

        self.show_all()

    def Testpulse_range_start_set(self, event):
        self.Testpulse_range_start_value = self.Testpulse_range_start.get_value_as_int()
        temp_Testpulse_range_stop_value = self.Testpulse_range_stop.get_value_as_int()
        new_adjustment_start = Gtk.Adjustment()
        new_adjustment_start.configure(200, self.Testpulse_range_start_value, 2911, 1, 0, 0)
        self.Testpulse_range_stop.disconnect_by_func(self.Testpulse_range_stop_set)
        self.Testpulse_range_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Testpulse_range_stop.set_value(temp_Testpulse_range_stop_value)
        self.Testpulse_range_stop.connect('value-changed', self.Testpulse_range_stop_set)

    def Testpulse_range_stop_set(self, event):
        self.Testpulse_range_stop_value = self.Testpulse_range_stop.get_value_as_int()
        temp_Testpulse_range_start_value = self.Testpulse_range_start.get_value_as_int()
        new_adjustment_stop = Gtk.Adjustment()
        new_adjustment_stop.configure(200, 0, self.Testpulse_range_stop_value, 1, 0, 0)
        self.Testpulse_range_start.disconnect_by_func(self.Testpulse_range_start_set)
        self.Testpulse_range_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Testpulse_range_start.set_value(temp_Testpulse_range_start_value)
        self.Testpulse_range_start.connect('value-changed', self.Testpulse_range_start_set)

    def n_injections_set(self, event):
        self.n_injections_value = self.n_injections.get_value_as_int()

    def on_Iterationbutton_toggled(self, button, name):
        self.Number_of_Iterations = int(name)

    def on_Startbutton_clicked(self, widget):
        if GUI.get_process_alive():
            self.other_process.set_text('Other process running')
            return
        elif GUI.get_simulation_alive():
            self.other_process.set_text('Simulation running')
            return
        GUI.Status_window_call(function = 'TestpulsScan', 
                                lowerTHL = self.Testpulse_range_start_value, 
                                upperTHL = self.Testpulse_range_stop_value, 
                                iterations = self.Number_of_Iterations, 
                                n_injections = self.n_injections_value)
        new_process = TPX3_multiprocess_start.process_call(function = 'TestpulseScan', 
                                                            VTP_fine_start = self.Testpulse_range_start_value, 
                                                            VTP_fine_stop = self.Testpulse_range_stop_value, 
                                                            n_injections = self.n_injections_value, 
                                                            mask_step = self.Number_of_Iterations, 
                                                            tp_period = TPX3_datalogger.read_value(name = 'TP_Period'), 
                                                            thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'),
                                                            maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                            progress = GUI.get_progress_value_queue(), 
                                                            status = GUI.get_status_queue(), 
                                                            plot_queue = GUI.plot_queue)
        GUI.set_running_process(running_process = new_process)
        GUI.set_quit_scan_label()

        self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_PixelDAC_opt(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'PixelDAC optimisation')
        self.connect('delete-event', self.window_destroy)

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text("")

        Threshold_label = Gtk.Label()
        Threshold_label.set_text('Threshold')

        #other process running
        self.other_process = Gtk.Label()
        self.other_process.set_text('')

        #Threshold_start
        self.Threshold_start_value = 1400
        Threshold_start_adj = Gtk.Adjustment()
        Threshold_start_adj.configure(1400, 0, 2911, 1, 0, 0)
        self.Threshold_start = Gtk.SpinButton(adjustment = Threshold_start_adj, climb_rate = 1, digits = 0)
        self.Threshold_start.set_value(self.Threshold_start_value) 
        self.Threshold_start.connect('value-changed', self.Threshold_start_set)
        Threshold_start_label = Gtk.Label()
        Threshold_start_label.set_text('Start ')

        #Threshold_stop
        self.Threshold_stop_value = 2900
        Threshold_stop_adj = Gtk.Adjustment()
        Threshold_stop_adj.configure(2900, 0, 2911, 1, 0, 0)
        self.Threshold_stop = Gtk.SpinButton(adjustment = Threshold_stop_adj, climb_rate = 1, digits = 0)
        self.Threshold_stop.set_value(self.Threshold_stop_value) 
        self.Threshold_stop.connect('value-changed', self.Threshold_stop_set)
        Threshold_stop_label = Gtk.Label()
        Threshold_stop_label.set_text('Stop ')

        #n_injections
        self.n_injections_value = 100
        n_injections_adj = Gtk.Adjustment()
        n_injections_adj.configure(100, 1, 65535, 1, 0, 0)
        self.n_injections = Gtk.SpinButton(adjustment = n_injections_adj, climb_rate = 1, digits = 0)
        self.n_injections.set_value(self.n_injections_value) 
        self.n_injections.connect('value-changed', self.n_injections_set)
        n_injections_label = Gtk.Label()
        n_injections_label.set_text('Number of injections')

        #Buttons for coulmn offset
        self.col_offset_value = 0
        offset_adj = Gtk.Adjustment()
        offset_adj.configure(0, 0, 15, 1, 0, 0)
        self.col_offset = Gtk.SpinButton(adjustment = offset_adj, climb_rate = 1, digits = 0)
        self.col_offset.set_value(self.col_offset_value)
        self.col_offset.connect('value-changed', self.offset_set)
        col_offset_label = Gtk.Label()
        col_offset_label.set_text('Column offset')

        #Startbutton
        self.Startbutton = Gtk.Button(label = 'Start')
        self.Startbutton.connect('clicked', self.on_Startbutton_clicked)

        grid.attach(Threshold_label, 0, 0, 6, 1)
        grid.attach(Threshold_start_label, 0, 1, 1, 1)
        grid.attach(self.Threshold_start, 1, 1, 2, 1)
        grid.attach(Threshold_stop_label, 3, 1, 1, 1)
        grid.attach(self.Threshold_stop, 4, 1, 2, 1)
        grid.attach(n_injections_label, 2, 2, 2, 1)
        grid.attach(self.n_injections, 2, 3, 2, 1)
        grid.attach(col_offset_label, 1, 4, 4, 1)
        grid.attach(self.col_offset, 2, 5, 2, 1)
        grid.attach(Space, 0, 6, 1, 1)
        grid.attach(self.other_process, 0, 7, 4, 1)
        grid.attach(self.Startbutton, 4, 7, 2, 1)

        self.show_all()

    def Threshold_start_set(self, event):
        self.Threshold_start_value = self.Threshold_start.get_value_as_int()
        temp_Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        new_adjustment_start = Gtk.Adjustment()
        new_adjustment_start.configure(200, self.Threshold_start_value, 2911, 1, 0, 0)
        self.Threshold_stop.disconnect_by_func(self.Threshold_stop_set)
        self.Threshold_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Threshold_stop.set_value(temp_Threshold_stop_value)
        self.Threshold_stop.connect('value-changed', self.Threshold_stop_set)

    def Threshold_stop_set(self, event):
        self.Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        temp_Threshold_start_value = self.Threshold_start.get_value_as_int()
        new_adjustment_stop = Gtk.Adjustment()
        new_adjustment_stop.configure(200, 0, self.Threshold_stop_value, 1, 0, 0)
        self.Threshold_start.disconnect_by_func(self.Threshold_start_set)
        self.Threshold_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Threshold_start.set_value(temp_Threshold_start_value)
        self.Threshold_start.connect('value-changed', self.Threshold_start_set)

    def n_injections_set(self, event):
        self.n_injections_value = self.n_injections.get_value_as_int()

    def offset_set(self, event):
        self.col_offset_value = self.col_offset.get_value_as_int()

    def on_Startbutton_clicked(self, widget):
        if GUI.get_process_alive():
            self.other_process.set_text('Other process running')
            return
        elif GUI.get_simulation_alive():
            self.other_process.set_text('Simulation running')
            return

        GUI.Status_window_call(function = 'PixelDAC_opt', 
                                lowerTHL = self.Threshold_start_value, 
                                upperTHL = self.Threshold_stop_value, 
                                n_injections = self.n_injections_value)
        new_process = TPX3_multiprocess_start.process_call(function = 'PixelDAC_opt', 
                                                            iteration = 0, 
                                                            Vthreshold_start = self.Threshold_start_value, 
                                                            Vthreshold_stop = self.Threshold_stop_value, 
                                                            n_injections = self.n_injections_value, 
                                                            offset = self.col_offset_value, 
                                                            tp_period = TPX3_datalogger.read_value(name = 'TP_Period'),
                                                            maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                            progress = GUI.get_progress_value_queue(), 
                                                            status = GUI.get_status_queue(), 
                                                            result = GUI.pixeldac_result, 
                                                            plot_queue = GUI.plot_queue)
        GUI.set_running_process(running_process = new_process)
        GUI.set_quit_scan_label()

        self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Run_Datataking(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Start Datataking')
        self.connect('delete-event', self.window_destroy)

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text("")

        #other process running
        self.other_process = Gtk.Label()
        self.other_process.set_text('')

        #Time range label
        Datataking_Time_label = Gtk.Label()
        Datataking_Time_label.set_text('Datataking Time')

        #Time range label
        self.Datataking_Time_label = Gtk.Label()
        self.Datataking_Time_label.set_text('Datataking End:' )

        #Time range entrys
        self.hours_entry = Gtk.Entry()
        self.hours_entry.set_text('0')
        self.hours_entry.connect('activate', self.time_entry_text, 'h')
        self.hours_entry.set_width_chars(8)
        self.minutes_entry = Gtk.Entry()
        self.minutes_entry.set_text('0')
        self.minutes_entry.connect('activate', self.time_entry_text, 'min')
        self.minutes_entry.set_width_chars(8)
        self.seconds_entry = Gtk.Entry()
        self.seconds_entry.set_text('0')
        self.seconds_entry.connect('activate', self.time_entry_text, 'sec')
        self.seconds_entry.set_width_chars(8)

        hours_label = Gtk.Label()
        hours_label.set_text('Hours')
        minutes_label = Gtk.Label()
        minutes_label.set_text('Minutes')
        seconds_label = Gtk.Label()
        seconds_label.set_text('Seconds')

        #default values
        self.Datataking_Time_value = 0
        self.finish_time = 0
        self.finish_str = ''

        #Startbutton
        self.Startbutton = Gtk.Button(label = 'Start')
        self.Startbutton.connect('clicked', self.on_Startbutton_clicked)

        grid.attach(Datataking_Time_label, 0, 0, 6, 1)
        grid.attach(hours_label, 0, 1, 2, 1)
        grid.attach(self.hours_entry, 0, 2, 2, 1)
        grid.attach(minutes_label, 2, 1, 2, 1)
        grid.attach(self.minutes_entry, 2, 2, 2, 1)
        grid.attach(seconds_label, 4, 1, 2, 1)
        grid.attach(self.seconds_entry, 4, 2, 2, 1)
        grid.attach(self.Datataking_Time_label, 0, 3, 6, 1)
        grid.attach(Space, 0, 4, 1, 1)
        grid.attach(self.other_process, 0, 5, 4, 1)
        grid.attach(self.Startbutton, 4, 5, 2, 1)

        self.show_all()

    def time_entry_text(self, button, name):
        non_int_input = False
        try:
            hours = int(self.hours_entry.get_text())
            self.hours_entry.set_text(str(hours))
        except ValueError:
            self.hours_entry.set_text('')
            non_int_input = True
        try:
            minutes = int(self.minutes_entry.get_text())
            self.minutes_entry.set_text(str(minutes))
        except ValueError:
            self.minutes_entry.set_text('')
            non_int_input = True
        try:
            seconds = int(self.seconds_entry.get_text())
            self.seconds_entry.set_text(str(seconds))
        except ValueError:
            self.seconds_entry.set_text('')
            non_int_input = True
        if non_int_input == True:
            return

        self.Datataking_Time_value = hours * 3600 + minutes * 60 + seconds
        self.finish_time = datetime.now() + timedelta(seconds = self.Datataking_Time_value)
        if not self.Datataking_Time_value == 0:
            self.finish_str = 'Datataking ends: ' +  self.finish_time.strftime('%d/%m/%Y %H:%M:%S')
        else:
            self.finish_str = 'Datataking ends on user quit.'
        self.Datataking_Time_label.set_text(self.finish_str)

    def on_Startbutton_clicked(self, widget):
        self.time_entry_text('button', 'start')
        if GUI.get_process_alive():
            self.other_process.set_text('Other process running')
            return
        elif GUI.get_simulation_alive():
            self.other_process.set_text('Simulation running')
            return

        GUI.Status_window_call(function = 'Run', lowerTHL = self.Datataking_Time_value, 
                                upperTHL = self.finish_str)
        new_process = TPX3_multiprocess_start.process_call(function = 'DataTake', 
                                                            scan_timeout = self.Datataking_Time_value, 
                                                            thrfile = TPX3_datalogger.read_value(name = 'Equalisation_path'), 
                                                            maskfile = TPX3_datalogger.read_value(name = 'Mask_path'), 
                                                            progress = GUI.get_progress_value_queue(), 
                                                            status = GUI.get_status_queue(), 
                                                            plot_queue = GUI.plot_queue, 
                                                            readout_interval = TPX3_datalogger.read_value(name = 'Readout_Speed'))
        GUI.set_running_process(running_process = new_process)
        GUI.set_quit_scan_label()

        self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_SetDAC(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'DAC settings')
        self.connect('delete-event', self.window_destroy)

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text("")

        #Ibias_Preamp_ON
        self.Ibias_Preamp_ON_value = TPX3_datalogger.read_value(name = 'Ibias_Preamp_ON')
        Ibias_Preamp_ON_adj = Gtk.Adjustment()
        Ibias_Preamp_ON_adj.configure(127, 0, 255, 1, 0, 0)
        self.Ibias_Preamp_ON = Gtk.SpinButton(adjustment = Ibias_Preamp_ON_adj, climb_rate = 1, digits=0)
        self.Ibias_Preamp_ON.set_value(self.Ibias_Preamp_ON_value) 
        self.Ibias_Preamp_ON.connect('value-changed', self.Ibias_Preamp_ON_set)
        Ibias_Preamp_ON_label = Gtk.Label()
        Ibias_Preamp_ON_label.set_text("Ibias_Preamp_ON ")

        #Ibias_Preamp_OFF
        self.Ibias_Preamp_OFF_value = 7
        Ibias_Preamp_OFF_adj = Gtk.Adjustment()
        Ibias_Preamp_OFF_adj.configure(7, 0, 15, 1, 0, 0)
        self.Ibias_Preamp_OFF = Gtk.SpinButton(adjustment = Ibias_Preamp_OFF_adj, climb_rate = 1, digits = 0)
        self.Ibias_Preamp_OFF.set_value(self.Ibias_Preamp_OFF_value) 
        self.Ibias_Preamp_OFF.connect('value-changed', self.Ibias_Preamp_OFF_set)
        Ibias_Preamp_OFF_label = Gtk.Label()
        Ibias_Preamp_OFF_label.set_text('Ibias_Preamp_OFF ')

        #VPreamp_NCAS
        self.VPreamp_NCAS_value = TPX3_datalogger.read_value(name = 'VPreamp_NCAS')
        VPreamp_NCAS_adj = Gtk.Adjustment()
        VPreamp_NCAS_adj.configure(127, 0, 255, 1, 0, 0)
        self.VPreamp_NCAS = Gtk.SpinButton(adjustment = VPreamp_NCAS_adj, climb_rate = 1, digits = 0)
        self.VPreamp_NCAS.set_value(self.VPreamp_NCAS_value) 
        self.VPreamp_NCAS.connect('value-changed', self.VPreamp_NCAS_set)
        VPreamp_NCAS_label = Gtk.Label()
        VPreamp_NCAS_label.set_text('VPreamp_NCAS ')

        #Ibias_Ikrum
        self.Ibias_Ikrum_value = TPX3_datalogger.read_value(name = 'Ibias_Ikrum')
        Ibias_Ikrum_adj = Gtk.Adjustment()
        Ibias_Ikrum_adj.configure(127, 0, 255, 1, 0, 0)
        self.Ibias_Ikrum = Gtk.SpinButton(adjustment = Ibias_Ikrum_adj, climb_rate = 1, digits = 0)
        self.Ibias_Ikrum.set_value(self.Ibias_Ikrum_value) 
        self.Ibias_Ikrum.connect('value-changed', self.Ibias_Ikrum_set)
        Ibias_Ikrum_label = Gtk.Label()
        Ibias_Ikrum_label.set_text('Ibias_Ikrum ')

        #Vfbk
        self.Vfbk_value = TPX3_datalogger.read_value(name = 'Vfbk')
        Vfbk_adj = Gtk.Adjustment()
        Vfbk_adj.configure(127, 0, 255, 1, 0, 0)
        self.Vfbk = Gtk.SpinButton(adjustment = Vfbk_adj, climb_rate = 1, digits = 0)
        self.Vfbk.set_value(self.Vfbk_value) 
        self.Vfbk.connect('value-changed', self.Vfbk_set)
        Vfbk_label = Gtk.Label()
        Vfbk_label.set_text('Vfbk ')

        #Vthreshold_fine
        self.Vthreshold_fine_value = TPX3_datalogger.read_value(name = 'Vthreshold_fine')
        Vthreshold_fine_adj = Gtk.Adjustment()
        Vthreshold_fine_adj.configure(255, 0, 511, 1, 0, 0)
        self.Vthreshold_fine = Gtk.SpinButton(adjustment = Vthreshold_fine_adj, climb_rate = 1, digits = 0)
        self.Vthreshold_fine.set_value(self.Vthreshold_fine_value) 
        self.Vthreshold_fine.connect('value-changed', self.Vthreshold_fine_set)
        Vthreshold_fine_label = Gtk.Label()
        Vthreshold_fine_label.set_text('Vthreshold_fine ')

        #Vthreshold_coarse
        self.Vthreshold_coarse_value = TPX3_datalogger.read_value(name = 'Vthreshold_coarse')
        Vthreshold_coarse_adj = Gtk.Adjustment()
        Vthreshold_coarse_adj.configure(7, 0, 15, 1, 0, 0)
        self.Vthreshold_coarse = Gtk.SpinButton(adjustment = Vthreshold_coarse_adj, climb_rate = 1, digits = 0)
        self.Vthreshold_coarse.set_value(self.Vthreshold_coarse_value) 
        self.Vthreshold_coarse.connect('value-changed', self.Vthreshold_coarse_set)
        Vthreshold_coarse_label = Gtk.Label()
        Vthreshold_coarse_label.set_text('Vthreshold_coarse ')

        #Ibias_DiscS1_ON
        self.Ibias_DiscS1_ON_value = TPX3_datalogger.read_value(name = 'Ibias_DiscS1_ON')
        Ibias_DiscS1_ON_adj = Gtk.Adjustment()
        Ibias_DiscS1_ON_adj.configure(127, 0, 255, 1, 0, 0)
        self.Ibias_DiscS1_ON = Gtk.SpinButton(adjustment = Ibias_DiscS1_ON_adj, climb_rate = 1, digits = 0)
        self.Ibias_DiscS1_ON.set_value(self.Ibias_DiscS1_ON_value) 
        self.Ibias_DiscS1_ON.connect('value-changed', self.Ibias_DiscS1_ON_set)
        Ibias_DiscS1_ON_label = Gtk.Label()
        Ibias_DiscS1_ON_label.set_text('Ibias_DiscS1_ON ')

        #Ibias_DiscS1_OFF
        self.Ibias_DiscS1_OFF_value = 7
        Ibias_DiscS1_OFF_adj = Gtk.Adjustment()
        Ibias_DiscS1_OFF_adj.configure(7, 0, 15, 1, 0, 0)
        self.Ibias_DiscS1_OFF = Gtk.SpinButton(adjustment = Ibias_DiscS1_OFF_adj, climb_rate = 1, digits = 0)
        self.Ibias_DiscS1_OFF.set_value(self.Ibias_DiscS1_OFF_value) 
        self.Ibias_DiscS1_OFF.connect('value-changed', self.Ibias_DiscS1_OFF_set)
        Ibias_DiscS1_OFF_label = Gtk.Label()
        Ibias_DiscS1_OFF_label.set_text('Ibias_DiscS1_OFF ')

        #Ibias_DiscS2_ON
        self.Ibias_DiscS2_ON_value = TPX3_datalogger.read_value(name = 'Ibias_DiscS2_ON')
        Ibias_DiscS2_ON_adj = Gtk.Adjustment()
        Ibias_DiscS2_ON_adj.configure(127, 0, 255, 1, 0, 0)
        self.Ibias_DiscS2_ON = Gtk.SpinButton(adjustment = Ibias_DiscS2_ON_adj, climb_rate = 1, digits = 0)
        self.Ibias_DiscS2_ON.set_value(self.Ibias_DiscS2_ON_value) 
        self.Ibias_DiscS2_ON.connect('value-changed', self.Ibias_DiscS2_ON_set)
        Ibias_DiscS2_ON_label = Gtk.Label()
        Ibias_DiscS2_ON_label.set_text('Ibias_DiscS2_ON ')

        #Ibias_DiscS2_OFF
        self.Ibias_DiscS2_OFF_value = 7
        Ibias_DiscS2_OFF_adj = Gtk.Adjustment()
        Ibias_DiscS2_OFF_adj.configure(7, 0, 15, 1, 0, 0)
        self.Ibias_DiscS2_OFF = Gtk.SpinButton(adjustment = Ibias_DiscS2_OFF_adj, climb_rate = 1, digits = 0)
        self.Ibias_DiscS2_OFF.set_value(self.Ibias_DiscS2_OFF_value) 
        self.Ibias_DiscS2_OFF.connect('value-changed', self.Ibias_DiscS2_OFF_set)
        Ibias_DiscS2_OFF_label = Gtk.Label()
        Ibias_DiscS2_OFF_label.set_text('Ibias_DiscS2_OFF ')

        #Ibias_PixelDAC
        self.Ibias_PixelDAC_value = TPX3_datalogger.read_value(name = 'Ibias_PixelDAC')
        Ibias_PixelDAC_adj = Gtk.Adjustment()
        Ibias_PixelDAC_adj.configure(127, 0, 255, 1, 0, 0)
        self.Ibias_PixelDAC = Gtk.SpinButton(adjustment = Ibias_PixelDAC_adj, climb_rate = 1, digits = 0)
        self.Ibias_PixelDAC.set_value(self.Ibias_PixelDAC_value) 
        self.Ibias_PixelDAC.connect('value-changed', self.Ibias_PixelDAC_set)
        Ibias_PixelDAC_label = Gtk.Label()
        Ibias_PixelDAC_label.set_text('Ibias_PixelDAC ')

        #Ibias_TPbufferIn
        self.Ibias_TPbufferIn_value = TPX3_datalogger.read_value(name = 'Ibias_TPbufferIn')
        Ibias_TPbufferIn_adj = Gtk.Adjustment()
        Ibias_TPbufferIn_adj.configure(127, 0, 255, 1, 0, 0)
        self.Ibias_TPbufferIn = Gtk.SpinButton(adjustment = Ibias_TPbufferIn_adj, climb_rate = 1, digits = 0)
        self.Ibias_TPbufferIn.set_value(self.Ibias_TPbufferIn_value) 
        self.Ibias_TPbufferIn.connect('value-changed', self.Ibias_TPbufferIn_set)
        Ibias_TPbufferIn_label = Gtk.Label()
        Ibias_TPbufferIn_label.set_text('Ibias_TPbufferIn ')

        #Ibias_TPbufferOut
        self.Ibias_TPbufferOut_value = TPX3_datalogger.read_value(name = 'Ibias_TPbufferOut')
        Ibias_TPbufferOut_adj = Gtk.Adjustment()
        Ibias_TPbufferOut_adj.configure(127, 0, 255, 1, 0, 0)
        self.Ibias_TPbufferOut = Gtk.SpinButton(adjustment = Ibias_TPbufferOut_adj, climb_rate = 1, digits = 0)
        self.Ibias_TPbufferOut.set_value(self.Ibias_TPbufferOut_value) 
        self.Ibias_TPbufferOut.connect('value-changed', self.Ibias_TPbufferOut_set)
        Ibias_TPbufferOut_label = Gtk.Label()
        Ibias_TPbufferOut_label.set_text('Ibias_TPbufferOut ')

        #VTP_coarse
        self.VTP_coarse_value = TPX3_datalogger.read_value(name = 'VTP_coarse')
        VTP_coarse_adj = Gtk.Adjustment()
        VTP_coarse_adj.configure(127, 0, 255, 1, 0, 0)
        self.VTP_coarse = Gtk.SpinButton(adjustment = VTP_coarse_adj, climb_rate = 1, digits = 0)
        self.VTP_coarse.set_value(self.VTP_coarse_value) 
        self.VTP_coarse.connect('value-changed', self.VTP_coarse_set)
        VTP_coarse_label = Gtk.Label()
        VTP_coarse_label.set_text('VTP_coarse ')

        #VTP_fine
        self.VTP_fine_value = TPX3_datalogger.read_value(name = 'VTP_fine')
        VTP_fine_adj = Gtk.Adjustment()
        VTP_fine_adj.configure(255, 0, 511, 1, 0, 0)
        self.VTP_fine = Gtk.SpinButton(adjustment = VTP_fine_adj, climb_rate = 1, digits = 0)
        self.VTP_fine.set_value(self.VTP_fine_value) 
        self.VTP_fine.connect('value-changed', self.VTP_fine_set)
        VTP_fine_label = Gtk.Label()
        VTP_fine_label.set_text('VTP_fine ')

        #Ibias_CP_PLL
        self.Ibias_CP_PLL_value = TPX3_datalogger.read_value(name = 'Ibias_CP_PLL')
        Ibias_CP_PLL_adj = Gtk.Adjustment()
        Ibias_CP_PLL_adj.configure(127, 0, 255, 1, 0, 0)
        self.Ibias_CP_PLL = Gtk.SpinButton(adjustment = Ibias_CP_PLL_adj, climb_rate = 1, digits = 0)
        self.Ibias_CP_PLL.set_value(self.Ibias_CP_PLL_value) 
        self.Ibias_CP_PLL.connect('value-changed', self.Ibias_CP_PLL_set)
        Ibias_CP_PLL_label = Gtk.Label()
        Ibias_CP_PLL_label.set_text('Ibias_CP_PLL ')

        #PLL_Vcntrl
        self.PLL_Vcntrl_value = TPX3_datalogger.read_value(name = 'PLL_Vcntrl')
        PLL_Vcntrl_adj = Gtk.Adjustment()
        PLL_Vcntrl_adj.configure(127, 0, 255, 1, 0, 0)
        self.PLL_Vcntrl = Gtk.SpinButton(adjustment = PLL_Vcntrl_adj, climb_rate = 1, digits = 0)
        self.PLL_Vcntrl.set_value(self.PLL_Vcntrl_value) 
        self.PLL_Vcntrl.connect('value-changed', self.PLL_Vcntrl_set)
        PLL_Vcntrl_label = Gtk.Label()
        PLL_Vcntrl_label.set_text('PLL_Vcntrl ')

        #Save Button
        self.Savebutton = Gtk.Button(label = 'Save')
        self.Savebutton.connect('clicked', self.on_Savebutton_clicked)


        grid.attach(Ibias_Preamp_ON_label, 0, 0, 1, 1)
        grid.attach(self.Ibias_Preamp_ON, 1, 0, 1, 1)
        #grid.attach(Ibias_Preamp_OFF_label, 0, 1, 1, 1)
        #grid.attach(self.Ibias_Preamp_OFF, 1, 1, 1, 1)
        grid.attach(VPreamp_NCAS_label, 0, 2, 1, 1)
        grid.attach(self.VPreamp_NCAS, 1, 2, 1, 1)
        grid.attach(Ibias_Ikrum_label, 0, 3, 1, 1)
        grid.attach(self.Ibias_Ikrum, 1, 3, 1, 1)
        grid.attach(Vfbk_label, 0, 4, 1, 1)
        grid.attach(self.Vfbk, 1, 4, 1, 1)
        grid.attach(Vthreshold_fine_label, 0, 5, 1, 1)
        grid.attach(self.Vthreshold_fine, 1, 5, 1, 1)
        grid.attach(Vthreshold_coarse_label, 0, 6, 1, 1)
        grid.attach(self.Vthreshold_coarse, 1, 6, 1, 1)
        grid.attach(Ibias_DiscS1_ON_label, 0, 7, 1, 1)
        grid.attach(self.Ibias_DiscS1_ON, 1, 7, 1, 1)
        #grid.attach(Ibias_DiscS1_OFF_label, 0, 8, 1, 1)
        #grid.attach(self.Ibias_DiscS1_OFF, 1, 8, 1, 1)
        grid.attach(Ibias_DiscS2_ON_label, 0, 9, 1, 1)
        grid.attach(self.Ibias_DiscS2_ON, 1, 9, 1, 1)
        #grid.attach(Ibias_DiscS2_OFF_label, 0, 10, 1 , 1)
        #grid.attach(self.Ibias_DiscS2_OFF, 1, 10, 1 , 1)
        grid.attach(Ibias_PixelDAC_label, 0, 11, 1, 1)
        grid.attach(self.Ibias_PixelDAC, 1, 11, 1, 1)
        grid.attach(Ibias_TPbufferIn_label, 0, 12, 1, 1)
        grid.attach(self.Ibias_TPbufferIn, 1, 12, 1, 1)
        grid.attach(Ibias_TPbufferOut_label, 0, 13, 1, 1)
        grid.attach(self.Ibias_TPbufferOut, 1, 13, 1, 1)
        grid.attach(VTP_coarse_label, 0, 14, 1, 1)
        grid.attach(self.VTP_coarse, 1, 14, 1, 1)
        grid.attach(VTP_fine_label, 0, 15, 1, 1)
        grid.attach(self.VTP_fine, 1, 15, 1, 1)
        grid.attach(Ibias_CP_PLL_label, 0, 16, 1, 1)
        grid.attach(self.Ibias_CP_PLL, 1, 16, 1, 1)
        grid.attach(PLL_Vcntrl_label, 0, 17, 1, 1)
        grid.attach(self.PLL_Vcntrl, 1, 17, 1, 1)
        grid.attach(Space, 0, 18, 1, 1)
        grid.attach(self.Savebutton, 1, 19, 1, 1)

        self.show_all()

    def Ibias_Preamp_ON_set(self, event):
        self.Ibias_Preamp_ON_value = self.Ibias_Preamp_ON.get_value_as_int()

    def Ibias_Preamp_OFF_set(self, event):
        self.Ibias_Preamp_OFF_value = self.Ibias_Preamp_OFF.get_value_as_int()

    def VPreamp_NCAS_set(self, event):
        self.VPreamp_NCAS_value = self.VPreamp_NCAS.get_value_as_int()

    def Ibias_Ikrum_set(self, event):
        self.Ibias_Ikrum_value = self.Ibias_Ikrum.get_value_as_int()

    def Vfbk_set(self, event):
        self.Vfbk_value = self.Vfbk.get_value_as_int()

    def Vthreshold_fine_set(self, event):
        self.Vthreshold_fine_value = self.Vthreshold_fine.get_value_as_int()

    def Vthreshold_coarse_set(self, event):
        self.Vthreshold_coarse_value = self.Vthreshold_coarse.get_value_as_int()

    def Ibias_DiscS1_ON_set(self, event):
        self.Ibias_DiscS1_ON_value = self.Ibias_DiscS1_ON.get_value_as_int()

    def Ibias_DiscS1_OFF_set(self, event):
        self.Ibias_DiscS1_OFF_value = self.Ibias_DiscS1_OFF.get_value_as_int()

    def Ibias_DiscS2_ON_set(self, event):
        self.Ibias_DiscS2_ON_value = self.Ibias_DiscS2_ON.get_value_as_int()

    def Ibias_DiscS2_OFF_set(self, event):
        self.Ibias_DiscS2_OFF_value = self.Ibias_DiscS2_OFF.get_value_as_int()

    def Ibias_PixelDAC_set(self, event):
        self.Ibias_PixelDAC_value = self.Ibias_PixelDAC.get_value_as_int()

    def Ibias_TPbufferIn_set(self, event):
        self.Ibias_TPbufferIn_value = self.Ibias_TPbufferIn.get_value_as_int()

    def Ibias_TPbufferOut_set(self, event):
        self.Ibias_TPbufferOut_value = self.Ibias_TPbufferOut.get_value_as_int()

    def VTP_coarse_set(self, event):
        self.VTP_coarse_value = self.VTP_coarse.get_value_as_int()

    def VTP_fine_set(self, event):
        self.VTP_fine_value = self.VTP_fine.get_value_as_int()

    def Ibias_CP_PLL_set(self, event):
        self.Ibias_CP_PLL_value = self.Ibias_CP_PLL.get_value_as_int()

    def PLL_Vcntrl_set(self, event):
        self.PLL_Vcntrl_value = self.PLL_Vcntrl.get_value_as_int()

    def on_Savebutton_clicked(self, widget):
        #check if process is running
        if GUI.get_process_alive():
            subw = GUI_Main_Error(title = 'Error', text = 'Process is running on the chip!')
            return

        #write values
        self.Ibias_Preamp_ON_value = self.Ibias_Preamp_ON.get_value_as_int()
        self.Ibias_Preamp_OFF_value = self.Ibias_Preamp_OFF.get_value_as_int()
        self.VPreamp_NCAS_value = self.VPreamp_NCAS.get_value_as_int()
        self.Ibias_Ikrum_value = self.Ibias_Ikrum.get_value_as_int()
        self.Vfbk_value = self.Vfbk.get_value_as_int()
        self.Vthreshold_fine_value = self.Vthreshold_fine.get_value_as_int()
        self.Vthreshold_coarse_value = self.Vthreshold_coarse.get_value_as_int()
        self.Ibias_DiscS1_ON_value = self.Ibias_DiscS1_ON.get_value_as_int()
        self.Ibias_DiscS1_OFF_value = self.Ibias_DiscS1_OFF.get_value_as_int()
        self.Ibias_DiscS2_ON_value = self.Ibias_DiscS2_ON.get_value_as_int()
        self.Ibias_DiscS2_OFF_value = self.Ibias_DiscS2_OFF.get_value_as_int()
        self.Ibias_PixelDAC_value = self.Ibias_PixelDAC.get_value_as_int()
        self.Ibias_TPbufferIn_value = self.Ibias_TPbufferIn.get_value_as_int()
        self.Ibias_TPbufferOut_value = self.Ibias_TPbufferOut.get_value_as_int()
        self.VTP_coarse_value = self.VTP_coarse.get_value_as_int()
        self.VTP_fine_value = self.VTP_fine.get_value_as_int()
        self.Ibias_CP_PLL_value = self.Ibias_CP_PLL.get_value_as_int()
        self.PLL_Vcntrl_value = self.PLL_Vcntrl.get_value_as_int()

        #write values to datalogger
        TPX3_datalogger.write_value(name = 'Ibias_Preamp_ON', value = self.Ibias_Preamp_ON_value)
        TPX3_datalogger.write_to_yaml(name = 'Ibias_Preamp_ON')
        #TPX3_datalogger.write_value(name = 'Ibias_Preamp_OFF', value = self.Ibias_Preamp_OFF_value)
        #TPX3_datalogger.write_to_yaml(name = 'Ibias_Preamp_OFF')
        TPX3_datalogger.write_value(name = 'VPreamp_NCAS', value = self.VPreamp_NCAS_value)
        TPX3_datalogger.write_to_yaml(name = 'VPreamp_NCAS')
        TPX3_datalogger.write_value(name = 'Ibias_Ikrum', value = self.Ibias_Ikrum_value)
        TPX3_datalogger.write_to_yaml(name = 'Ibias_Ikrum')
        TPX3_datalogger.write_value(name = 'Vfbk', value = self.Vfbk_value)
        TPX3_datalogger.write_to_yaml(name = 'Vfbk')
        TPX3_datalogger.write_value(name = 'Vthreshold_fine', value = self.Vthreshold_fine_value)
        TPX3_datalogger.write_to_yaml(name = 'Vthreshold_fine')
        TPX3_datalogger.write_value(name = 'Vthreshold_coarse', value = self.Vthreshold_coarse_value)
        TPX3_datalogger.write_to_yaml(name = 'Vthreshold_coarse')
        TPX3_datalogger.write_value(name = 'Ibias_DiscS1_ON', value = self.Ibias_DiscS1_ON_value)
        TPX3_datalogger.write_to_yaml(name = 'Ibias_DiscS1_ON')
        #TPX3_datalogger.write_value(name = 'Ibias_DiscS1_OFF', value = self.Ibias_DiscS1_OFF_value)
        #TPX3_datalogger.write_to_yaml(name = 'Ibias_DiscS1_OFF')
        TPX3_datalogger.write_value(name = 'Ibias_DiscS2_ON', value = self.Ibias_DiscS2_ON_value)
        TPX3_datalogger.write_to_yaml(name = 'Ibias_DiscS2_ON')
        #TPX3_datalogger.write_value(name = 'Ibias_DiscS2_OFF', value = self.Ibias_DiscS2_OFF_value)
        #TPX3_datalogger.write_to_yaml(name = 'Ibias_DiscS2_OFF')
        TPX3_datalogger.write_value(name = 'Ibias_PixelDAC', value = self.Ibias_PixelDAC_value)
        TPX3_datalogger.write_to_yaml(name = 'Ibias_PixelDAC')
        TPX3_datalogger.write_value(name = 'Ibias_TPbufferIn', value = self.Ibias_TPbufferIn_value)
        TPX3_datalogger.write_to_yaml(name = 'Ibias_TPbufferIn')
        TPX3_datalogger.write_value(name = 'Ibias_TPbufferOut', value = self.Ibias_TPbufferOut_value)
        TPX3_datalogger.write_to_yaml(name = 'Ibias_TPbufferOut')
        TPX3_datalogger.write_value(name = 'VTP_coarse', value = self.VTP_coarse_value)
        TPX3_datalogger.write_to_yaml(name = 'VTP_coarse')
        TPX3_datalogger.write_value(name = 'VTP_fine', value = self.VTP_fine_value)
        TPX3_datalogger.write_to_yaml(name = 'VTP_fine')
        TPX3_datalogger.write_value(name = 'Ibias_CP_PLL', value = self.Ibias_CP_PLL_value)
        TPX3_datalogger.write_to_yaml(name = 'Ibias_CP_PLL')
        TPX3_datalogger.write_value(name = 'PLL_Vcntrl', value = self.PLL_Vcntrl_value)
        TPX3_datalogger.write_to_yaml(name = 'PLL_Vcntrl')

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Additional_Settings(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Settings')
        self.connect('delete-event', self.window_destroy)
        self.expert_value = False
        self.sense_DAC_dict = {'Off' : 0, 'Ibias_Preamp_ON' : 1, 'Ibias_Preamp_OFF' : 2, 'VPreamp_NCAS' : 3, 'Ibias_Ikrum' : 4, 'Vfbk' : 5, 
                            'Vthreshold_fine' : 6, 'Vtreshold_corse' : 7, 'IBias_DiscS1_ON' : 8, 'IBias_DiscS1_OFF' : 9, 'IBias_DiscS2_ON' : 10, 
                            'IBias_DiscS2_OFF' : 11, 'IBias_PixelDAC' : 12, 'IBias_TPbufferIn' : 13, 'IBias_TPbufferOut' : 14, 'VTP_coarse' : 15,
                            'VTP_fine' : 16, 'Ibias_CP_PLL' : 17, 'PLL_Vcntrl' : 18, 'BandGap_output' : 28, 'BandGap_Temp' : 29,
                            'Ibias_dac' : 30, 'Ibias_dac_cas' : 31}

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text("")
        self.Space2 = Gtk.Label()
        self.Space2.set_text("")
        self.Space3 = Gtk.Label()
        self.Space3.set_text("")

        #Button for polarity select
        self.polarity_value = TPX3_datalogger.read_value('Polarity')
        self.set_polarity_button = Gtk.ToggleButton()
        if self.polarity_value == 1:
            self.set_polarity_button.set_active(True)
            self.set_polarity_button.set_label('  NEG  ')
        else:
            self.set_polarity_button.set_active(False)
            self.set_polarity_button.set_label('  POS  ')

        self.set_polarity_button.connect('toggled', self.set_polarity_button_toggled)
        set_polarity_button_label = Gtk.Label()
        set_polarity_button_label.set_text('Polarity')

        #Button for Fast IO select
        self.Fast_IO_en_value = TPX3_datalogger.read_value('Fast_Io_en')
        self.Fast_IO_button = Gtk.ToggleButton()
        if self.Fast_IO_en_value == 1:
            self.Fast_IO_button.set_active(True)
            self.Fast_IO_button.set_label('  ON  ')
        else:
            self.Fast_IO_button.set_active(False)
            self.Fast_IO_button.set_label('  OFF  ')
        self.Fast_IO_button.connect('toggled', self.Fast_IO_button_toggled)
        Fast_IO_button_label = Gtk.Label()
        Fast_IO_button_label.set_text('Fast IO')

        #Buttons for number of operation mode
        self.op_mode_value = TPX3_datalogger.read_value('Op_mode')
        Op_mode_button1 = Gtk.RadioButton.new_with_label_from_widget(None, 'ToT and ToA')
        Op_mode_button2 = Gtk.RadioButton.new_with_label_from_widget( Op_mode_button1, 'Only ToA')
        Op_mode_button3 = Gtk.RadioButton.new_with_label_from_widget( Op_mode_button1, 'Event Count & Integral ToT')
        if self.op_mode_value == 0:
            Op_mode_button1.set_active(True)
        elif self.op_mode_value == 1:
            Op_mode_button2.set_active(True)
        else:
            Op_mode_button3.set_active(True)
        Op_mode_button1.connect('toggled', self.Op_mode_button_toggled, '0')
        Op_mode_button2.connect('toggled', self.Op_mode_button_toggled, '1')
        Op_mode_button3.connect('toggled', self.Op_mode_button_toggled, '2')
        Op_mode_label = Gtk.Label()
        Op_mode_label.set_text('     Operation mode     ')

        #TP_Period setting
        self.TP_Period_value = TPX3_datalogger.read_value(name = 'TP_Period')
        TP_Period_adj = Gtk.Adjustment()
        TP_Period_adj.configure(1, 0, 255, 1, 0, 0)
        self.TP_Period = Gtk.SpinButton(adjustment = TP_Period_adj, climb_rate = 1, digits = 0)
        self.TP_Period.set_value(self.TP_Period_value)
        self.TP_Period.connect('value-changed', self.TP_Period_set)
        TP_Period_label = Gtk.Label()
        TP_Period_label.set_text('TP_Period')

        #Input for Readout_Speed
        self.Readout_Speed_value = float(TPX3_datalogger.read_value('Readout_Speed'))
        self.Readout_Speed_entry = Gtk.Entry()
        self.Readout_Speed_entry.set_text(str(self.Readout_Speed_value))
        self.Readout_Speed_entry.connect('activate', self.readout_speed_entered)
        Readout_Speed_entry_label = Gtk.Label()
        Readout_Speed_entry_label.set_text('Readout Speed')

        #Expert check box
        self.expert_checkbox = Gtk.CheckButton(label='Expert')
        self.expert_checkbox.connect('toggled', self.on_expert_toggled)
        self.expert_checkbox.set_active(False)

        #Button for Set AckCommand_en
        self.AckCommand_en_value = TPX3_datalogger.read_value('AckCommand_en')
        self.AckCommand_en_button = Gtk.ToggleButton()
        if self.AckCommand_en_value == 1:
            self.AckCommand_en_button.set_active(True)
            self.AckCommand_en_button.set_label('  ON  ')
        else:
            self.AckCommand_en_button.set_active(False)
            self.AckCommand_en_button.set_label('  OFF  ')
        self.AckCommand_en_button.connect('toggled', self.AckCommand_en_button_toggled)
        self.AckCommand_en_button_label = Gtk.Label()
        self.AckCommand_en_button_label.set_text('AckCommand enable')

        #Button for Select TP_Ext_Int
        self.TP_Ext_Int_en_value = TPX3_datalogger.read_value('SelectTP_Ext_Int')
        self.TP_Ext_Int_button = Gtk.ToggleButton()
        if self.TP_Ext_Int_en_value == 1:
            self.TP_Ext_Int_button.set_active(True)
            self.TP_Ext_Int_button.set_label('  ON  ')
        else:
            self.TP_Ext_Int_button.set_active(False)
            self.TP_Ext_Int_button.set_label('  OFF  ')
        self.TP_Ext_Int_button.connect('toggled', self.TP_Ext_Int_button_toggled)
        self.TP_Ext_Int_button_label = Gtk.Label()
        self.TP_Ext_Int_button_label.set_text('TP_Ext_Int')

        #ClkOut_frequency_src
        self.ClkOut_frequency_src_value = TPX3_datalogger.read_value('ClkOut_frequency_src')
        self.ClkOut_frequency_combo = Gtk.ComboBoxText()
        self.ClkOut_frequency_combo.set_entry_text_column(0)
        self.ClkOut_frequency_combo.connect('changed', self.ClkOut_frequency_combo_changed)
        self.ClkOut_frequency_combo.append_text('320\u200AMHz')
        self.ClkOut_frequency_combo.append_text('160\u200AMHz')
        self.ClkOut_frequency_combo.append_text('80\u200AMHz')
        self.ClkOut_frequency_combo.append_text('40\u200AMHz')
        self.ClkOut_frequency_combo.append_text('external')
        self.ClkOut_frequency_combo.set_active((TPX3_datalogger.read_value('ClkOut_frequency_src')-1))
        self.ClkOut_frequency_combo_label = Gtk.Label()
        self.ClkOut_frequency_combo_label.set_text('ClkOut_frequency_src')

        #Drop down for sense DAC
        self.sense_DAC_value = TPX3_datalogger.read_value('Sense_DAC')
        self.dropdown = Gtk.ComboBoxText()
        self.dropdown.append_text('Off')
        self.dropdown.append_text('Ibias_Preamp_ON')
        self.dropdown.append_text('Ibias_Preamp_OFF')
        self.dropdown.append_text('VPreamp_NCAS')
        self.dropdown.append_text('Ibias_Ikrum')
        self.dropdown.append_text('Vfbk')
        self.dropdown.append_text('Vthreshold_fine')
        self.dropdown.append_text('Vtreshold_corse')
        self.dropdown.append_text('IBias_DiscS1_ON')
        self.dropdown.append_text('IBias_DiscS1_OFF')
        self.dropdown.append_text('IBias_DiscS2_ON')
        self.dropdown.append_text('IBias_DiscS2_OFF')
        self.dropdown.append_text('IBias_PixelDAC')
        self.dropdown.append_text('IBias_TPbufferIn')
        self.dropdown.append_text('IBias_TPbufferOut')
        self.dropdown.append_text('VTP_coarse')
        self.dropdown.append_text('VTP_fine')
        self.dropdown.append_text('Ibias_CP_PLL')
        self.dropdown.append_text('PLL_Vcntrl')
        self.dropdown.append_text('BandGap_output')
        self.dropdown.append_text('BandGap_Temp')
        self.dropdown.append_text('Ibias_dac')
        self.dropdown.append_text('Ibias_dac_cas')

        if self.sense_DAC_value in range(19):
            self.dropdown.set_active(self.sense_DAC_value)
        elif self.sense_DAC_value in range(28, 32):
            self.dropdown.set_active(self.sense_DAC_value - 9)
        else:
            print('Error at set sense Dac')
        self.dropdown.connect('changed', self.dropdown_changed)
        self.dropdown_label = Gtk.Label()
        self.dropdown_label.set_text('Sense DAC')

        #Link_Toggle
        self.Link_label = Gtk.Label()
        self.Link_label.set_text('Chip links')
        self.Link_0_label = Gtk.Label()
        self.Link_0_label.set_text('0')
        self.Link_1_label = Gtk.Label()
        self.Link_1_label.set_text('1')
        self.Link_2_label = Gtk.Label()
        self.Link_2_label.set_text('2')
        self.Link_3_label = Gtk.Label()
        self.Link_3_label.set_text('3')
        self.Link_4_label = Gtk.Label()
        self.Link_4_label.set_text('4')
        self.Link_5_label = Gtk.Label()
        self.Link_5_label.set_text('5')
        self.Link_6_label = Gtk.Label()
        self.Link_6_label.set_text('6')
        self.Link_7_label = Gtk.Label()
        self.Link_7_label.set_text('7')
        if TPX3_datalogger.get_link_status(0) in [1, 3, 5, 7]:
            self.Link_0_enable = 1
        else:
            self.Link_0_enable = 0
        self.Link_0_enable_button = Gtk.ToggleButton()
        if self.Link_0_enable == 1:
            self.Link_0_enable_button.set_active(True)
            self.Link_0_enable_button.set_label(' ON  ')
        else:
            self.Link_0_enable_button.set_active(False)
            self.Link_0_enable_button.set_label(' OFF  ')
        self.Link_0_enable_button.connect('toggled', self.Link_0_enable_button_toggled)
        if TPX3_datalogger.get_link_status(1) in [1, 3, 5, 7]:
            self.Link_1_enable = 1
        else:
            self.Link_1_enable = 0
        self.Link_1_enable_button = Gtk.ToggleButton()
        if self.Link_1_enable == 1:
            self.Link_1_enable_button.set_active(True)
            self.Link_1_enable_button.set_label(' ON  ')
        else:
            self.Link_1_enable_button.set_active(False)
            self.Link_1_enable_button.set_label(' OFF  ')
        self.Link_1_enable_button.connect('toggled', self.Link_1_enable_button_toggled)
        if TPX3_datalogger.get_link_status(2) in [1, 3, 5, 7]:
            self.Link_2_enable = 1
        else:
            self.Link_2_enable = 0
        self.Link_2_enable_button = Gtk.ToggleButton()
        if self.Link_2_enable == 1:
            self.Link_2_enable_button.set_active(True)
            self.Link_2_enable_button.set_label(' ON  ')
        else:
            self.Link_2_enable_button.set_active(False)
            self.Link_2_enable_button.set_label(' OFF  ')
        self.Link_2_enable_button.connect('toggled', self.Link_2_enable_button_toggled)
        if TPX3_datalogger.get_link_status(3) in [1, 3, 5, 7]:
            self.Link_3_enable = 1
        else:
            self.Link_3_enable = 0
        self.Link_3_enable_button = Gtk.ToggleButton()
        if self.Link_3_enable == 1:
            self.Link_3_enable_button.set_active(True)
            self.Link_3_enable_button.set_label(' ON  ')
        else:
            self.Link_3_enable_button.set_active(False)
            self.Link_3_enable_button.set_label(' OFF  ')
        self.Link_3_enable_button.connect('toggled', self.Link_3_enable_button_toggled)
        if TPX3_datalogger.get_link_status(4) in [1, 3, 5, 7]:
            self.Link_4_enable = 1
        else:
            self.Link_4_enable = 0
        self.Link_4_enable_button = Gtk.ToggleButton()
        if self.Link_4_enable == 1:
            self.Link_4_enable_button.set_active(True)
            self.Link_4_enable_button.set_label(' ON  ')
        else:
            self.Link_4_enable_button.set_active(False)
            self.Link_4_enable_button.set_label(' OFF  ')
        self.Link_4_enable_button.connect('toggled', self.Link_4_enable_button_toggled)
        if TPX3_datalogger.get_link_status(5) in [1, 3, 5, 7]:
            self.Link_5_enable = 1
        else:
            self.Link_5_enable = 0
        self.Link_5_enable_button = Gtk.ToggleButton()
        if self.Link_5_enable == 1:
            self.Link_5_enable_button.set_active(True)
            self.Link_5_enable_button.set_label(' ON  ')
        else:
            self.Link_5_enable_button.set_active(False)
            self.Link_5_enable_button.set_label(' OFF  ')
        self.Link_5_enable_button.connect('toggled', self.Link_5_enable_button_toggled)
        if TPX3_datalogger.get_link_status(6) in [1, 3, 5, 7]:
            self.Link_6_enable = 1
        else:
            self.Link_6_enable = 0
        self.Link_6_enable_button = Gtk.ToggleButton()
        if self.Link_6_enable == 1:
            self.Link_6_enable_button.set_active(True)
            self.Link_6_enable_button.set_label(' ON  ')
        else:
            self.Link_6_enable_button.set_active(False)
            self.Link_6_enable_button.set_label(' OFF  ')
        self.Link_6_enable_button.connect('toggled', self.Link_6_enable_button_toggled)
        if TPX3_datalogger.get_link_status(7) in [1, 3, 5, 7]:
            self.Link_7_enable = 1
        else:
            self.Link_7_enable = 0
        self.Link_7_enable_button = Gtk.ToggleButton()
        if self.Link_7_enable == 1:
            self.Link_7_enable_button.set_active(True)
            self.Link_7_enable_button.set_label(' ON  ')
        else:
            self.Link_7_enable_button.set_active(False)
            self.Link_7_enable_button.set_label(' OFF  ')
        self.Link_7_enable_button.connect('toggled', self.Link_7_enable_button_toggled)


        #Save Button
        self.Savebutton = Gtk.Button(label = 'Save')
        self.Savebutton.connect('clicked', self.on_Savebutton_clicked)

        grid.attach(set_polarity_button_label, 0, 0, 2, 1)
        grid.attach(self.set_polarity_button, 2, 0, 2, 1)
        grid.attach(self.expert_checkbox, 5, 0, 1, 1)
        grid.attach(Fast_IO_button_label, 0, 1, 2, 1)
        grid.attach(self.Fast_IO_button, 2, 1, 2, 1)
        grid.attach(Op_mode_label, 0, 2, 2, 1)
        grid.attach(Op_mode_button1, 2, 2, 4, 1)
        grid.attach(Op_mode_button2, 2, 3, 4, 1)
        grid.attach(Op_mode_button3, 2, 4, 4, 1)
        grid.attach(TP_Period_label, 0, 5, 2, 1)
        grid.attach(self.TP_Period, 2, 5, 2, 1)
        grid.attach(Readout_Speed_entry_label, 0, 6, 2, 1)
        grid.attach(self.Readout_Speed_entry, 2, 6, 3, 1)
        grid.attach(Space, 0, 7, 3, 1)
        grid.attach(self.TP_Ext_Int_button_label, 0, 8, 2, 1)
        grid.attach(self.TP_Ext_Int_button, 2, 8, 2, 1)
        grid.attach(self.AckCommand_en_button_label, 0, 9, 2, 1)
        grid.attach(self.AckCommand_en_button, 2, 9, 2, 1)
        grid.attach(self.ClkOut_frequency_combo_label, 0, 10, 2, 1)
        grid.attach(self.ClkOut_frequency_combo, 2, 10, 3, 1)
        grid.attach(self.dropdown_label, 0, 11, 2, 1)
        grid.attach(self.dropdown, 2, 11, 3, 1)
        grid.attach(self.Space2, 0, 12, 3, 1)
        grid.attach(self.Link_label, 0, 13, 7, 1)
        grid.attach(self.Link_0_label, 0, 14, 1, 1)
        grid.attach(self.Link_1_label, 1, 14, 1, 1)
        grid.attach(self.Link_2_label, 2, 14, 1, 1)
        grid.attach(self.Link_3_label, 3, 14, 1, 1)
        grid.attach(self.Link_4_label, 4, 14, 1, 1)
        grid.attach(self.Link_5_label, 5, 14, 1, 1)
        grid.attach(self.Link_6_label, 6, 14, 1, 1)
        grid.attach(self.Link_7_label, 7, 14, 1, 1)
        grid.attach(self.Link_0_enable_button, 0, 15, 1, 1)
        grid.attach(self.Link_1_enable_button, 1, 15, 1, 1)
        grid.attach(self.Link_2_enable_button, 2, 15, 1, 1)
        grid.attach(self.Link_3_enable_button, 3, 15, 1, 1)
        grid.attach(self.Link_4_enable_button, 4, 15, 1, 1)
        grid.attach(self.Link_5_enable_button, 5, 15, 1, 1)
        grid.attach(self.Link_6_enable_button, 6, 15, 1, 1)
        grid.attach(self.Link_7_enable_button, 7, 15, 1, 1)
        grid.attach(self.Space3, 0, 16, 3, 1)
        grid.attach(self.Savebutton, 8, 17, 1, 1)

        self.show_all()
        self.TP_Ext_Int_button_label.hide()
        self.TP_Ext_Int_button.hide()
        self.AckCommand_en_button_label.hide()
        self.AckCommand_en_button.hide()
        self.ClkOut_frequency_combo_label.hide()
        self.ClkOut_frequency_combo.hide()
        self.dropdown_label.hide()
        self.dropdown.hide()
        self.Space2.hide()
        self.Link_label.hide()
        self.Link_0_label.hide()
        self.Link_1_label.hide()
        self.Link_2_label.hide()
        self.Link_3_label.hide()
        self.Link_4_label.hide()
        self.Link_5_label.hide()
        self.Link_6_label.hide()
        self.Link_7_label.hide()
        self.Link_0_enable_button.hide()
        self.Link_1_enable_button.hide()
        self.Link_2_enable_button.hide()
        self.Link_3_enable_button.hide()
        self.Link_4_enable_button.hide()
        self.Link_5_enable_button.hide()
        self.Link_6_enable_button.hide()
        self.Link_7_enable_button.hide()
        self.resize(1,1)

    def TP_Period_set(self, event):
        self.TP_Period_value = self.TP_Period.get_value_as_int()

    def on_expert_toggled(self, button):
        self.expert_value = button.get_active()
        if self.expert_value == True:
            self.TP_Ext_Int_button_label.show()
            self.TP_Ext_Int_button.show()
            self.AckCommand_en_button_label.show()
            self.AckCommand_en_button.show()
            self.ClkOut_frequency_combo_label.show()
            self.ClkOut_frequency_combo.show()
            self.dropdown_label.show()
            self.dropdown.show()
            self.Space2.show()
            self.Link_label.show()
            self.Link_0_label.show()
            self.Link_1_label.show()
            self.Link_2_label.show()
            self.Link_3_label.show()
            self.Link_4_label.show()
            self.Link_5_label.show()
            self.Link_6_label.show()
            self.Link_7_label.show()
            self.Link_0_enable_button.show()
            self.Link_1_enable_button.show()
            self.Link_2_enable_button.show()
            self.Link_3_enable_button.show()
            self.Link_4_enable_button.show()
            self.Link_5_enable_button.show()
            self.Link_6_enable_button.show()
            self.Link_7_enable_button.show()
            self.resize(1,1)
        else:
            self.TP_Ext_Int_button_label.hide()
            self.TP_Ext_Int_button.hide()
            self.AckCommand_en_button_label.hide()
            self.AckCommand_en_button.hide()
            self.ClkOut_frequency_combo_label.hide()
            self.ClkOut_frequency_combo.hide()
            self.dropdown_label.hide()
            self.dropdown.hide()
            self.Space2.hide()
            self.Link_label.hide()
            self.Link_0_label.hide()
            self.Link_1_label.hide()
            self.Link_2_label.hide()
            self.Link_3_label.hide()
            self.Link_4_label.hide()
            self.Link_5_label.hide()
            self.Link_6_label.hide()
            self.Link_7_label.hide()
            self.Link_0_enable_button.hide()
            self.Link_1_enable_button.hide()
            self.Link_2_enable_button.hide()
            self.Link_3_enable_button.hide()
            self.Link_4_enable_button.hide()
            self.Link_5_enable_button.hide()
            self.Link_6_enable_button.hide()
            self.Link_7_enable_button.hide()
            self.resize(1,1)

    def readout_speed_entered(self, widget):
        try: 
            self.Readout_Speed_value = float(self.Readout_Speed_entry.get_text())
        except:
            self.Readout_Speed_entry.set_text(str(self.Readout_Speed_value))

    def set_polarity_button_toggled(self, button):
        if self.set_polarity_button.get_active():
            state = 1
            self.set_polarity_button.set_label('  NEG ')
        else:
            state = 0
            self.set_polarity_button.set_label('  POS  ')
        self.polarity_value = state

    def Fast_IO_button_toggled(self, button):
        if self.Fast_IO_button.get_active():
            state = 1
            self.Fast_IO_button.set_label('  ON  ')
        else:
            state = 0
            self.Fast_IO_button.set_label('  OFF ')
        self.Fast_IO_en_value = state

    def TP_Ext_Int_button_toggled(self, button):
        if self.TP_Ext_Int_button.get_active():
            state = 1
            self.TP_Ext_Int_button.set_label('  ON  ')
        else:
            state = 0
            self.TP_Ext_Int_button.set_label('  OFF ')
        self.TP_Ext_Int_en_value = state

    def AckCommand_en_button_toggled(self, button):
        if self.AckCommand_en_button.get_active():
            state = 1
            self.AckCommand_en_button.set_label('  ON  ')
        else:
            state = 0
            self.AckCommand_en_button.set_label('  OFF ')
        self.AckCommand_en_value = state

    def Op_mode_button_toggled(self, button, name):
        self.op_mode_value = int(name)

    def ClkOut_frequency_combo_changed(self, combo):
        text = combo.get_active_text()
        if text == '320\u200AMHz':
            self.ClkOut_frequency_src_value = 1
        elif text == '160\u200AMHz':
            self.ClkOut_frequency_src_value = 2
        elif text == '80\u200AMHz':
            self.ClkOut_frequency_src_value = 3
        elif text == '40\u200AMHz':
            self.ClkOut_frequency_src_value = 4
        elif text == 'external':
            self.ClkOut_frequency_src_value = 5

    def Link_0_enable_button_toggled(self, button):
        if self.Link_0_enable_button.get_active():
            state = 1
            self.Link_0_enable_button.set_label(' ON  ')
        else:
            state = 0
            self.Link_0_enable_button.set_label(' OFF ')
        self.Link_0_enable = state

    def Link_1_enable_button_toggled(self, button):
        if self.Link_1_enable_button.get_active():
            state = 1
            self.Link_1_enable_button.set_label(' ON  ')
        else:
            state = 0
            self.Link_1_enable_button.set_label(' OFF ')
        self.Link_1_enable = state

    def Link_2_enable_button_toggled(self, button):
        if self.Link_2_enable_button.get_active():
            state = 1
            self.Link_2_enable_button.set_label(' ON  ')
        else:
            state = 0
            self.Link_2_enable_button.set_label(' OFF ')
        self.Link_2_enable = state

    def Link_3_enable_button_toggled(self, button):
        if self.Link_3_enable_button.get_active():
            state = 1
            self.Link_3_enable_button.set_label(' ON  ')
        else:
            state = 0
            self.Link_3_enable_button.set_label(' OFF ')
        self.Link_3_enable = state

    def Link_4_enable_button_toggled(self, button):
        if self.Link_4_enable_button.get_active():
            state = 1
            self.Link_4_enable_button.set_label(' ON  ')
        else:
            state = 0
            self.Link_4_enable_button.set_label(' OFF ')
        self.Link_4_enable = state

    def Link_5_enable_button_toggled(self, button):
        if self.Link_5_enable_button.get_active():
            state = 1
            self.Link_5_enable_button.set_label(' ON  ')
        else:
            state = 0
            self.Link_5_enable_button.set_label(' OFF ')
        self.Link_5_enable = state

    def Link_6_enable_button_toggled(self, button):
        if self.Link_6_enable_button.get_active():
            state = 1
            self.Link_6_enable_button.set_label(' ON  ')
        else:
            state = 0
            self.Link_6_enable_button.set_label(' OFF ')
        self.Link_6_enable = state

    def Link_7_enable_button_toggled(self, button):
        if self.Link_7_enable_button.get_active():
            state = 1
            self.Link_7_enable_button.set_label(' ON  ')
        else:
            state = 0
            self.Link_7_enable_button.set_label(' OFF ')
        self.Link_7_enable = state

    def dropdown_changed(self, widget):
        self.sense_DAC_value = self.sense_DAC_dict[self.dropdown.get_active_text()]

    def on_Savebutton_clicked(self, widget):
        # check if some process is runing
        if GUI.get_process_alive():
            subw = GUI_Main_Error(title = 'Error', text = 'Process is running on the chip!')
            return

        # get values
        self.TP_Period_value = self.TP_Period.get_value_as_int()
        try: 
            self.Readout_Speed_value = float(self.Readout_Speed_entry.get_text())
        except:
            self.Readout_Speed_entry.set_text(str(self.Readout_Speed_value))
            return

        # write values
        TPX3_datalogger.write_value(name = 'Polarity', value = self.polarity_value)
        TPX3_datalogger.write_to_yaml(name = 'Polarity')
        TPX3_datalogger.write_value(name = 'Fast_Io_en', value = self.Fast_IO_en_value)
        TPX3_datalogger.write_to_yaml(name = 'Fast_Io_en')
        TPX3_datalogger.write_value(name = 'Op_mode', value = self.op_mode_value)
        TPX3_datalogger.write_to_yaml(name = 'Op_mode')
        TPX3_datalogger.write_value(name = 'AckCommand_en', value = self.AckCommand_en_value)
        TPX3_datalogger.write_to_yaml(name = 'AckCommand_en')
        TPX3_datalogger.write_value(name = 'SelectTP_Ext_Int', value = self.TP_Ext_Int_en_value)
        TPX3_datalogger.write_to_yaml(name = 'SelectTP_Ext_Int')
        TPX3_datalogger.write_value(name = 'ClkOut_frequency_src', value = self.ClkOut_frequency_src_value)
        TPX3_datalogger.write_to_yaml(name = 'ClkOut_frequency_src')
        TPX3_datalogger.write_value(name = 'Sense_DAC', value = self.sense_DAC_value)
        TPX3_datalogger.write_to_yaml(name = 'Sense_DAC')
        TPX3_datalogger.write_value(name = 'Readout_Speed', value = self.Readout_Speed_value)
        TPX3_datalogger.write_value(name = 'TP_Period', value = self.TP_Period_value)
        TPX3_datalogger.change_link_status(0, self.Link_0_enable)
        TPX3_datalogger.change_link_status(1, self.Link_1_enable)
        TPX3_datalogger.change_link_status(2, self.Link_2_enable)
        TPX3_datalogger.change_link_status(3, self.Link_3_enable)
        TPX3_datalogger.change_link_status(4, self.Link_4_enable)
        TPX3_datalogger.change_link_status(5, self.Link_5_enable)
        TPX3_datalogger.change_link_status(6, self.Link_6_enable)
        TPX3_datalogger.change_link_status(7, self.Link_7_enable)

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Equalisation(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Equalisation')
        self.connect('delete-event', self.window_destroy)

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text('')

        Threshold_label = Gtk.Label()
        Threshold_label.set_text('Threshold')

        #Buttons for Typ of Equalisation
        Equalisation_Type_label = Gtk.Label()
        Equalisation_Type_label.set_text('Equalisation approach')
        Equalisation_Type_button1 = Gtk.RadioButton.new_with_label_from_widget(None, 'Noise')
        Equalisation_Type_button1.connect('toggled', self.on_Equalisation_Typebutton_toggled, 'Noise')
        Equalisation_Type_button2 = Gtk.RadioButton.new_with_label_from_widget(Equalisation_Type_button1, 'Testpulse')
        Equalisation_Type_button2.connect('toggled', self.on_Equalisation_Typebutton_toggled, 'Testpulse')
        self.Equalisation_Type = 'Noise'

        #Threshold_start
        self.Threshold_start_value = 1400
        Threshold_start_adj = Gtk.Adjustment()
        Threshold_start_adj.configure(1400, 0, 2911, 1, 0, 0)
        self.Threshold_start = Gtk.SpinButton(adjustment = Threshold_start_adj, climb_rate = 1, digits = 0)
        self.Threshold_start.set_value(self.Threshold_start_value) 
        self.Threshold_start.connect('value-changed', self.Threshold_start_set)
        Threshold_start_label = Gtk.Label()
        Threshold_start_label.set_text('Start')

        #Threshold_stop
        self.Threshold_stop_value = 2900
        Threshold_stop_adj = Gtk.Adjustment()
        Threshold_stop_adj.configure(2900, 0, 2911, 1, 0, 0)
        self.Threshold_stop = Gtk.SpinButton(adjustment = Threshold_stop_adj, climb_rate = 1, digits = 0)
        self.Threshold_stop.set_value(self.Threshold_stop_value) 
        self.Threshold_stop.connect('value-changed', self.Threshold_stop_set)
        Threshold_stop_label = Gtk.Label()
        Threshold_stop_label.set_text('Stop')

        #Buttons for number of iteration
        Iterationbutton1 = Gtk.RadioButton.new_with_label_from_widget(None, '4')
        Iterationbutton2 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '16')
        Iterationbutton3 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '64')
        Iterationbutton4 = Gtk.RadioButton.new_with_label_from_widget(Iterationbutton1, '256')
        Iterationbutton2.set_active(True)
        Iterationbutton1.connect('toggled', self.on_Iterationbutton_toggled, '4')
        Iterationbutton2.connect('toggled', self.on_Iterationbutton_toggled, '16')
        Iterationbutton3.connect('toggled', self.on_Iterationbutton_toggled, '64')
        Iterationbutton4.connect('toggled', self.on_Iterationbutton_toggled, '256')
        Number_of_iteration_label = Gtk.Label()
        Number_of_iteration_label.set_text('Number of iterations')
        self.Number_of_Iterations = 16

        #Startbutton
        self.Startbutton = Gtk.Button(label = 'Start')
        self.Startbutton.connect('clicked', self.on_Startbutton_clicked)

        grid.attach(Equalisation_Type_label, 0, 0, 6, 1)
        grid.attach(Equalisation_Type_button1, 1, 1, 2, 1)
        grid.attach(Equalisation_Type_button2, 3, 1, 2, 1)
        grid.attach(Threshold_label, 0, 2, 6, 1)
        grid.attach(Threshold_start_label, 0, 3, 1, 1)
        grid.attach(self.Threshold_start, 1, 3, 2, 1)
        grid.attach(Threshold_stop_label, 3, 3, 1, 1)
        grid.attach(self.Threshold_stop, 4, 3, 2, 1)
        grid.attach(Number_of_iteration_label, 1, 4, 4, 1)
        grid.attach(Iterationbutton1, 1, 5, 1, 1)
        grid.attach(Iterationbutton2, 2, 5, 1, 1)
        grid.attach(Iterationbutton3, 3, 5, 1, 1)
        grid.attach(Iterationbutton4, 4, 5, 1, 1)
        grid.attach(Space, 0, 6, 1, 1)
        grid.attach(self.Startbutton, 4, 7, 2, 1)

        self.show_all()

    def Threshold_start_set(self, event):
        self.Threshold_start_value = self.Threshold_start.get_value_as_int()
        temp_Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        new_adjustment_start = Gtk.Adjustment()
        new_adjustment_start.configure(200, self.Threshold_start_value, 2911, 1, 0, 0)
        self.Threshold_stop.disconnect_by_func(self.Threshold_stop_set)
        self.Threshold_stop.set_adjustment(adjustment = new_adjustment_start)
        self.Threshold_stop.set_value(temp_Threshold_stop_value)
        self.Threshold_stop.connect('value-changed', self.Threshold_stop_set)

    def Threshold_stop_set(self, event):
        self.Threshold_stop_value = self.Threshold_stop.get_value_as_int()
        temp_Threshold_start_value = self.Threshold_start.get_value_as_int()
        new_adjustment_stop = Gtk.Adjustment()
        new_adjustment_stop.configure(200, 0, self.Threshold_stop_value, 1, 0, 0)
        self.Threshold_start.disconnect_by_func(self.Threshold_start_set)
        self.Threshold_start.set_adjustment(adjustment = new_adjustment_stop)
        self.Threshold_start.set_value(temp_Threshold_start_value)
        self.Threshold_start.connect('value-changed', self.Threshold_start_set)

    def on_Iterationbutton_toggled(self, button, name):
        self.Number_of_Iterations = int(name)

    def on_Equalisation_Typebutton_toggled(self, button, name):
        self.Equalisation_Type = name

    def on_Startbutton_clicked(self, widget):
        if GUI.get_process_alive():
            self.other_process.set_text('Other process running')
            return
        elif GUI.get_simulation_alive():
            self.other_process.set_text('Simulation running')
            return

        GUI.Status_window_call(function='Equalisation', 
                                subtype = self.Equalisation_Type, 
                                lowerTHL = self.Threshold_start_value, 
                                upperTHL = self.Threshold_stop_value, 
                                iterations = self.Number_of_Iterations)
        if self.Equalisation_Type == 'Noise':
            new_process = TPX3_multiprocess_start.process_call(function = 'Equalisation', 
                                                                Vthreshold_start = self.Threshold_start_value, 
                                                                Vthreshold_stop = self.Threshold_stop_value, 
                                                                mask_step = self.Number_of_Iterations,
                                                                maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                                progress = GUI.get_progress_value_queue(), 
                                                                status = GUI.get_status_queue(), 
                                                                result_path = GUI.eq_result_path, 
                                                                plot_queue = GUI.plot_queue)
        elif self.Equalisation_Type == 'Testpulse':
            new_process = TPX3_multiprocess_start.process_call(function = 'Equalisation_charge', 
                                                                Vthreshold_start = self.Threshold_start_value, 
                                                                Vthreshold_stop = self.Threshold_stop_value, 
                                                                n_injections = 100, 
                                                                mask_step = self.Number_of_Iterations,
                                                                maskfile = TPX3_datalogger.read_value(name = 'Mask_path'),
                                                                tp_period = TPX3_datalogger.read_value(name = 'TP_Period'), 
                                                                progress = GUI.get_progress_value_queue(), 
                                                                status = GUI.get_status_queue(), 
                                                                result_path = GUI.eq_result_path, 
                                                                plot_queue = GUI.plot_queue)
        GUI.set_running_process(running_process = new_process)
        GUI.set_quit_scan_label()

        self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Set_Mask_Coord_Window(Gtk.Window):
    def __init__(self, coords):
        Gtk.Window.__init__(self, title = 'Coords')
        self.connect('delete-event', self.window_destroy)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.MOUSE)
        self.move((self.get_position()[0] + 100), (self.get_position()[1] + 80))
        label = Gtk.Label()
        label.set_text(coords)
        self.add(label)

        self.show_all()

    def window_destroy(self, widget, event = True):
        self.destroy()

class GUI_Mask_Entry_Window(Gtk.Window):
    def __init__(self, np_mask_list, np_column_list, np_row_list):
        Gtk.Window.__init__(self, title = 'Mask Coordinats Entry')
        self.connect("delete-event", self.window_destroy)

        global mask_window
        self.np_mask_list = np_mask_list
        self.np_column_list = np_column_list
        self.np_row_list = np_row_list

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(10)
        self.add(grid)

        self.Mask_entry = Gtk.Entry()
        self.Mask_entry.set_text('')
        self.Mask_entry.connect('activate', self.mask_entered)
        Mask_entry_label = Gtk.Label()
        Mask_entry_label.set_text('Enter coordinats')

        grid.attach(Mask_entry_label, 0, 0, 2, 1)
        grid.attach(self.Mask_entry, 2, 0, 3, 1)

        self.show_all()

    def mask_entered(self, widget): 
        mask_input = self.Mask_entry.get_text()
        if mask_input == '':
            return
        else:
            mask_input_list = mask_input.split()
            mask_list = [[]]
            mask_element = []
            for element in mask_input_list:
                if not element == '+':
                    mask_element.append(element)
                elif element == '+':
                    mask_list.append(mask_element)
                    mask_element = []
        mask_list.append(mask_element)
        mask_list.pop(0)
        for mask in mask_list:
            if mask[0] in {'all', 'All', 'a'}:
                self.np_mask_list = np.ones((256 * 256, ), dtype=bool)
                self.np_row_list = np.ones((256, ), dtype=bool)
                self.np_column_list = np.ones((256, ), dtype=bool)
            elif mask[0] in {'unall', 'Unall', 'ua'}:
                self.np_mask_list = np.zeros((256 * 256, ), dtype=bool)
                self.np_row_list = np.zeros((256, ), dtype=bool)
                self.np_column_list = np.zeros((256, ), dtype=bool)
            elif mask[0] in {'row', 'Row', 'r'}:
                if len(mask) >= 2:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256:
                        self.np_row_list[int(mask[1])] = True
                        for x in range(256):
                            self.np_mask_list[(x * 256 + int(mask[1]))] = True
            elif mask[0] in {'unrow', 'Unrow', 'ur'}:
                if len(mask) >= 2:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256:
                        self.np_row_list[int(mask[1])] = False
                        for x in range(256):
                            self.np_mask_list[(x * 256 + int(mask[1]))] = False
            elif mask[0] in {'column', 'Column', 'c'}:
                if len(mask) >= 2:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256:
                        self.np_column_list[int(mask[1])] = True
                        for y in range(256):
                            self.np_mask_list[(int(mask[1]) * 256 + y)] = True
            elif mask[0] in {'uncolumn', 'Uncolumn', 'uc'}:
                if len(mask) >= 2:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256:
                        self.np_column_list[int(mask[1])] = False
                        for y in range(256):
                            self.np_mask_list[(int(mask[1]) * 256 + y)] = False
            elif mask[0] in {'pixel', 'Pixel', 'p'}:
                if len(mask) >= 3:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256 and int(mask[2]) >= 0 and int(mask[2]) < 256:
                        x_y_entry = int(mask[1]) * 256 + int(mask[2])
                        self.np_mask_list[x_y_entry] = True
            elif mask[0] in {'unpixel', 'Unpixel', 'up'}:
                if len(mask) >= 3:
                    if int(mask[1]) >= 0 and int(mask[1]) < 256 and int(mask[2]) >= 0 and int(mask[2]) < 256:
                        x_y_entry = int(mask[1]) * 256 + int(mask[2])
                        self.np_mask_list[x_y_entry] = False
        self.Mask_entry.set_text('')
        mask_window.set_new_values(self.np_mask_list, self.np_column_list, self.np_row_list)

    def window_destroy(self, widget, event = True):
        self.destroy()

class GUI_Set_Mask(Gtk.Window):
    def __init__(self):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'appdata')
        Gtk.Window.__init__(self, title = 'Set Mask')
        self.connect('delete-event', self.window_destroy)
        self.connect("key-press-event", self.on_key_pressed)
        self.coord_window = None

        if  isinstance(mask_logger.get_mask(), bool):
            self.np_mask_list = np.zeros((256 * 256, ), dtype = bool)
        else:
            current_mask = mask_logger.get_mask()
            self.np_mask_list = current_mask.reshape((256 * 256))

        grid = Gtk.Grid()
        grid.set_row_spacing(0)
        grid.set_column_spacing(0)
        grid.set_border_width(1)
        grid.set_column_homogeneous(False)
        grid.set_row_homogeneous(False)
        self.add(grid)

        self.np_row_list = np.zeros((256, ), dtype = bool)
        self.np_column_list = np.zeros((256, ), dtype = bool)

        self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 2610, 2610)
        self.cr = cairo.Context(self.surface)
        self.cr.rectangle(0, 0, 2610, 2610)
        self.cr.set_source_rgb(1, 1, 1)
        self.cr.fill()
        self.cr.select_font_face('Open Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.cr.set_font_size(9)

        self.row_numbers = cairo.ImageSurface(cairo.FORMAT_RGB24, 21, 2610)
        self.row_num = cairo.Context(self.row_numbers)
        self.row_num.rectangle(0, 0, 21, 2610)
        self.row_num.set_source_rgb(1, 1, 1)
        self.row_num.fill()
        self.row_num.select_font_face('Open Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.row_num.set_font_size(9)

        self.column_numbers = cairo.ImageSurface(cairo.FORMAT_RGB24, 2610, 21)
        self.column_num = cairo.Context(self.column_numbers)
        self.column_num.rectangle(0, 0, 2610, 21)
        self.column_num.set_source_rgb(1, 1, 1)
        self.column_num.fill()
        self.column_num.select_font_face('Open Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.column_num.set_font_size(9)

        for x in range(4, 260):
            self.cr.set_line_width(1)
            self.cr.set_source_rgb(0.4, 0.4, 0.4)
            self.cr.rectangle(x * 10, 10, 10, 20)
            self.cr.move_to(((x + 1) * 10) - 1, 29)
            self.cr.rotate(-1.5708)
            self.cr.show_text(str(x-4))
            self.cr.rotate(1.5708)
            self.cr.stroke()

            self.column_num.set_line_width(1)
            self.column_num.set_source_rgb(0.4, 0.4, 0.4)
            self.column_num.rectangle(x * 10, 0, 10, 20)
            self.column_num.move_to(((x + 1) * 10) - 1, 19)
            self.column_num.rotate(-1.5708)
            self.column_num.show_text(str(x-4))
            self.column_num.rotate(1.5708)
            self.column_num.stroke()

        for y in range(4, 260):
            self.cr.rectangle(10, y * 10, 20, 10)
            self.cr.move_to(11, ((y + 1) * 10) - 1)
            self.cr.show_text(str(255 - (y-4)))
            self.cr.stroke()  

            self.row_num.set_line_width(1)
            self.row_num.set_source_rgb(0.4, 0.4, 0.4)
            self.row_num.rectangle(0, y * 10, 20, 10)
            self.row_num.move_to(1, ((y + 1) * 10) - 1)
            self.row_num.show_text(str(255 - (y-4)))
            self.row_num.stroke()

        for x in range(4, 260):
            for y in range(4, 260):
                self.cr.rectangle(x * 10, y * 10, 10, 10)
                self.cr.stroke()

        np_masked = np.argwhere(self.np_mask_list == True)
        for xy_coords in np_masked:
            x_coord = int((xy_coords / 256)) + 4
            y_coord = int(255 - (xy_coords - ((x_coord - 4) * 256))) + 4
            self.cr.set_source_rgb(1, 0, 0)
            self.cr.rectangle(x_coord * 10, y_coord * 10, 10, 10)
            self.cr.fill()

        self.row_numbers.write_to_png(user_path + os.sep + 'row_number.png')
        self.column_numbers.write_to_png(user_path + os.sep + 'column_number.png')
        self.surface.write_to_png(user_path + os.sep + 'chip_mask.png')

        self.map_area = Gtk.EventBox()
        self.mapview = Gtk.ScrolledWindow()
        self.mapview.set_property('width-request', 700)
        self.mapview.set_property('height-request', 700)
        self.mapview.set_border_width(0)
        self.mapview.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        self.mapview.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        self.map = Gtk.Image()
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(user_path + os.sep + 'chip_mask.png')
        self.map.set_from_pixbuf(self.pixbuf)

        self.columnview = Gtk.ScrolledWindow()
        self.columnview.set_property('width-request', 700)
        self.columnview.set_property('height-request', 21)
        self.columnview.set_border_width(0)
        self.columnview.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.NEVER)
        self.column = Gtk.Image()
        self.column_pixbuf = GdkPixbuf.Pixbuf.new_from_file(user_path + os.sep + 'column_number.png')
        self.column.set_from_pixbuf(self.column_pixbuf)
        self.columnview.add(self.column)

        self.rowview = Gtk.ScrolledWindow()
        self.rowview.set_property('width-request', 21)
        self.rowview.set_property('height-request', 700)
        self.rowview.set_max_content_height(500)
        self.rowview.set_border_width(0)
        self.rowview.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        #motion-notify-event
        #self.rowview.set_sensitive(False)
        self.row = Gtk.Image()
        self.row_pixbuf = GdkPixbuf.Pixbuf.new_from_file(user_path + os.sep + 'row_number.png')
        self.row.set_from_pixbuf(self.row_pixbuf)
        self.rowview.add(self.row)

        self.map_area.add(self.map)
        self.map_area.connect ('button-press-event', self.on_drawing_area_button_press)
        self.map_area.connect ('button-release-event', self.on_drawing_area_button_release)
        self.mapview.add(self.map_area)

        Space = Gtk.Label()
        Space.set_text('') 

        #Savebutton
        self.Savebutton = Gtk.Button(label = 'Save')
        self.Savebutton.connect('clicked', self.on_Savebutton_clicked)

        grid.attach(self.mapview, 0, 0, 20, 20)
        grid.attach(self.columnview, 0, 20, 20, 2)
        grid.attach(self.rowview, 20, 0, 2, 20)
        grid.attach(self.Savebutton, 23, 21, 2, 1)

        self.rowview.set_vadjustment(self.mapview.get_vadjustment())
        self.columnview.set_hadjustment(self.mapview.get_hadjustment())

        self.show_all()

    def draw_clicked(self):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'appdata')
        self.cr.rectangle(0, 0, 2610, 2610)
        self.cr.set_source_rgb(1, 1, 1)
        self.cr.fill()
        for x in range(4, 260):
            self.cr.set_line_width(1)
            self.cr.set_source_rgb(0.4, 0.4, 0.4)
            self.cr.rectangle(x * 10, 10, 10, 20)
            self.cr.move_to(((x + 1) * 10) - 1, 29)
            self.cr.rotate(-1.5708)
            self.cr.show_text(str(x-4))
            self.cr.rotate(1.5708)
            self.cr.stroke()
        for y in range(4, 260):
            self.cr.rectangle(10, y * 10, 20, 10)
            self.cr.move_to(11, ((y + 1) * 10) - 1)
            self.cr.show_text(str(255 - (y-4)))
            self.cr.stroke()
        for x in range(4, 260):
            for y in range(4, 260):
                self.cr.rectangle(x * 10, y * 10, 10, 10)
                self.cr.stroke()
        np_masked = np.argwhere(self.np_mask_list == True)
        np_row = np.argwhere(self.np_row_list == True)
        np_column = np.argwhere(self.np_column_list == True)
        for row in np_row:
            self.cr.set_source_rgb(1, 0, 0)
            self.cr.rectangle(10, (255 - (row - 4)) * 10, 20, 10)
            self.cr.fill()
        for column in np_column:
            self.cr.set_source_rgb(1, 0, 0)
            self.cr.rectangle((column + 4) * 10, 10, 10, 20)
            self.cr.fill()
        for xy_coords in np_masked:
            x_coord = int((xy_coords / 256)) + 4
            y_coord = int(255 - (xy_coords - ((x_coord - 4) * 256))) + 4
            self.cr.set_source_rgb(1, 0, 0)
            self.cr.rectangle(x_coord * 10, y_coord * 10, 10, 10)
            self.cr.fill()
        self.surface.write_to_png(user_path + os.sep + 'chip_mask.png')
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(user_path + os.sep + 'chip_mask.png')
        self.map.set_from_pixbuf(self.pixbuf)

    def on_drawing_area_button_press(self, widget, event):
        if event.button == 1:
            x_coord = (int(event.x / 10) - 4)
            y_coord = 255 - (int(event.y / 10) - 4)

            if x_coord in range(256) and y_coord in [257, 258]:
                if self.np_column_list[x_coord]:
                    self.np_column_list[x_coord] = False
                    for y in range(256):
                        self.np_mask_list[(x_coord * 256 + y)] = False
                else:
                    self.np_column_list[x_coord] = True
                    for y in range(256):
                        self.np_mask_list[(x_coord * 256 + y)] = True 
                self.draw_clicked()
            elif y_coord in range(256) and x_coord in [-3, -2]:
                if self.np_row_list[y_coord]:
                    self.np_row_list[y_coord] = False
                    for x in range(256):
                        self.np_mask_list[(x * 256 + y_coord)] = False
                else:
                    self.np_row_list[y_coord] = True
                    for x in range(256):
                        self.np_mask_list[(x * 256 + y_coord)] = True 
                self.draw_clicked()
            elif x_coord in range(256) and y_coord in range(256):
                x_y_entry = x_coord * 256 + y_coord
                if self.np_mask_list[x_y_entry]:
                    self.np_mask_list[x_y_entry] = False
                else:
                    self.np_mask_list[x_y_entry] = True
                self.draw_clicked()
        elif event.button == 3:
            x_coord = (int(event.x / 10) - 4)
            y_coord = 255 - (int(event.y / 10) - 4)
            coord_string = ('x=' + str(x_coord) + ', y=' + str(y_coord))
            self.coord_window = GUI_Set_Mask_Coord_Window(coord_string)

    def on_drawing_area_button_release(self, widget, event):
        if event.button == 3:
            self.coord_window.window_destroy(widget = widget)

    def on_key_pressed(self, widget, event):
        if event.keyval == 65293:   # 65293 is the keyvalue for "Enter"
            entry_window = GUI_Mask_Entry_Window(self.np_mask_list, self.np_column_list, self.np_row_list)

    def set_new_values(self, mask_list, column_list, row_list):
        self.np_mask_list = mask_list
        self.np_column_list = column_list
        self.np_row_list = row_list
        self.draw_clicked()

    def on_Savebutton_clicked(self, widget):
        mask_array = self.np_mask_list.reshape((256,256))
        mask_logger.write_full_mask(full_mask = mask_array)

        self.destroy()
    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Set_Run_Name(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Set Run Name')
        self.connect('delete-event', self.window_destroy)
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        self.add(grid)

        label = Gtk.Label()
        label.set_text('Enter run name')

        self.entry = Gtk.Entry()
        self.entry.connect('activate', self.entered_text)

        self.space = Gtk.Label()
        self.space.set_text('')

        grid.attach(label, 0, 0, 1, 1)
        grid.attach(self.entry, 0, 1, 1, 1)
        grid.attach(self.space, 0, 2, 1, 1)

        self.show_all()

    def entered_text(self, widget):
        run_name = self.entry.get_text()
        TPX3_datalogger.write_value(name = 'Run_name', value = run_name)
        self.destroy()

    def window_destroy(self, widget, event = True):
        self.destroy()

class GUI_Additional_Information(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Info')
        self.connect('delete-event', self.window_destroy)

        try:
            self.equalisation_file = os.path.split(TPX3_datalogger.read_value(name = 'Equalisation_path'))[1]
        except:
            if TPX3_datalogger.read_value(name = 'Equalisation_path') == None:
                self.equalisation_file = 'None'
            else:
                self.equalisation_file = 'Corrupt Data'

        try:
            self.mask_file = os.path.split(TPX3_datalogger.read_value(name = 'Mask_path'))[1]
        except:
            if TPX3_datalogger.read_value(name = 'Equalisation_path') == None:
                self.mask_file = 'None'
            else:
                self.mask_file = 'Corrupt Data'
        
        self.run_name = TPX3_datalogger.read_value(name = 'Run_name')
        
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        grid.set_border_width(20)
        self.add(grid)

        Space = Gtk.Label()
        Space.set_text("")

        self.Backup_File_label = Gtk.Label()
        self.Backup_File_label.set_text('\nCurrent equalisation file:\t\t' + str(self.equalisation_file) + '\nCurrent mask file:\t\t\t' + str(self.mask_file) + '\nProposed run name:\t\t\t' + str(self.run_name))

        self.refresh_button = Gtk.Button(label = "Refresh")
        self.refresh_button.connect("clicked", self.on_refresh_button_clicked)

        grid.attach(self.Backup_File_label, 0, 0, 2, 3)
        grid.attach(Space, 0, 4, 2, 1)
        grid.attach(self.refresh_button, 2, 5, 1, 1)

        self.show_all()

    def on_refresh_button_clicked(self, clicked):
        try:
            self.equalisation_file = os.path.split(TPX3_datalogger.read_value(name = 'Equalisation_path'))[1]
        except:
            if TPX3_datalogger.read_value(name = 'Equalisation_path') == None:
                self.equalisation_file = 'None'
            else:
                self.equalisation_file = 'Corrupt Data'

        try:
            self.mask_file = os.path.split(TPX3_datalogger.read_value(name = 'Mask_path'))[1]
        except:
            if TPX3_datalogger.read_value(name = 'Equalisation_path') == None:
                self.mask_file = 'None'
            else:
                self.mask_file = 'Corrupt Data'
        
        self.run_name = TPX3_datalogger.read_value(name = 'Run_name')
        
        self.Backup_File_label.set_text('\nCurrent equalisation file:\t\t' + str(self.equalisation_file) + '\nCurrent mask file:\t\t\t' + str(self.mask_file) + '\nProposed run name:\t\t\t' + str(self.run_name))

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Main_Settings(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Settings')
        self.connect('delete-event', self.window_destroy)

        self.input_window = None

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        self.add(grid)

        self.load_Backup_button = Gtk.Button(label = 'Load Backup')
        self.load_Backup_button.connect('clicked', self.on_load_Backup_button_clicked)

        self.load_Equalisation_button = Gtk.Button(label = 'Load Equalisation')
        self.load_Equalisation_button.connect('clicked', self.on_load_Equalisation_button_clicked)

        self.load_Mask_button = Gtk.Button(label = 'Load Mask')
        self.load_Mask_button.connect('clicked', self.on_load_Mask_button_clicked)

        self.load_default_Equalisation_button = Gtk.Button(label = 'Load Default Equalisation')
        self.load_default_Equalisation_button.connect('clicked', self.on_load_default_Equalisation_button_clicked)

        self.load_default_Mask_button = Gtk.Button(label = 'Load Default Mask')
        self.load_default_Mask_button.connect('clicked', self.on_load_default_Mask_button_clicked)

        self.save_Backup_button = Gtk.Button(label = 'Save Backup')
        self.save_Backup_button.connect('clicked', self.on_save_Backup_button_clicked)

        self.save_Equalisation_button = Gtk.Button(label = 'Save Equalisation')
        self.save_Equalisation_button.connect('clicked', self.on_save_Equalisation_button_clicked)

        self.save_Mask_button = Gtk.Button(label = 'Save Mask')
        self.save_Mask_button.connect('clicked', self.on_save_Mask_button_clicked)

        grid.attach(self.load_Backup_button, 0, 0, 1, 1)
        grid.attach(self.load_Equalisation_button, 0, 1, 1, 1)
        grid.attach(self.load_Mask_button, 0, 2, 1, 1)
        grid.attach(self.load_default_Equalisation_button, 0, 3, 1, 1)
        grid.attach(self.load_default_Mask_button, 0, 4, 1, 1)
        grid.attach(self.save_Backup_button, 0, 5, 1, 1)
        grid.attach(self.save_Equalisation_button, 0, 6, 1, 1)
        grid.attach(self.save_Mask_button, 0, 7, 1, 1)

        self.show_all()

    def on_load_Backup_button_clicked(self, widget):

        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')

        backup_dialog = Gtk.FileChooserDialog(title = 'Please choose a backup file', parent = self, action = Gtk.FileChooserAction.OPEN)
        backup_dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK, )
        backup_dialog.set_current_folder(user_path)
        backup_dialog.set_local_only(True)

        def change_folder(event):
            self.restrict_to_folder(dialog = backup_dialog, folder = user_path)

        filter_backup = Gtk.FileFilter()
        filter_backup.set_name('Backup files')
        filter_backup.add_pattern('*.TPX3')
        backup_dialog.add_filter(filter_backup)

        backup_dialog.connect('current_folder_changed', change_folder)

        response = backup_dialog.run()

        if response == Gtk.ResponseType.OK:
            file_name = os.path.basename(backup_dialog.get_filename())
            backup_data = file_logger.read_backup(file = file_name)
            TPX3_datalogger.set_data(config = backup_data)
            TPX3_datalogger.write_backup_to_yaml()
            GUI.statuslabel.set_text('Set backup from file.')

        backup_dialog.destroy()

    def on_load_Equalisation_button_clicked(self, widget):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'equalisations')

        equalisation_dialog = Gtk.FileChooserDialog(title = 'Please choose a equalisation file', parent = self, action = Gtk.FileChooserAction.OPEN)
        equalisation_dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK, )
        equalisation_dialog.set_current_folder(user_path)
        equalisation_dialog.set_local_only(True)

        def change_folder(event):
            self.restrict_to_folder(dialog = equalisation_dialog, folder = user_path)

        filter_equalisation = Gtk.FileFilter()
        filter_equalisation.set_name('Equalisation files')
        filter_equalisation.add_pattern('*.h5')
        equalisation_dialog.add_filter(filter_equalisation)

        equalisation_dialog.connect('current_folder_changed', change_folder)

        response = equalisation_dialog.run()

        if response == Gtk.ResponseType.OK:
            TPX3_datalogger.write_value(name = 'Equalisation_path', value = equalisation_dialog.get_filename())
            GUI.statuslabel.set_text('Set equalisation from file.')

        equalisation_dialog.destroy()

    def on_load_Mask_button_clicked(self, widget):
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'masks')

        mask_dialog = Gtk.FileChooserDialog(title = 'Please choose a mask file', parent = self, action = Gtk.FileChooserAction.OPEN)
        mask_dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK, )
        mask_dialog.set_current_folder(user_path)
        mask_dialog.set_local_only(True)

        def change_folder(event):
            self.restrict_to_folder(dialog = mask_dialog, folder = user_path)

        filter_mask = Gtk.FileFilter()
        filter_mask.set_name('Mask files')
        filter_mask.add_pattern('*.h5')
        mask_dialog.add_filter(filter_mask)

        mask_dialog.connect('current_folder_changed', change_folder)

        response = mask_dialog.run()

        if response == Gtk.ResponseType.OK:
            TPX3_datalogger.write_value(name = 'Mask_path', value = mask_dialog.get_filename())
            GUI.statuslabel.set_text('Set mask from file.')

        mask_dialog.destroy()

    def on_load_default_Equalisation_button_clicked(self, widget):
        TPX3_datalogger.write_value(name = 'Equalisation_path', value = None)
        GUI.statuslabel.set_text('Set equalisation to default.')

    def on_load_default_Mask_button_clicked(self, widget):
        TPX3_datalogger.write_value(name = 'Mask_path', value = None)
        GUI.statuslabel.set_text('Set mask to default.')

    def on_save_Backup_button_clicked(self, widget):
        self.input_window = GUI_Main_Save_Backup_Input()
        self.input_window.connect('destroy', self.window_destroy)

    def on_save_Equalisation_button_clicked(self, widget):
        self.input_window = GUI_Main_Save_Equalisation_Input()
        self.input_window.connect('destroy', self.window_destroy)

    def on_save_Mask_button_clicked(self, widget):
        self.input_window = GUI_Main_Save_Mask_Input()
        self.input_window.connect('destroy', self.window_destroy)

    def restrict_to_folder(self, dialog, folder):
        if not dialog.get_current_folder() == folder:
            dialog.set_current_folder(folder)

    def window_destroy(self, widget, event = True):
        GUI.set_destroyed()
        if self.input_window is not None:
            self.input_window.window_destroy(widget)
        self.destroy()

class GUI_Main_Save_Backup_Input(Gtk.Window):
    def __init__(self):

        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')

        Gtk.Window.__init__(self, title = 'Save Backup')
        self.connect('delete-event', self.window_destroy)
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        self.add(grid)

        label = Gtk.Label()
        label.set_text('Enter backup file name')

        self.entry = Gtk.Entry()
        self.entry.connect('activate', self.entered_text)

        self.existing_label = Gtk.Label()
        self.existing_label.set_text('')

        grid.attach(label, 0, 0, 1, 1)
        grid.attach(self.entry, 0, 1, 1, 1)
        grid.attach(self.existing_label, 0, 2, 1, 1)

        self.show_all()

    def entered_text(self, widget):
        filename = self.entry.get_text()
        full_path = user_path + os.sep + filename + '.TPX3'
        if os.path.isfile(full_path) == True:
            self.entry.set_text('')
            self.existing_label.set_text('File already exists')
        else:
            file = open(full_path, 'w')
            file_logger.write_backup(file = file)
            self.destroy()

    def window_destroy(self, widget, event = True):
        self.destroy()

class GUI_Main_Save_Equalisation_Input(Gtk.Window):
    def __init__(self):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'equalisations')

        Gtk.Window.__init__(self, title = 'Save Equalisation')
        self.connect('delete-event', self.window_destroy)
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        self.add(grid)

        label = Gtk.Label()
        label.set_text('Enter equalisation file name')

        self.entry = Gtk.Entry()
        self.entry.connect('activate', self.entered_text)

        self.existing_label = Gtk.Label()
        self.existing_label.set_text('')

        grid.attach(label, 0, 0, 1, 1)
        grid.attach(self.entry, 0, 1, 1, 1)
        grid.attach(self.existing_label, 0, 2, 1, 1)

        self.show_all()

    def entered_text(self, widget):
        equal_path = self.entry.get_text()
        full_path = user_path + os.sep + equal_path + '.h5'
        if os.path.isfile(full_path) == True:
            self.entry.set_text('')
            self.existing_label.set_text('File already exists')
        else:
            current_equal = TPX3_datalogger.read_value(name = 'Equalisation_path')
            copy(current_equal, full_path)
            self.destroy()

    def window_destroy(self, widget, event = True):
        self.destroy()

class GUI_Main_Save_Mask_Input(Gtk.Window):
    def __init__(self):

        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'masks')

        Gtk.Window.__init__(self, title = 'Save Mask')
        self.connect('delete-event', self.window_destroy)
        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        self.add(grid)

        label = Gtk.Label()
        label.set_text('Enter mask file name')

        self.entry = Gtk.Entry()
        self.entry.connect('activate', self.entered_text)

        self.existing_label = Gtk.Label()
        self.existing_label.set_text('')

        grid.attach(label, 0, 0, 1, 1)
        grid.attach(self.entry, 0, 1, 1, 1)
        grid.attach(self.existing_label, 0, 2, 1, 1)

        self.show_all()

    def entered_text(self, widget):
        mask_path = self.entry.get_text()
        full_path = user_path + os.sep + mask_path + '.h5'
        if os.path.isfile(full_path) == True:
            self.entry.set_text('')
            self.existing_label.set_text('File already exists.')
        else:
            current_equal = TPX3_datalogger.read_value(name = 'Mask_path')
            copy(current_equal, full_path)
            self.destroy()

    def window_destroy(self, widget, event = True):
        self.destroy()

class GUI_Main_Error(Gtk.Window):
    def __init__(self, title, text):
        Gtk.Window.__init__(self, title = title)
        self.connect('delete-event', self.window_destroy)

        self.input_window = None

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        self.add(grid)

        self.ok_button = Gtk.Button(label = 'Ok')
        self.ok_button.connect('clicked', self.on_ok_button_clicked)
        self.label1 = Gtk.Label()
        self.label1.set_text(' ')
        self.label2 = Gtk.Label()
        self.label2.set_text(text)
        self.label3 = Gtk.Label()
        self.label3.set_text(' ')

        grid.attach(self.label1, 0, 0, 10, 1)
        grid.attach(self.label2, 1, 1, 9, 1)
        grid.attach(self.label3, 0, 2, 10, 1)
        grid.attach(self.ok_button, 9, 3, 2, 1)

        self.show_all()

    def on_ok_button_clicked(self, widget):
        self.destroy()

    def window_destroy(self, widget, event):
        self.destroy()

class GUI_Plot_Box_close_all(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title = 'Close all')
        #self.set_decorated(False)
        self.connect('delete-event', self.window_destroy)

        grid = Gtk.Grid()
        grid.set_row_spacing(2)
        grid.set_column_spacing(10)
        self.add(grid)

        self.yes_button = Gtk.Button(label = 'Yes')
        self.yes_button.connect('clicked', self.on_yes_button_clicked)
        self.no_button = Gtk.Button(label = 'No')
        self.no_button.connect('clicked', self.on_no_button_clicked)
        label1 = Gtk.Label()
        label1.set_text('Close all plots?')

        grid.attach(label1, 0, 0, 2, 1)
        grid.attach(self.yes_button, 0, 1, 1, 1)
        grid.attach(self.no_button, 1, 1, 1, 1)

        self.show_all()

    def on_yes_button_clicked(self, widget):
        GUI.delete_all_plot_windows()
        self.destroy()

    def on_no_button_clicked(self, widget):
        self.destroy()

    def window_destroy(self, widget, event = True):
        self.destroy()

class GUI_Plot_Box(Gtk.Window):
    def __init__(self, plotname, figure, figure_width, figure_height):
        Gtk.Window.__init__(self, title = plotname)
        self.connect('delete-event', self.window_destroy)
        self.connect('button_press_event', self.window_on_button_press_event)
        canvas = FigureCanvas(figure)
        canvas.set_size_request(figure_width, figure_height)
        self.add(canvas)
        self.show_all()

    def window_on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            subw = GUI_Plot_Box_close_all()

    def window_destroy(self, widget, event = True):
        self.destroy()

class GUI_Main(Gtk.Window):
    def __init__(self):
        self.open = False
        current_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        png_path = os.path.join(current_path, 'UI' + os.sep + 'GUI' + os.sep + 'icon.png')
        Gtk.Window.__init__(self, title = 'TPX3 control')

        self.set_icon_from_file(png_path)
        self.connect('button_press_event', self.window_on_button_press_event)
        self.progress_value_queue = Queue()
        self.status_queue = Queue()
        self.hardware_scan_results = Queue()
        self.pixeldac_result = Queue()
        self.eq_result_path = Queue()
        self.plot_queue = Queue()
        self.data_queue = Queue()
        self.running_process = None
        self.iteration_symbol = False
        self.running_scan_idle = None
        self.hardware_scan_idle = None
        self.update_progress_idle = None
        self.init_done = False
        self.plot1_window_open = False
        self.converter_process = None
        self.plot1_window = None
        self.pipe_dest_conn, self.pipe_source_conn = Pipe(False)
        self.simulation_running = False
        self.simulator_process = None
        self.step_starttime = datetime.now()
        self.software_version = utils.get_software_version(git = False)
        self.firmware_version = 'x.x'
        self.plot_window_list = []

        self.grid = Gtk.Grid()
        self.add(self.grid)

        self.statusbar = Gtk.Statusbar()
        self.context_id = self.statusbar.get_context_id('Status Main')
        self.statusbar.push(self.context_id, 'Please initialize the hardware with "Hardware Init".')

        self.notebook = Gtk.Notebook()
        self.grid.add(self.notebook)
        self.grid.attach(self.statusbar, 0, 1, 1, 1)

        self.notebook.connect('switch-page', self.switch_notebook_page)

        self.statusstring4 = ''
        self.statusstring3 = ''
        self.statusstring2 = ''
        self.statusstring1 = ''

        #get last backup
        data = file_logger.read_backup()
        TPX3_datalogger.set_data(data)
        TPX3_datalogger.write_backup_to_yaml()
        TPX3_datalogger.write_value(name = 'software_version', value = self.software_version)
        conv_utils.setup_logging('INFO')


    #########################################################################################################
        ### Page 1
        page1 = Gtk.Box()
        page1_label = Gtk.Label()
        page1_label.set_text('Basic Funktion')
        self.notebook.append_page(page1, page1_label)
        page1.set_border_width(10)
        page1.grid = Gtk.Grid()
        page1.grid.set_row_spacing(2)
        page1.grid.set_column_spacing(10)
        page1.grid.set_column_homogeneous(True)
        page1.grid.set_row_homogeneous(True)
        page1.add(page1.grid)

        Space = Gtk.Label()
        Space.set_text('')

        self.PixelDACbutton = Gtk.Button(label = 'PixelDAC')
        self.PixelDACbutton.connect('clicked', self.on_PixelDACbutton_clicked)

        self.Equalbutton = Gtk.Button(label = 'Equalisation')
        self.Equalbutton.connect('clicked', self.on_Equalbutton_clicked)

        self.TOTCalibbutton = Gtk.Button(label = 'TOT Calibration')
        self.TOTCalibbutton.connect('clicked', self.on_TOTCalibbutton_clicked)

        self.THLCalibbutton = Gtk.Button(label = 'THL Calibration')
        self.THLCalibbutton.connect('clicked', self.on_THLCalibbutton_clicked)

        self.THLScanbutton = Gtk.Button(label = 'THL Scan')
        self.THLScanbutton.connect('clicked', self.on_THLScanbutton_clicked)

        self.TestpulsScanbutton = Gtk.Button(label = 'Testpuls Scan')
        self.TestpulsScanbutton.connect('clicked', self.on_TestpulsScanbutton_clicked)

        self.NoiseScanbutton = Gtk.Button(label = 'Noise Scan')
        self.NoiseScanbutton.connect('clicked', self.on_NoiseScanbutton_clicked)

        self.Runbutton = Gtk.Button(label = 'Start readout')
        self.Runbutton.connect('clicked', self.on_Runbutton_clicked)

        self.Startupbutton = Gtk.Button(label = 'Hardware Init')
        self.Startupbutton.connect('clicked', self.on_Startupbutton_clicked)

        self.Resetbutton = Gtk.Button(label = 'Default')
        self.Resetbutton.connect('clicked', self.on_Resetbutton_clicked)

        self.SetDACbutton = Gtk.Button(label = 'Set DACs')
        self.SetDACbutton.connect('clicked', self.on_SetDACbutton_clicked)

        self.AddSetbutton = Gtk.Button(label = 'Settings')
        self.AddSetbutton.connect('clicked', self.on_AddSetbutton_clicked)

        self.SetMaskbutton = Gtk.Button(label = 'Set Mask')
        self.SetMaskbutton.connect('clicked', self.on_SetMaskbutton_clicked)

        self.Infobutton = Gtk.Button(label = 'Info')
        self.Infobutton.connect('clicked', self.on_Infobutton_clicked)
        
        self.Run_Name_button = Gtk.Button(label = 'Run Name')
        self.Run_Name_button.connect('clicked', self.on_Run_Name_button_clicked)

        self.QuitCurrentFunctionbutton = Gtk.Button(label = 'Quit')
        self.QuitCurrentFunctionbutton.connect('clicked', self.on_QuitCurrentFunctionbutton_clicked)

        self.about_label = Gtk.Label()
        try:
            self.about_label.set_markup('<big>TPX3 GUI</big> \nSoftware version: ' + str(self.software_version) +
                                        '\nFirmware version: ' + str(self.firmware_version) +
                                        '\nGit branch: ' + str(utils.get_git_branch()) +
                                        '\nGit commit: ' + str(utils.get_git_commit()) +
                                        '\nGit date: ' + str(utils.get_git_date()) +
                                        '\n<small>GasDet Bonn 2019-2021</small>')
        except:
            self.about_label.set_markup('<big>TPX3 GUI</big> \nSoftware version: ' + str(self.software_version) + 
                                        '\nFirmware version: ' + str(self.firmware_version) + '\n<small>GasDet Bonn 2019-2021</small>')

        Status = Gtk.Frame()
        self.Statusbox = Gtk.Box(orientation = Gtk.Orientation.VERTICAL, spacing = 6)
        Status.add(self.Statusbox)
        self.progressbar = Gtk.ProgressBar()
        self.show_progress_text = False
        self.statuslabel = Gtk.Label()
        self.statuslabel2 = Gtk.Label()
        self.statuslabel3 = Gtk.Label()
        self.statuslabel4 = Gtk.Label()
        self.statuslabel5 = Gtk.Label()
        self.statuslabel6 = Gtk.Label()
        self.statuslabel7 = Gtk.Label()
        self.statuslabel.set_text('')
        self.statuslabel2.set_text('')
        self.statuslabel3.set_text('')
        self.statuslabel4.set_text('')
        self.statuslabel5.set_text('')
        self.statuslabel6.set_text('')
        self.statuslabel7.set_text('')
        self.statuslabel2.set_justify(Gtk.Justification.LEFT)
        self.statuslabel3.set_justify(Gtk.Justification.LEFT)
        self.statuslabel4.set_justify(Gtk.Justification.LEFT)
        self.statuslabel5.set_justify(Gtk.Justification.LEFT)
        self.statuslabel6.set_justify(Gtk.Justification.LEFT)
        self.statuslabel7.set_justify(Gtk.Justification.LEFT)
        self.Statusbox.add(self.statuslabel)
        self.Statusbox.add(self.statuslabel2)
        self.Statusbox.add(self.statuslabel3)
        self.Statusbox.add(self.statuslabel4)
        self.Statusbox.add(self.statuslabel5)
        self.Statusbox.add(self.statuslabel6)
        self.Statusbox.add(self.statuslabel7)
        self.Statusbox.pack_end(self.progressbar, True, True, 5)

        page1.grid.attach(self.Startupbutton, 0, 0, 2, 1)
        page1.grid.attach(self.PixelDACbutton, 0, 1, 2, 1)
        page1.grid.attach(self.Equalbutton, 0, 2, 2, 1)
        page1.grid.attach(self.TOTCalibbutton, 0, 3, 2, 1)
        page1.grid.attach(self.THLCalibbutton, 0, 4, 2, 1)
        page1.grid.attach(self.THLScanbutton, 0, 5, 2, 1)
        page1.grid.attach(self.TestpulsScanbutton, 0, 6, 2, 1)
        page1.grid.attach(self.NoiseScanbutton, 0, 7, 2, 1)
        page1.grid.attach(self.Runbutton, 0, 8, 2, 2)
        page1.grid.attach(Status, 2, 8, 12, 6)
        page1.grid.attach(Space, 0, 10, 2, 2)
        page1.grid.attach(self.Resetbutton, 0, 13, 2, 1)
        page1.grid.attach(self.about_label, 14, 0, 3, 3)
        page1.grid.attach(self.SetDACbutton, 14, 3, 3, 1)
        page1.grid.attach(self.AddSetbutton, 14, 4, 3, 1)
        page1.grid.attach(self.Infobutton, 14, 5, 3, 1)
        page1.grid.attach(self.Run_Name_button, 14, 6, 3, 1)
        page1.grid.attach(self.SetMaskbutton, 14, 7, 3, 1)
        page1.grid.attach(self.QuitCurrentFunctionbutton, 14, 13, 3, 1)


    #######################################################################################################
        ### Page 2 
        ChipName = 'Chip1'
        self.page2 = Gtk.Box()
        page2_label = Gtk.Label()
        page2_label.set_text(ChipName)
        self.notebook.append_page(self.page2, page2_label)
        self.page2.set_border_width(10)
        self.page2.grid = Gtk.Grid()
        self.page2.grid.set_row_spacing(10)
        self.page2.grid.set_column_spacing(10)
        self.page2.add(self.page2.grid)
        self.page2.space = Gtk.Label()
        self.page2.space.set_text('         ')
        self.page2.space1 = Gtk.Label()
        self.page2.space1.set_text('    ')

        self.plotbutton = Gtk.Button(label = 'Show Plot')
        self.simulationbutton = Gtk.Button(label = 'Start Simulation')
        self.plotbutton.connect('clicked', self.on_plotbutton_clicked)
        self.simulationbutton.connect('clicked', self.on_simulationbutton_clicked)
        self.page2.grid.attach(self.plotbutton, 0, 0, 1, 1)
        self.page2.grid.attach(self.simulationbutton, 0, 1, 1, 1)

        self.plotwidget = plotwidget(data_queue = self.data_queue)
        self.page2.pack_end(self.plotwidget.canvas, True, False, 0)
        self.page2.pack_end(self.page2.space, True, False, 0)
        self.page2.pack_end(self.page2.space1, True, False, 0)
        self.Tag2 = GLib.timeout_add(250, self.plotwidget.update_plot)

        self.init_done = True

    ################################################################################################### 
    ### Overall window event

    def window_on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3 and self.open == False:
            self.open = True
            self.settingwindow = GUI_Main_Settings()
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1 and self.open == True:
            self.settingwindow.window_destroy(widget = widget, event = event)

    def set_destroyed(self):
        self.open = False

    def switch_notebook_page(self, notebook, tab, index):
        self.on_notebook_page = index
        if self.init_done and (not self.plot1_window_open):
            if index == 1:
                self.Tag2 = GLib.timeout_add(250, self.plotwidget.update_plot)
                self.start_converter()
            elif index == 0:
                GLib.source_remove(self.Tag2)
                self.terminate_converter()


    ####################################################################################################
    ### Functions Page 1

    def on_PixelDACbutton_clicked(self, widget):
        subw = GUI_PixelDAC_opt()

    def on_Equalbutton_clicked(self, widget):
        subw = GUI_Equalisation()

    def on_TOTCalibbutton_clicked(self, widget):
        subw = GUI_ToT_Calib()

    def on_THLCalibbutton_clicked(self, widget):
        subw = GUI_Threshold_Calib()

    def on_THLScanbutton_clicked(self, widget):
        subw = GUI_Threshold_Scan()

    def on_TestpulsScanbutton_clicked(self, widget):
        subw = GUI_Testpulse_Scan()

    def on_NoiseScanbutton_clicked(self, widget):
        print('Function call: NoiseScan')

    def on_Runbutton_clicked(self, widget):
        subw = GUI_Run_Datataking()

    def on_Startupbutton_clicked(self, widget):
        self.Status_window_call(function = 'InitHardware')
        new_process = TPX3_multiprocess_start.process_call(function = 'ScanHardware', 
                                                            results = self.hardware_scan_results, 
                                                            progress = GUI.get_progress_value_queue(), 
                                                            status = GUI.get_status_queue(), 
                                                            plot_queue = GUI.plot_queue)
        self.set_running_process(running_process = new_process)
        self.set_quit_scan_label()
        self.hardware_scan_idle = GLib.timeout_add(250, self.update_status)

    def on_Resetbutton_clicked(self, widget):
        if not self.get_process_alive():
            TPX3_datalogger.set_data(config = TPX3_datalogger.default_config())
            TPX3_datalogger.write_backup_to_yaml()
            self.progressbar.hide()
            self.statuslabel.set_text('')
            self.statuslabel2.set_text('')
            self.statuslabel3.set_text('')
            self.statuslabel4.set_text('')
            self.statuslabel5.set_text('')
            self.statuslabel6.set_text('')
            self.statuslabel7.set_text('')
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
            self.progressbar.set_fraction(0.0)
            self.resize(1,1)
            self.write_statusbar('Default setting initialised')
        else:
            subw = GUI_Main_Error(title = 'Error', text = 'Process is running on the chip!')

    def on_SetDACbutton_clicked(self, widget):
        subw = GUI_SetDAC()

    def on_AddSetbutton_clicked(self, widget):
        subw = GUI_Additional_Settings()

    def on_SetMaskbutton_clicked(self, widget):
        global mask_window
        mask_window = GUI_Set_Mask()

    def on_Infobutton_clicked(self, widget):
        Info_subw = GUI_Additional_Information()
        
    def on_Run_Name_button_clicked(self, widget):
        Info_subw = GUI_Set_Run_Name()

    def on_QuitCurrentFunctionbutton_clicked(self, widget):
        self.progressbar.hide()
        self.statuslabel.set_text('')
        self.statuslabel2.set_text('')
        self.statuslabel3.set_text('')
        self.statuslabel4.set_text('')
        self.statuslabel5.set_text('')
        self.statuslabel6.set_text('')
        self.statuslabel7.set_text('')
        self.statusstring4 = ''
        self.statusstring3 = ''
        self.statusstring2 = ''
        self.statusstring1 = ''
        self.progressbar.set_fraction(0.0)
        self.progressbar.set_show_text(False)
        self.resize(1,1)
        if self.running_process == None: 
            file_logger.write_backup(file = file_logger.create_file())
            self.terminate_simulator()
            self.terminate_converter()
            Gtk.main_quit()
        elif not self.running_process.is_alive():
            if not self.update_progress_idle == None:
                GLib.source_remove(self.update_progress_idle)
                self.update_progress_idle = None
                while not self.status_queue.empty():
                    self.status_queue.get()
                while not self.progress_value_queue.empty():
                    self.progress_value_queue.get()
            if not self.hardware_scan_idle == None:
                GLib.source_remove(self.hardware_scan_idle)
                self.hardware_scan_idle = None
                while(not self.hardware_scan_results.empty()):
                    self.hardware_scan_results.get()
            if not self.running_scan_idle == None:
                GLib.source_remove(self.running_scan_idle)
                self.running_scan_idle = None
                while(not self.pixeldac_result.empty()):
                    self.pixeldac_result.get()
                while(not self.eq_result_path.empty()):
                    self.eq_result_path.get()
                while(not self.plot_queue.empty()):
                    self.plot_queue.get()
            self.QuitCurrentFunctionbutton.set_label('Quit')
            self.running_process = None

        else:
            self.running_process.terminate()
            if not self.update_progress_idle == None:
                GLib.source_remove(self.update_progress_idle)
                self.update_progress_idle = None
                while not self.status_queue.empty():
                    self.status_queue.get()
                while not self.progress_value_queue.empty():
                    self.progress_value_queue.get()
            if not self.hardware_scan_idle == None:
                GLib.source_remove(self.hardware_scan_idle)
                self.hardware_scan_idle = None
                while(not self.hardware_scan_results.empty()):
                    self.hardware_scan_results.get()
            if not self.running_scan_idle == None:
                GLib.source_remove(self.running_scan_idle)
                self.running_scan_idle = None
                while(not self.pixeldac_result.empty()):
                    self.pixeldac_result.get()
                while(not self.eq_result_path.empty()):
                    self.eq_result_path.get()
                while(not self.plot_queue.empty()):
                    self.plot_queue.get()
            self.QuitCurrentFunctionbutton.set_label('Quit')
            self.running_process = None

    def Status_window_call(self, function = 'default', subtype = '', lowerTHL = 0, upperTHL = 0, iterations = 0, n_injections = 0, n_pulse_heights = 0, statusstring = '', progress = 0):
        if function == 'PixelDAC_opt':
            self.statuslabel.set_markup('<big><b>PixelDAC Optimisation</b></big>')
            self.progressbar.show()
            self.progressbar.set_fraction(progress)
            self.statuslabel2.set_text('From THL\u200A=\u200A' + str(lowerTHL) + ' to THL\u200A=\u200A' + str(upperTHL) + ' using ' + str(n_injections) + ' testpulses.')
            self.statuslabel3.set_text('Data is saved to: ' + self.make_run_name(scan_type = 'PixelDAC_opt'))
            self.statuslabel7.set_text(statusstring)
            self.show_progress_text = True
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
        elif function == 'Equalisation':
            self.statuslabel.set_markup('<big><b>' + subtype + '-based Equalisation</b></big>')
            self.progressbar.show()
            self.statuslabel2.set_text('From THL\u200A=\u200A' + str(lowerTHL) + ' to THL\u200A=\u200A' + str(upperTHL) + ' with ' + str(iterations) + ' iterations per step')
            if subtype == 'Noise':
                self.statuslabel3.set_text('Data is saved to: ' + self.make_run_name(scan_type = 'Equalisation'))
            elif subtype == 'Testpulse':
                self.statuslabel3.set_text('Data is saved to: ' + self.make_run_name(scan_type = 'Equalisation_charge'))
            self.statuslabel7.set_text(statusstring)
            self.progressbar.set_fraction(progress)
            self.show_progress_text = True
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
        elif function == 'ToT_Calib':
            self.statuslabel.set_markup('<big><b>ToT Calibration</b></big>')
            self.progressbar.show()
            self.statuslabel2.set_text('For testpulses ranging from ' + utils.print_nice(lowerTHL * 0.5) + '\u200AmV to ' + utils.print_nice(upperTHL * 0.5) + '\u200AmV with ' + str(iterations) + ' iterations per step')
            self.statuslabel3.set_text('Data is saved to: ' + self.make_run_name(scan_type = 'ToT_calib'))
            self.statuslabel7.set_text(statusstring)
            self.progressbar.set_fraction(progress)
            self.show_progress_text = True
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
        elif function == 'ThresholdScan':
            self.statuslabel.set_markup('<big><b>Threshold Scan</b></big>')
            self.progressbar.show()
            self.statuslabel2.set_text('From THL\u200A=\u200A' + str(lowerTHL) + ' to THL\u200A=\u200A' + str(upperTHL) + ' with ' + str(iterations) + ' iterations per step using ' + str(n_injections) + ' testpulses.')
            self.statuslabel3.set_text('Data is saved to: ' + self.make_run_name(scan_type = 'threshold_scan'))
            self.statuslabel7.set_text(statusstring)
            self.progressbar.set_fraction(progress)
            self.show_progress_text = True
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
        elif function == 'ThresholdCalib':
            self.statuslabel.set_markup('<big><b>Threshold Calibration</b></big>')
            self.progressbar.show()
            self.statuslabel2.set_text('Scanning ' + str(n_pulse_heights) + ' puls heights from THL\u200A=\u200A' + str(lowerTHL) + ' to THL\u200A=\u200A' + str(upperTHL) + ' with ' + str(iterations) + ' iterations per step using ' + str(n_injections) + ' testpulses.')
            self.statuslabel3.set_text('Data is saved to: ' + self.make_run_name(scan_type = 'threshold_calib'))
            self.statuslabel7.set_text(statusstring)
            self.progressbar.set_fraction(progress)
            self.show_progress_text = True
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
        elif function == 'InitHardware':
            self.statuslabel.set_markup('<big><b>Hardware Initialization</b></big>')
            self.progressbar.show()
            self.statuslabel2.set_text('Scanning over all FPGA and chip links.')
            self.statuslabel7.set_text(statusstring)
            self.progressbar.set_fraction(progress)
            self.show_progress_text = True
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
        elif function == 'TestpulsScan':
            self.statuslabel.set_markup('<big><b>Testpuls Scan</b></big>')
            self.progressbar.show()
            self.statuslabel2.set_text('For testpulses ranging from ' + utils.print_nice(lowerTHL * 0.5) + '\u200AmV to ' + utils.print_nice(upperTHL * 0.5) + '\u200AmV with ' + str(iterations) + ' iterations per step using ' + str(n_injections) + ' testpulses.')
            self.statuslabel3.set_text('Data is saved to: ' + self.make_run_name(scan_type = 'testpulse_scan'))
            self.statuslabel7.set_text(statusstring)
            self.progressbar.set_fraction(progress)
            self.show_progress_text = True
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
        elif function == 'Run':
            self.statuslabel.set_markup('<big><b>Run</b></big>')
            if upperTHL != 'Datataking ends on user quit.':
                self.progressbar.show()
            self.statuslabel2.set_text('Run datataking for ' + str(lowerTHL) + '\u200As. ' + upperTHL + '.')
            self.statuslabel3.set_text('Data is saved to: ' + self.make_run_name(scan_type = 'data_take'))
            self.statuslabel7.set_text(statusstring)
            self.progressbar.set_fraction(progress)
            self.show_progress_text = False
            self.statusstring4 = ''
            self.statusstring3 = ''
            self.statusstring2 = ''
            self.statusstring1 = ''
        elif function == 'status':
            if statusstring == 'iteration_symbol':
                self.iteration_symbol = True
                self.statusstring4 = self.statusstring3
                self.statusstring3 = self.statusstring2
                self.statusstring2 = self.statusstring1
                self.step_starttime = datetime.now()
                runtime = datetime.now() - self.step_starttime
                self.progressbar.set_text(str(int(0)) + ' %, Step time ' + utils.strfdelta(runtime, '%M:%S') + ' / ' + 'xx:xx')
                return
            elif statusstring == 'iteration_finish_symbol':
                self.iteration_symbol = False
                return
            if self.iteration_symbol == True:
                self.statusstring1 = statusstring
            else:
                self.statusstring4 = self.statusstring3
                self.statusstring3 = self.statusstring2
                self.statusstring2 = self.statusstring1
                self.statusstring1 = statusstring
                self.step_starttime = datetime.now()
                runtime = datetime.now() - self.step_starttime
                self.progressbar.set_show_text(self.show_progress_text)
                self.progressbar.set_text(str(int(0)) + ' %, Step time ' + utils.strfdelta(runtime, '%M:%S') + ' / ' + 'xx:xx')
            self.statuslabel4.set_text(self.statusstring4)
            self.statuslabel5.set_text(self.statusstring3)
            self.statuslabel6.set_text(self.statusstring2)
            self.statuslabel7.set_text(self.statusstring1)
        elif function == 'progress':
            self.progressbar.set_fraction(progress)
        elif function == 'default':
            self.statuslabel.set_text('Error: Call without functionname')
        else:
            self.statuslabel.set_text('Error: ' + function + ' is not known!')

    def get_progress_bar(self):
        return self.progressbar

    def write_statusbar(self, status):
        self.statusbar.push(self.context_id, str(status))

    def get_progress_value_queue(self):
        return self.progress_value_queue

    def get_status_queue(self):
        return self.status_queue

    def set_quit_scan_label(self):
        self.QuitCurrentFunctionbutton.set_label('Quit Scan')

    def set_running_process(self, running_process):
        self.running_process = running_process
        self.running_scan_idle = GLib.timeout_add(500, self.update_scan)
        self.update_progress_idle = GLib.timeout_add(100, self.update_progress)

    def get_process_alive(self):
        if self.running_process == None:
            return False
        else:
            return self.running_process.is_alive()

    def get_simulation_alive(self):
        if self.simulator_process == None:
            return False
        else:
            return self.simulator_process.is_alive()

    def delete_all_plot_windows(self):
        while self.plot_window_list:
            plot_window = self.plot_window_list.pop()
            plot_window.window_destroy(widget = 'GUI')

    def update_progress(self):
        while not self.progress_value_queue.empty():
            fraction = self.progress_value_queue.get()
            self.progressbar.set_fraction(fraction)
            runtime = datetime.now() - self.step_starttime
            estimate = runtime / fraction - runtime
            if runtime.seconds < 3600 and estimate.seconds < 3600:
                self.progressbar.set_text(str(int(fraction * 100)) + ' %, Step time ' + utils.strfdelta(runtime, '%M:%S') + ' / ' + utils.strfdelta(estimate, '%M:%S'))
            elif runtime.seconds >= 3600 and estimate.seconds < 3600:
                self.progressbar.set_text(str(int(fraction * 100)) + ' %, Step time ' + utils.strfdelta(runtime, '%H:%M:%S') + ' / ' + utils.strfdelta(estimate, '%M:%S'))
            elif estimate.seconds >= 3600 and runtime.seconds < 3600: 
                self.progressbar.set_text(str(int(fraction * 100)) + ' %, Step time ' + utils.strfdelta(runtime, '%M:%S') + ' / ' + utils.strfdelta(estimate, '%H:%M:%S'))
            else:
                self.progressbar.set_text(str(int(fraction * 100)) + ' %, Step time ' + utils.strfdelta(runtime, '%H:%M:%S') + ' / ' + utils.strfdelta(estimate, '%H:%M:%S'))
        while not self.status_queue.empty():
            statusstring = self.status_queue.get()
            if statusstring == 'Scan finished':
                self.QuitCurrentFunctionbutton.set_label('Quit')
                self.show_progress_text = False
                self.progressbar.set_show_text(self.show_progress_text)
            self.Status_window_call(function = 'status', statusstring = statusstring)
        if self.progress_value_queue.empty() and self.status_queue.empty() and not self.get_process_alive():
            GLib.source_remove(self.update_progress_idle)
            self.update_progress_idle = None
        return True

    def update_status(self):
        if not self.hardware_scan_results.empty():
            Chip_List = self.hardware_scan_results.get()
            for n in range(0,2):
                if n == 0 and Chip_List:
                    self.firmware_version = Chip_List.pop(0)
                    TPX3_datalogger.write_value(name = 'firmware_version', value = self.firmware_version)
                    try:
                        self.about_label.set_markup('<big>TPX3 GUI</big> \nSoftware version: ' + str(self.software_version) +
                                                    '\nFirmware version: ' + str(self.firmware_version) +
                                                    '\nGit branch: ' + str(utils.get_git_branch()) +
                                                    '\nGit commit: ' + str(utils.get_git_commit()) +
                                                    '\nGit date: ' + str(utils.get_git_date()) +
                                                    '\n<small>GasDet Bonn 2019-2021</small>')
                    except:
                        self.about_label.set_markup('<big>TPX3 GUI</big> \nSoftware version: ' + str(self.software_version) + 
                                                    '\nFirmware version: ' + str(self.firmware_version) + '\n<small>GasDet Bonn 2019-2021</small>')
                elif Chip_List:
                    name = 'Chip' + str(n - 1) + '_name'
                    TPX3_datalogger.write_value(name = name, value = Chip_List.pop(0))
                else:
                    name = 'Chip' + str(n - 1) + '_name'
                    TPX3_datalogger.write_value(name = name, value = [None])
            statusstring = 'Connected to '
            for n, Chipname in enumerate(TPX3_datalogger.get_chipnames()):
                number_of_links = TPX3_datalogger.get_links(chipname = Chipname)
                if number_of_links == 1:
                    statusstring += Chipname + ' (' + str(number_of_links) + ' active link)'
                else:
                    statusstring += Chipname + ' (' + str(number_of_links) + ' active links)'
                if n == 0:
                    self.notebook.set_tab_label_text(self.page2, Chipname)
            self.statusbar.push(self.context_id, statusstring)
        if self.hardware_scan_results.empty() and not self.get_process_alive():
            GLib.source_remove(self.hardware_scan_idle)
            self.hardware_scan_idle = None
        return True

    def update_scan(self):
        if not self.pixeldac_result.empty():
            TPX3_datalogger.write_value(name = 'Ibias_PixelDAC', value = self.pixeldac_result.get())
            TPX3_datalogger.write_to_yaml(name = 'Ibias_PixelDAC')
        if not self.eq_result_path.empty():
            TPX3_datalogger.write_value(name = 'Equalisation_path', value = self.eq_result_path.get())
        while not self.plot_queue.empty():
            fig, suffix = self.plot_queue.get()
            self.plot_from_figure(suffix, fig)
        if self.pixeldac_result.empty() and self.eq_result_path.empty() and self.plot_queue.empty() and not self.get_process_alive():
            GLib.source_remove(self.running_scan_idle)
            self.running_scan_idle = None
        return True

    ########################################################################################################################
    ### Functions Page2

    def on_plotbutton_clicked(self, widget):
        if not self.plot1_window_open:
            self.plot1_window_open = True
            GLib.source_remove(self.Tag2)
            self.plot1_window = GUI_Plot1(data_queue = self.data_queue)

    def on_simulationbutton_clicked(self, widget):
        if self.simulation_running == False:
            if self.get_process_alive():
                self.error_window = GUI_Main_Error(title = 'Error', text = 'Simulation can not be started during an active scan')
                return
            else:
                path, response = self.select_simulation_file()
                if response == Gtk.ResponseType.OK:
                    self.start_simulator(path)
                else:
                    return
            self.simulationbutton.set_label('Stop Simulation')
            self.simulation_running = True
        else:
            self.terminate_simulator()
            self.simulationbutton.set_label('Start Simulation')
            self.simulation_running = False

    def select_simulation_file(self):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')

        simulation_dialog = Gtk.FileChooserDialog(title = 'Please choose a HDF5 file for simulation', parent = self, action = Gtk.FileChooserAction.OPEN)
        simulation_dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK, )
        simulation_dialog.set_current_folder(user_path)
        simulation_dialog.set_local_only(True)

        filter_simulation = Gtk.FileFilter()
        filter_simulation.set_name('Simulation files')
        filter_simulation.add_pattern('*.h5')
        simulation_dialog.add_filter(filter_simulation)

        response = simulation_dialog.run()
        path = simulation_dialog.get_filename()

        simulation_dialog.destroy()

        return path, response

    ########################################################################################################################
    ### Function plot

    def plot_from_figure(self, plotname, figure, figure_width = 500, figure_height = 400):
        plotw = GUI_Plot_Box(plotname, figure, figure_width, figure_height)
        self.plot_window_list.append(plotw)

    ########################################################################################################################
    ### General functions

    def terminate_converter(self):
        if self.plot1_window_open:
            self.plot1_window.stop_idle_job()
        elif self.on_notebook_page == 1:
            GLib.source_remove(self.Tag2)
        if self.converter_process == None:
            return
        self.pipe_source_conn.send(False)
        time.sleep(0.1)
        while(not self.data_queue.empty()):
            self.data_queue.get(False)
            time.sleep(0.001)
        self.converter_process.terminate()

    def start_converter(self):
        current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cm = ConverterManager(configuration = current_path + os.sep + 'tpx3_monitor.yaml', data_queue = self.data_queue, symbol_pipe = self.pipe_dest_conn)
        self.converter_process = Process(target = cm.start)
        self.pipe_source_conn.send(True)
        self.converter_process.start()

    def closed_plot1(self):
        self.plot1_window_open = False
        if self.on_notebook_page == 0:
            self.terminate_converter()
        elif self.on_notebook_page == 1:
            self.Tag2 = GLib.timeout_add(250, self.plotwidget.update_plot)
        else:
            self.terminate_converter()

    def terminate_simulator(self):
        if self.simulator_process == None:
            return
        self.simulator_process.terminate()

    def start_simulator(self, path):
        current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sim = ProducerSimManager(configuration = current_path + os.sep + 'tpx3_monitor.yaml', path = path, loglevel = 'INFO', delay = 0.1, kind = 'tpx3_sim', name = 'TPX3')
        self.simulator_process = Process(target = sim.start)
        self.simulator_process.start()
    
    def make_run_name(self, scan_type):
        if TPX3_datalogger.read_value(name = 'Run_name') == None:
            run_name = str(scan_type) + '_' + time.strftime('%Y-%m-%d_%H-%M-%S')
        elif TPX3_datalogger.read_value(name = 'Run_name') in ['False', 'false', '', 'None', 'none']:
            run_name = (scan_type) + '_' + time.strftime('%Y-%m-%d_%H-%M-%S')
        else:
            run_name = (scan_type) + '_' + TPX3_datalogger.read_value(name = 'Run_name')
        return run_name

def quit_procedure(gui):
    GUI.on_QuitCurrentFunctionbutton_clicked(widget = None)
    time.sleep(0.75)
    file_logger.write_backup(file = file_logger.create_file())
    GUI.terminate_simulator()
    GUI.terminate_converter()
    Gtk.main_quit()

def GUI_start():
    GUI.connect('destroy', quit_procedure)
    GUI.show_all()
    GUI.progressbar.hide()
    Gtk.main()

GUI = GUI_Main()

def main():
    GUI.connect('destroy', quit_procedure)
    GUI.show_all()
    GUI.progressbar.hide()
    Gtk.main()

if __name__ == '__main__':
    main()
