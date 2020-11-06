import json
import os
import time
import glob
import yaml
import numpy as np
import tables as tb

class mask_logger(object):

    def create_file(filename = None):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'masks')
        if filename == None:
            filename = "mask_" + time.strftime("%Y-%m-%d_%H-%M-%S")
        if os.path.isfile(user_path + os.sep + filename + ".h5") == False:
            full_path = user_path + os.sep + filename + ".h5"
            return full_path
        elif os.path.isfile(user_path + os.sep + filename + ".h5") == True:
            print('File exists already')

    def write_mask(mask_element, mask = None):
        mask_matrix = np.zeros((256, 256), dtype=np.bool)
        if mask == None:
            path = TPX3_datalogger.read_value(name = 'Mask_path')
            if path == None:
                path = mask_logger.create_file()
                TPX3_datalogger.write_value(name = 'Mask_path', value = path)
        else:
            user_path = os.path.expanduser('~')
            user_path = os.path.join(user_path, 'Timepix3')
            user_path = os.path.join(user_path, 'masks')
            path = user_path + os.sep + mask + ".h5"

        #open file if existing and writing set data to mask_matrix
        if os.path.isfile(path):
            with tb.open_file(path, 'a') as infile:
                mask_matrix = infile.root.mask_matrix[:]
                infile.remove_node(infile.root.mask_matrix)

        #manipulate mask matrix
            if mask_element[0] == 'row':
                mask_matrix[ : , int(mask_element[1])] = 1
            elif mask_element[0] == 'column':
                mask_matrix[int(mask_element[1]), :] = 1
            elif mask_element[0] == 'pixel':
                mask_matrix[int(mask_element[1]), int(mask_element[2])] = 1
            else:
                print('Error: Unknown mask element')

        #Saving the final matrix
            with tb.open_file(path, 'a') as out_file:
                out_file.create_carray(out_file.root, name='mask_matrix', title='Matrix mask', obj=mask_matrix)
        
    def delete_mask(mask_element, mask = None):
        mask_matrix = np.zeros((256, 256), dtype=np.bool)
        if mask == None:
            path = TPX3_datalogger.read_value(name = 'Mask_path')
            if path == None:
                print('Error: No mask to work with!')
        else:
            user_path = os.path.expanduser('~')
            user_path = os.path.join(user_path, 'Timepix3')
            user_path = os.path.join(user_path, 'masks')
            path = user_path + os.sep + mask + ".h5"
            
        #open file if existing and writing set data to mask_matrix
        if os.path.isfile(path):
            with tb.open_file(path, 'a') as infile:
                mask_matrix = infile.root.mask_matrix[:]
                infile.remove_node(infile.root.mask_matrix)

        #manipulate mask matrix
            if mask_element[0] == 'row':
                mask_matrix[ : , int(mask_element[1])] = 0
            elif mask_element[0] == 'column':
                mask_matrix[int(mask_element[1]), :] = 0
            elif mask_element[0] == 'pixel':
                mask_matrix[int(mask_element[1]), int(mask_element[2])] = 0
            elif mask_element[0] == 'all':
                mask_matrix = np.zeros((256, 256), dtype=np.bool)
            else:
                print('Error: Unknown mask element')

        #Saving the final matrix
            with tb.open_file(path, 'a') as out_file:
                out_file.create_carray(out_file.root, name='mask_matrix', title='Matrix mask', obj=mask_matrix)
        

    def get_mask(mask = None):
        if mask == None:
            path = TPX3_datalogger.read_value(name = 'Mask_path')
            if path == None:
                print('No mask set')
        else:
            user_path = os.path.expanduser('~')
            user_path = os.path.join(user_path, 'Timepix3')
            user_path = os.path.join(user_path, 'masks')
            path = user_path + os.sep + mask + ".h5"

        with tb.open_file(path, 'r') as infile:
            mask_matrix = infile.root.mask_matrix[:]
            return mask_matrix


