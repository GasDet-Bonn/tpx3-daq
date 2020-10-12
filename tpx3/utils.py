from __future__ import absolute_import
from __future__ import division
from basil.utils.BitLogic import BitLogic
from six.moves import range


# this should really be a class method of BitLogic, but to stay compatible with
# the current basil version, we add it at runtime
def toByteList(obj, bitwise=False):
    """
    Converts bitstring to a list of bytes
    If `bitwise` == True, we return a list of strings containing the binary repr
    of the bytes.
    """
    if obj.length() % 8 != 0:
        raise ValueError("""Cannot convert to array of bytes, if number of
        bits not a multiple of a byte""")
    nbytes = obj.length() // 8
    byteList = []

    # range from 0 to 40, reversed to get MSB first
    # for some reason list comprehension doesn't work here?
    for i in reversed(list(range(0, obj.length(), 8))):
        if bitwise is False:
            byteList += [obj[i + 7:i].tovalue()]
        else:
            byteList += [obj[i + 7:i].__str__()]

    return byteList


def bitword_to_byte_list(data, string=False):
    """
    Given a 32 bit word, convert it to a list of bytes using BitLogic
    """
    result = BitLogic(32)
    result[31:0] = int(data)
    result = toByteList(result, string)
    return result
