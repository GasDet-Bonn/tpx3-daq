#JSON
import json
import os
import time
import glob
import yaml


class file_logger(object):
    #This class contains the functions to write the setting to a file which will then be call next time the GUI is started
    
    def create_file(filename = None):
    #Creates backup folder and file if not existing
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        if filename == None:
            filename = "backup_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".TPX3"
        if os.path.isdir(user_path) == False:
            os.mkdir(user_path)
            if os.path.isfile(user_path + os.sep + filename) == False:
                backup_file = open(user_path + os.sep + filename, "w")
                return backup_file
        elif os.path.isdir(user_path) == True:
            if os.path.isfile(user_path + os.sep + filename) == False:
                backup_file = open(user_path + os.sep + filename, "w")
                return backup_file

    def write_backup(file, data = None):
        #writes the backup to the file given
        file = file
        if data == None:
            data = datalogger.get_data()
        json.dump(data, file)
        
    def read_backup(file = None):
        #reads backup and returns the data
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        if file == None:
            #Get most recent file
            file = file_logger.get_newest_backup_file()
            data = json.load(open(file, "r"))
            return data
        else:
            file = file
            if os.path.isfile(user_path + os.sep + file) == True:
                data = json.load(open(user_path + os.sep + file, "r"))
                print(data)
                return data
            else:
                print("Error! File does not exist")
                return False
                
    def get_newest_backup_file():
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        if os.path.isdir(user_path) == True:
            list_of_files = glob.glob(user_path + os.sep + "*.TPX3")
            if list_of_files:
                file = max(list_of_files, key=os.path.getctime)
                return file
        file = file_logger.create_default_file()
        return file
            
    def create_default_file():
        user_path = '~'
        user_path = os.path.expanduser(user_path)
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        filename = "default.TPX3"
        if os.path.isdir(user_path) == False:
            os.mkdir(user_path)
        default_file = open(user_path + os.sep + filename, "w")
        json.dump(datalogger.default_config(), default_file)
        file = user_path + os.sep + filename
        return file
        
    def get_backup_value(name, file = None):
        backup_data = file_logger.read_backup(file)
        if datalogger.name_valid(name) == True:
            value = backup_data[name]
            return value
        print("Error: Unknown data name")
        return False    
        
        
        
class TPX3_data_logger(object):
 
#here the data will be logged while the programm is running this function is called as global
    def __init__(self):
        self.config_keys = ['plottype', 'colorsteps', 'integration_length', 
                            'color_depth', 'Ibias_Preamp_ON', 'VPreamp_NCAS', 
                            'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine', 
                            'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 
                            'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 
                            'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl', 
                            'Equalisation_path', 'Polarity', 'Op_mode', 'Fast_Io_en']
        self.data = self.default_config()
    
    def default_config(self):
        return {'plottype' : 'normal', 
                'colorsteps' : 50, 
                'integration_length' : 500, 
                'color_depth' : 10, 
                'Ibias_Preamp_ON' : 127, 
                'VPreamp_NCAS' : 127, 
                'Ibias_Ikrum' : 5, 
                'Vfbk' : 127, 
                'Vthreshold_fine' : 255, 
                'Vthreshold_coarse' : 7, 
                'Ibias_DiscS1_ON' : 127, 
                'Ibias_DiscS2_ON' : 127, 
                'Ibias_PixelDAC' : 127, 
                'Ibias_TPbufferIn' : 127, 
                'Ibias_TPbufferOut' : 127, 
                'VTP_coarse' : 127,
                'VTP_fine' : 255, 
                'Ibias_CP_PLL' : 127, 
                'PLL_Vcntrl' : 127, 
                'Equalisation_path' : None,
                'Polarity' : 1,
                'Op_mode' : 0,
                'Fast_Io_en' : 0}
        
    def is_valid(self, config):
        if not isinstance(config, dict):
            # depending on impl may also just return False
            raise TypeError("Invalid type for configuration")
        return sorted(list(config)) == sorted(self.config_keys)

    def name_valid(self, name):
        for key in self.config_keys:
            if key == name:
                return True
        return False
        
    def write_value(self, name, value):#was write_data TODO: change in GUI
        if self.name_valid(name) == True:
            self.data[name] = value
            return True
        print("Error: Unknown data name")
        return False
        
    def read_value(self, name):
        if self.name_valid(name) == True:
            value = self.data[name]
            return value
        print("Error: Unknown data name")
        return False    
        
    def get_data(self):
        return self.data

    def set_data(self, config):
        if self.is_valid(config):
            self.data = config    
            return True
        print("Error: Corrupted data")
        return False
    
    def write_to_yaml(self, name):
        current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if name in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine', 'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl'}:
            yaml_file = os.path.join(current_path, 'tpx3' + os.sep + 'dacs.yml')

        #elif name in {}
        #    yaml_file = os.path.join(current_path, 'tpx3' + os.sep + 'outputBlock.yml')

        elif name in {'Polarity', 'Op_mode', 'Fast_Io_en'}:
            yaml_file = os.path.join(current_path, 'tpx3' + os.sep + 'GeneralConfiguration.yml')

        else:
            yaml_file = None

        if not yaml_file == None:
            with open(yaml_file) as file:
                yaml_data = yaml.load(file, Loader=yaml.FullLoader)
            for register in yaml_data['registers']:
                if register['name'] == name:
                    register['value'] = self.data[name]
            with open(yaml_file, 'w') as file:
                yaml.dump(yaml_data, file)
            return True
        else:
            print('No known .yml contains the asked name.')
            return False
    
TPX3_datalogger = TPX3_data_logger()