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
if __name__ == '__main__':
    pass
