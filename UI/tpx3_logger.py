import json
import os
import time
import glob
import yaml
import numpy as np
import tables as tb
from copy import deepcopy
from tpx3.utils import check_user_folders

class mask_logger(object):
    '''
        The mask logger takes care of the mask file, adds and removes items
    '''
    def create_file(filename = None):
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'masks')
        Chipnames = TPX3_datalogger.get_chipnames()
        if len(Chipnames) == 1:
            Chip = Chipnames[0]
        else:
            print('not implemented')

        if filename == None:
            #filename = Chip + '_mask_' + time.strftime('%Y-%m-%d_%H-%M-%S')
            filename = 'mask_' + time.strftime('%Y-%m-%d_%H-%M-%S')
        if os.path.isfile(user_path + os.sep + filename + '.h5') == False:
            full_path = user_path + os.sep + filename + ".h5"
            return full_path
        elif os.path.isfile(user_path + os.sep + filename + '.h5') == True:
            print('File exists already')

    def write_mask(mask_element, mask = None):
        '''
            This will mask the 'pixel', 'row' or 'column' given to it via mask_element.
            Additionally the mask file to change can be given via mask.
        '''
        mask_matrix = np.zeros((256, 256), dtype=np.bool)
        if mask == None:
            path = TPX3_datalogger.read_value(name = 'Mask_path')
            if path == None:
                path = mask_logger.create_file()
                TPX3_datalogger.write_value(name = 'Mask_path', value = path, chip=None)
        else:
            user_path = os.path.expanduser('~')
            user_path = os.path.join(user_path, 'Timepix3')
            user_path = os.path.join(user_path, 'masks')
            path = user_path + os.sep + mask + '.h5'

        #open file if existing and writing set data to mask_matrix
        if os.path.isfile(path):
            with tb.open_file(path, 'a') as infile:
                mask_matrix = infile.root.mask_matrix[:]
                infile.remove_node(infile.root.mask_matrix)

        #manipulate mask matrix
        if mask_element[0] == 'all':
            mask_matrix = np.ones((256, 256), dtype=np.bool)
        elif mask_element[0] == 'row':
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
        '''
            This will unmask the 'pixel', 'row' or 'column' given to it via mask_element.
            Additionally the mask file to change can be given via mask.
        '''
        mask_matrix = np.zeros((256, 256), dtype=np.bool)
        if mask == None:
            path = TPX3_datalogger.read_value(name = 'Mask_path')
            if path == None:
                print('Error: No mask to work with!')
        else:
            user_path = os.path.expanduser('~')
            user_path = os.path.join(user_path, 'Timepix3')
            user_path = os.path.join(user_path, 'masks')
            path = user_path + os.sep + mask + '.h5'

        #open file if existing and writing set data to mask_matrix
        if os.path.isfile(path):
            with tb.open_file(path, 'a') as infile:
                mask_matrix = infile.root.mask_matrix[:]
                infile.remove_node(infile.root.mask_matrix)

        #manipulate mask matrix
            if mask_element[0] == 'all':
                mask_matrix = np.zeros((256, 256), dtype=np.bool)
            elif mask_element[0] == 'row':
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

    def write_full_mask(full_mask, mask = None):
        '''
            This overwrites the complete mask, so a proper mask has to be given via full_mask
        '''
        if mask == None:
            path = TPX3_datalogger.read_value(name = 'Mask_path')
            if path == None:
                path = mask_logger.create_file()
                TPX3_datalogger.write_value(name = 'Mask_path', value = path, chip = None)
        else:
            user_path = os.path.expanduser('~')
            user_path = os.path.join(user_path, 'Timepix3')
            user_path = os.path.join(user_path, 'masks')
            path = user_path + os.sep + mask + '.h5'

        #delete last mask
        if os.path.isfile(path):
            with tb.open_file(path, 'a') as infile:
                infile.remove_node(infile.root.mask_matrix)

        #Saving the final matrix
        with tb.open_file(path, 'a') as out_file:
            out_file.create_carray(out_file.root, name='mask_matrix', title='Matrix mask', obj=full_mask)
        return True

    def get_mask(mask = None):
        '''
            This returns the mask matrix as a list.
        '''
        if mask == None:
            path = TPX3_datalogger.read_value(name = 'Mask_path')
            if path == None:
                print('No mask set')
                return False
        else:
            user_path = os.path.expanduser('~')
            user_path = os.path.join(user_path, 'Timepix3')
            user_path = os.path.join(user_path, 'masks')
            path = user_path + os.sep + mask + '.h5'

        with tb.open_file(path, 'r') as infile:
            mask_matrix = infile.root.mask_matrix[:]
            return mask_matrix

