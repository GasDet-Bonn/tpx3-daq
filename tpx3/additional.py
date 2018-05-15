def read_pixel_config_reg(self, SColSelect=range(256), write=True):
    """
    Sends the Pixel Matrix Read Data Driven command (see manual v1.9 p.32 and  v1.9 p.50). The sended bytes are also returned.
    """
    data = []

    # presync header: 40 bits
    data = self.getGlobalSyncHeader()

    # append the code for the ReadMatrixSequential command header: 8 bits
    data += [self.periphery_header_map["ReadConfigMatrix"]]
    SColSelectReg= BitLogic(128)
    for index in range(256):
        if SColSelect[index] == 0:
            SColSelectReg[index] = 0
        else:
            SColSelectReg = 1
    data += SColSelectReg.toByteList()
    data += [0x00]

    if write is True:
        self.write(data)
    return data

def read_ctpr(self, write=True):
    """
    Sends a command to read the COlumn Test Pulse Register (Manual v 1.9 pg. 50)
    """
    data = []

    # presync header: 40 bits; TODO: header selection
    data = self.getGlobalSyncHeader()

    # append the code for the LoadConfigMatrix command header: 8 bits
    data += [self.matrix_header_map["ReadCTPR"]]


    data += [0x00]

    if write is True:
        self.write(data)
    return data

def reset_sequential(self, write=True):
    """
    Sends a command to reset the pixel matrix column by column  (Manual v 1.9 pg. 51). If any data is still present on the pixel
    matrix (eoc_active is high) then an End of Readout packet is sent.
    """
    data = []

    # presync header: 40 bits; TODO: header selection
    data = self.getGlobalSyncHeader()

    # append the code for the LoadConfigMatrix command header: 8 bits
    data += [self.matrix_header_map["ResetSequential"]]
    dummy= BitLogic(142)
    data += dummy.toByteList()
    data += [0x00]

    if write is True:
        self.write(data)
    return data

def stop_readout(self, write=True):
    """
    Sends a command to read the COlumn Test Pulse Register (Manual v 1.9 pg. 50)
    """
    data = []

    # presync header: 40 bits; TODO: header selection
    data = self.getGlobalSyncHeader()

    # append the code for the LoadConfigMatrix command header: 8 bits
    data += [self.matrix_header_map["StopMatrixCommand"]]
    data += [0x00]

    if write is True:
        self.write(data)
    return data

def read_pixel_matrix_datadriven(self, write=True):
    """
    Sends the Pixel Matrix Read Data Driven command (see manual v1.9 p.32 and  v1.9 p.50). The sended bytes are also returned.
    """
    data = []

    # presync header: 40 bits
    data = self.getGlobalSyncHeader()

    # append the code for the ReadMatrixSequential command header: 8 bits
    data += [self.periphery_header_map["ReadMatrixDataDriven"]]

    data += [0x00]

    if write is True:
        self.write(data)
    return data

def read_pixel_matrix_sequential(self, TokenSelect=range(128), write=True):
    """
    Sends the Pixel Matrix Read Sequential command (see manual v1.9 p.32) together with the
    SyncHeader, DColSelect and TokenSelect registers (see manual v1.9 p.46). The sended bytes are also returned.
    """
    data = []

    # presync header: 40 bits
    data = self.getGlobalSyncHeader()

    # append the code for the ReadMatrixSequential command header: 8 bits
    data += [self.periphery_header_map["ReadMatrixSequential"]]

    DColSelect= BitLogic(128)
    for index in range(128):
        DColSelect[index] = 0

    data += DColSelect.toByteList()
    TokenSelectReg= BitLogic(128)
    for index in range(128):
        if TokenSelect[index] == 0:
            TokenSelectReg[index] = 0
        else:
            TokenSelectReg = 1

    data += TokenSelectReg.toByteList()

    data += [0x00]

    if write is True:
        self.write(data)
    return data
