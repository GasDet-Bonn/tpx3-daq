#JSON
import json
import os
import time
import glob


class file_logger(object):
    #This class contains the functions to write the setting to a file which will then be call next time the GUI is started
    
    def create_file(filename = None):
    #Creates backup folder and file if not existing
        if filename == None:
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

    def write_backup(file, data = None):
        #writes the backup to the file given
        file = file
        if data == None:
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
                file = max(list_of_files, key=os.path.getctime)
                return file
        file = file_logger.create_default_file()
        return file
            
    def create_default_file():
        filename = "default.GUI"
        if os.path.isdir("backup") == False:
            os.mkdir("backup")
        default_file = open("backup/" + filename, "w")
        json.dump(datalogger.default_config(), default_file)
        file = "backup/" + filename
        return file
        
    def get_backup_value(type, file = None):
        backup_data = file_logger.read_backup(file)
        if datalogger.type_valid(type) == True:
            value = backup_data[type]
            return value
        print("Error: Unknown data type")
        return False    
        
        
        
class TPX3_data_logger(object):
 
#here the data will be logged while the programm is running this function is called as global
    def __init__(self):
        self.config_keys = ['plottype', 'colorsteps', 'integration_length', 'color_depth', 'Ibias_Preamp', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine', 'Vthreshold_coarse', 'Ibias_DiscS1', 'Ibias_DiscS2', 'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl', 'Equalisation_path']
        self.data = self.default_config()
    
    def default_config(self):
        return {'plottype' : 'normal', 
                'colorsteps' : 50, 
                'integration_length' : 500, 
                'color_depth' : 10, 
                'Ibias_Preamp' : 127, 
                'VPreamp_NCAS' : 127, 
                'Ibias_Ikrum' : 5, 
                'Vfbk' : 127, 
                'Vthreshold_fine' : 255, 
                'Vthreshold_coarse' : 7, 
                'Ibias_DiscS1' : 127, 
                'Ibias_DiscS2' : 127, 
                'Ibias_PixelDAC' : 127, 
                'Ibias_TPbufferIn' : 127, 
                'Ibias_TPbufferOut' : 127, 
                'VTP_coarse' : 127,
                'VTP_fine' : 255, 
                'Ibias_CP_PLL' : 127, 
                'PLL_Vcntrl' : 127, 
                'Equalisation_path' : None}
        
    def is_valid(self, config):
        if not isinstance(config, dict):
            # depending on impl may also just return False
            raise TypeError("Invalid type for configuration")
        return sorted(list(config)) == sorted(self.config_keys)

    def type_valid(self, type):
        for key in self.config_keys:
            if key == type:
                return True
        return False
        
    def write_data(self, type, value):
        if self.type_valid(type) == True:
            self.data[type] = value
            return True
        print("Error: Unknown data type")
        return False
        
    def read_value(self, type):
        if self.type_valid(type) == True:
            value = self.data[type]
            return value
        print("Error: Unknown data type")
        return False    
        
    def get_data(self):
        return self.data

    def set_data(self, config):
        if self.is_valid(config):
            self.data = config    
            return True
        print("Error: Corrupted data")
        return False
        
datalogger = TPX3_data_logger()
    