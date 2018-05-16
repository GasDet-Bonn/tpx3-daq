#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

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
from utils import toByteList, bitword_to_byte_list

# add toByteList() method to BitLogic
BitLogic.toByteList = toByteList


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


class TPX3(Dut):

    # '' Map hardware IDs for board identification '''
    # hw_map = {
    #    0: 'SIMULATION',
    #    1: 'MIO2',
    # }

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

    # DAC names
    # will have to be careful when using these, due to 5 bit value
    dac_map = {"Ibias_Preamp_ON": 0b00001,
               "Ibias_Preamp_OFF": 0b00010,
               "VPreamp_NCAS": 0b00011,
               "Ibias_Ikrum": 0b00100,
               "Vfbk": 0b00101,
               "Vthreshold_fine": 0b00110,
               "Vthreshold_coarse": 0b00111,
               "Ibias_DiscS1_ON": 0b01000,
               "Ibias_DiscS1_OFF": 0b01001,
               "Ibias_DiscS2_ON": 0b01010,
               "Ibias_DiscS2_OFF": 0b01011,
               "Ibias_PixelDAC": 0b01100,
               "Ibias_TPbufferIn": 0b01101,
               "Ibias_TPbufferOut": 0b01110,
               "VTP_coarse": 0b01111,
               "VTP_fine": 0b10000,
               "Ibias_CP_PLL": 0b10001,
               "PLL_Vcntrl": 0b10010}

    # number of bits a value for a DAC can have maximally
    DAC_VALUE_BITS = 9

    # DAC value size in bits
    dac_valsize_map = {"Ibias_Preamp_ON":   8,
                       "Ibias_Preamp_OFF":  4,
                       "VPreamp_NCAS":      8,
                       "Ibias_Ikrum":       8,
                       "Vfbk":              8,
                       "Vthreshold_fine":   9,
                       "Vthreshold_coarse": 4,
                       "Ibias_DiscS1_ON":   8,
                       "Ibias_DiscS1_OFF":  4,
                       "Ibias_DiscS2_ON":   8,
                       "Ibias_DiscS2_OFF":  4,
                       "Ibias_PixelDAC":    8,
                       "Ibias_TPbufferIn":  8,
                       "Ibias_TPbufferOut": 8,
                       "VTP_coarse":        8,
                       "VTP_fine":          9,
                       "Ibias_CP_PLL":      8,
                       "PLL_Vcntrl":        8}

    # monitoring voltage maps
    monitoring_map = {"PLL_Vcntrl": 0b10010,
                      "BandGap output": 0b11100,
                      "BandGap_Temp": 0b11101,
                      "Ibias_dac": 0b11110,
                      "Ibias_dac_cas": 0b11111,
                      "SenseOFF": 0b00000}

    def __init__(self, conf=None, **kwargs):

        self.proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if not conf:
            conf = os.path.join(self.proj_dir, 'tpx3' + os.sep + 'tpx3.yaml')

        logger.info("Loading configuration file from %s" % conf)
        super(TPX3, self).__init__(conf)

    def init(self, config_file=None):
        super(TPX3, self).init()

        # self.fw_version, self.board_version = self.get_daq_version()
        # logger.info('Found board %s running firmware version %s' % (self.hw_map[self.board_version], self.fw_version))
        #
        # if self.fw_version != VERSION[:3]:     #Compare only the first two digits
        #    raise Exception("Firmware version %s does not satisfy version requirements %s!)" % ( self.fw_version, VERSION))

        # self['CONF_SR'].set_size(3924)

        self['CONTROL']['DATA_MUX_SEL'] = 1
        self['CONTROL'].write()

        # dummy Chip ID, which will be replaced by some value read from a YAML file
        # for a specific Timepix3
        self.chipId = [0x00 for _ in range(4)]

        # reset all matrices to empty defaults
        self.reset_matrices()

        # set all configuration attributes to their default values, also sets
        # the `config_written_to_chip` flag to False
        self.reset_config_attributes()

        # config dictionary will store the full yaml as a nested dict
        self.config = {}
        # configuration settings
        if config_file is not None:
            self.config_file = config_file
        else:
            # TODO: replace this by something more general!
            self.config_file = 'tpx3/GeneralConfiguration.yml'
        # TODO: think about whether we should always read the YAML config file?
        self.read_config_yaml(self.config_file)


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
            self.thr_matrix = np.zeros((256, 256), dtype=int)
        # set the mask matrix with zeros for all pixels
        if mask:
            self.mask_matrix = np.zeros((256, 256), dtype=int)
        # matrix storing ToT (= Time over Threshold) values of this Tpx3
        # 8 bit values
        if tot:
            self.tot = np.zeros((256, 256), dtype = np.int8)
        # matrix storing ToA (= Time of Arrival) values of this Tpx3
        # 12 bit values
        if toa:
            self.toa = np.zeros((256, 256), dtype = np.int16)
        # matrix storing fToA (= fast Time of Arrival; see manual v1.9 p.10) used if
        # VCO is on
        # 4 bit values
        if ftoa:
            self.ftoa = np.zeros((256, 256), dtype = np.int8)
        # matrix storing hit counts of each pixel, if a hit happened without ToA and
        # ToT being registered, i.e. two hits happenening too close to one another
        # 4 bit values
        if hits:
            self.hits = np.zeros((256, 256), dtype = np.int8)

    def reset_config_attributes(self):
        """
        Resets all configuration attributes to their default values
        """
                # flag to determine whether the configuration has been written to the chip already
        self.config_written_to_chip = False
        # general configuration settings are initialized with the default chip values
        # for an explanation see manual v1.9 p.40 or the general config YAML file
        # selects polarity (0 = positive, 1 = negative)
        self.polarity = 1
        # pixel operation mode (0b00 = ToA and ToT, 0b01 = ToA, 0b10 = Event and iToT)
        self.op_mode = 0b00
        # end of command Gray counter (for ToA measurements?) (0 = disabled, 1 = enabled)
        self.gray_counter = 0
        # AckCommand package (0 = disabled, 1 = enabled)
        self.ack_command_enable = 0
        # test pulse enable (0 = disabled, 1 = enabled)
        self.tp_enable = 0
        # super pixel oscillator enable (Fast_Io_en; 0 = disabled, 1 = enabled)
        self.fast_io_enable = 0
        # time overflow control for 48bit timer
        # (0 = will cycle through, 1 = stops at 0hFFFF_FFFF_FFFF)
        self.timer_overflow_control = 0
        # select if test pulses are sent to the Front-End (analog domain) or
        # the discriminator input (digital domain)
        # (0 = Front-End, 1 = Discr. input)
        self.select_tp_dig_analog = 0
        # test pulse generation internal or external (0 = internal, 1 = external)
        self.select_tp_ext_int = 0
        # select if clock is phase shifted in the end of command Gray counters
        # (0 = phase shifted, 1 = not shifted)
        self.select_toa_clk = 0


    def read_config_yaml(self, config_file):
        """
        Reads a configuration YAML file for the general Timepix3 configuration,
        saves the content in the `self.config` field, assigns the chip attributes,
        which store the settings correctly.
        Note: It does not return the configuration ready to be written to the chip,
        for that use the `get_configuration_register` method
        """
        # get the configuration bits from the GeneralConfiguration file
        config = yaml.load(open(config_file, 'r'))

        for register in config['registers']:
            name = register['name']
            address = register['address']
            size = register['size']
            mode = register['mode']
            self.config[name] = {'address' : address,
                                 'size': size,
                                 'mode': mode}
        # for an explanation on the different options see manual v1.9 p.40,
        # the YAML file or the declaration of the fields at the beginning of the class
        self.polarity = self.config['Polarity']['mode']
        self.op_mode = self.config['Op_mode']['mode']
        self.gray_counter = self.config['Gray_count_en']['mode']
        self.ack_command_enable = self.config['AckCommand_en']['mode']
        self.tp_enable = self.config['TP_en']['mode']
        self.fast_io_enable = self.config['Fast_Io_en']['mode']
        self.timer_overflow_control = self.config['TimerOverflowControl']['mode']
        self.select_tp_dig_analog = self.config['SelectTP_Dig_Analog']['mode']
        self.select_tp_ext_int = self.config['SelectTP_Ext_Int']['mode']
        self.select_toa_clk = self.config['SelectTP_ToA_Clk']['mode']

    def get_configuration_register(self):
        """
        Checks whether a YAML configuration file was already read and if so,
        creates a configuration register from it and returns it.
        """
        if len(self.config) == 0 and self.config_file is not None:
            read_config_yaml(self.config_file)
        elif len(self.config) == 0 and self.config_file is None:
            # in this case we don't know about a config file, nor have we read one,
            # return None
            return None
        # create a 12 bit variable for the values of the GlobalConfig registers
        configuration_bits = BitLogic(12)
        # iterate over all values of the config dictionary, since each nested dict
        # contains all necessary information, i.e. the key (=name) is not needed.
        for reg in self.config.values():
            address = reg['address']
            size = reg['size']
            mode = reg['mode']
            # fill the variable for the register values with the values from the yaml file
            # see see manual v1.9 p.40 for the registers
            configuration_bits[address + size - 1:address] = mode
        return configuration_bits

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

    def set_dac(self, dac, value, chip=None, write=True):
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
        if chip is None:
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
        data = self.getGlobalSyncHeader()

        data += [self.periphery_header_map["ReadDAC"]]

        # add DAC code to last 4 bit of final 16 bit
        bits = BitLogic(16)
        bits[4:0] = self.dac_map[dac]
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

    def write(self, data):
        """
        Performs a write of `data` on the SPI interface to the Tpx3.
        Note: this function is blocking until the write is complete.
        Inputs:
            data: list of bytes to write. MSB is first element of list

        """
        # total size in bits
        self['SPI'].set_size(len(data) * 8)
        self['SPI'].set_data(data)
        self['SPI'].start()

        while(not self['SPI'].is_ready):
            # wait until SPI is done
            pass

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
        For periphery commands d2[3] contains the hex code of which function was called,
        as the first byte of the returned list the rest is the 40bit DataOut
        (see manual v1.9 p.32).
        """

        # determine number of 48bit words
        assert len(data) % 2 == 0, "Missing one 32bit subword of a 48bit package"
        nwords = len(data) / 2
        result = []
        for i in range(nwords):
            d1 = bitword_to_byte_list(int(data[i]), string)
            d2 = bitword_to_byte_list(int(data[i + 1]), string)
            dataout = [d2[3], d2[2], d2[1], d1[3], d1[2], d1[1]]

            result.append(dataout)

        return result

    def decode(self, data, command_header):
        """
        Given a FPGA decoded 48 bit word given as a list of
        bytes, perform a decoding based on
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
        if len(data) is not 6:
            raise ValueError("The data must contain 6 bytes and not {}!".format(len(data)))

        # create bitarrays for the complete data (48 bits) and the header (8 bit)
        data_payload = BitLogic(48)
        header = BitLogic(8)

        # combine the 6 bytes in the data list to one bitarray
        i = 0
        for d in data:
            if len(d) is not 8:
                raise ValueError("All bytes of the data must contain 8 bits and not {}!".format(len(d)))
            data_payload[47 - (i * 8):40 - (i * 8)] = d
            i += 1

        # The command header is always a byte but for pixel matrix operations only bits 7 to 4 are part of the
        # data packets because bits 3 to 0 are all 0. Furthermore pixel matrix operation headers have always
        # bit 7 as 1 while periphery and control commands have always bit 7 as 0 (see manual v1.9 p.32).
        if data_payload[47] is True:
            # Pixel matrix operations: Only bits 7 to 4 are part of the data, bits 3 to 0 are 0
            header[7:4] = data_payload[47:44]
        else:
            # Periphery and control commands: Get full header from the data
            header[7:0] = data_payload[47:40]

        # Check if the expected and the received header are the same
        if header.tovalue() is command_header:
            # If the header is a acquisition header dataout is the following list:
            # [address - 16 bit, TOA (or iTOT) - 14 bit, TOT (or dummy or EventCounter) - 10 bit, FTOA (or dummy or HitCounter) - 4 bit]
            if header[7:5].tovalue() is 0b101:
                address = data_payload[43:28]
                TOA = data_payload[27:14]
                TOT = data_payload[13:4]
                HitCounter = data_payload[3:0]
                dataout = [address, TOA, TOT, HitCounter]
            # If the header is a Stop matrix readout or a reset sequential header dataout is the following list:
            # [dummy - 44 bit]
            elif header[7:5].tovalue() is 0b111:
                dataout = [data_payload[43:0]]
            # If the header is the CTPR configuration header dataout is the following list:
            # [address - 7 bit, EoC - 18 bit, CTPR - 2 bit]
            elif header[7:5].tovalue() is 0b110:
                address = data_payload[43:37]
                EoC = data_payload[27:10]
                CTPR = data_payload[1:0]
                dataout = [address, EoC, CTPR]
            # If the header is the pixel configuration header dataout is the following list:
            # [address - 14 bit, Config - 6 bit]
            elif header[7:5].tovalue() is 0b100:
                address = data_payload[43:28]
                Config = data_payload[19:14]
                dataout = [address, Config]
            # If the header is a control command header dataout is the following list:
            # [H1H2H3 - 8 bit, ChipID - 32 bit]
            elif header[7:5].tovalue() is 0b011:
                ReturnedHeader = data_payload[39:32]
                ChipID = data_payload[31:0]
                dataout = [ReturnedHeader, ChipID]
            # If the header is none of the previous headers its a periphery command header and dataout is the following list:
            # [DataOutPeriphery - 40 bits]
            else:
                dataout = [data_payload[39:0]]
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

        # create the variables for EoC, Superpixel and Pixel with their defined lenghts
        EoC = BitLogic(7)
        Superpixel = BitLogic(6)
        Pixel = BitLogic(3)

        # calculate EoC, Superpixel and Pixel with the x and y position of the pixel
        EoC = (x_pos - x_pos % 2) / 2
        Superpixel = (y_pos - y_pos % 4) / 4
        Pixel = (x_pos % 2) * 4 + (y_pos % 4)

        # create a 16 bit variable for the address
        timepix_pixel_address = BitLogic(16)

        # fill the address with the calculated values of EoC, Superpixel and Pixel
        timepix_pixel_address[15:9] = EoC
        timepix_pixel_address[8:3] = Superpixel
        timepix_pixel_address[2:0] = Pixel

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
        EoC = timepix_pixel_address[15:9]
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
        Pixel = timepix_pixel_address[2:0]

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
        self.thr_matrix[x_pos, y_pos] = thr
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

        # create the variables for test, thr and mask with their defined lenghts
        test = BitLogic(1)
        thr = BitLogic(4)
        mask = BitLogic(1)

        # get test, thr and matrix from the corresponding matrices
        test = self.test_matrix[x_pos, y_pos]
        thr = BitLogic.from_value(self.thr_matrix[x_pos, y_pos], 4)
        mask = self.mask_matrix[x_pos, y_pos]

        # fill the pcr with test, thr and mask
        pcr[5] = test
        pcr[4:1] = thr
        pcr[0] = mask

        return pcr

    def produce_column_mask(self, columns=range(256)):
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
        for col in range(256):
            # all bits 0 which are elements of columns, else 1
            columnMask[col] = 1 if col in columns else 0

        data = []

        data += columnMask.toByteList()
        return data

    def write_pcr(self, columns=range(256), write=True):
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
        pixeldata = BitLogic(1536)

        # presync header: 40 bits; TODO: header selection
        data = self.getGlobalSyncHeader()

        # append the code for the LoadConfigMatrix command header: 8 bits
        data += [self.matrix_header_map["LoadConfigMatrix"]]

        # append the columnMask for the column selection: 256 bits
        data += self.produce_column_mask(columns)

        # append the pcr for the pixels in the selected columns: 1535*columns bits
        for column in columns:
            for row in range(256):
                pixeldata[(5 + 6 * row):(0 + 6 * row)] = self.matrices_to_pcr(column, row)
            data += pixeldata.toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def write_general_config(self, write=True):
        """
        reads the values for the GeneralConfig registers (see manual v1.9 p.40) from a yaml file
        and writes them to the chip. Furthermore the sent data is returned.
        """
        data = []
        # presync header: 40 bits
        data = self.getGlobalSyncHeader()

        # append the code for the GeneralConfig command header: 8 bits
        data += [self.periphery_header_map["GeneralConfig"]]

        # create a 12 bit variable for the values of the GlobalConfig registers based
        # on the read YAML file storing the chip configuration
        configuration_bits = self.get_configuration_register()

        # append the the GeneralConfiguration register with 4 additional bits to get the 16 bit DataIn
        data += (configuration_bits + BitLogic(4)).toByteList()

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def read_general_config(self, write=True):
        """
        Sends the GeneralConfig_Read command (see manual v1.9 p.32) together with the
        SyncHeader and a dummy for DataIn to request the actual values of the GlobalConfig
        registers (see manual v1.9 p.40). The sent bytes are also returned.
        """
        data = []

        # presync header: 40 bits
        data = self.getGlobalSyncHeader()

        # append the code for the GeneralConfig_Read command header: 8 bits
        data += [self.periphery_header_map["GeneralConfig_Read"]]

        # fill with two dummy bytes for DataIN
        data += [0x00]
        data += [0x00]

        data += [0x00]

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

        data = []

        # create a 12 bit variable for the period (bits [7:0]) and the phase (bits [11:8])
        bits = BitLogic(12)

        # presync header: 40 bits; TODO: header selection
        data = self.getGlobalSyncHeader()

        # append the code for the GeneralConfig_Read command header: 8 bits
        data += [self.periphery_header_map["TP_Period"]]

        # fill the 12-bit variable with the period and the phase
        bits[7:0] = period
        bits[11:8] = phase

        # append the period/phase variable to the data
        data += (bits + BitLogic(4)).toByteList()

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
        data = []

        # presync header: 40 bits; TODO: header selection
        data = self.getGlobalSyncHeader()

        # append the code for the GeneralConfig_Read command header: 8 bits
        data += [self.periphery_header_map["TPConfig_Read"]]

        # fill with two dummy bytes for DataIN
        data += [0x00]
        data += [0x00]

        data += [0x00]

        if write is True:
            self.write(data)
        return data

    def write_ctpr(self, columns=range(256), write=True):
        """
        Writes the column test pulse register to the chip (see manual v1.9 p.50) and returns
        the written data. The masked columns can be selected with the `columns` variable.
        """
        if len(columns) > 256 and np.all(np.asarray(columns) < 256):
            # check if the columns list has a valid length and no elements larger than
            # number of columns
            raise ValueError("""The columns list must not contain more than 256 entries and
            no entry may be larger than 255!""")

        data = []

        # presync header: 40 bits; TODO: header selection
        data = self.getGlobalSyncHeader()

        # append the code for the LoadConfigMatrix command header: 8 bits
        data += [self.matrix_header_map["LoadCTPR"]]

        # append the column mask based on the selected columns
        # TODO: The manual (v1.9) does not state if columns are masked with 1 or 0
        # so in the current implementation the column mask is used (see manual v1.9 p.46)
        # with 0 for load and 1 for skip. This needs a check.
        data += self.produce_column_mask(columns)

        data += [0x00]

        if write is True:
            self.write(data)
        return data

if __name__ == '__main__':
    pass
