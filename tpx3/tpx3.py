#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import zlib # workaround
import yaml
import logging
import os
import time
import struct
import numpy as np
import tables as tb

import basil

from basil.dut import Dut
from basil.utils.BitLogic import BitLogic
from utils import toByteList

# add toByteList() method to BitLogic
BitLogic.toByteList = toByteList


import pkg_resources
VERSION = pkg_resources.get_distribution("tpx3-daq").version

loglevel = logging.DEBUG

''' Set up main logger '''
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
#logging.getLogger('basil.HL.RegisterHardwareLayer').setLevel(logging.WARNING)

logging.basicConfig(format="%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s")

logger = logging.getLogger('tpx3')
logger.setLevel(loglevel)


class TPX3(Dut):

    #'' Map hardware IDs for board identification '''
    #hw_map = {
    #    0: 'SIMULATION',
    #    1: 'MIO2',
    #}

    ################################################################################
    ### Some maps defining mappings of string names to binary / hex values #########
    ################################################################################
    # TODO: move to a YAML file, similar to e.g. basil/register_lookup.yaml ?

    # map defining the header values needed for different periphery operation commands
    periphery_header_map = {"SenseDACsel" : 0x00,
                            "ExtDACsel" : 0x01,
                            "SetDAC" : 0x02,
                            "ReadDAC" : 0x03,
                            # ^ DACs
                            # Fuse
                            "EFuse_Burn" : 0x08,
                            "EFuse_Read" : 0x09,
                            "EfuseRead_BurnConfig" : 0x0A,
                            # Timepix
                            "TP_Period" : 0x0C,
                            "TP_PulseNumber" : 0x0D,
                            "TPConfig_Read" : 0x0E,
                            "TP_internalfinished" : 0x0F,
                            # Output block
                            "OutBlockConfig" : 0x10,
                            "OutBlockConfig_Read" : 0x11,
                            # PLL Config
                            "PLLConfig" : 0x20,
                            "PLLConfig_Read" : 0x21,
                            # General config
                            "GeneralConfig" : 0x30,
                            "GeneralConfig_Read" : 0x31,
                            "SLVSConfig" : 0x34,
                            "SLVSConfig_Read" : 0x35,
                            "PowerPulsingPattern" : 0x3C,
                            "PowerPulsingConfig_Read" : 0x3D,
                            "PowerPulsingON_finished" : 0x3F,
                            # Timer
                            "ResetTimer" : 0x40,
                            "SetTimer_15_0" : 0x41,
                            "SetTimer_31_16" : 0x42,
                            "SetTimer_47_32" : 0x43,
                            "RequestTimeLow" : 0x44,
                            "RequestTimeHigh" : 0x45,
                            "TimeRisingShutterLow" : 0x46,
                            "TimeRisingShutterHigh" : 0x47,
                            "TimeFallingShutterLow" : 0x48,
                            "TimeFallingShutterHigh" : 0x49,
                            "T0_Sync_Command" : 0x4A,
                            # Control operation
                            "Acknlowledge" : 0x70,
                            "EndOfCommand" : 0x71,
                            "OtherChipCommand" : 0x72,
                            "WrongCommand" : 0x73}

    # DAC names
    # will have to be careful when using these, due to 5 bit value
    dac_map = {"Ibias_Preamp_ON" : 0b00001,
               "Ibias_Preamp_OFF" : 0b00010,
               "VPreamp_NCAS" : 0b00011,
               "Ibias_Ikrum" : 0b00100,
               "Vfbk" : 0b00101,
               "Vthreshold_fine" : 0b00110,
               "Vthreshold_coarse" : 0b00111,
               "Ibias_DiscS1_ON" : 0b01000,
               "Ibias_DiscS1_OFF" : 0b01001,
               "Ibias_DiscS2_ON" : 0b01010,
               "Ibias_DiscS2_OFF" : 0b01011,
               "Ibias_PixelDAC" : 0b01100,
               "Ibias_TPbufferIn" : 0b01101,
               "Ibias_TPbufferOut" : 0b01110,
               "VTP_coarse" : 0b01111,
               "VTP_fine" : 0b10000,
               "Ibias_CP_PLL" : 0b10001,
               "PLL_Vcntrl" : 0b10010}

    # number of bits a value for a DAC can have maximally
    DAC_VALUE_BITS = 9

    # DAC value size in bits
    dac_valsize_map = {"Ibias_Preamp_ON" :   8,
                       "Ibias_Preamp_OFF" :  4,
                       "VPreamp_NCAS" :      8,
                       "Ibias_Ikrum" :       8,
                       "Vfbk" :              8,
                       "Vthreshold_fine" :   9,
                       "Vthreshold_coarse" : 4,
                       "Ibias_DiscS1_ON" :   8,
                       "Ibias_DiscS1_OFF" :  4,
                       "Ibias_DiscS2_ON" :   8,
                       "Ibias_DiscS2_OFF" :  4,
                       "Ibias_PixelDAC" :    8,
                       "Ibias_TPbufferIn" :  8,
                       "Ibias_TPbufferOut" : 8,
                       "VTP_coarse" :        8,
                       "VTP_fine" :          9,
                       "Ibias_CP_PLL" :      8,
                       "PLL_Vcntrl" :        8}

    # monitoring voltage maps
    monitoring_map = {"PLL_Vcntrl" : 0b10010,
                      "BandGap output" : 0b11100,
                      "BandGap_Temp" : 0b11101,
                      "Ibias_dac" : 0b11110,
                      "Ibias_dac_cas" : 0b11111,
                      "SenseOFF" : 0b00000}


    def __init__(self, conf=None, **kwargs):

        self.proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if not conf:
            conf = os.path.join(self.proj_dir, 'tpx3' + os.sep + 'tpx3.yaml')

        logger.info("Loading configuration file from %s" % conf)

        super(TPX3, self).__init__(conf)


    def init(self):
        super(TPX3, self).init()

        #self.fw_version, self.board_version = self.get_daq_version()
        #logger.info('Found board %s running firmware version %s' % (self.hw_map[self.board_version], self.fw_version))
        #
        #if self.fw_version != VERSION[:3]:     #Compare only the first two digits
        #    raise Exception("Firmware version %s does not satisfy version requirements %s!)" % ( self.fw_version, VERSION))

        #self['CONF_SR'].set_size(3924)

        self['CONTROL']['DATA_MUX_SEL'] = 1
        self['CONTROL'].write()

        # dummy Chip ID, which will be replaced by some value read from a YAML file
        # for a specific Timepix3
        self.chipId = [0x00 for _ in range(4)]

    def getGlobalSyncHeader(self):
        """
        Returns the global sync header, which is used to address all available
        Timepix3 chips

        Outputs:
            list of 5 bytes corresponding to 40 bits
        """
        # 0xAA = global sync header
        return [0xAA] + [0x00 for _ in range(4)]

    def getLocalSyncHeader(self):
        """
        Returns the local sync header, which is used to address a specific Timepix3
        chip

        Outputs:
            list of 5 bytes corresponding to 40 bits
        """
        # 0x4E == local sync header
        return [0x4E] + self.chipId

    def set_dac(self, dac, value, chip = None, write = True):
        """
        Sets the DAC given by the name `dac` to value `value`.
        If `write` is `True`, we perform the write of the data immediately,
        else we return a string of the command.
        If `chip` is `None`, we send a global command, else a local command for
        the chip given by `chip`. Type yet undecided...

        Manual:
        SyncHeader[63:24] + {SetDAC_Code == 0x02}[23:16] + 0x00 + {DAC Value}[13:5] + {DAC Code}[4:0]

        Inputs:
            dac: string = name of the DAC
            value: int = value to set for the DAC
            chip: ? = determines whether local or global header used (individual or all chips)
            write: bool = if True, we write immediately, else we return the data array to perform
                the write with

        Outputs:
            list of 8 ints (64 bit) of the command, if `write` == False, else ack?
        """
        data = []
        # first header, first 40 bits [63:24]
        if chip == None:
            data = self.getGlobalSyncHeader()
        else:
            data = self.getLocalSyncHeader()

        # bit logic for final 24 bits
        bits = BitLogic(24)
        # append the code for the SetDAC command header: bits 23:16
        bits[23:16] = self.periphery_header_map["SetDAC"]

        # get number of bits for values in this DAC
        dac_value_size = self.dac_valsize_map[dac]
        if value >= (2 ** dac_value_size):
            # value for the DAC, check whether in allowed range
            raise ValueError("Value {} for DAC {} exceeds the maximum size of a {} bit value!".format(value, dac, dac_value_size))
        # safely set the data for the values

        # set the given value at positions indicated in manual
        bits[13:5] = value
        # final bits [4:0], DAC code
        bits[4:0] = self.dac_map[dac]
        # append bits as list of bytes
        data += bits.toByteList()

        data += [0x00]

        if write == True:
            raise NotImplementedError("Immediate write upon call of Tpx3.setDAC() not implemented yet.")
        else:
            return data

    def read_dac(self, dac, write = True):
        """
        Reads the DAC of name `dac` and returns a tuple of the read value and the
        name.

        Manual:
        SyncHeader[63:24] + {readDAC_Code == 0x03}[23:16] + {0}[15:5] + {DAC Code}[4:0]

        Inputs:
            dac: string = name of the DAC
            write: bool = if True, we write immediately, else we return the data array to perform
                the write with

        Outputs:
            If `write` == True, tuple of (DAC value, DAC name)
            Else: command to perform read
        """
        # TODO: change to local sync header later
        data = self.getGlobalSyncHeader()

        data += [self.periphery_header_map["ReadDAC"]]

        # add DAC code to last 4 bit of final 16 bit
        bits = BitLogic(16)
        bits[4:0] = self.dac_map[dac]
        # add 16 bits as list of byte to result
        data += bits.toByteList()

        data += [0x00]

        if write == True:
            raise NotImplementedError("Immediate write upon call of Tpx3.readDAC() not implemented yet.")
        else:
            return data

    def read_dac_exp(self, dac, value):
        """
        Debugging function. Returns the expected value of the DataOut after reading a DAC
        given some DAC `dac`, which should contain `value`
        NOTE: in fact the read data comes in w/ LSB first, so we need to reverse this (I guess?)!

        Manual:
        {readDAC_Code == 0x03}[47:40] + {0}[39:14] + {DAC Value}[13:5] + {DAC Code}[4:0]
        """
        # add read DAC command header [47:40]
        data = [self.periphery_header_map["ReadDAC"]]

        # get size of DAC value
        dac_value_size = self.dac_valsize_map[dac]
        if value >= (2 ** dac_value_size):
            # value for the DAC, check whether in allowed range
            raise ValueError("Value {} for DAC {} exceeds the maximum size of a {} bit value!".format(value, dac, dac_value_size))

        # create final 40 bit, most empty
        bits = BitLogic(40)

        # determine starting position in bits array, 13 starting pos
        bits_start = 13 - (self.DAC_VALUE_BITS - dac_value_size)
        bits[bits_start:5] = value

        bits[4:0] = self.dac_map[dac]
        # add 40 bits as list of bytes to result
        data += bits.toByteList()

        data += [0x00]
        return data
        
if __name__ == '__main__':
    pass
