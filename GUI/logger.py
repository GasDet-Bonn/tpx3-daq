#JSON
import json
import os
import time
import glob


class file_logger(object):
	#This class contains the functions to write the setting to a fil wich will then be call next time the GUI is started
	
	def create_file():
	#Creates backup folder and file if not existing
		filename = "backup_" + time.strftime("%Y_%m_%d") + ".GUI"
		if os.path.isdir("backup") == False:
			os.mkdir("backup")
			if os.path.isfile("backup/" + filename) == False:
				backup_file = open("backup/" + filename, "w")
				return backup_file
			elif os.path.isfile("backup/" + filename) == True:
				backup_file = open("backup/" + "1" + filename, "w")
				return backup_file
		elif os.path.isdir("backup") == True:
			if os.path.isfile("backup/" + filename) == False:
				backup_file = open("backup/" + filename, "w")
				return backup_file
			elif os.path.isfile("backup/" + filename) == True:
				backup_file = open("backup/" + "1" + filename, "w")
				return backup_file

	def write_backup(file):
		#writes the backup to the file given
		file = file
		data = datalogger.get_data()
		json.dump(data, file)
		
	def read_backup(file = None):
		#reads backup and returns the data
		if file == None:
			#Get most recent file
			file = file_logger.get_newest_backup_file()
			data = json.load(open(file, "r"))
			return data
		else:
			file = file
			if os.path.isfile(file) == True:
				data = json.load(open(file, "r"))
				print(data)
				return data
			else:
				print("Error! File does not exist")
				return False
				
	def get_newest_backup_file():
		if os.path.isdir("backup") == True:
			list_of_files = glob.glob("backup/*.GUI")
			if list_of_files:
				print(list_of_files)
				file = max(list_of_files, key=os.path.getctime)
				return file
		file = file_logger.create_default_file()
		return file
			
	def create_default_file():
		filename = "default.GUI"
		data = [["plottype", "normal"], ["colorsteps", 50], ["integration_length", 500], ["color_depth", 10]]
		if os.path.isdir("backup") == False:
			os.mkdir("backup")
		default_file = open("backup/" + filename, "w")
		json.dump(data, default_file)
		file = "backup/" + filename
		return file
		
	def get_backup_value(type):
		backup_data = file_logger.read_backup()
		for x, data in enumerate(backup_data):
			if type in data:
				value = backup_data[x][1]
				return value
		print("Error: Unknown data type")
		return False
		
class data_logger(object):
 
#here the data will be logged while the programm is running this function should be calles as global
	def __init__(self):
		self.data = [["plottype", "normal"], ["colorsteps", 50], ["integration_length", 500], ["color_depth", 10]]
	def write_data(self, type, value):
		for x, data in enumerate(self.data):
			if type in data:
				self.data[x][1] = value
				return True
		print("Error: Unknown data type")
		return False		
	def get_data(self):
		return self.data
		

datalogger = data_logger()
	
