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

class ChipIDError(Exception):
    pass

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
        status_map = np.zeros(8, np.int8)

        # Check for which combinations of FPGA and chip links the connection is ready
        for chip_link in range(8):
            # Create the chip output channel mask and write the output block
            self.chip._outputBlocks["chan_mask"] = 0b1 << chip_link
            data = self.chip.write_outputBlock_config()

            for fpga_link_number, fpga_link in enumerate(rx_list_names):
                rx_map[chip_link][fpga_link_number] = self.chip[fpga_link].is_ready

        status_map = np.sum(rx_map, axis = 0)
        status_map = np.clip(status_map, 0, 1)

        for fpga_link_number, fpga_link in enumerate(rx_list_names):
            self.chip._outputBlocks["chan_mask"] = 0b00000000
            data = self.chip.write_outputBlock_config()
            self.chip[fpga_link].ENABLE = 0

        # Test if links see data when everything is switched off
        noisy_map = np.zeros(8, np.int8)
        for i in range(500):
            for fpga_link_number, fpga_link in enumerate(rx_list_names):
                noisy_map[fpga_link_number] += self.chip[fpga_link].is_ready

        # Mark links that show data when everything is off as borken zero patter (status 6)
        for fpga_link_number, fpga_link in enumerate(rx_list_names):
            if noisy_map[fpga_link_number] > 0:
                status_map[fpga_link_number] = 6

        # Check for each link individually for which delay settings there are no errors
        for fpga_link_number, fpga_link in enumerate(rx_list_names):
            # Do this check only on links which are connected and show no errors sofar
            if status_map[fpga_link_number] == 1:
                self.chip._outputBlocks["chan_mask"] = 0b1 << int(np.where(rx_map == 1)[0][fpga_link_number])
                data = self.chip.write_outputBlock_config()

                for delay in range(32):
                    self.chip[fpga_link].ENABLE = 0
                    self.chip[fpga_link].reset()
                    self.chip[fpga_link].ENABLE = 1
                    self.chip[fpga_link].DATA_DELAY = delay
                    self.chip[fpga_link].INVERT = 0
                    self.chip[fpga_link].SAMPLING_EDGE = 0

                    # Check the number of errors for the current setting
                    error_map[fpga_link_number][delay] = self.chip[fpga_link].get_decoder_error_counter()
                    self.chip[fpga_link].ENABLE = 0

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
            if status_map[fpga_link_number] == 1:
                zero_error_map = np.where(error_map[receiver] == 0)[0]
                # If there is no delay without errors set the link status to 4 (Connected, No delay without errors, Off)
                if len(zero_error_map) == 0:
                    status_map[receiver] = 4
                    continue
                zero_delays = np.split(zero_error_map, np.where(zero_error_map[:-1] != zero_error_map[1:] - 1)[0])
                list_index = np.argmax(np.array([zero_delays[i].size for i in range(len(zero_delays))]))
                delays[receiver] = int(np.median(zero_delays[list_index]))

        # Check for each receiver the ChipID of the connected chip
        Chip_IDs = np.zeros(8, dtype=np.int32)
        for fpga_link_number, fpga_link in enumerate(rx_list_names):
            if status_map[fpga_link_number] == 0:
                Chip_IDs[fpga_link_number] = 0
                continue

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

            try:
                # Get the ChipID from the received data packages
                fdata = self.chip['FIFO'].get_data()
                if len(fdata) < 4:
                    raise ChipIDError("ChipIDError: Unexpected amount of response packages")
                elif (fdata[2] & 0xff000000) >> 24 != ((fpga_link_number << 1) + 1) or (fdata[3] & 0xff000000) >> 24 != ((fpga_link_number << 1) + 0):
                    raise ChipIDError("ChipIDError: Unexpected headers in response packages")
                dout = self.chip.decode_fpga(fdata, True)
                Chip_IDs[fpga_link_number] = dout[1][19:0].tovalue()
            except Exception as a:
                # If there is no valid ChipID set the ID to 0 and set the corresponding status (8)
                Chip_IDs[fpga_link_number] = 0
                status_map[fpga_link_number] = 8
            self.chip[fpga_link].ENABLE = 0

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
            register['link-status'] = int(status_map[i])

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
            if register['chip-id'] not in ID_List:
                ID_List.append([register['chip-id'], ID])

        # Create a list of Chips with all link settings for the specific chip
        Chip_List = []
        # Iterate over all links
        for register in yaml_data['registers']:
            for ID in ID_List:
                if ID[0] == register['chip-id']:
                    # If the list is empty or the current chip is not in the list add it with its settings
                    if len(Chip_List) == 0 or ID[1] not in Chip_List[:][0]:
                        if register['link-status'] != 0:
                            Chip_List.append([ID[1], [register['fpga-link'], register['chip-link'], register['data-delay'], register['data-invert'], register['data-edge'], register['link-status']]])
                        else:
                            Chip_List.append([ID[1], [register['fpga-link'], 0, 0, 0, 0, register['link-status']]])

                    # If the Chip is already in the list just add the link settings to it
                    else:
                        for chip in Chip_List:
                            if ID[1] == chip[0]:
                                if register['link-status'] != 0:
                                    chip.append([register['fpga-link'], register['chip-link'], register['data-delay'], register['data-invert'], register['data-edge'], register['link-status']])
                                else:
                                    chip.append([register['fpga-link'], 0, 0, 0, 0, register['link-status']])
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