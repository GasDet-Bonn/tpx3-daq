import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from multiprocessing import Process, Queue, Pipe
import signal
import sys
import time
from UI.GUI.GUI import GUI_Plot1
from UI.GUI.converter import utils as conv_utils
from UI.GUI.converter.converter_manager import ConverterManager


class CLI_Plot():
    def __init__(self, **kwargs):
        signal.signal(signal.SIGTERM, self.window_destroy)

        self.converter_process = None
        self.data_queue = Queue()
        self.pipe_dest_conn, self.pipe_source_conn = Pipe(False)

        self.plottype = None
        self.integration_length = None
        self.color_depth = None
        self.colorsteps = None

        for key, v in kwargs.items():
            if key == 'plottype':
                self.plottype = v
            elif key == 'integration_length':
                self.integration_length = int(v)
            elif key == 'color_depth':
                self.color_depth = int(v)
            elif key == 'colorsteps':
                self.colorsteps = int(v)

        self.start_converter()

        self.Plot_window = GUI_Plot1(data_queue = self.data_queue, 
                                        startet_from = 'CLI', 
                                        plottype = self.plottype, 
                                        integration_length = self.integration_length, 
                                        color_depth = self.color_depth, 
                                        colorsteps = self.colorsteps)

    def start_converter(self):
        conv_utils.setup_logging('INFO')
        cm = ConverterManager(configuration = 'tpx3_monitor.yaml', data_queue = self.data_queue, symbol_pipe = self.pipe_dest_conn)
        self.converter_process = Process(target=cm.start, name = 'TPX3 Converter')
        self.pipe_source_conn.send(True)
        self.converter_process.start()

    def stop_converter(self):
        self.pipe_source_conn.send(False)
        time.sleep(0.1)
        if self.data_queue != None:
            while(not self.data_queue.empty()):
                self.data_queue.get(False)
                time.sleep(0.001)
        time.sleep(0.5)
        self.converter_process.terminate()

    def window_destroy(self, event, widget):
        self.stop_converter()
        self.Plot_window.window_destroy(event = 'destroy', widget = 'CLI')
        Gtk.main_quit()


GUI = CLI_Plot(**dict(arg.split('=') for arg in sys.argv[1:]))
Gtk.main()