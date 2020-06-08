#import gi

#gi.require_version("Gtk", "3.0")
#from gi.repository import Gtk
#from gi.repository import GObject
import numpy as np
from matplotlib.figure import Figure
from numpy import arange, pi, random, linspace
import matplotlib.cm as cm
from matplotlib.backends.backend_gtk3agg import (FigureCanvasGTK3Agg as FigureCanvas)
from matplotlib.colors import ListedColormap, LinearSegmentedColormap

class plotwidget2(object):#For tests
	def __init__(self):
		self.active=True
		self.fig = Figure(figsize=(5,5), dpi=100)
		self.ax = self.fig.add_subplot(111, projection='polar')
		
		self.canvas = FigureCanvas(self.fig)
		self.canvas.set_size_request(400,400)

		N = 20
		theta = linspace(0.0, 2 * pi, N, endpoint=False)
		radii = 10 * random.rand(N)
		width = pi / 4 * random.rand(N)

		self.bars = self.ax.bar(theta, radii, width=width, bottom=0.0)
		for r, bar in zip(radii, self.bars):
			bar.set_facecolor(cm.jet(r / 10.))
			bar.set_alpha(0.5)
		self.ax.plot()
	
	def update_plot(self):
		print("upsate")
		self.ax.cla()
		N = 20
		theta = linspace(0.0, 2 * pi, N, endpoint=False)
		radii = 10 * random.rand(N)
		width = pi / 4 * random.rand(N)

		self.bars = self.ax.bar(theta, radii, width=width, bottom=0.0)

		for r, bar in zip(radii, self.bars):
			bar.set_facecolor(cm.jet(r / 10.))
			bar.set_alpha(0.5)
		self.canvas.draw()
		return True
		
