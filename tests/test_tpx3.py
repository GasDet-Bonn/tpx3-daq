#!/usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
from tpx3.tpx3 import TPX3


def run_tests():
    chip = TPX3()
    # TODO: some way to not initialize the hardware?
    chip.init()

    dac = "Vfbk"
    dac_bits = chip.dac_valsize_map[dac]
    # some number larger than the allowed value
    val_large = 2 ** (dac_bits + 2)
    val_allowed = 2 ** (dac_bits - 1)
    print(dac_bits, val_allowed)
    # Don't want to bother with unittest module for now, so poor man's
    # "assertraises"
    try:
        # check if ValueError is correctly raised
        chip.set_dac(dac, val_large, write=False)
        raise Exception
    except ValueError:
        pass

    dac_set = chip.getGlobalSyncHeader()
    assert(dac_set == [0xAA, 0x00, 0x00, 0x00, 0x00])
    # set DAC is command 0x02
    dac_set += [0x02]  # , 0x00]
    # val_allowed is last part of returned array
    from basil.utils.BitLogic import BitLogic
    bits = BitLogic(16)
    bits[13:5] = val_allowed
    bits[4:0] = 0x05
    print(bits.toByteList())
    # dac_set += [val_allowed]
    # Vfkb has DAC code 0x05
    # dac_set += [0x05]
    dac_set += bits.toByteList()
    print("Return value of set_dac ".ljust(30), chip.set_dac(dac, val_allowed, write=False))
    print("Value we expect?! ".ljust(30), dac_set)
    assert(chip.set_dac(dac, val_allowed, write=False) == dac_set)

    dac_read = chip.getGlobalSyncHeader()
    # read DAC is command 0x03
    dac_read += [0x03]
    # empty byte
    dac_read += [0x00]
    # add DAC code of Vfkb, which is 0x05
    dac_read += [0x05]
    print("Return value of read_dac ".ljust(30), chip.read_dac(dac, write=False))
    print("Value we expect?!".ljust(30), dac_read)
    print("Value we officially expect".ljust(30), chip.read_dac_exp(dac, val_allowed))
    assert(chip.read_dac(dac, write=False) == dac_read)

    print("All tests done")

if __name__ == "__main__":
    run_tests()