class file_logger(object):
    #This class contains the functions to write the setting to a file which will then be call next time the GUI is started
    
    def create_file(filename = None):
        #Creates backup folder and file if not existing
        user_path = os.path.expanduser('~')
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
            data = TPX3_datalogger.get_data()
        json.dump(data, file)
        
    def read_backup(file = None):
        #reads backup and returns the data
        user_path = os.path.expanduser('~')
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
                return data
            else:
                print("Error! File does not exist")
                return False
                
    def get_newest_backup_file():
        user_path = os.path.expanduser('~')
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
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        filename = "default.TPX3"
        if os.path.isdir(user_path) == False:
            os.mkdir(user_path)
        default_file = open(user_path + os.sep + filename, "w")
        json.dump(TPX3_datalogger.default_config(), default_file)
        file = user_path + os.sep + filename
        return file
        
    def get_backup_value(name, file = None):
        backup_data = file_logger.read_backup(file)
        if TPX3_datalogger.name_valid(name) == True:
            value = backup_data[name]
            return value
        print("Error: Unknown data name")
        return False    
        
        
        
class TPX3_data_logger(object):
 
#here the data will be logged while the programm is running this function is called as global
    def __init__(self):
        self.config_keys = ['Chip0_name', 'Chip1_name', 'Chip2_name', 'Chip3_name', 
                            'Chip4_name', 'Chip5_name', 'Chip6_name', 'Chip7_name', 
                            'plottype', 'colorsteps', 'integration_length', 
                            'color_depth', 'Ibias_Preamp_ON', 'VPreamp_NCAS', 
                            'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine', 
                            'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 
                            'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 
                            'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl', 
                            'Equalisation_path', 'Mask_path', 'Polarity', 'Op_mode', 'Fast_Io_en']
        self.data = self.default_config()
    
    def default_config(self):
        return {'Chip0_name' : [None],#[W?_??, [FPGA n, link n , delay, data-invert, data-edge], [FPGA m, link m , delay, data-invert, data-edge], ... ]
                'Chip1_name' : [None],
                'Chip2_name' : [None],
                'Chip3_name' : [None],
                'Chip4_name' : [None],
                'Chip5_name' : [None],
                'Chip6_name' : [None],
                'Chip7_name' : [None],
                'plottype' : 'normal', 
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
                'Mask_path' : None,
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
        if name == 'init':
            yaml_file = os.path.join(current_path, 'tpx3' + os.sep + 'links.yml')

            with open(yaml_file) as file:
                yaml_data = yaml.load(file, Loader=yaml.FullLoader)

                for i in range (0,7):
                    name = 'Chip' + str(i) +'_name'
                    value_list = self.data[name]
                    if not value_list == [None]:

                        Chipname = value_list[0]
                        wafer_number = ''
                        chip_coord2 = '' 
                        for i in range (1, len(Chipname)):
                            if Chipname[i] == '-':
                                start_chipname = i
                        for i in range (1, start_chipname):
                            wafer_number = wafer_number + Chipname[i]
                        chip_coord1 = Chipname[start_chipname+1]
                        for i in range (start_chipname+2, len(Chipname)):
                            chip_coord2 = chip_coord2 + Chipname[i]

                        wafer_number = int(wafer_number)
                        chip_coord1 = ord(chip_coord1.lower()) - ord('a') + 1
                        chip_coord2 = int(chip_coord2)

                        Chip_ID = (wafer_number << 8) | (chip_coord2 << 4) | chip_coord1

                        for n in range(1, len(value_list)):
                            element_list = value_list[n]
                            if element_list[0] == 0: 
                                element = 'RX'
                                fpga_link = element_list[0]
                                chip_link = element_list[1]
                                data_delay = element_list[2]
                                data_invert = element_list[3]
                                data_edge = element_list[4]
                            else:
                                element = 'RX' + str(element_list[0])
                                fpga_link = element_list[0]
                                chip_link = element_list[1]
                                data_delay = element_list[2]
                                data_invert = element_list[3]
                                data_edge = element_list[4]

                            for register in yaml_data['registers']:
                                if register['name'] == element:
                                    register['fpga-link'] = fpga_link
                                    register['chip-link'] = chip_link
                                    register['chip-id'] = Chip_ID
                                    register['data-delay'] = data_delay
                                    register['data-invert'] = data_invert
                                    register['data-edge'] = data_edge

            with open(yaml_file, 'w') as file:
                yaml.dump(yaml_data, file)
            return True

        else:
            if name in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine', 
                            'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 
                            'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl'}:
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

    def write_backup_to_yaml(self):
        current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for key in self.data:
            if key in {'Chip0_name', 'Chip1_name', 'Chip2_name', 'Chip3_name', 'Chip4_name', 'Chip5_name', 'Chip6_name', 'Chip7_name'}:
                yaml_file = os.path.join(current_path, 'tpx3' + os.sep + 'links.yml')
                with open(yaml_file) as file:
                    yaml_data = yaml.load(file, Loader=yaml.FullLoader)
                value_list = self.data[key]
                if not value_list == [None]:

                    Chipname = value_list[0]
                    wafer_number = ''
                    chip_coord2 = '' 
                    for i in range (1, len(Chipname)):
                        if Chipname[i] == '-':
                            start_chipname = i
                    for i in range (1, start_chipname):
                        wafer_number = wafer_number + Chipname[i]
                    chip_coord1 = Chipname[start_chipname+1]
                    for i in range (start_chipname+2, len(Chipname)):
                        chip_coord2 = chip_coord2 + Chipname[i]

                    wafer_number = int(wafer_number)
                    chip_coord1 = ord(chip_coord1.lower()) - ord('a') + 1
                    chip_coord2 = int(chip_coord2)

                    Chip_ID = (wafer_number << 8) | (chip_coord2 << 4) | chip_coord1

                    for n in range(1, len(value_list)):
                        element_list = value_list[n]
                        if element_list[0] == 0: 
                            element = 'RX'
                            fpga_link = element_list[0]
                            chip_link = element_list[1]
                            data_delay = element_list[2]
                            data_invert = element_list[3]
                            data_edge = element_list[4]
                        else:
                            element = 'RX' + str(element_list[0])
                            fpga_link = element_list[0]
                            chip_link = element_list[1]
                            data_delay = element_list[2]
                            data_invert = element_list[3]
                            data_edge = element_list[4]

                        for register in yaml_data['registers']:
                            if register['name'] == element:
                                register['fpga-link'] = fpga_link
                                register['chip-link'] = chip_link
                                register['chip-id'] = Chip_ID
                                register['data-delay'] = data_delay
                                register['data-invert'] = data_invert
                                register['data-edge'] = data_edge

                with open(yaml_file, 'w') as file:
                    yaml.dump(yaml_data, file)

            else:
                if key in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine', 'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl'}:
                    yaml_file = os.path.join(current_path, 'tpx3' + os.sep + 'dacs.yml')

                #elif key in {}
                #    yaml_file = os.path.join(current_path, 'tpx3' + os.sep + 'outputBlock.yml')

                elif key in {'Polarity', 'Op_mode', 'Fast_Io_en'}:
                    yaml_file = os.path.join(current_path, 'tpx3' + os.sep + 'GeneralConfiguration.yml')

                else:
                    yaml_file = None

                if not yaml_file == None:
                    with open(yaml_file) as file:
                        yaml_data = yaml.load(file, Loader=yaml.FullLoader)
                    for register in yaml_data['registers']:
                        if register['name'] == key:
                            register['value'] = self.data[key]
                    with open(yaml_file, 'w') as file:
                        yaml.dump(yaml_data, file)
                    
    
TPX3_datalogger = TPX3_data_logger()