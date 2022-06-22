#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
import zlib  # workaround
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
from .utils import toByteList, bitword_to_byte_list, threshold_decompose
from io import open
import six
from six.moves import range

# add toByteList() method to BitLogic
BitLogic.toByteList = toByteList

# some defaults...
TPX3_SLEEP = 0.001


import pkg_resources
VERSION = pkg_resources.get_distribution("tpx3-daq").version

loglevel = logging.DEBUG

''' Set up main logger '''
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
# logging.getLogger('basil.HL.RegisterHardwareLayer').setLevel(logging.WARNING)

logging.basicConfig(format="%(asctime)s - [%(name)-15s] - %(levelname)-7s %(message)s")

logger = logging.getLogger('tpx3')
logger.setLevel(loglevel)


customDictErrors = {
    "DacsDict" :
    { "invalidKey"  : "DAC with name {} does not exist!",
      "invalidSize" : "DAC value of {} for DAC {} is too large for size of {}",
      "negativeVal" : "DAC value for {} DAC may not be negative!" },
    "ConfigDict" :
    {
        "invalidKey"  : "Config with name {} does not exist!",
        "invalidSize" : "Config value of {} for Configuration {} is too large for size of {}",
        "negativeVal" : "Config value for {} Configuration may not be negative!"
    },
    "OutputBlockDict" :
    {
        "invalidKey"  : "OutputBlock with name {} does not exist!",
        "invalidSize" : "OutputBlock value of {} for OutputBlock {} is too large for size of {}",
        "negativeVal" : "OutputBlock value for {} OutputBlock may not be negative!"
    },
    "PLLConfigDict" :
    {
        "invalidKey"  : "PLLConfig with name {} does not exist!",
        "invalidSize" : "PLLConfig value of {} for PLLConfig {} is too large for size of {}",
        "negativeVal" : "PLLConfig value for {} PLLConfig may not be negative!"
    }
}

# a dictionary containing the attribute names of the different
# custom dictionaries and the corresponding dictionaries containing
# the data from the YAML files
dictNames = {
    "ConfigDict" : {
        "CustomDict" : "_configs",
        "YamlContent" : "config",
        "Filename" : ("GeneralConfiguration.yml" if self.chipID == None else "chip_GeneralConfiguration.yml"),
        "FnameVar" : "config_file"
    },
    "DacsDict" : {
        "CustomDict" : "_dacs",
        "YamlContent" : "dac",
        "Filename" : ("dacs.yml" if self.chipID == None else "chip_dacs.yml"),
        "FnameVar" : "dac_file"
    },
    "OutputBlockDict" : {
        "CustomDict" : "_outputBlocks",
        "YamlContent" : "outputBlock",
        "Filename" : ("outputBlock.yml" if self.chipID == None else "chip_outputBlock.yml"),
        "FnameVar" : "outputBlock_file"
    },
    "PLLConfigDict" : {
        "CustomDict" : "_PLLConfigs",
        "YamlContent" : "PLLConfigDict",
        "Filename" : ("PLLConfig.yml" if self.chipID == None else "chip_PLLconfig.yml"),
        "FnameVar" : "PLLConfig_file"
    }
}

class CustomDict(dict):
    """
    A custom dictionary class, used for the DACs, the general and the output
    config of Timepix3, which overrides the __setitem__ class of a dictionary
    to also make a check for the validity of a given value for a dictionary
    """
    def __init__(self, valsize_map, dict_type):
        """
        as initialization we need the allowed sizes of each DAC / value for each config
        """
        self.valsize_map = valsize_map
        self.dictErrors  = customDictErrors[dict_type]

    def __setitem__(self, key, value):
        """
        Override the __setitem__ function of the dictionary and check the size
        of the given value. Else raise a ValueError
        """
        # check if valid by checking size smaller than max value
        isValidKey = True if key in list(self.valsize_map.keys()) else False
        if not isValidKey:
            raise KeyError(self.dictErrors['invalidKey'].format(key))
        isValid = True if value < 2 ** self.valsize_map[key] and value >= 0 else False
        if isValid and isValidKey:
            super(CustomDict, self).__setitem__(key, value)
        elif isValid == False:
            if value >= 0:
                raise ValueError(
                    self.dictErrors['invalidSize'].format(value,
                                                          key,
                                                          self.valsize_map[key])
                )
            else:
                raise ValueError(self.dictErrors['negativeVal'].format(key))