class equal_logger(object):
    '''
        The equal logger takes care of the equalisation file
    '''

    def write_full_equal(full_equal, path):
        '''
            This overwrites the complete equal, so a proper mask has to be given via full_equal
        '''
        TPX3_datalogger.write_value(name = 'Equalisation_path', value = path, chip = None)

        #delete last equal
        if os.path.isfile(path):
            with tb.open_file(path, 'a') as infile:
                infile.remove_node(infile.root.thr_matrix)

        #Saving the final equal
        with tb.open_file(path, 'a') as out_file:
            out_file.create_carray(out_file.root, name='thr_matrix', title='Matrix Threshold', obj=full_equal)
        return True

class file_logger(object):
    '''
        This class contains the functions to write the setting to a file
        which will then be call next time the GUI is started
    '''
    def create_file(filename = None):
        '''
            Creates backup folder and file if not existing
        '''
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        Chipnames = TPX3_datalogger.get_chipnames()
        if len(Chipnames) == 0:
            Chip = 'W?_??'
        elif len(Chipnames) == 1:
            Chip = Chipnames[0]
        else:
            Chip = 'Multi_chip'
            print('not implemented')

        if filename == None:
            #filename = Chip + '_backup_' + time.strftime('%Y-%m-%d_%H-%M-%S') + '.TPX3'
            filename = 'backup_' + time.strftime('%Y-%m-%d_%H-%M-%S') + '.TPX3'
        if os.path.isdir(user_path) == False:
            os.mkdir(user_path)
            if os.path.isfile(user_path + os.sep + filename) == False:
                backup_file = open(user_path + os.sep + filename, 'w')
                return backup_file
        elif os.path.isdir(user_path) == True:
            if os.path.isfile(user_path + os.sep + filename) == False:
                backup_file = open(user_path + os.sep + filename, 'w')
                return backup_file

    def write_backup(file, data = None):
        '''
            Writes the backup to the file given
        '''
        file = file
        if data == None:
            data = TPX3_datalogger.get_data()
        json.dump(data, file)

    def write_tmp_backup():
        '''
            Writes temporary backup
        '''
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'tmp')
        filename = 'backup_' + time.strftime('%Y-%m-%d_%H-%M-%S') + '.TPX3'

        if os.path.isfile(user_path + os.sep + filename) == False:
            backup_file = open(user_path + os.sep + filename, 'w')
            data = TPX3_datalogger.get_data()
            json.dump(data, backup_file)
            return True
        else:
            print('Error: tried to call existing tmp file')
            return False

    def delete_tmp_backups(days_to_hold = None):
        '''
            Deletes old temporary backups which are older then 'days_to_hold' days.
        '''
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'tmp')

        # Time in days before file will be removed if none is given
        if days_to_hold == None:
            days_to_hold = 14

        # Look if there are older files
        now = time.time()

        for f in os.listdir(user_path):
            if os.stat(os.path.join(user_path, f)).st_mtime < now - days_to_hold * 86400:
                if os.path.isfile(os.path.join(user_path, f)) and f.endswith('.TPX3'):
                    os.remove(os.path.join(user_path, f))


    def read_backup(file = None):
        '''
            reads backup and returns the data
        '''
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        if file == None:
            #Get most recent file
            file = file_logger.get_newest_backup_file()
            data = json.load(open(file, 'r'))
            return data
        else:
            file = file
            if os.path.isfile(user_path + os.sep + file) == True:
                data = json.load(open(user_path + os.sep + file, 'r'))
                return data
            else:
                print('Error: File does not exist')
                return False

    def get_newest_backup_file():
        '''
            This function looks for the most recent backup file in the backup folder
        '''
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')

        user_path_tmp = os.path.expanduser('~')
        user_path_tmp = os.path.join(user_path, 'Timepix3')
        user_path_tmp = os.path.join(user_path, 'tmp')
        #Look for newest backup in backup folder
        if os.path.isdir(user_path) == True:
            list_of_files = glob.glob(user_path + os.sep + '*.TPX3')
            if list_of_files:
                file = max(list_of_files, key=os.path.getctime)
                #return file
            else:
                file = None
        else:
            file = None
        #Look for newest backup in tmp folder
        if os.path.isdir(user_path_tmp) == True:
            list_of_files = glob.glob(user_path_tmp + os.sep + '*.TPX3')
            if list_of_files:
                file_tmp = max(list_of_files, key=os.path.getctime)
            else:
                file_tmp = None
        else:
            file_tmp = None

        if file_tmp != None and file != None:
            if os.path.getctime(file) < os.path.getctime(file_tmp):
                return file_tmp
            elif os.path.getctime(file) >= os.path.getctime(file_tmp):
                return file
        elif not file == None:
            return file
        elif not file_tmp == None:
            return file_tmp
        else:
            file = file_logger.create_default_file()
            return file

    def create_default_file():
        '''
            This function creates a default backup file
        '''
        user_path = os.path.expanduser('~')
        user_path = os.path.join(user_path, 'Timepix3')
        user_path = os.path.join(user_path, 'backups')
        filename = 'default.TPX3'
        if os.path.isdir(user_path) == False:
            os.mkdir(user_path)
        default_file = open(user_path + os.sep + filename, "w")
        json.dump(TPX3_datalogger.default_config(), default_file)
        file = user_path + os.sep + filename
        return file

    def get_backup_value(name, file = None):
        '''
            This returns the backup value 'name'
        '''
        backup_data = file_logger.read_backup(file)
        if TPX3_datalogger.name_valid(name) == True:
            value = backup_data[name]
            return value
        print('Error: Unknown data name')
        return False


