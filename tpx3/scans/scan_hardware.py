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

def HardwareScan(progress = None, **kwargs):
    '''
        Scans over fpga and chip links and additionally over data delays to detect the optimal link settings.
        If progress is None a tqdm progress bar is used else progress should be a Multiprocess Queue which stores the progress as fraction of 1
        Stores the result in links.yml and returns a table of chips with a list of their links and settings.
    '''
    # Open the link yaml file
    proj_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    yaml_file =  os.path.join(proj_dir, 'tpx3' + os.sep + 'links.yml')

    if not yaml_file == None:
        with open(yaml_file) as file:
            yaml_data = yaml.load(file, Loader=yaml.FullLoader)

    # Initialize the chip communication
    chip = TPX3()
    chip.init()

    rx_list_names = ['RX0','RX1','RX2','RX3','RX4','RX5','RX6','RX7']

    if progress == None:
        # Initialize the progress bar
        pbar = tqdm(total = len(rx_list_names))
    else:
        # Initailize counter for progress
        step_counter = 0

    # Iterate over all fpga links
    for fpga_link_number, fpga_link in enumerate(rx_list_names):
        # Reset the chip
        chip['CONTROL']['RESET'] = 1
        chip['CONTROL'].write()
        chip['CONTROL']['RESET'] = 0
        chip['CONTROL'].write()

        # Write the PLL 
        data = chip.write_pll_config()

        # Iterate over all chip links
        for chip_link in range(8):
            link_found = False

            # Create the chip output channel mask and write the output block
            chip._outputBlocks["chan_mask"] = 0b1 << chip_link
            data = chip.write_outputBlock_config()

            # Iterate over all possible data delays
            for delay in range(32):

                # Deactivate all fpga links
                for i in range(len(rx_list_names)):
                    chip[rx_list_names[i]].ENABLE = 0
                    chip[rx_list_names[i]].reset()

                # Aktivate the current fpga link and set all its settings
                chip[fpga_link].ENABLE = 1
                chip[fpga_link].DATA_DELAY = delay
                chip[fpga_link].INVERT = 0
                chip[fpga_link].SAMPLING_EDGE = 0

                # Reset and clean the FIFO
                chip['FIFO'].reset()
                time.sleep(0.01)
                chip['FIFO'].get_data()

                # Send the EFuse_Read command multiple times for statistics
                for _ in range(50):
                    data = chip.read_periphery_template("EFuse_Read")
                    data += [0x00]*4
                    chip.write(data)

                # Only proceed for settings which lead to no decoder errors and a ready signal of the receiver
                if chip[fpga_link].get_decoder_error_counter() == 0 and chip[fpga_link].is_ready:
                    # Get the data from the chip
                    fdata = chip['FIFO'].get_data()
                    dout = chip.decode_fpga(fdata, True)

                    # Only proceed if we got the expected number of data packages
                    if len(dout) == 100:
                        link_found = True

                        # Store the settings
                        for register in yaml_data['registers']:
                            if register['name'] == fpga_link:
                                register['fpga-link'] = fpga_link_number
                                register['chip-link'] = chip_link
                                register['chip-id'] = dout[1][19:0].tovalue()
                                register['data-delay'] = delay
                                register['data-invert'] = 0
                                register['data-edge'] = 0

                        # Stop after the first working set of settings
                        break

            # Stop after the first working set of settings
            if link_found == True:
                break
            if chip_link == 7 and link_found == False:
                for register in yaml_data['registers']:
                    if register['name'] == fpga_link:
                        register['fpga-link'] = fpga_link_number
                        register['chip-link'] = 0
                        register['chip-id'] = 0
                        register['data-delay'] = 0
                        register['data-invert'] = 0
                        register['data-edge'] = 0

        if progress == None:
            # Update the progress bar
            pbar.update(1)
        else:
            # Update the progress fraction and put it in the queue
            step_counter += 1
            fraction = step_counter / (len(mask_cmds) * len(cal_high_range))
            progress.put(fraction)

        # Write the ideal settings to the yaml file
        with open(yaml_file, 'w') as file:
            yaml.dump(yaml_data, file)

    if progress == None:
        # Close the progress bar
        pbar.close()

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

    return Chip_List

if __name__ == "__main__":
    HardwareScan()