class plotwidget(object):
	def __init__(self):
		self.plottype = "normal"
		self.fig = Figure(figsize = (5, 5), dpi = 100)
		self.ax = self.fig.add_subplot(111)
		self.ax.set_xlabel('X', size = 12)
		self.ax.set_ylabel('Y', size = 12)
		self.ax.axis([0, 255, 0, 255])
		self.x_vals = []
		self.y_vals = []
		self.t_vals = []
		self.intensity = []
		self.length = []
		self.i = 0
		self.occupancy_array = np.array([[0, 0, 0]])
		self.occ_length = []
		self.j = 0
		self.old_elements = np.array([[0, 0]])
		self.occupancy = []
		self.integration_length = 500
		self.color_depth = 10
		#self.scatter = self.ax.scatter(self.x_vals,self.y_vals, c=[], cmap=cm.viridis, vmin=0,vmax=10)
		cmap = self.fading_colormap(50)
		self.scatter = self.ax.scatter(self.x_vals, self.y_vals, c = [], cmap = cmap, vmin = 0,vmax = 1)

		self.canvas = FigureCanvas(self.fig)
		self.canvas.set_size_request(400, 400)
		
		self.ax.plot()
	
	def fading_colormap(self,steps = 50):
		self.colorsteps = steps
		i = 1
		viridis = cm.get_cmap("viridis", 256)
		newcmap = viridis(np.linspace(0, 1, 256))
		newmap1 = np.tile(newcmap, (self.colorsteps, 1))
		while(i<self.colorsteps):
			newmap1[(i-1)*256:(i*256), -1] = np.linspace(i*1/self.colorsteps, i*1/self.colorsteps, 256)
			i = i + 1
		cmap = ListedColormap(newmap1)
		return cmap
		
	def get_new_vals(self):
		#Get values from Chip
		#t need to between 0 and 1 then the calculation 1-(t/self.colorsteps) needs 
		#to be done in order to distribute is correctly over the colormap
		
		n = np.random.randint(1,5)
		x = np.random.randint(255, size = n)
		y = np.random.randint(255, size = n)
		t = (1-(np.random.rand(n)/self.colorsteps))

		return list(x), list(y), list(t)

	def update_plot(self):
		self.plottype="normal"
		new_xvals, new_yvals, new_tvals = self.get_new_vals()
		self.x_vals.extend(new_xvals)
		self.y_vals.extend(new_yvals)
		self.t_vals.extend(new_tvals)
		self.length.append(len(new_xvals))
		
		#Cut plotting arrays to 50 Timeblocks
		if self.i < (self.colorsteps-1):
			self.i = self.i + 1
		elif self.i == (self.colorsteps-1):
			n = 0
			number = self.length[0]
			self.length.pop(0)
			while n < number:
				n = n+1
				self.x_vals.pop(0)
				self.y_vals.pop(0)
				self.t_vals.pop(0)
				self.intensity = np.delete(self.intensity, 0)
		elif self.i > (self.colorsteps-1):
			while self.i >= (self.colorsteps):
				n = 0
				number = self.length[0]
				self.length.pop(0)
				while n < number:
					
					n = n + 1
					self.x_vals.pop(0)
					self.y_vals.pop(0)
					self.t_vals.pop(0)
					self.intensity = np.delete(self.intensity, 0)
				self.i = self.i-1
		#Add to plot and change intensity
		self.scatter.set_offsets(np.c_[self.x_vals, self.y_vals])
		self.intensity = np.concatenate((np.array(self.intensity)-(1/self.colorsteps), new_tvals))
		#print (self.intensity)
		self.scatter.set_array(self.intensity)
		
		self.canvas.draw()
		
		return True
				
				
	def update_occupancy_plot(self):
		self.plottype = "occupancy"
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
				print("Error")
				
		#remove hited pixel
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
					#print("remove item if no count left")
					self.occupancy_array = np.delete(self.occupancy_array, pos[0, 0], axis = 0)
					
				elif self.occupancy_array[pos[0, 0], 2] > 1:
					#decrement element at pos
					self.occupancy_array[pos[0, 0], 2] = (self.occupancy_array[pos[0, 0], 2] - 1)
					
				else:
					print("Error")
					
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
						#print("remove item if no count left")
						self.occupancy_array = np.delete(self.occupancy_array,pos[0, 0], axis = 0)
						
					elif self.occupancy_array[pos[0, 0], 2] > 1:
						#decrement element at pos
						self.occupancy_array[pos[0, 0], 2] = (self.occupancy_array[pos[0, 0], 2] - 1)
						
					else:
						print("Error")
						
				self.j = self.j - 1
		
		self.scatter.set_offsets(self.occupancy_array[ : , :2])
		self.occupancy = self.occupancy_array[ : , 2: ]
		self.scatter.set_array(np.squeeze(self.occupancy))
		self.canvas.draw()
		#print("update")
		return True

	def reset_occupancy(self):
		self.occupancy_array = np.array([[0, 0, 0]])
		self.occ_length = []
		self.j = 0
		self.old_elements = np.array([[0, 0]])
		self.occupancy = []
		return True
		
	def change_colormap(self, colormap, vmin = 0, vmax = 1):
		x_vals = []
		y_vals = []
		cmap = colormap
		vmin = vmin
		vmax = vmax
		if self.plottype == "occupancy":
			self.color_depth = vmax
			
		self.ax.remove()
		self.ax = self.fig.add_subplot(111)
		self.ax.set_xlabel('X', size = 12)
		self.ax.set_ylabel('Y', size = 12)
		self.ax.axis([0, 255, 0, 255])
		self.scatter = self.ax.scatter(x_vals, y_vals, c = [], cmap = cmap, vmin = vmin,vmax = vmax)
		self.ax.plot()
		return True
	
	def get_iteration_depth(self,function = "normal"):
		function = function
		if function == "normal":
			return self.colorsteps
		elif function == "occupancy":
			return self.integration_length
		elif function == "occupancy.color":
			return self.color_depth
		else:
			print("Unknown argument. Use 'normal', 'occupancy' or 'occupancy.color'")
			return False
		
	def get_plottype(self):
		return self.plottype
		
	def set_occupancy_length(self, length):
		self.integration_length = length
		return True

	
