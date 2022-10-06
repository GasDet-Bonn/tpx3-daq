#import gi

import numpy as np
from matplotlib.figure import Figure
import matplotlib.cm as cm
from matplotlib.backends.backend_gtk3agg import (FigureCanvasGTK3Agg as FigureCanvas)
from matplotlib.colors import ListedColormap

class plotwidget(object):
    def __init__(self, data_queue):
        self.plottype           = 'normal'
        self.fig                = Figure(figsize = (5, 5), dpi = 100)
        self.cmap               = self.fading_colormap(5)
        self.integration_length = 500
        self.color_depth        = 10
        self.data_queue         = data_queue
        self.canvas             = FigureCanvas(self.fig)
        self.canvas.set_size_request(500, 500)
        self.num_plots          = 0

    def init_figure(self, chip_links):
        # Since InitHardware can be pressed multiple times and triggers init_figure
        # we simply surpress this function, if plots already exist
        if self.num_plots != 0:
            for axis in self.plots:
                axis.remove()
            for scatter in self.scatter:
                scatter.remove()

        self.num_plots = len(chip_links)
        self.chip_list = [chip for chip in chip_links]
        self.plots     = []
        self.scatter   = []
        
        # Adjust size of figures depending on the number of plots
        if self.num_plots > 4:
            self.num_rows = 3
            self.fig.set_size_inches(10., 10., forward=True)
            self.canvas.set_size_request(1000, 1000)
        elif self.num_plots > 1:
            self.num_rows = 2
            self.fig.set_size_inches(9., 9., forward=True)
            self.canvas.set_size_request(900, 900)
        else:
            self.num_rows = 1
            self.canvas.set_size_request(600, 600)

        self.x_vals             = [np.empty(0, np.uint16)]*self.num_plots
        self.y_vals             = [np.empty(0, np.uint16)]*self.num_plots
        self.t_vals             = [np.empty(0, np.uint16)]*self.num_plots
        self.intensity          = [np.empty(0, np.uint16)]*self.num_plots
        self.length             = [np.empty(0, np.uint16)]*self.num_plots
        self.i                  = 0
        self.occupancy_array    = [np.array([[0, 0, 0]])]*self.num_plots
        self.occ_length         = [0]*self.num_plots
        self.j                  = 0
        self.old_elements       = [np.array([[0, 0]])]*self.num_plots
        self.occupancy          = [[]]*self.num_plots

        for chip in range(self.num_plots):
            ax = self.fig.add_subplot(eval(f'{self.num_rows}{self.num_rows}{chip+1}'), aspect='equal')
            ax.set_xlabel('X', size = 8)
            ax.set_ylabel('Y', size = 8)
            ax.set_title(f'Chip: {self.chip_list[chip]}', size = 8)
            ax.axis([0, 255, 0, 255])
            scatter_plot = ax.scatter(self.x_vals[chip], self.y_vals[chip], c = [], s = 1, marker = 's', cmap = self.cmap, vmin = 0, vmax = 1)

            self.plots.append(ax)
            self.scatter.append(scatter_plot)
            self.plots[chip].plot()
        
        self.fig.subplots_adjust(left = 0.1, top = 0.90)
        

    def fading_colormap(self, steps = 5):
        # This creates a fading colormap of 'steps' steps. Each step is more transparent,
        # so if plotted correctly the data appears to be fading out.
        if steps <= 0:
            self.colorsteps = 1
            print('ERROR: Minimum number of colorsteps is 1. Colorsteps have been set to 1.')
        else:
            self.colorsteps = steps

        i = 1
        viridis = cm.get_cmap('viridis', 256)
        newcmap = viridis(np.linspace(0, 1, 256))
        newmap1 = np.tile(newcmap, (self.colorsteps, 1))
        while(i<self.colorsteps):
            newmap1[(i - 1) * 256:(i * 256), -1] = np.linspace(i * 1 / self.colorsteps, i * 1 / self.colorsteps, 256)
            i = i + 1
        cmap = ListedColormap(newmap1)

        return cmap

    def get_new_vals(self):
        #Get values from Chip
        #t need to between 0 and 1 then the calculation 1 - (t / self.colorsteps) needs
        #to be done in order to distribute is correctly over the colormap
        x         = [np.empty(0, np.uint16)]*self.num_plots
        y         = [np.empty(0, np.uint16)]*self.num_plots
        t         = [np.empty(0, np.uint16)]*self.num_plots
        x_new     = [[]]*self.num_plots
        y_new     = [[]]*self.num_plots
        t_new     = [[]]*self.num_plots

        max_value = [0]*self.num_plots

        if not self.data_queue.empty():
            pixeldata = self.data_queue.get()
            for chip, chip_data in enumerate(pixeldata):
                x_new[chip] = chip_data[0]
                y_new[chip] = chip_data[1]
                t_new[chip] = chip_data[2]

            for chip in range(self.num_plots):
                x[chip] = np.append(x[chip], x_new[chip])
                y[chip] = np.append(y[chip], y_new[chip])
                t[chip] = np.append(t[chip], t_new[chip])
        
        for chip in range(self.num_plots):
            if len(t[chip]) > 0:
                self.t_vals[chip] = np.append(self.t_vals[chip], t[chip])
                max_value[chip]   = np.amax(self.t_vals[chip]) # This has to be changed to a more general way
                t[chip]           = t[chip]/max_value[chip]

        return x, y, t

    def update_plot(self):
        if self.num_plots == 0:
            return

        pixeldata = self.get_new_vals()
        new_xvals = pixeldata[0]
        new_yvals = pixeldata[1]
        new_tvals = pixeldata[2]

        #Plot the fading plot with new data.
        for chip in range(self.num_plots):
            self.x_vals[chip] = np.append(self.x_vals[chip], new_xvals[chip])
            self.y_vals[chip] = np.append(self.y_vals[chip], new_yvals[chip])
            self.length[chip] = np.append(self.length[chip], new_xvals[chip].size)

        #Cut plotting arrays to n_colorsteps Timeblocks
        if self.i < (self.colorsteps):
            self.i = self.i + 1

        elif self.i == (self.colorsteps):
            for chip in range(self.num_plots):
                number               = np.arange(self.length[chip][0])
                self.length[chip]    = np.delete(self.length[chip], 0)
                self.x_vals[chip]    = np.delete(self.x_vals[chip], number)
                self.y_vals[chip]    = np.delete(self.y_vals[chip], number)
                self.t_vals[chip]    = np.delete(self.t_vals[chip], number)
                self.intensity[chip] = np.delete(self.intensity[chip], number)

        elif self.i > (self.colorsteps):
            while self.i >= (self.colorsteps):
                for chip in range(self.num_plots):
                    number               = np.arange(self.length[chip][0])
                    self.length[chip]    = np.delete(self.length[chip], 0)
                    self.x_vals[chip]    = np.delete(self.x_vals[chip], number)
                    self.y_vals[chip]    = np.delete(self.y_vals[chip], number)
                    self.t_vals[chip]    = np.delete(self.t_vals[chip], number)
                    self.intensity[chip] = np.delete(self.intensity[chip], number)
                self.i = self.i-1

        for chip in range(self.num_plots):
            if np.c_[self.x_vals[chip], self.y_vals[chip]].size != 0:
                self.scatter[chip].set_offsets(np.c_[self.x_vals[chip], self.y_vals[chip]])
                self.intensity[chip] = np.concatenate((np.array(self.intensity[chip]) - (1 / self.colorsteps), new_tvals[chip]))
                self.scatter[chip].set_array(self.intensity[chip])
        
        self.canvas.draw()

        return True

    def update_occupancy_plot(self):
        new_xvals, new_yvals, new_tvals = self.get_new_vals()
        new_elements = np.c_[new_xvals, new_yvals]
        self.occ_length.append(new_elements.shape[0])
        self.old_elements = np.append(self.old_elements, new_elements, axis = 0)

        #count hited pixel
        for new_element in new_elements:
            pos = np.argwhere(np.all(self.occupancy_array[ : , :2] == new_element, axis = 1) == True)
            if pos.size == 0:
                # add new element
                self.occupancy_array = np.append(self.occupancy_array, [np.append(new_element, 1)], axis = 0)

            elif pos.size == 1:
                #increment element at pos
                x = pos[0, 0]
                self.occupancy_array[pos[0, 0], 2] = (self.occupancy_array[pos[0, 0], 2] + 1)

            else:
                print('Error')

        #remove hitted pixel
        if self.j <= (self.integration_length):
            self.j = self.j + 1

        elif self.j == (self.integration_length + 1):
            number = self.occ_length[0]
            self.occ_length.pop(0)
            k = 0
            while k < number:
                k = k + 1
                pos = np.argwhere(np.all(self.occupancy_array[ : , :2] == self.old_elements[1], axis = 1) == True)
                self.old_elements = np.delete(self.old_elements, 1, axis = 0)
                if self.occupancy_array[pos[0, 0], 2] == 1:
                    #Remove item if no count left
                    self.occupancy_array = np.delete(self.occupancy_array, pos[0, 0], axis = 0)

                elif self.occupancy_array[pos[0, 0], 2] > 1:
                    #decrement element at pos
                    self.occupancy_array[pos[0, 0], 2] = (self.occupancy_array[pos[0, 0], 2] - 1)

                else:
                    print('Error')

        elif self.j > (self.integration_length + 1):
            while self.j > (self.integration_length + 1):
                number = self.occ_length[0]
                self.occ_length.pop(0)
                k = 0
                while k < number:
                    k = k + 1
                    pos = np.argwhere(np.all(self.occupancy_array[ : , :2] == self.old_elements[1], axis = 1) == True)
                    self.old_elements = np.delete(self.old_elements, 1, axis = 0)
                    if self.occupancy_array[pos[0, 0], 2] == 1:
                        #Remove item if no count left
                        self.occupancy_array = np.delete(self.occupancy_array,pos[0, 0], axis = 0)

                    elif self.occupancy_array[pos[0, 0], 2] > 1:
                        #Decrement element at pos
                        self.occupancy_array[pos[0, 0], 2] = (self.occupancy_array[pos[0, 0], 2] - 1)

                    else:
                        print('Error')

                self.j = self.j - 1

        if self.occupancy_array.size > 3:
            self.scatter.set_offsets(self.occupancy_array[ : , :2])
            self.occupancy = self.occupancy_array[ : , 2: ]
            self.scatter.set_array(np.squeeze(self.occupancy))
            self.canvas.draw()

        return True

    def reset_occupancy(self):
        self.occupancy_array = np.array([[0, 0, 0]])
        self.occ_length = []
        self.j = 0
        self.old_elements = np.array([[0, 0]])
        self.occupancy = []

        return True

    def change_colormap(self, colormap, vmin = 0, vmax = 1):
        
        self.cmap = colormap
        vmin      = vmin
        vmax      = vmax
        if self.plottype == 'occupancy':
            self.color_depth = vmax

        for chip in range(self.num_plots):
            x_vals    = []
            y_vals    = []
            self.plots[chip].remove()
            self.plots[chip] = self.fig.add_subplot(111, aspect='equal')
            self.plots[chip].set_xlabel('X', size = 12)
            self.plots[chip].set_ylabel('Y', size = 12)
            self.plots[chip].axis([0, 255, 0, 255])
            self.scatter[chip] = self.plots[chip].scatter(x_vals, y_vals, c = [], s = 1, marker = 's', cmap = self.cmap, vmin = vmin, vmax = vmax)
            self.plots[chip].plot()

        return True

    def get_iteration_depth(self,function = 'normal'):
        function = function
        if function == 'normal':
            return self.colorsteps

        elif function == 'occupancy':
            return self.integration_length

        elif function == 'occupancy.color':
            return self.color_depth

        else:
            print('Unknown argument. Use "normal", "occupancy" or "occupancy.color')
            return False

    def get_plottype(self):
        return self.plottype

    def set_plottype(self, plottype):
        self.plottype = plottype
        return True

    def set_occupancy_length(self, length):
        self.integration_length = length
        return True

    def set_color_depth(self, color_depth):
        self.color_depth = color_depth
        return True

    def set_color_steps(self, color_steps):
        self.colorsteps = color_steps
        return True