class TPX3():

    ''' Map hardware IDs for board identification '''
    hw_map = {
        1: 'SIMULATION',
        2: 'FECv6',
        3: 'ML605',
        4: 'MIMAS_A7'
    }

    ''' Compatible firware version '''
    fw_version_required = 3

    ################################################################################
    ### Some maps defining mappings of string names to binary / hex values #########
    ################################################################################
    # TODO: move to a YAML file, similar to e.g. basil/register_lookup.yaml ?

    # map defining the header values needed for different periphery operation commands
    periphery_header_map = {"SenseDACsel": 0x00,
                            "ExtDACsel": 0x01,
                            "SetDAC": 0x02,
                            "ReadDAC": 0x03,
                            # ^ DACs
                            # Fuse
                            "EFuse_Burn": 0x08,
                            "EFuse_Read": 0x09,
                            "EfuseRead_BurnConfig": 0x0A,
                            # Timepix
                            "TP_Period": 0x0C,
                            "TP_PulseNumber": 0x0D,
                            "TPConfig_Read": 0x0E,
                            "TP_internalfinished": 0x0F,
                            # Output block
                            "OutBlockConfig": 0x10,
                            "OutBlockConfig_Read": 0x11,
                            # PLL Config
                            "PLLConfig": 0x20,
                            "PLLConfig_Read": 0x21,
                            # General config
                            "GeneralConfig": 0x30,
                            "GeneralConfig_Read": 0x31,
                            "SLVSConfig": 0x34,
                            "SLVSConfig_Read": 0x35,
                            "PowerPulsingPattern": 0x3C,
                            "PowerPulsingConfig_Read": 0x3D,
                            "PowerPulsingON_finished": 0x3F,
                            # Timer
                            "ResetTimer": 0x40,
                            "SetTimer_15_0": 0x41,
                            "SetTimer_31_16": 0x42,
                            "SetTimer_47_32": 0x43,
                            "RequestTimeLow": 0x44,
                            "RequestTimeHigh": 0x45,
                            "TimeRisingShutterLow": 0x46,
                            "TimeRisingShutterHigh": 0x47,
                            "TimeFallingShutterLow": 0x48,
                            "TimeFallingShutterHigh": 0x49,
                            "T0_Sync_Command": 0x4A,
                            # Control operation
                            "Acknlowledge": 0x70,
                            "EndOfCommand": 0x71,
                            "OtherChipCommand": 0x72,
                            "WrongCommand": 0x73}

    # map defining the header values needed for different matrix operation commands
    matrix_header_map = {"LoadConfigMatrix": 0x80,
                         "ReadConfigMatrix": 0x90,
                         "ReadMatrixSequential": 0xA0,
                         "ReadMatrixDataDriven": 0xB0,
                         "LoadCTPR": 0xC0,
                         "ReadCTPR": 0xD0,
                         "ResetSequential": 0xE0,
                         "StopMatrixCommand": 0xF0}

    # number of bits a value for a DAC can have maximally
    DAC_VALUE_BITS = 9

    # PCR Definitions
    MASK_ON  = 0
    MASK_OFF = 1
    TP_ON    = 1
    TP_OFF   = 0

    def __init__(self, conf=None, **kwargs):

        self.proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.lfsr_10  = {}
        self.lfsr_14  = {}
        self.lfsr_4   = {}

    def init(self, ChipId=None, inter_layer=None, config_file=None, dac_file=None, outputBlock_file=None, PLLConfig_file=None):
        
        if inter_layer != None:
            self.Dut_layer     = inter_layer
            self.fw_version    = self.Dut_layer['intf'].read(0x0000, 1)[0]
            self.board_version = self.hw_map[self.Dut_layer['intf'].read(0x0001, 1)[0]]

            logger.info('Found board %s running firmware version %d.' % (self.board_version, self.fw_version))

            if self.fw_version != self.fw_version_required:
                raise Exception("Firmware version %s does not satisfy version requirements %s!)" % ( self.fw_version, VERSION))

            # self['CONF_SR'].set_size(3924)

            self.Dut_layer['CONTROL']['DATA_MUX_SEL'] = 1
            self.Dut_layer['CONTROL'].write()
        
        # dummy Chip ID, which will be replaced by some value read from a YAML file
        # for a specific Timepix3
        # Our current chip seems to think its chip ID is all 0s. ?!
        #self.chipId = [0x00 for _ in range(3)] + [0x01]

        # When creating TPX3 object without a chipId (ChipId=None),
        # every function uses global sync header.
        # If we create TPX3 object with a chipId (or if we set chipId after init),
        # every function uses local sync header.
        self.chipId = ChipId
        # reset all matrices to empty defaults
        self.reset_matrices()

        # set all configuration attributes to their default values, also sets
        # the `config_written_to_chip` flag to False
        self.lfsr_10_bit()
        self.lfsr_14_bit()
        self.lfsr_4_bit()

        # assign filenames so we can check them
        self.config_file      = config_file
        self.dac_file         = dac_file
        self.outputBlock_file = outputBlock_file
        self.PLLConfig_file   = PLLConfig_file

        for dict_type, type_dict in six.iteritems(dictNames):
            setattr(self, type_dict["YamlContent"], {})
            # get the name of the variable, which stores the filename, e.g. `config_file`
            var_name = type_dict["FnameVar"]
            if getattr(self, var_name) is None:
                setattr(
                    self,
                    var_name,
                    os.path.join(self.proj_dir, 'tpx3' + os.sep + type_dict["Filename"])
                )

            # read the general configuration from the YAML file and set the _configs dictionary
            # to the values given by the 'value' field (i.e. the user desired setting)
            # read all 3 YAML files for config registers, DACS and the output block configuration
            self.read_yaml(getattr(self, var_name), dict_type)

    def reset_matrices(self, test=True, thr=True, mask=True, tot=True,
                       toa=True, ftoa=True, hits=True):
        """
        resets all matrices to default
        """
        # set the test matrix with zeros for all pixels
        if test:
            self.test_matrix = np.zeros((256, 256), dtype=int)
        # set the thr matrix with zeros for all pixels
        if thr:
            self.thr_matrix = np.full((256, 256), dtype=np.uint8, fill_value=8)
        # set the mask matrix with zeros for all pixels
        if mask:
            self.mask_matrix = np.zeros((256, 256), dtype=np.bool)
        # matrix storing ToT (= Time over Threshold) values of this Tpx3
        # 8 bit values
        if tot:
            self.tot = np.zeros((256, 256), dtype=np.int8)
        # matrix storing ToA (= Time of Arrival) values of this Tpx3
        # 12 bit values
        if toa:
            self.toa = np.zeros((256, 256), dtype=np.int16)
        # matrix storing fToA (= fast Time of Arrival; see manual v1.9 p.10) used if
        # VCO is on
        # 4 bit values
        if ftoa:
            self.ftoa = np.zeros((256, 256), dtype=np.int8)
        # matrix storing hit counts of each pixel, if a hit happened without ToA and
        # ToT being registered, i.e. two hits happening too close to one another
        # 4 bit values
        if hits:
            self.hits = np.zeros((256, 256), dtype=np.int8)


    def reset_attributes(self, dict_type, to_default=False):
        """
        Resets all attributes of the given dictionary (cased on `dict_type`, either
        _configs, _outputBlocks or _dacs) to their default values if `to_default` is
        True, else we reset the values to the `value` field of the YAML file,
        i.e. the user desired chip specific settings.
        """
        # build the correct attribute name based on dictNames "YamlContent" string
        var_name = dictNames[dict_type]["YamlContent"] + "_written_to_chip"
        # set this to False (Note: not used so far)
        setattr(self, var_name, False)

        yaml_dict = getattr(self, dictNames[dict_type]["YamlContent"])
        c_dict = getattr(self, dictNames[dict_type]["CustomDict"])
        for k, v in six.iteritems(yaml_dict):
            if to_default:
                c_dict[k] = v['default']
            else:
                c_dict[k] = v['value']

        # set c_dict back as the correct CustomDict
        setattr(self, dictNames[dict_type]["CustomDict"], c_dict)

    # based on above proc, define methods with easier names to work with
    def reset_config_attributes(self, to_default=False):
        self.reset_attributes("ConfigDict", to_default)

    def reset_outputBlock_attributes(self, to_default=False):
        self.reset_attributes("OutputBlockDict", to_default)

    def reset_dac_attributes(self, to_default=False):
        self.reset_attributes("DacsDict", to_default)

    def reset_PLLConfig_attributes(self, to_default=False):
        self.reset_attributes("PLLConfigDict", to_default)

    def read_yaml(self, filename, dict_type):
        """
        This function reads a given YAML file, stores each register in
        a small dictionary containing its values. Depending on the
        `dict_type` it generically creates a custom dictionary of the correct
        type, writes the user defined values of the YAML file to that dictionary
        and assigns it to the correct attribute, taken from the dictNames global
        variable.
        """
        data = yaml.load(open(filename, 'r'), Loader=yaml.FullLoader)

        # map storing the allowed sizes of each value
        valsize_map = {}
        # define a list of the different keys we have in each YAML file
        elements = ["address", "size", "default", "value"]
        # first fill this dictionary
        outdict = {}
        # iterate over all registers, build small dictionary for
        # each register and assign to full dictionary
        for register in data['registers']:
            tmp_dict = {}
            for key in elements:
                tmp_dict[key] = register[key]
            outdict[register['name']]  = tmp_dict
            valsize_map[register['name']] = int(tmp_dict['size'])
        # now create the correct custom dict
        c_dict = CustomDict(valsize_map, dict_type)

        # now write values to this dictionary
        for k, v in six.iteritems(outdict):
            c_dict[k] = v['value']

        # set the (now filled) custom dict as attribute
        setattr(self, dictNames[dict_type]["CustomDict"], c_dict)
        # and set the dict containing the YAML content
        setattr(self, dictNames[dict_type]["YamlContent"], outdict)

        # now set the `_written_to_chip` variables as attributes, init with False
        var_name = dictNames[dict_type]["YamlContent"] + "_written_to_chip"
        # set this to False (Note: not used so far)
        setattr(self, var_name, False)
    
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
        # 0xE4 == local sync header
        return [0xE4] + self.chipId

    @property
    def dacs(self):
        """
        Getter function for the `dacs` dictionary of the Tpx3 class.
        With this a `self.dacs[<DAC name>]` statement will return the value
        of the DAC stored in the `DactDict` dictionary _dacs
        """
        return self._dacs

    @property
    def configs(self):
        """
        Getter function for the `config` dictionary of the Tpx3 class.
        With this a `self.config[<config name>]` statement will return
        the value of the general config register stored in the `ConfigDict`
        dictionary _configs
        """
        return self._configs

    @property
    def outputBlocks(self):
        """
        Getter function for the `outputBlock` dictionary of the Tpx3 class.
        With this a `self.outputBlock[<outputBlock name>]` statement will
        return the value of the outputBlock register stored in the `OutputBlockDict`
        dictionary _outputBlocks
        """
        return self._outputBlocks

    @property
    def PLLConfigs(self):
        """
        Getter function for the `PLLConfig` dictionary of the Tpx3 class.
        With this a `self.PLLConfig[<PLLConfig name>]` statement will
        return the value of the PLLConfig register stored in the `PLLConfigDict`
        dictionary _PLLConfigs
        """
        return self._PLLConfigs

    def write_dacs(self):
        """
        A convenience function, which simply writes all DAC values, by iterating over
        the internal _dacs dictionary and calling `write` for each.
        """
        # Note: here we can now iterate over self.dacs instead of self._dacs
        # due to the `dacs` property!
        data = []

        for dac, val in six.iteritems(self.dacs):
            if dac != 'Sense_DAC':
                data.append(self.set_dac(dac, val, write = False))
                #self.write(data, True)
            else:
                data.append(self.sense_dac_sel(dac = val, write = False))
                #self.write(data, True)
        
        return data

    def read_dacs(self):
        """
        A convenience function to read back all DACs, print them and compare with the
        values we have stored in the _dacs DactDict dictionary
        Besides printing the DAC names, codes and EoC for the read_dac command,
        it also prints the expected value (the one we wrote before, i.e. contained
        in the _dacs dictionary) and the value we read back.
        Then we assert that this is actually the same value.
        """
        # TODO: currently we compare with the values of the _dacs dictionary. However,
        # since we currently never check whether the _dacs dict is written to the chip
        # this may fail!
        if self.dac_written_to_chip == False:
            print("The assertion in the following loop may fail, since we are not",
                  " may not have written the DAC values to the chip!")

        for dac, val in six.iteritems(self.dacs):
            data = self.read_dac(dac, False)
            self.write(data, True)
            print("Wrote {} to dac {}".format(data, dac))
            print("\tGet DAC value, DAC code and EoC:")
            dout  = self.decode_fpga(self.Dut_layer['FIFO'].get_data(), True)
            b     = BitLogic(9)
            b[:]  = val
            ddout = self.decode(dout[0], 0x03)
            # TODO: this whole decode and printing can be made much nicer!!
            print("Data is ", ddout[0][13:5], " wrote ", b)
            # assert we read the correct values we wrote before
            assert(ddout[0][13:5].tovalue() == b.tovalue())

    # TODO: add the given values to the _dacs dictionary, if this function is used!
    def set_dac(self, dac, value, write=True):
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
        if self.chipId != None:
            data = self.getLocalSyncHeader()
        else:
            data = self.getGlobalSyncHeader()

        # bit logic for final 24 bits
        bits        = BitLogic(24)
        # append the code for the SetDAC command header: bits 23:16
        bits[23:16] = self.periphery_header_map["SetDAC"]

        # get number of bits for values in this DAC
        dac_value_size = self.dac[dac]['size']
        if value >= (2 ** dac_value_size):
            # value for the DAC, check whether in allowed range
            raise ValueError("Value {} for DAC {} exceeds the maximum size of a {} bit value!".format(value, dac, dac_value_size))
        # safely set the data for the values

        # set the given value at positions indicated in manual
        bits[13:5] = value
        # final bits [4:0], DAC code
        bits[4:0]  = self.dac[dac]['address']
        # append bits as list of bytes
        data += bits.toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        else:
            return data

    def read_dac(self, dac, write=True):
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
        if self.chipId != None:
            data = self.getLocalSyncHeader()
        else:
            data = self.getGlobalSyncHeader()  

        data += [self.periphery_header_map["ReadDAC"]]

        # add DAC code to last 4 bit of final 16 bit
        bits      = BitLogic(16)
        bits[4:0] = self.dac[dac]['address']
        # add 16 bits as list of byte to result
        data += bits.toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
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
        dac_value_size = self.dac[dac]['size']
        if value >= (2 ** dac_value_size):
            # value for the DAC, check whether in allowed range
            raise ValueError("Value {} for DAC {} exceeds the maximum size of a {} bit value!".format(value, dac, dac_value_size))

        # create final 40 bit, most empty
        bits = BitLogic(40)

        # determine starting position in bits array, 13 starting pos
        bits_start         = 13 - (self.DAC_VALUE_BITS - dac_value_size)
        bits[bits_start:5] = value

        bits[4:0]          = self.dac[dac]['address']
        # add 40 bits as list of bytes to result
        data += bits.toByteList()

        data += [0x00]
        return data

    def sense_dac_sel(self, dac, write=True):
        """
        Sets the DAC which is connected to the DACout pad. One can select either the
        DACs or the monitoring voltages. As default the DACout pad is not connected.
        (see manual v1.9 p.34)
        """
        # TODO: change to local sync header later
        if self.chipId != None:
            data = self.getLocalSyncHeader()
        else:
            data = self.getGlobalSyncHeader()
        data += [self.periphery_header_map["SenseDACsel"]]

        # add DAC code to last 4 bit of final 16 bit
        bits      = BitLogic(16)
        bits[4:0] = dac
        # add 16 bits as list of byte to result
        data += bits.toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        else:
            return data

    def write(self, data, clear_fifo=False):
        """
        Performs a write of `data` on the SPI interface to the Tpx3.
        Note: this function is blocking until the write is complete.
        Inputs:
            data: list of bytes to write. MSB is first element of list
            clear_fifo: bool = if True, we clear the FIFO and wait before and
                after writing to the chip
        """

        if isinstance(data[0], list):
            for indata in data:
                self.write(indata, clear_fifo)
            return

        if clear_fifo:
            self.Dut_layer['FIFO'].RESET
            time.sleep(TPX3_SLEEP)

        # total size in bits
        self.Dut_layer['SPI'].set_size(len(data) * 8)
        self.Dut_layer['SPI'].set_data(data)
        self.Dut_layer['SPI'].start()

        while(not self.Dut_layer['SPI'].is_ready):
            # wait until SPI is done
            pass

        if clear_fifo:
            time.sleep(TPX3_SLEEP)

    def decode_fpga(self, data, string=False):
        """
        Performs a decoding of a raw 48 bit word received from the FPGA in decoded
        2 * 32bit form. Output is interpreted, i.e. split into different components
        Note:
        By default the Tpx3 uses 8b10b mode (8 bit values represented by 10 bit
        values to keep number of 0's and 1's even). In that mode it sends 60 bit
        packets (manual v1.9 wrongly states 64 bit!) ~= 6 byte of data. The
        firmware performs the decoding of the 60bit -> 48bit.
        Data is repackaged into 2 * 32bit words, consisting of
          [32 bit] == [header: 8bit | data: 24bit].
        The 48bits are packaged as follows:
          [48 bit] == [a: 24bit | b: 24bit] transforms as:
            -> d1 = [h: 1 | reversedBytes(b)]
            -> d2 = [h: 0 | reversedBytes(a)]
        i.e. reconstruction of 48 bits given the two 32 bit words, indexed in bytes as:
          [48 bit] == d2[3] + d2[2] + d2[1] + d1[3] + d1[2] + d1[1]
        Depending on the used command the first 4 bits or all bits of d2[3] contain the
        command header (see manual v1.9 p.28)
        A list of 48 bit bitarrays for each word is returned.
        """

        # remove data that belongs to the timestamp
        data = np.asarray([data_part for data_part in data if ((data_part & 0xF0000000) >> 28) != 0b0101],dtype=np.uint32)

        # determine number of 48bit words
        assert len(data) % 2 == 0, "Missing one 32bit subword of a 48bit package"
        nwords = len(data) // 2
        result = []

        for i in range(nwords):
            # create a 48 bit bitarrray for the current 48 bit word
            dataout = BitLogic(48)

            # transform the header and data of the 32 bit words lists of bytes
            d1 = bitword_to_byte_list(int(data[2 * i]), string)
            d2 = bitword_to_byte_list(int(data[2 * i + 1]), string)

            # use the byte lists to construct the dataout bitarray (d2[0] and d1[0]
            # contain the header which is not needed).
            dataout[47:40] = d2[3]
            dataout[39:32] = d2[2]
            dataout[31:24] = d2[1]
            dataout[23:16] = d1[3]
            dataout[15:8]  = d1[2]
            dataout[7:0]   = d1[1]

            # add the bitarray for the current 48 bit word to the output list
            result.append(dataout)

        return result

    def decode(self, data, command_header):
        """
        Given a FPGA decoded 48 bit word given as a bitarray, perform a decoding based on
        - the header of the 48 bit words (case machine based on manual v1.9 p.28
        - that read data correctly.
          This is done by first comparing the expected command header with the
          header which is part of the data. In a second step the data is split
          into a list of bitarrays based on the formation of the different packets
          (see manual v1.9 p.28).

        The following lists are used:

                                    dataout[0]      dataout[1]      dataout[2]      dataout[3]
         - Acquisition*:            Address[15:0]   TOA[13:0]       TOT[9:0]        FTOA[3:0]
         - @ data readout:          Dummy[43:0]         -               -               -
         - CTPR configuration:      Address[6:0]    EoC[17:0]       CTPR[1:0]           -
         - Pixel configuration:     Address[15:0]   Config[5:0]         -               -
         - Periphery command:       DataOut[39:0]       -               -               -
         - Control command:         H1,H2,H3[7:0]   ChipID[31:0]        -               -

         * Note that for acquisition the meaning of dataout[1] to dataout[3] depends on the
           settings of the general config registers 'Op_mode' and 'Fast_Io_en' (see manual
           v1.9 p.40). The composition of the list is independent of this, only the
           interpretation must change accordingly.
        """
        if len(data) != 48:
            raise ValueError("The data must contain 48 bits and not {}!".format(len(data)))

        # create a bitarray for the the header (8 bit)
        header = BitLogic(8)

        # The command header is always a byte but for pixel matrix operations only bits 7 to 4 are part of the
        # data packets because bits 3 to 0 are all 0. Furthermore pixel matrix operation headers have always
        # bit 7 as 1 while periphery and control commands have always bit 7 as 0 (see manual v1.9 p.32).
        if data[47] is True:
            # Pixel matrix operations: Only bits 7 to 4 are part of the data, bits 3 to 0 are 0
            header[7:4] = data[47:44]
        else:
            # Periphery and control commands: Get full header from the data
            header[7:0] = data[47:40]

        # Check if the expected and the received header are the same
        if header.tovalue() is command_header:
            # If the header is a acquisition header dataout is the following list:
            # [address - 16 bit, TOA (or iTOT) - 14 bit, TOT (or dummy or EventCounter) - 10 bit, FTOA (or dummy or HitCounter) - 4 bit]
            if header[7:5].tovalue() == 0b101:
                address    = data[43:28]
                TOA        = data[27:14]
                TOT        = data[13:4]
                HitCounter = data[3:0]
                dataout    = [address, TOA, TOT, HitCounter]
            # If the header is a Stop matrix readout or a reset sequential header dataout is the following list:
            # [dummy - 44 bit]
            elif header[7:5].tovalue() == 0b111:
                dataout = [data[43:0]]
            # If the header is the CTPR configuration header dataout is the following list:
            # [address - 7 bit, EoC - 18 bit, CTPR - 2 bit]
            elif header[7:5].tovalue() == 0b110:
                address = data[43:37]
                EoC     = data[27:10]
                CTPR    = data[1:0]
                dataout = [address, EoC, CTPR]
            # If the header is the pixel configuration header dataout is the following list:
            # [address - 14 bit, Config - 6 bit]
            elif header[7:5].tovalue() == 0b100:
                address = data[43:28]
                Config  = data[19:14]
                dataout = [address, Config]
            # If the header is a control command header dataout is the following list:
            # [H1H2H3 - 8 bit, ChipID - 32 bit]
            elif header[7:5].tovalue() == 0b011:
                ReturnedHeader = data[39:32]
                ChipID         = data[31:0]
                dataout        = [ReturnedHeader, ChipID]
            # If the header is none of the previous headers its a periphery command header and dataout is the following list:
            # [DataOutPeriphery - 40 bits]
            else:
                dataout = [data[39:0]]
        else:
            if header.tovalue() == 0x71:
                print("Got an EndOfCommand")
                return ["EoC", data[39:0]]
            else:
                # If the expected and the received header doesn't match raise an error
                raise ValueError("Received header {} does not match with expected header {}!".format(header.tovalue(), command_header))

        return dataout

    def xy_to_pixel_address(self, x_pos, y_pos):
        """
        Converts the pixel positions from x/y coordinates to EoC, Superpixel and Pixel
        (see manual v1.9 p.25) and returns it as 16bit list:
        EoC_address[15:9] + SP_address[8:3] + Pixel_address[2:0]
        """
        if x_pos > 255:
            # value for the x position, check whether in allowed range
            raise ValueError("Value {} for x position exceeds the maximum size of a {} bit value!".format(x_pos, 8))
        if y_pos > 255:
            # value for the y position, check whether in allowed range
            raise ValueError("Value {} for y position exceeds the maximum size of a {} bit value!".format(y_pos, 8))

        # create the variables for EoC, Superpixel and Pixel with their defined lengths
        EoC        = BitLogic(7)
        Superpixel = BitLogic(6)
        Pixel      = BitLogic(3)

        # calculate EoC, Superpixel and Pixel with the x and y position of the pixel
        EoC        = (x_pos - x_pos % 2) // 2
        Superpixel = (y_pos - y_pos % 4) // 4
        Pixel      = (x_pos % 2) * 4 + (y_pos % 4)

        # create a 16 bit variable for the address
        timepix_pixel_address = BitLogic(16)

        # fill the address with the calculated values of EoC, Superpixel and Pixel
        timepix_pixel_address[15:9] = EoC
        timepix_pixel_address[8:3]  = Superpixel
        timepix_pixel_address[2:0]  = Pixel

        return timepix_pixel_address

    def pixel_address_to_x(self, timepix_pixel_address):
        """
        Converts the Timepix3 pixel address which contains EoC, Superpixel and Pixel
        (see manual v1.9 p.25) and returns the x position of the pixel.
        The Timepix3 pixel address is:
        EoC_address[15:9] + SP_address[8:3] + Pixel_address[2:0]
        """
        if len(timepix_pixel_address) != 16:
            # check if the timepix_pixel_address has a valid length
            raise ValueError("The timepix pixel address must be a 16 bit value!")

        # get EoC and Pixel from the address, Superpixel is not needed for x
        EoC   = timepix_pixel_address[15:9]
        Pixel = timepix_pixel_address[2:0]

        # calculate the x position of the pixel based on EoC
        # <= 3: left column of a superpixel; > 3: right side of a superpixel
        if Pixel.tovalue() <= 3:
            x_pos = (EoC.tovalue() * 2)
        else:
            x_pos = (EoC.tovalue() * 2) + 1

        return x_pos

    def pixel_address_to_y(self, timepix_pixel_address):
        """
        Converts the Timepix3 pixel address which contains EoC, Superpixel and Pixel
        (see manual v1.9 p.25) and returns the x position of the pixel.
        The Timepix3 pixel address is:
        EoC_address[15:9] + SP_address[8:3] + Pixel_address[2:0]
        """
        if len(timepix_pixel_address) != 16:
            # check if the timepix_pixel_address has a valid length
            raise ValueError("The timepix pixel address must be a 16 bit value!")

        # get Superpixel and Pixel from the address, EoC is not needed for y
        Superpixel = timepix_pixel_address[8:3]
        Pixel      = timepix_pixel_address[2:0]

        # calculate the x position of the pixel based on EoC
        # <= 3: left column of a superpixel; > 3: right side of a superpixel
        if Pixel.tovalue() <= 3:
            y_pos = (Superpixel.tovalue() * 4) + Pixel.tovalue()
        else:
            y_pos = (Superpixel.tovalue() * 4) + (Pixel.tovalue() - 4)

        return y_pos

    def set_pixel_pcr(self, x_pos, y_pos, test, thr, mask):
        """
        sets test (1 bit), thr (4 bits) and mask (1 bit) for a selected pixel to new values
        """
        if x_pos > 255:
            # value for the x position, check whether in allowed range
            raise ValueError("Value {} for x position exceeds the maximum size of a {} bit value!".format(x_pos, 8))
        if y_pos > 255:
            # value for the y position, check whether in allowed range
            raise ValueError("Value {} for y position exceeds the maximum size of a {} bit value!".format(y_pos, 8))
        if test > 1:
            # value for the x position, check whether in allowed range
            raise ValueError("Value {} for test exceeds the maximum size of a {} bit value!".format(test, 1))
        if thr > 15:
            # value for the y position, check whether in allowed range
            raise ValueError("Value {} for thr exceeds the maximum size of a {} bit value!".format(y_pos, 4))
        if mask > 1:
            # value for the x position, check whether in allowed range
            raise ValueError("Value {} for mask exceeds the maximum size of a {} bit value!".format(mask, 1))

        # set the new values for test, thr and mask
        self.test_matrix[x_pos, y_pos] = test
        self.thr_matrix[x_pos, y_pos]  = thr
        self.mask_matrix[x_pos, y_pos] = mask

    def matrices_to_pcr(self, x_pos, y_pos):
        """
        returns the 6 bit PCR (see manual v1.9 p.44) of a selected pixel
        """
        if x_pos > 255:
            # value for the x position, check whether in allowed range
            raise ValueError("Value {} for x position exceeds the maximum size of a {} bit value!".format(x_pos, 8))
        if y_pos > 255:
            # value for the y position, check whether in allowed range
            raise ValueError("Value {} for y position exceeds the maximum size of a {} bit value!".format(y_pos, 8))

        # create a 6 bit variable for the pcr
        pcr = BitLogic(6)

        # fill the pcr with test, thr and mask
        thr    = BitLogic.from_value(self.thr_matrix[x_pos, y_pos])
        pcr[5] = np.int(self.test_matrix[x_pos, y_pos])
        pcr[4] = thr[3]
        pcr[3] = thr[2]
        pcr[2] = thr[1]
        pcr[1] = thr[0]
        pcr[0] = np.int(self.mask_matrix[x_pos, y_pos])

        return pcr

    def produce_column_mask(self, columns=list(range(256)), ctpr = False):
        """
        returns the 256 bit column mask (see manual v1.9 p.44) based on a list of selected columns
        """
        if len(columns) > 256 and np.all(np.asarray(columns) < 256):
            # check if the columns list has a valid length and no elements larger than
            # number of columns
            raise ValueError("""The columns list must not contain more than 256 entries and
            no entry may be larger than 255!""")

        # create a 256 bit variable for the column mask
        columnMask = BitLogic(256)

        # set the bits for all except the selected columns to 1
        for col in columns:
            columnMask[col] = 1

        if ctpr is False:
            columnMask.invert()

        data = []

        data += columnMask.toByteList()
        return data

    def write_pcr(self, columns=list(range(256)), write=True):
        """
        writes the pcr for all pixels in selected columns (see manual v1.9 p.44) and returns also
        the data
        """
        if len(columns) > 256 and np.all(np.asarray(columns) < 256):
            # check if the columns list has a valid length and no elements larger than
            # number of columns
            raise ValueError("""The columns list must not contain more than 256 entries and
            no entry may be larger than 255!""")

        data = []

        # create a 1536 bit variable for the PCRs of all pixels of one column
        pixeldata = np.zeros((1536), dtype=np.uint8)

        # presync header: 40 bits; TODO: header selection
        if self.chipId != None:
            data = self.getLocalSyncHeader()
        else:
            data = self.getGlobalSyncHeader()

        # append the code for the LoadConfigMatrix command header: 8 bits
        data += [self.matrix_header_map["LoadConfigMatrix"]]

        # append the columnMask for the column selection: 256 bits
        data += self.produce_column_mask(columns)

        # append the pcr for the pixels in the selected columns: 1535*columns bits
        for column in columns:
            pixeldata[0::6] = self.mask_matrix[column,:]
            col_thr_bits    = np.unpackbits(self.thr_matrix[column,:])
            pixeldata[1::6] = col_thr_bits[4::8]
            pixeldata[2::6] = col_thr_bits[5::8]
            pixeldata[3::6] = col_thr_bits[6::8]
            pixeldata[4::6] = col_thr_bits[7::8]
            pixeldata[5::6] = self.test_matrix[column,:]
            data           += np.packbits(pixeldata[::-1]).tolist()

        data += [0x00]

        if write is True:
            self.write(data)
        return data


    # TODO: replace explicit calls to the _configs and _outputBlocks_config dicts by
    # looping over the correct dictionary and using the `size` field to determine the
    # number of bits of each setting
    def write_general_config(self, write=True):
        """
        reads the values for the GeneralConfig registers (see manual v1.9 p.40) from a yaml file
        and writes them to the chip. Furthermore the sent data is returned.
        """
        data               = []
        configuration_bits = BitLogic(12)

        data = self.read_periphery_template("GeneralConfig", header_only=True)

        # create a 12 bit variable for the values of the GlobalConfig registers based
        # on the read YAML file storing the chip configuration
        configuration_bits[0]   = self._configs["Polarity"]
        configuration_bits[2:1] = self._configs["Op_mode"]
        configuration_bits[3]   = self._configs["Gray_count_en"]
        configuration_bits[4]   = self._configs["AckCommand_en"]
        configuration_bits[5]   = self._configs["TP_en"]
        configuration_bits[6]   = self._configs["Fast_Io_en"]
        configuration_bits[7]   = self._configs["TimerOverflowControl"]
        configuration_bits[8]   = 0
        configuration_bits[9]   = self._configs["SelectTP_Dig_Analog"]
        configuration_bits[10]  = self._configs["SelectTP_Ext_Int"]
        configuration_bits[11]  = self._configs["SelectTP_ToA_Clk"]

        # append the the GeneralConfiguration register with 4 additional bits to get the 16 bit DataIn
        data += (configuration_bits + BitLogic(4)).toByteList()
        # append dummy byte
        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def write_outputBlock_config(self, write=True):
        """
        reads the values for the outputBlock registers (see manual v1.9 p.37) from a yaml file
        and writes them to the chip. Furthermore the sent data is returned.
        """
        data               = []
        configuration_bits = BitLogic(16)

        data = self.read_periphery_template("OutBlockConfig", header_only=True)

        # create a 16 bit variable for the values of the GlobalConfig registers based
        # on the read YAML file storing the outputBlock configuration
        configuration_bits[7:0]   = self._outputBlocks["chan_mask"]
        configuration_bits[10:8]  = self._outputBlocks["clk_readout_src"]
        configuration_bits[11]    = self._outputBlocks["8b_10b_en"]
        configuration_bits[12]    = self._outputBlocks["clk_fast_out"]
        configuration_bits[15:13] = self._outputBlocks["ClkOut_frequency_src"]

        # append the the outputBlock register
        data += (configuration_bits).toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def read_periphery_template(self, name, header_only = False):
        # presync header: 40 bits
        if self.chipId != None:
            data = self.getLocalSyncHeader()
        else:
            data = self.getGlobalSyncHeader()

        # append the correct data for each periphery command
        data += [self.periphery_header_map[name]]
        if not header_only:
            # only append data, if not only header requested
            # fill with two dummy bytes for DataIN
            data += [0x00, 0x00]
            # final dummy byte
            data += [0x00]

        return data

    def read_matrix_template(self, name, header_only = False):
        if self.chipId != None:
            data = self.getLocalSyncHeader()
        else:
            data = self.getGlobalSyncHeader()

        # append the correct data for each periphery command
        data += [self.matrix_header_map[name]]
        if not header_only:
            # only append data, if not only header requested
            # final dummy byte
            data += [0x00]

        return data

    def read_general_config(self, write=True):
        """
        Sends the GeneralConfig_Read command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the GlobalConfig
        registers (see manual v1.9 p.40). The sent bytes are also returned.
        """
        # append the code for the GeneralConfig_Read command header: 8 bits
        data = self.read_periphery_template("GeneralConfig_Read")

        if write is True:
            self.write(data)
        return data

    def resetTimer(self, write=True):
        """
        Sends the ResetTimer command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the GlobalConfig
        registers (see manual v1.9 p.40). The sent bytes are also returned.
        """
        data = self.read_periphery_template("ResetTimer")

        if write is True:
            self.write(data)
        return data

    def requestTimerLow(self, write=True):
        """
        Sends the RequestTimerLow command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the GlobalConfig
        registers (see manual v1.9 p.40). The sent bytes are also returned.
        """
        data = self.read_periphery_template("RequestTimeLow")

        if write is True:
            self.write(data)
        return data

    def requestTimerHigh(self, write=True):
        """
        Sends the RequestTimerhigh command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the GlobalConfig
        registers (see manual v1.9 p.40). The sent bytes are also returned.
        """
        data = self.read_periphery_template("RequestTimeHigh")
        if write is True:
            self.write(data)
        return data

    def requestTimerRisingShutterLow(self, write=True):
        """
        Sends the Timer Rising Shutter Low command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the timer at shutter start. The sent bytes are also returned.
        """
        data = self.read_periphery_template("TimeRisingShutterLow")

        if write is True:
            self.write(data)
        return data

    def requestTimerRisingShutterHigh(self, write=True):
        """
        Sends the Timer Rising Shutter High command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the timer at shutter start. The sent bytes are also returned.
        """
        data = self.read_periphery_template("TimeRisingShutterHigh")

        if write is True:
            self.write(data)
        return data

    def requestTimerFallingShutterLow(self, write=True):
        """
        Sends the Timer Falling Shutter Low command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the timer at shutter start. The sent bytes are also returned.
        """
        data = self.read_periphery_template("TimeFallingShutterLow")

        if write is True:
            self.write(data)
        return data

    def requestTimerFallingShutterHigh(self, write=True):
        """
        Sends the Timer Falling Shutter High command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the timer at shutter start. The sent bytes are also returned.
        """
        data = self.read_periphery_template("TimeFallingShutterHigh")

        if write is True:
            self.write(data)
        return data

    def read_output_block_config(self, write=True):
        """
        Sends the OutBlockConfig_Read command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the timer at
        shutter start. The sent bytes are also returned.
        """
        data = self.read_periphery_template("OutBlockConfig_Read")

        if write is True:
            self.write(data)
        return data


    # TODO: combine all 3 set timer functions into 1. No need for all 3!
    def SetTimer_15_0(self, setTime, write=True):
        """
        Sends the RequestTimerhigh command (see manual v1.9 p.32) together with the
        SyncHeader and timer values for DataIn (see manual v1.9 p.43). The sent bytes are also returned.
        """
        data = self.read_periphery_template("SetTimer_15_0", True)

        # fill with two dummy bytes for DataIN
        time       = BitLogic(16)
        time[15:0] = setTime
        data      += BitLogic.toByteList(time)

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def SetTimer_31_16(self, setTime, write=True):
        """
        Sends the setTimer_31_!6 command (see manual v1.9 p.32) together with the
        SyncHeader and timer values for DataIn to (see manual v1.9 p.43). The sent bytes are also returned.
        """
        data = self.read_periphery_template("SetTimer_31_16", True)

        # fill with two dummy bytes for DataIN
        time       = BitLogic(16)
        time[15:0] = setTime
        data      += BitLogic.toByteList(time)

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def SetTimer_47_32(self, setTime, write=True):
        """
        Sends the Set Timer 47_32 command (see manual v1.9 p.32) together with the
        SyncHeader and timer values for DataIn (see manual v1.9 p.43). The sent bytes are also returned.
        """
        data = self.read_periphery_template("SetTimer_47_32", True)

        # fill with two dummy bytes for DataIN
        time       = BitLogic(16)
        time[15:0] = setTime
        data      += BitLogic.toByteList(time)

        data += [0x00]

        if write is True:
            self.write(data)
        return data


    def startTimer(self, write=True):
        """
        Sends the T0_Sync_Command command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the GlobalConfig
        registers (see manual v1.9 p.40). The sent bytes are also returned.
        """
        data = self.read_periphery_template("T0_Sync_Command")

        if write is True:
            self.write(data)
        return data

    def write_tp_pulsenumber(self, number, write=True):
        """
        Writes the number of testpulses to the TP_number test pulse register (see manual v1.9 p.35)
        and returns the written data. The number if test pulses is a 16-bit value.
        """
        if number > 65535:
            #  check if the number of test pulses is allowed
            raise ValueError("The number of test pulses must not be bigger than 65535!")

        data = []

        # create a 16 bit variable for the number of testpulses
        number_bits = BitLogic(16)

        # presync header: 40 bits; TODO: header selection
        if self.chipId != None:    
            data = self.getLocalSyncHeader()
        else:
            data = self.getGlobalSyncHeader()

        # append the code for the GeneralConfig_Read command header: 8 bits
        data += [self.periphery_header_map["TP_PulseNumber"]]

        # fill the 16-bit variable for the number of test pulses
        number_bits[15:0] = number

        # append the number of test pulses to the data
        data += number_bits.toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def write_tp_period(self, period, phase, write=True):
        """
        Writes the period and the phase to the TP_period and TP_phase test pulse registers (see manual v1.9 p.35)
        and returns the written data. The period is a 8-bit value and the phase is a 4-bit value.
        """
        if period > 255:
            #  check if the period is allowed
            raise ValueError("The period must not be bigger than 255!")
        if phase > 15:
            #  check if the phase is allowed
            raise ValueError("The phase must not be bigger than 15!")

        data = self.read_periphery_template("TP_Period", header_only = True)
        # create a 12 bit variable for the period (bits [7:0]) and the phase (bits [11:8])
        bits = BitLogic(12)

        # fill the 12-bit variable with the period and the phase
        bits[7:0]  = period
        bits[11:8] = phase

        # append the period/phase variable to the data
        data += (bits + BitLogic(4)).toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def burn_fuses(self, width, fuse, write=True):
        """
        Burns a selected fuse for a selected time (width). The sent bytes are also returned.
        (see manual v1.9 p. 34)
        """
        if width > 63:
            #  check if the width is allowed
            raise ValueError("The program width must not be bigger than 63!")
        if fuse > 31:
            #  check if the fuse is allowed
            raise ValueError("The selected fuse must not be bigger than 31!")

        data = self.read_periphery_template("EFuse_Burn", True)
        # create a 11 bit variable for the program width (bits [5:0]) and the fuse selection (bits [10:6])
        bits = BitLogic(11)

        # fill the 11-bit variable with the width and the fuse selection
        bits[5:0]  = width
        bits[10:6] = fuse

        # append the variable to the data and add empty bits to create the complete data input
        data += (bits + BitLogic(5)).toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def read_tp_config(self, write=True):
        """
        Sends the TPConfig_Read command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the test pulse
        registers (see manual v1.9 p.35). The sent bytes are also returned.
        """
        data = self.read_periphery_template("TPConfig_Read")

        if write is True:
            self.write(data)
        return data

    def write_ctpr(self, columns=list(range(256)), write=True):
        """
        Writes the column test pulse register to the chip (see manual v1.9 p.50) and returns
        the written data. The masked columns can be selected with the `columns` variable.
        """
        if len(columns) > 256 or np.all(np.asarray(columns) > 256):
            # check if the columns list has a valid length and no elements larger than
            # number of columns
            raise ValueError("""The columns list must not contain more than 256 entries and
            no entry may be larger than 255!""")

        # append the code for the LoadConfigMatrix command header: 8 bits
        data = self.read_matrix_template("LoadCTPR", True)

        # append the column mask based on the selected columns
        # TODO: The manual (v1.9) does not state if columns are masked with 1 or 0
        # so in the current implementation the column mask is used (see manual v1.9 p.46)
        # with 0 for load and 1 for skip. This needs a check.
        data += self.produce_column_mask(columns, ctpr = True)

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def read_pixel_config_reg(self, columns, write=True):
        """
        Sends the ReadConfigMatrix command (see manual v1.9 p.49) together with
        a mask of selected columns based on the list of selected columns given
        in 'columns'.
        """
        data = self.read_matrix_template("ReadConfigMatrix", True)

        # create a 256-bit bitarrays for single column selection
        SColSelectReg = BitLogic(256)

        # Set SColSelect for selected columns to 0 and for other columns to 1
        for col in range(256):
            SColSelectReg[col] = 0 if col in columns else 1
        data += SColSelectReg.toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def read_pixel_matrix_sequential(self, TokenSelect, write=True):
        """
        Sends the ReadMatrixSequential command (see manual v1.9 p.45) together with
        a token select to select the maximum number of columns which are read
        simultaneously.
        """
        data = self.read_matrix_template("ReadMatrixSequential", True)

        # create two 128-bit bitarrays for double column select and token select
        DColSelect = BitLogic(128)
        TokenSelectReg = BitLogic(128)

        # Fill the double column select with zeros (manual v1.9 p.45) and
        # append it to the data
        for index in range(128):
            DColSelect[index] = 0
        data += DColSelect.toByteList()

        # Fill the token select (manual v1.9 p.34) with the given tokens, reverse
        # it and append it to data
        TokenSelectReg[127:0] = TokenSelect
        TokenSelectReg.reverse()
        data += TokenSelectReg.toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def reset_sequential(self, write=True):
        """
        Sends a command to reset the pixel matrix column by column  (Manual v 1.9 pg. 51). If any data is still present on the pixel
        matrix (eoc_active is high) then an End of Readout packet is sent.
        """
        # append the code for the ResetSequential command header: 8 bits
        data = self.read_matrix_template("ResetSequential", True)

        # NOTE: The manual (v1.9 p.52) states to send 142 bits, we need to
        # send full bytes though, so we send 144 bits. The manual also states
        # that data to be dummy bytes anyways.
        # TODO: The manual (v1.9 p.32) also states that after the header a
        # 256-bit column mask is needed. So test if maybe a 256-bit dummy
        # is needed instead of the 144-bit dummy
        dummy = BitLogic(144)
        data += dummy.toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def stop_readout(self, write=True):
        """
        Sends a command to stop / pause a pixel readout (Manual v 1.9 pg. 52)
        """
        data = self.read_matrix_template("StopMatrixCommand")

        if write is True:
            self.write(data)
        return data


    def write_pll_config(self, write=True):
        """
        reads the values for the PLLConfig registers (see manual v1.9 p.37) from a yaml file
        and writes them to the chip. Furthermore the sent data is returned.
        """
        data = []
        configuration_bits = BitLogic(16)

        data = self.read_periphery_template("PLLConfig", header_only=True)

        # create a 16 bit variable for the values of the PLLConfig registers based
        # on the read YAML file storing the PLL configuration
        configuration_bits[0]     = self._PLLConfigs["bypass"]
        configuration_bits[1]     = self._PLLConfigs["reset"]
        configuration_bits[2]     = self._PLLConfigs["selectVctl"]
        configuration_bits[3]     = self._PLLConfigs["dualedge"]
        configuration_bits[5:4]   = self._PLLConfigs["clkphasediv"]
        configuration_bits[8:6]   = self._PLLConfigs["clkphasenum"]
        configuration_bits[13:9]  = self._PLLConfigs["PLLOutConfig"]
        configuration_bits[15:14] = 0

        # append the the outputBlock register
        data += (configuration_bits).toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def read_pll_config(self, write=True):
        """
        Sends the PLLConfig_Read command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the PLL Config
        registers (see manual v1.9 p.37). The sent bytes are also returned.
        """
        data = self.read_periphery_template("PLLConfig_Read")

        if write is True:
            self.write(data)
        return data

    # TODO: which data driven proc is correct? need column mask???
    # table p. 32 states column mask needed
    # schematic p. 50 states NOT needed...
    # Tests show that both procs work, so it works with and without
    # the column mask. But its not clear if the column mask has any
    # effect.
    def read_pixel_matrix_datadriven(self, write=True):
        """
        Sends the Pixel Matrix Read Data Driven command (see manual v1.9 p.32 and
        v1.9 p.50). The sended bytes are also returned.
        """
        data = self.read_matrix_template("ReadMatrixDataDriven")

        if write is True:
            self.write(data)
        return data

    def read_matrix_data_driven(self, write=True):
        """
        Sends the "ReadMatrixDataDriven" command with the column mask. The column mask is
        set such all columns are loaded.
        """
        data = self.read_matrix_template("ReadMatrixDataDriven", True)

        # append the 256 bit column mask; TODO: make the columns selectable
        data += self.produce_column_mask(list(range(256)))

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def read_ctpr(self, write=True):
        """
        Sends a command to read the Column Test Pulse Register (Manual v 1.9 pg. 50)
        """
        data = self.read_matrix_template("ReadCTPR")

        if write is True:
            self.write(data)
        return data

    def set_threshold(self, threshold):
        """
        Calculates the fine and the coarse threshold and writes it to the chip
        """
        fine_threshold, coarse_threshold = threshold_decompose(threshold)

        # Set the threshold DACs
        self.set_dac("Vthreshold_coarse", coarse_threshold)
        self.set_dac("Vthreshold_fine", fine_threshold)

    def toggle_pin(self, pin, sleep_time = 0.01):
        """
        Toggles a pin for a defined time
        """
        if pin not in {"TO_SYNC", "RESET", "SHUTTER"}:
            raise ValueError("You can only toggle TO_SYNC, RESET and SHUTTER pins!")

        self.Dut_layer['CONTROL'][pin] = 1
        self.Dut_layer['CONTROL'].write()
        time.sleep(sleep_time)
        self.Dut_layer['CONTROL'][pin] = 0
        self.Dut_layer['CONTROL'].write()

    def lfsr_10_bit(self):
        """
        Generates a 10bit LFSR according to Manual v1.9 page 19
        """
        lfsr = BitLogic(10)
        lfsr[7:0] = 0xFF
        lfsr[9:8] = 0b11
        dummy = 0
        for i in range(2**10):
            self.lfsr_10[BitLogic.tovalue(lfsr)] = i
            dummy = lfsr[9]
            lfsr[9] = lfsr[8]
            lfsr[8] = lfsr[7]
            lfsr[7] = lfsr[6]
            lfsr[6] = lfsr[5]
            lfsr[5] = lfsr[4]
            lfsr[4] = lfsr[3]
            lfsr[3] = lfsr[2]
            lfsr[2] = lfsr[1]
            lfsr[1] = lfsr[0]
            lfsr[0] = lfsr[7] ^ dummy
        self.lfsr_10[2 ** 10 - 1] = 0

    def lfsr_14_bit(self):
        """
        Generates a 14bit LFSR according to Manual v1.9 page 19
        """
        lfsr       = BitLogic(14)
        lfsr[7:0]  = 0xFF
        lfsr[13:8] = 63
        dummy = 0
        for i in range(2**14):
            self.lfsr_14[BitLogic.tovalue(lfsr)] = i
            dummy = lfsr[13]
            lfsr[13] = lfsr[12]
            lfsr[12] = lfsr[11]
            lfsr[11] = lfsr[10]
            lfsr[10] = lfsr[9]
            lfsr[9]  = lfsr[8]
            lfsr[8]  = lfsr[7]
            lfsr[7]  = lfsr[6]
            lfsr[6]  = lfsr[5]
            lfsr[5]  = lfsr[4]
            lfsr[4]  = lfsr[3]
            lfsr[3]  = lfsr[2]
            lfsr[2]  = lfsr[1]
            lfsr[1]  = lfsr[0]
            lfsr[0]  = lfsr[2] ^ dummy ^ lfsr[12] ^ lfsr[13]
        self.lfsr_14[2 ** 14 - 1] = 0

    def lfsr_4_bit(self):
        """
        Generates a 4bit LFSR according to Manual v1.9 page 19
        """
        lfsr = BitLogic(4)
        lfsr[3:0] = 0xF
        dummy = 0
        for i in range(2**4):
            self.lfsr_4[BitLogic.tovalue(lfsr)] = i
            dummy   = lfsr[3]
            lfsr[3] = lfsr[2]
            lfsr[2] = lfsr[1]
            lfsr[1] = lfsr[0]
            lfsr[0] = lfsr[3] ^ dummy
        self.lfsr_4[2 ** 4 - 1] = 0

    def gray_decrypt(self, value):
        """
        Decrypts a gray encoded 48 bit value according to Manual v1.9 page 19
        """
        encoded_value       = BitLogic(48)
        encoded_value[47:0] = value
        gray_decrypt        = BitLogic(48)
        gray_decrypt[47]    = encoded_value[47]
        for i in range (46, -1, -1):
            gray_decrypt[i] = gray_decrypt[i+1]^encoded_value[i]

        return gray_decrypt