class TPX3_data_logger(object):
    '''
        here the data will be logged while the programm is
        running this function is called as global
    '''
    def __init__(self):
        check_user_folders()
        self.config_keys = ['software_version', 'firmware_version', 'hardware_links',
                            'Chip0_name', 'Chip1_name', 'Chip2_name', 'Chip3_name',
                            'Chip4_name', 'Chip5_name', 'Chip6_name', 'Chip7_name',
                            'plottype', 'colorsteps', 'integration_length',
                            'color_depth', 'Ibias_Preamp_ON', 'VPreamp_NCAS',
                            'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine',
                            'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON',
                            'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut',
                            'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl',
                            'Equalisation_path', 'Mask_path', 'Run_name', 'Polarity', 'Op_mode', 'Fast_Io_en',
                            'clk_fast_out', 'ClkOut_frequency_src', 'AckCommand_en', 'SelectTP_Ext_Int',
                            'clkphasediv', 'clkphasenum', 'PLLOutConfig', 'Readout_Speed', 'TP_Period', 'Sense_DAC']
        self.general_config_keys = ['software_version', 'firmware_version', 'hardware_links', 'Chip0_name',
                                    'Chip1_name', 'Chip2_name', 'Chip3_name', 'Chip4_name',
                                    'Chip5_name', 'Chip6_name', 'Chip7_name', 'plottype',
                                    'colorsteps', 'integration_length', 'color_depth', 
                                    'Equalisation_path', 'Mask_path', 'Run_name', 'Readout_Speed', 'TP_Period']
        self.data         = self.config()
        self.current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def config(self):
        return {'software_version'   : 'x.x',
                'firmware_version'   : 'x.x',
                'hardware_links'     : 0,
                'Chip0_name'         : [None],#[W?_??, [FPGA n, link n , delay, data-invert, data-edge, link n-status], [FPGA m, link m , delay, data-invert, data-edge, link m-status], ... ]
                'Chip1_name'         : [None], 'Chip2_name': [None], 'Chip3_name': [None], 'Chip4_name': [None],
                'Chip5_name'         : [None], 'Chip6_name': [None], 'Chip7_name': [None],
                'plottype'           : 'normal',
                'colorsteps'         : 50,
                'integration_length' : 500,
                'color_depth'        : 10,
                'Equalisation_path'  : None,
                'Mask_path'          : None,
                'Run_name'           : None,
                'Readout_Speed'      : 0.1,
                'TP_Period'          : 3,
                # to be filled after initialization of hardware
                'links' : {'Link_0': {'chip-id': None, 'chip-link': 0, 'fpga-link': 0, 'data-delay': 0, 'data-invert': 0, 'data-edge': 0, 'link-status': 0, 'name': 'RX0'},
                           'Link_1': {'chip-id': None, 'chip-link': 0, 'fpga-link': 0, 'data-delay': 0, 'data-invert': 0, 'data-edge': 0, 'link-status': 0, 'name': 'RX1'},
                           'Link_2': {'chip-id': None, 'chip-link': 0, 'fpga-link': 0, 'data-delay': 0, 'data-invert': 0, 'data-edge': 0, 'link-status': 0, 'name': 'RX2'},
                           'Link_3': {'chip-id': None, 'chip-link': 0, 'fpga-link': 0, 'data-delay': 0, 'data-invert': 0, 'data-edge': 0, 'link-status': 0, 'name': 'RX3'},
                           'Link_4': {'chip-id': None, 'chip-link': 0, 'fpga-link': 0, 'data-delay': 0, 'data-invert': 0, 'data-edge': 0, 'link-status': 0, 'name': 'RX4'},
                           'Link_5': {'chip-id': None, 'chip-link': 0, 'fpga-link': 0, 'data-delay': 0, 'data-invert': 0, 'data-edge': 0, 'link-status': 0, 'name': 'RX5'},
                           'Link_6': {'chip-id': None, 'chip-link': 0, 'fpga-link': 0, 'data-delay': 0, 'data-invert': 0, 'data-edge': 0, 'link-status': 0, 'name': 'RX6'},
                           'Link_7': {'chip-id': None, 'chip-link': 0, 'fpga-link': 0, 'data-delay': 0, 'data-invert': 0, 'data-edge': 0, 'link-status': 0, 'name': 'RX7'}}, 
                'chip_links'   : {}, # active chip links configuration for analysing data
                'chip_polarity': {}, # convinience dict for analysis -> s/z-curve fit
                'chip_dacs'    : {'default': # settings for chips and defaults
                                 {'Ibias_Preamp_ON'      : 150,
                                 'VPreamp_NCAS'         : 128,
                                 'Ibias_Ikrum'          : 5,
                                 'Vfbk'                 : 132,
                                 'Vthreshold_fine'      : 255,
                                 'Vthreshold_coarse'    : 7,
                                 'Ibias_DiscS1_ON'      : 100,
                                 'Ibias_DiscS2_ON'      : 128,
                                 'Ibias_PixelDAC'       : 120,
                                 'Ibias_TPbufferIn'     : 128,
                                 'Ibias_TPbufferOut'    : 128,
                                 'VTP_coarse'           : 100,
                                 'VTP_fine'             : 300,
                                 'Ibias_CP_PLL'         : 128,
                                 'PLL_Vcntrl'           : 128,
                                 'Polarity'             : 1,
                                 'Op_mode'              : 0,
                                 'Fast_Io_en'           : 0,
                                 'clk_fast_out'         : 1,
                                 'ClkOut_frequency_src' : 2,
                                 'AckCommand_en'        : 0,
                                 'SelectTP_Ext_Int'     : 0,
                                 'clkphasediv'          : 1,
                                 'clkphasenum'          : 4,
                                 'PLLOutConfig'         : 0,
                                 'Sense_DAC'            : 29}} 
                }

    def is_valid(self, config):
        if not isinstance(config, dict):
            # depending on impl may also just return False
            raise TypeError('Invalid type for configuration')
        config = self.complete(config)
        return sorted(list(config)) == sorted(self.config_keys)

    def complete(self, config):
        for key in self.config_keys:
            try:
                config[key]
            except KeyError:
                config[key] = self.get_default_value(key)
        return config

    def get_default_value(self, key):
        defaults = self.default_config()
        return defaults[key]

    def name_valid(self, name):
        for key in self.config_keys:
            if key == name:
                return True
        return False

    def update_chip_links(self):
        new_config  = {}
        link_config = self.data['links']

        for n, info in enumerate(link_config):
            if link_config[info]['chip-id'] not in new_config:
                new_config[link_config[info]['chip-id']] = [n]
            else:
                new_config[link_config[info]['chip-id']].append(n)
            
        self.data['chip_links'] = new_config
        #print('self.data[chip_links]')
        #print(self.data['chip_links'])

    def update_links(self, link_config):
        chip_name = link_config[0]
        configs   = link_config[1:]
        
        for link in configs:
            chip_link   = int(link[1])
            fpga_link   = int(link[0])
            data_delay  = int(link[2])
            link_status = int(link[5])
            data_invert = int(link[3])
            data_edge   = int(link[4])
            label       = f'Link_{fpga_link}'
            self.data['links'][label]['chip-id']     = chip_name
            self.data['links'][label]['chip-link']   = chip_link
            self.data['links'][label]['fpga-link']   = fpga_link
            self.data['links'][label]['data-delay']  = data_delay
            self.data['links'][label]['data-invert'] = data_invert
            self.data['links'][label]['data-edge']   = data_edge
            self.data['links'][label]['link-status'] = link_status
        
        self.update_chip_links()

    def update_polarity(self):
        for chip in self.data['chip_dacs']:
            self.data['chip_polarity'][chip] = self.data['chip_dacs'][chip]['Polarity']
        print(self.data['chip_polarity'])

    def write_value(self, name, value, chip=None):
        if self.name_valid(name) == True:
            if name in ['Chip0_name', 'Chip1_name', 'Chip2_name', 'Chip3_name',
                        'Chip4_name', 'Chip5_name', 'Chip6_name', 'Chip7_name']:
                value_list = self.data[name]
                self.update_links(value)
                if value == value_list:
                    return True
                elif value_list == [None]:
                    self.data[name] = value
                    return True
                elif value_list[0] != value[0]:
                    self.data[name] = value
                    return True
                else:
                    self.final_list = [value[0]]
                    for n in range(1, len(value)):
                        new_element_list = value[n]
                        new_chip_link    = new_element_list[1]
                        new_link_status  = new_element_list[5]
                        for i in range(1, len(value_list)):
                            element_list = value_list[i]
                            chip_link    = element_list[1]
                            link_status  = element_list[5]
                            if new_chip_link == chip_link:
                                if new_link_status == 0: # not connected
                                    new_link_status = 0
                                elif new_link_status == link_status:
                                    new_link_status = int(new_link_status)
                                elif new_link_status == 1 and link_status == 2: # user switched link off
                                    new_link_status = int(link_status)
                                elif new_link_status == 4 and link_status == 3: # user switched link on
                                    new_link_status = int(link_status)
                                elif new_link_status == 6 and link_status == 5: # user switched link on
                                    new_link_status = int(link_status)
                                elif new_link_status == 8 and link_status == 7: # user switched link on
                                    new_link_status = int(link_status)
                                else:
                                    new_link_status = int(new_link_status)
                            else:
                                continue
                        
                        self.final_list.append([new_element_list[0], new_element_list[1], new_element_list[2], new_element_list[3], new_element_list[4], new_link_status])
                        self.data[name] = self.final_list
                        self.write_to_yaml(name = 'init')
                    
                    return True
            
            else:
                if name in self.general_config_keys:
                    self.data[name] = value
                else:
                    if chip == None:
                        self.data['chip_dacs']['default'][name] = value
                    else:
                        self.data['chip_dacs'][chip][name] = value
                
                if name == 'Polarity':
                    self.update_polarity()
                return True
            
        print('Error: Unknown data name')
        return False

    def read_value(self, name, chip=None):
        if self.name_valid(name) == True:
            if name in self.general_config_keys:
                value = self.data[name]
            else:
                if chip == None:
                    value = self.data['chip_dacs']['default'][name]
                else:
                    value = self.data['chip_dacs'][chip][name]
            return value
        print('Error: Unknown data name')
        return False

    def get_run_name(self, scan_type = None):
        if scan_type == None:
            scan_type = 'Test'
        if self.data['Run_name'] == None:
            run_name = scan_type + '_' + time.strftime('%Y-%m-%d_%H-%M-%S')
        elif self.data['Run_name'] in ['False', 'false', '', 'None', 'none']:
            run_name = scan_type + '_' + time.strftime('%Y-%m-%d_%H-%M-%S')
            self.data['Run_name'] = None
        else:
            run_name = scan_type + '_' + self.data['Run_name']
            self.data['Run_name'] = None
        return run_name

    def get_data(self):
        return self.data

    def set_data(self, config):
        if self.is_valid(config):
            self.data = config
            return True
        print('Error: Corrupted data')
        return False

    def get_chipnames(self):
        chiplist = []
        for i in range (0,7):
            name       = 'Chip' + str(i) +'_name'
            value_list = self.data[name]
            if not value_list == [None]:
                chiplist = chiplist + [value_list[0]]
        return chiplist

    def get_links(self, chipname):
        for i in range (0,7):
            name       = 'Chip' + str(i) +'_name'
            value_list = self.data[name]
            if value_list[0] == chipname:
                number_of_links = 0
                for i in range(1, len(value_list)):
                    if value_list[i][5] in [1, 3, 5, 7]:
                        number_of_links += 1
                return number_of_links

        print('Name of Chipname not in list')
        return False

    def change_link_status(self, link, status):
        for i in range (0,7):
            name       = 'Chip' + str(i) +'_name'
            value_list = self.data[name]
            if not value_list == [None]:
                self.final_list = [value_list[0]]
                for n in range(1, len(value_list)):
                    element_list = value_list[n]
                    chip_link    = element_list[1]
                    link_status  = element_list[5]
                    if chip_link == link:
                        if status == 0: #disable
                            if int(link_status) in [1, 3, 5, 7]:
                                link_status = int(link_status) + 1
                        elif status == 1: #enable
                            if int(link_status) in [2, 4, 6, 8]:
                                link_status = int(link_status) - 1
                        else:
                            print('Error: Unknown link status')
                            return False
                    self.final_list.append([element_list[0], element_list[1], element_list[2], element_list[3], element_list[4], link_status])
                self.data[name] = self.final_list
                self.update_links(self.final_list)
                self.write_to_yaml(name = 'init')

        return True

    def get_link_status(self, link):
        '''
            Get link status of 'link'. Right now fpga-link and chip-link (from carrier board) might not be
            the same value. The data logger logs the Link_n with n == fpga-link for testing purposes
            Some links on current testing board output garbage like fpga-link == 2, chip-link == 0.
            chip-link == 0 would be then assigned 2 times.  Change to n == link-number later.
        '''
        label = f'Link_{link}' # == fpga-link.
        
        try:
            link_status = self.data['links'][label]['link-status']
            return int(link_status)
        except:
            print('No link data, run Init')
            return False
        '''    
        for i in range (0,7):
            name       = 'Chip' + str(i) +'_name'
            value_list = self.data[name]
            if not value_list == [None]:
                for n in range(1, len(value_list)):
                    element_list = value_list[n]
                    chip_link    = element_list[1]
                    link_status  = element_list[5]
                    if chip_link == link:
                        return int(link_status)
            else:
                print('Error: Unknown link status')
                return False
    
        else:
            print('No link data, run Init')
            return False
        '''


    def get_dacs_from_yaml(self):
        '''
            This function writes DAC configuarions from chip_dacs.yml, chip_GeneralConfiguration.yml,
            chip_outputBlock.yml and chip_PLLConfig.yml, to the dataloggers data.chip_dacs-dictionary
        '''

        file_names = ['chip_dacs.yml', 'chip_GeneralConfiguration.yml', 'chip_outputBlock.yml', 'chip_PLLConfig.yml']
        for file in file_names:
            yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + file)

            with open(yaml_file) as f:
                yaml_data = yaml.load(f, Loader=yaml.FullLoader)

            for chip in yaml_data['chips']:
                chip_name = chip['chip_ID_decoded']

                if chip_name not in self.data['chip_dacs']:
                    # create dict for chip, if not existing yet
                    self.data['chip_dacs'][chip_name] = {}

                for register in chip['registers']:
                    if register['name'] in self.config_keys:
                        self.data['chip_dacs'][chip_name][register['name']] = register['value']
        self.update_polarity()


    def write_to_yaml(self, name, chip='default'):
        if name == 'init':
            yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'links.yml')

            with open(yaml_file) as file:
                yaml_data = yaml.load(file, Loader=yaml.FullLoader)
            
            for i in range(8):
                label = f'Link_{i}'
                yaml_data['registers'][i] = self.data['links'][label]

                '''
                for i in range (0,7):
                    name = 'Chip' + str(i) +'_name'
                    value_list = self.data[name]
                    if not value_list == [None]:

                        Chipname     = value_list[0]
                        wafer_number = ''
                        chip_coord2  = ''
                        for i in range (1, len(Chipname)):
                            if Chipname[i] == '-':
                                start_chipname = i
                        for i in range (1, start_chipname):
                            wafer_number = wafer_number + Chipname[i]
                        chip_coord1 = Chipname[start_chipname+1]
                        for i in range (start_chipname+2, len(Chipname)):
                            chip_coord2 = chip_coord2 + Chipname[i]

                        wafer_number = int(wafer_number)
                        chip_coord1  = ord(chip_coord1.lower()) - ord('a') + 1
                        chip_coord2  = int(chip_coord2)

                        Chip_ID = (wafer_number << 8) | (chip_coord2 << 4) | chip_coord1

                        for n in range(1, len(value_list)):
                            element_list = value_list[n]
                            element      = 'RX' + str(element_list[0])
                            fpga_link    = element_list[0]
                            chip_link    = element_list[1]
                            data_delay   = element_list[2]
                            data_invert  = element_list[3]
                            data_edge    = element_list[4]
                            link_status  = element_list[5]

                            for register in yaml_data['registers']:
                                if register['name'] == element:
                                    register['fpga-link']   = fpga_link
                                    register['chip-link']   = chip_link
                                    register['chip-id']     = Chip_ID
                                    register['data-delay']  = data_delay
                                    register['data-invert'] = data_invert
                                    register['data-edge']   = data_edge
                                    register['link-status'] = link_status
                '''
            with open(yaml_file, 'w') as file:
                yaml.dump(yaml_data, file)
            return True

        else:
            if name in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine',
                            'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC',
                            'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl', 'Sense_DAC'}:
                if chip == 'default':
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'dacs.yml')
                else:
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'chip_dacs.yml')
            elif name in {'clk_fast_out', 'ClkOut_frequency_src'}:
                if chip == 'default':
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'outputBlock.yml')
                else:
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'chip_outputBlock.yml')
            elif name in {'Polarity', 'Op_mode', 'Fast_Io_en', 'AckCommand_en', 'SelectTP_Ext_Int'}:
                if chip == 'default':
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'GeneralConfiguration.yml')
                else:
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'chip_GeneralConfiguration.yml')
            elif name in {'clkphasediv', 'clkphasenum', 'PLLOutConfig'}:
                if chip == 'default':
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'PLLConfig.yml')
                else:
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'chip_PLLConfig.yml')
            else:
                yaml_file = None

            if not yaml_file == None:
                with open(yaml_file) as file:
                    yaml_data = yaml.load(file, Loader=yaml.FullLoader)
                if chip == 'default':
                    for register in yaml_data['registers']:
                        if register['name'] == name:
                            register['value'] = self.data['chip_dacs']['default'][name]
                    
                else:
                    for current_chip in yaml_data['chips']:
                        if chip == current_chip['chip_ID_decoded']:
                            for register in current_chip['registers']:
                                if register['name'] == name:
                                    register['value'] = self.data['chip_dacs'][chip][name]

                with open(yaml_file, 'w') as file:
                        yaml.dump(yaml_data, file)
                return True
            else:
                print('No known .yml contains the asked name.')
                return False

    def write_backup_to_yaml(self):

        dac_keys = ['Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk',
                    'Vthreshold_fine', 'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON',
                    'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse',
                    'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl', 'Sense_DAC']
        outputBlock_keys   = ['clk_fast_out', 'ClkOut_frequency_src']
        generalConfig_keys = ['Polarity', 'Op_mode', 'Fast_Io_en', 'AckCommand_en', 'SelectTP_Ext_Int']
        PLLConfig_keys     = ['clkphasediv', 'clkphasenum', 'PLLOutConfig']

        key_list          = [dac_keys, outputBlock_keys, generalConfig_keys, PLLConfig_keys]
        default_file_list = ['dacs.yml', 'outputBlock.yml', 'generalConfiguration.yml', 'PLLConfiguration.yml']
        chip_file_list    = ['chip_dacs.yml', 'chip_outputBlock.yml', 'chip_generalConfiguration.yml', 'chip_PLLConfiguration.yml']

        # Save links
        yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'links.yml')

        with open(yaml_file) as file:
            yaml_data = yaml.load(file, Loader=yaml.FullLoader)

        for i in range(8):
            label                     = f'Link_{i}'
            yaml_data['registers'][i] = self.data['Links'][label]
        
        with open(yaml_file, 'w') as file:
            yaml.dump(yaml_data, file)

        # Save DACs
        for i in range(4):
            default_file = os.path.join(self.current_path, 'tpx3' + os.sep + default_file_list[i])
            chip_file    = os.path.join(self.current_path, 'tpx3' + os.sep + chip_file_list[i])

            with open(default_file) as file:
                default_data = yaml.load(file, Loader=yaml.FullLoader)
            with open(chip_file) as file:
                chip_data = yaml.load(file, Loader=yaml.FullLoader)

            for chip_key in self.data['chip_dacs']:
                if chip_key == 'default':
                    for register in default_data['registers']:
                        if register['name'] in key_list[i]:
                            register['value'] = self.data['chip_dacs']['default'][register['name']]
                else:
                    for chip in chip_data['chips']:
                        if chip['chip_ID_decoded'] == chip_key:
                            for register in chip['registers']:
                                if register['name'] in key_list[i]:
                                    register['value'] = self.data['chip_dacs'][chip_key][register['name']]

            with open(default_file, 'w') as file:
                yaml.dump(default_data, file)
            with open(chip_file, 'w') as file:
                yaml.dump(chip_data, file)

        
        '''
        for key in self.data:
            if key in {'Chip0_name', 'Chip1_name', 'Chip2_name', 'Chip3_name', 'Chip4_name', 'Chip5_name', 'Chip6_name', 'Chip7_name'}:
                yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'links.yml')
                with open(yaml_file) as file:
                    yaml_data = yaml.load(file, Loader=yaml.FullLoader)
                value_list = self.data[key]
                if not value_list == [None]:
                    Chipname     = value_list[0]
                    wafer_number = ''
                    chip_coord2  = ''
                    for i in range (1, len(Chipname)):
                        if Chipname[i] == '-':
                            start_chipname = i
                    for i in range (1, start_chipname):
                        wafer_number = wafer_number + Chipname[i]
                    chip_coord1 = Chipname[start_chipname+1]
                    for i in range (start_chipname+2, len(Chipname)):
                        chip_coord2 = chip_coord2 + Chipname[i]

                    wafer_number = int(wafer_number)
                    chip_coord1  = ord(chip_coord1.lower()) - ord('a') + 1
                    chip_coord2  = int(chip_coord2)

                    Chip_ID = (wafer_number << 8) | (chip_coord2 << 4) | chip_coord1

                    for n in range(1, len(value_list)):
                        element_list = value_list[n]
                        element      = 'RX' + str(element_list[0])
                        fpga_link    = element_list[0]
                        chip_link    = element_list[1]
                        data_delay   = element_list[2]
                        data_invert  = element_list[3]
                        data_edge    = element_list[4]
                        # try except for compatibility with backups without link_status
                        try:
                            link_status = element_list[5]
                        except:
                            link_status = 0

                        for register in yaml_data['registers']:
                            if register['name'] == element:
                                register['fpga-link']   = fpga_link
                                register['chip-link']   = chip_link
                                register['chip-id']     = Chip_ID
                                register['data-delay']  = data_delay
                                register['data-invert'] = data_invert
                                register['data-edge']   = data_edge
                                register['link-status'] = link_status

                with open(yaml_file, 'w') as file:
                    yaml.dump(yaml_data, file)

            else:
                if key in {'Ibias_Preamp_ON', 'VPreamp_NCAS', 'Ibias_Ikrum', 'Vfbk', 'Vthreshold_fine', 'Vthreshold_coarse', 'Ibias_DiscS1_ON', 'Ibias_DiscS2_ON', 'Ibias_PixelDAC', 'Ibias_TPbufferIn', 'Ibias_TPbufferOut', 'VTP_coarse', 'VTP_fine', 'Ibias_CP_PLL', 'PLL_Vcntrl', 'Sense_DAC'}:
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'dacs.yml')

                elif key in {'clk_fast_out', 'ClkOut_frequency_src'}:
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'outputBlock.yml')

                elif key in {'Polarity', 'Op_mode', 'Fast_Io_en', 'AckCommand_en', 'SelectTP_Ext_Int'}:
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'GeneralConfiguration.yml')

                elif key in {'clkphasediv', 'clkphasenum', 'PLLOutConfig'}:
                    yaml_file = os.path.join(self.current_path, 'tpx3' + os.sep + 'PLLConfig.yml')
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
        '''


TPX3_datalogger = TPX3_data_logger()