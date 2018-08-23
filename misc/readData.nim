import sequtils, os, strformat, tables

import nimhdf5
import nimhdf5/hdf5_wrapper

import tpx3-daq/tpx3/decode

when isMainModule:

  if paramCount() > 0:
    # create dataset to store with filter and read back
    var h5f = H5File(paramStr(1), "r")

    # open file and read again
    let dset = h5f["raw_data".dset_str]
    let read = dset[uint32]

    #echo read
    echo "Data is ", read.len, " long"

    let fdata = read.decode_fpga

    echo fdata[0]

    let tab = fdata[0 .. 10].decode(vcoMode = 1, mode = 0)
    echo tab

    discard h5f.close()
