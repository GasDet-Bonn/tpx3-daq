#!/usr/bin/env python

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from tpx3.tpx3 import TPX3
from basil.utils.BitLogic import BitLogic
from six.moves import range
from tqdm import tqdm
import time
import os
import yaml
import numpy as np

class ScanHardware(object):
    def __init__(self):
        pass

    def start(self, results = None, progress = None, status = None, **kwargs):
        '''
            Scans over fpga and chip links and additionally over data delays to detect the optimal link settings.
            If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
            If there is a status queue information about the status of the scan are put into it
            Stores the result in links.yml and returns a table of chips with a list of their links and settings.
        '''
        # Open the link yaml file
        proj_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        yaml_file =  os.path.join(proj_dir, 'tpx3' + os.sep + 'links.yml')

        if not yaml_file == None:
            with open(yaml_file) as file:
                yaml_data = yaml.load(file, Loader=yaml.FullLoader)

        # Initialize the chip communication
        self.chip = TPX3()
        self.chip.init()

        rx_list_names = ['RX0','RX1','RX2','RX3','RX4','RX5','RX6','RX7']

        if progress == None:
            # Initialize the progress bar
            pbar = tqdm(total = len(rx_list_names))
        else:
            # Initailize counter for progress
            step_counter = 0

        if status != None:
            status.put("Starting scan")
        if status != None:
            status.put("iteration_symbol")

        # Reset the chip
        self.chip['CONTROL']['RESET'] = 1
        self.chip['CONTROL'].write()
        self.chip['CONTROL']['RESET'] = 0
        self.chip['CONTROL'].write()

        # Write the PLL 
        data = self.chip.write_pll_config()

        rx_map = np.zeros((8,8), np.int8)
        error_map = np.zeros((8, 32), np.int16)

        # Check for which combinations of FPGA and chip links the connection is ready
        for chip_link in range(8):
            # Create the chip output channel mask and write the output block
            self.chip._outputBlocks["chan_mask"] = 0b1 << chip_link
            data = self.chip.write_outputBlock_config()

            for fpga_link_number, fpga_link in enumerate(rx_list_names):
                self.chip[fpga_link].ENABLE = 0
                self.chip[fpga_link].reset()
                self.chip[fpga_link].ENABLE = 1
                rx_map[chip_link][fpga_link_number] = self.chip[fpga_link].is_ready

        # Check for each link individually for which delay settings there are no errors
        for chip_link in range(8):
            # Create the chip output channel mask and write the output block
            self.chip._outputBlocks["chan_mask"] = 0b1 << chip_link
            data = self.chip.write_outputBlock_config()

            for delay in range(32):
                for fpga_link_number, fpga_link in enumerate(rx_list_names):
                    self.chip[fpga_link].ENABLE = 0
                    self.chip[fpga_link].reset()
                    # Enable only the receiver which is connected to the current chip link
                    if rx_map[chip_link][fpga_link_number]:
                        self.chip[fpga_link].ENABLE = 1
                        self.chip[fpga_link].DATA_DELAY = delay
                        self.chip[fpga_link].INVERT = 0
                        self.chip[fpga_link].SAMPLING_EDGE = 0

                # Check the number of errors for the current setting
                for fpga_link_number, fpga_link in enumerate(rx_list_names):
                    if rx_map[chip_link][fpga_link_number]:
                        error_map[fpga_link_number][delay] = self.chip[fpga_link].get_decoder_error_counter()

            if progress == None:
                # Update the progress bar
                pbar.update(1)
            else:
                # Update the progress fraction and put it in the queue
                step_counter += 1
                fraction = step_counter / len(rx_list_names)
                progress.put(fraction)

        # Find for each receiver the delay with the most distance to a delay with errors
        delays = np.zeros(8, dtype=np.int8)
        for receiver in range(8):
            zero_error_map = np.where(error_map[receiver] == 0)[0]
            zero_delays = np.split(zero_error_map, np.where(zero_error_map[:-1] != zero_error_map[1:] - 1)[0])
            list_index = np.argmax(np.array([zero_delays[i].size for i in range(len(zero_delays))]))
            delays[receiver] = zero_delays[list_index][int(np.median(zero_delays[list_index]))]

        # Check for each receiver the ChipID of the connected chip
        Chip_IDs = np.zeros(8, dtype=np.int32)
        for fpga_link_number, fpga_link in enumerate(rx_list_names):
            # Deactiveate all receivers
            for fpga_link_2 in rx_list_names:
                self.chip[fpga_link_2].ENABLE = 0
                self.chip[fpga_link_2].reset()
            # Activate the current receivers
            self.chip[fpga_link].ENABLE = 1
            self.chip[fpga_link].DATA_DELAY = int(delays[fpga_link_number])
            self.chip[fpga_link].INVERT = 0
            self.chip[fpga_link].SAMPLING_EDGE = 0

            # Enable the corrresponding chip link
            for chip_link in range(8):
                if rx_map[chip_link][fpga_link_number]:
                    # Create the chip output channel mask and write the output block
                    self.chip._outputBlocks["chan_mask"] = 0b1 << chip_link
            data = self.chip.write_outputBlock_config()

            # Reset and clean the FIFO
            self.chip['FIFO'].reset()
            time.sleep(0.001)
            self.chip['FIFO'].get_data()

            # Send the EFuse_Read to receive the ChipID
            data = self.chip.read_periphery_template("EFuse_Read")
            data += [0x00]*4
            self.chip.write(data)

            # Get the ChipID from the received data packages
            fdata = self.chip['FIFO'].get_data()
            dout = self.chip.decode_fpga(fdata, True)
            Chip_IDs[fpga_link_number] = dout[1][19:0].tovalue()

        # Open the link yaml file
        proj_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        yaml_file =  os.path.join(proj_dir, 'tpx3' + os.sep + 'links.yml')

        if not yaml_file == None:
            with open(yaml_file) as file:
                yaml_data = yaml.load(file, Loader=yaml.FullLoader)

        # Write the registers based on the scan results
        for i, register in enumerate(yaml_data['registers']):
            register['name'] = rx_list_names[i]
            register['fpga-link'] = i
            register['chip-link'] = int(np.where(rx_map[:][i] == 1)[0][0])
            register['chip-id'] = int(Chip_IDs[i])
            register['data-delay'] = int(delays[i])
            register['data-invert'] = 0
            register['data-edge'] = 0

        # Write the ideal settings to the yaml file
        with open(yaml_file, 'w') as file:
            yaml.dump(yaml_data, file)

        # Create a list if unique Chip-ID strings and corresponding Chip-ID bits
        ID_List = []
        for register in yaml_data['registers']:
            bit_id = BitLogic.from_value(register['chip-id'])

            # Decode the Chip-ID
            wafer_number = bit_id[19:8].tovalue()
            x_position = chr(ord('a') + bit_id[3:0].tovalue() - 1).upper()
            y_position =bit_id[7:4].tovalue()
            ID = 'W' + str(wafer_number) + '-' + x_position + str(y_position)

            # Write new Chip-ID to the list
            if ID not in ID_List and register['chip-id'] != 0:
                ID_List.append([register['chip-id'], ID])

        # Create a list of Chips with all link settings for the specific chip
        Chip_List = []
        # Iterate over all links
        for register in yaml_data['registers']:
            for ID in ID_List:
                if ID[0] == register['chip-id']:
                    # If the list is empty or the current chip is not in the list add it with its settings
                    if len(Chip_List) == 0 or ID[1] not in Chip_List[:][0]:
                        Chip_List.append([ID[1], [register['fpga-link'], register['chip-link'], register['data-delay'], register['data-invert'], register['data-edge']]])

                    # If the Chip is already in the list just add the link settings to it
                    else:
                        for chip in Chip_List:
                            if ID[1] == chip[0]:
                                chip.append([register['fpga-link'], register['chip-link'], register['data-delay'], register['data-invert'], register['data-edge']])
                    break

        if results == None:
            print(Chip_List)
            return Chip_List
        else:
            results.put([self.chip.fw_version] + Chip_List)


    def analyze(self, **kwargs):
        raise NotImplementedError('scan_hardware.analyze() not implemented')

    def plot(self, **kwargs):
        raise NotImplementedError('scan_hardware.analyze() not implemented')

if __name__ == "__main__":
    scan = ScanHardware()
    scan.start()