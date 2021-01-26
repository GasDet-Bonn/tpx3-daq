from __future__ import absolute_import
from __future__ import division
import sys
from basil.utils.BitLogic import BitLogic
from six.moves import range
import os


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


def print_nice(f):
    if isinstance(f, int):
        return str(f)
    elif isinstance(f, float):
        if abs(f - round(f)) <= sys.float_info.epsilon:
            return str(round(f))
        else:
            return str(f)
    else:
        raise TypeError("`print_nice` only supports floats and ints! Input " +
                        "is of type {}!".format(type(f)))


def check_user_folders():
    """
    Checks if if the expected folder structure for user files is present.
    If not missing folders are created.
    """
    # Setup folder structure in user home folder
    user_path = os.path.expanduser('~')
    user_path = os.path.join(user_path, 'Timepix3')
    if not os.path.exists(user_path):
        os.makedirs(user_path)
    backup_path = os.path.join(user_path, 'backups')
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    mask_path = os.path.join(user_path, 'masks')
    if not os.path.exists(mask_path):
        os.makedirs(mask_path)
    scan_path = os.path.join(user_path, 'scans')
    if not os.path.exists(scan_path):
        os.makedirs(scan_path)
    data_path = os.path.join(user_path, 'data')
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    tmp_path = os.path.join(user_path, 'tmp')
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    picture_path = os.path.join(user_path, 'pictures')
    if not os.path.exists(picture_path):
        os.makedirs(picture_path)

    scan_hdf_path = os.path.join(scan_path, 'hdf')
    if not os.path.exists(scan_hdf_path):
        os.makedirs(scan_hdf_path)
    scan_log_path = os.path.join(scan_path, 'logs')
    if not os.path.exists(scan_log_path):
        os.makedirs(scan_log_path)

    data_hdf_path = os.path.join(data_path, 'hdf')
    if not os.path.exists(data_hdf_path):
        os.makedirs(data_hdf_path)
    data_log_path = os.path.join(data_path, 'logs')
    if not os.path.exists(data_log_path):
        os.makedirs(data_log_path)
