from __future__ import absolute_import
from __future__ import division
import sys
from basil.utils.BitLogic import BitLogic
from six.moves import range
import os
from string import Template
import subprocess
import pkg_resources
from datetime import datetime
import numpy as np


def get_software_version(git = True):
    '''
        Tries to get the software version based on the git commit and branch. If this does not
        work the version defined in __init__.py is used
    '''
    if git:
        try:
            rev = get_git_commit()
            branch = get_git_branch()
            return branch + '@' + rev
        except:
            return pkg_resources.get_distribution("tpx3-daq").version
    else:
        return pkg_resources.get_distribution("tpx3-daq").version

def get_git_branch():
    return subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode()

def get_git_commit():
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode()

def get_git_date(short = True):
    time = int(subprocess.check_output(['git', 'log', '-1', '--format=%at']).strip().decode().strip())
    if short:
        return datetime.utcfromtimestamp(time).strftime('%d.%m.%Y')
    else:
        return datetime.utcfromtimestamp(time).strftime('%d.%m.%Y %H:%M:%S')

# this should really be a class method of BitLogic, but to stay compatible with
# the current basil version, we add it at runtime
def toByteList(obj, bitwise=False):
    """
    Converts bitstring to a list of bytes
    If `bitwise` == True, we return a list of strings containing the binary repr
    of the bytes.
    """
    if len(obj) % 8 != 0:
        raise ValueError("""Cannot convert to array of bytes, if number of
        bits not a multiple of a byte""")
    nbytes = len(obj) // 8
    byteList = []

    # range from 0 to 40, reversed to get MSB first
    # for some reason list comprehension doesn't work here?
    for i in reversed(list(range(0, len(obj), 8))):
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

def threshold_compose(fine, coarse):
    """
    Returns the composed threshold based on the fine and the coarse threshold DACs
    """
    fine *= 0.5
    coarse *= 80
    threshold = (fine + coarse) / 0.5

    return threshold

def threshold_decompose(threshold):
    """
    Returns (fine, coarse) threshold DACs based on the composed threshold
    """
    if(threshold <= 511):
        coarse_threshold = 0
        fine_threshold = threshold
    else:
        relative_fine_threshold = (threshold - 512) % 160
        coarse_threshold = (((threshold - 512) - relative_fine_threshold) // 160) + 1
        fine_threshold = relative_fine_threshold + 352
    
    return fine_threshold, coarse_threshold

def number_of_possible_thresholds(threshold):
    '''
        Determine th number of possible carse and fine thresholds that generate the given 'threshold'.
        Returns the number of thresholds, and the lowest and highest needed coarse thresholds.
    '''
    # Calculate the highest and lowest possible coarse threshold
    higher_coarse = (threshold / 2) // 80
    lower_coarse = (threshold / 2 - 256) // 80 + 1

    # The coarse threshold can not be bigger than 15 and smaller than 0
    if higher_coarse > 15:
        higher_coarse = 15
    if lower_coarse < 0:
        lower_coarse = 0

    # Calculate the number of possible thresholds
    number = higher_coarse - lower_coarse + 1
    return number, lower_coarse, higher_coarse

def get_possible_thresholds(threshold):
    '''
        Generate a list of possible coarse/fine combinations that represent the 'threshold'.
        Returns a the list of coarse and fine thresholds
    '''
    _, lower_coarse, higher_coarse = number_of_possible_thresholds(threshold)

    # Generate the list of coarse thresholds
    coarses = np.arange(lower_coarse, higher_coarse + 1, 1)

    # Generate the list of fine thresholds
    fines = (threshold / 2 - coarses * 80) *2

    return coarses, fines

def get_range_thresholds(start, stop):
    '''
        Return for a range of thresholds (start to stop) the coarse and fine thresholds that have
        the highest possible coarse for start and the lowest possible for stop.
    '''
    # Get the list of possible thresholds for start and stop
    start_coarses, start_fines = get_possible_thresholds(start)
    stop_coarses, stop_fines = get_possible_thresholds(stop)

    # Get the thresholds with the highest coarse for start
    start_coarse = start_coarses[len(start_coarses) - 1]
    start_fine = start_fines[len(start_fines) - 1]

    # Get the thresholds with the lowest coarse for stop
    stop_coarse = stop_coarses[0]
    stop_fine = stop_fines[0]

    # Catch the case that the lowest possible stop coarse is smaller than the highest possible start coarse
    if stop_coarse <= start_coarse:
        stop_coarse = start_coarse
        stop_fine = stop_fines[np.where(stop_coarses == stop_coarse)][0]

    return start_coarse, start_fine, stop_coarse, stop_fine

def recursive_jumps(target_coarse, current_coarse, current_fine, direction, start_coarses, start_fines):
    '''
        Generate recursively the threshold jump list for a given start threshold and a given target threshold.
        The function get the target value for the coarse threshold, the current coarse and fine thresholds of
        the current recursion step, the direction (down towards lower thresholds or up towards higher thresholds)
        and the alls possible start fine and coarse thresholds that define together with the target the threshold
        range of the recursion step
    '''
    # If the target coarse is within the possible start coarse thresholds no further recursion is needed
    try:
        mid_start_index = np.where(start_coarses == target_coarse)[0][0]
    except IndexError:
        # Differentiate between the both directions
        if direction == 'up':
            # In up direction the next coarse threshold should be as high as possible
            start_coarse = start_coarses[len(start_coarses) - 1]
            start_fine = start_fines[len(start_fines) - 1]

            # If the coarse threshold is at maximum no further recursion is needed
            if start_coarse == 15:
                return [current_coarse, current_fine, start_coarse, start_fine]
            # If the new carse threshold equals the current coarse no jump is necessary
            elif start_coarse == current_coarse:
                return

            # Get all possible threshold combinations for the new coarse threshold and calculate the jumps recursively
            coarses, fines = get_possible_thresholds((start_coarse * 80 + 255.5) * 2)
            new = recursive_jumps(target_coarse, start_coarse, 511, 'up', coarses, fines)

            # Combine the existing and the new results in the right order
            start = [current_coarse, current_fine, start_coarse, start_fine]
            start.extend(new)
        elif direction == 'down':
            # In down direction the next coarse threshold should be as low as possible
            start_coarse = start_coarses[0]
            start_fine = start_fines[0]

            # If the coarse threshold is at minimum no further recursion is needed
            if start_coarse == 0:
                return [start_coarse, start_fine, current_coarse, current_fine]
            # If the new carse threshold equals the current coarse no jump is necessary
            elif start_coarse == current_coarse:
                return

            # Get all possible threshold combinations for the new coarse threshold and calculate the jumps recursively
            coarses, fines = get_possible_thresholds((start_coarse * 80) * 2)
            new = recursive_jumps(target_coarse, start_coarse, 0, 'down', coarses, fines)

            # Combine the existing and the new results in the right order
            start = new
            start.extend([start_coarse, start_fine, current_coarse, current_fine])
    else:
        # If the new carse threshold equals the current coarse no jump is necessary
        if start_coarses[mid_start_index] == current_coarse:
            return
        else:
            # Create a result list in the right order
            if direction == 'up':
                start = [current_coarse, current_fine, start_coarses[mid_start_index], start_fines[mid_start_index]]
            elif direction == 'down':
                start = [start_coarses[mid_start_index], start_fines[mid_start_index], current_coarse, current_fine]

    return start

def get_coarse_jumps(start, stop):
    '''
        Generate a list of coarse and fine thresholds at which a coarse jump is necessary. It is optimized to set the positions of the
        jumps on the edges of the range, such that there are no jumps in the middle of the range.
        Returns [start_coarse, start_fine, jump_1_coarse_1, jump_1_fine_1, jump_1_coarse_2, jump_1_fine_2, ... , stop_coarse, stop_fine].
    '''
    # Get the fine and coarse thresholds for start and stop
    start_coarse, start_fine, stop_coarse, stop_fine = get_range_thresholds(start, stop)

    if(start_coarse == stop_coarse):
        return [start_coarse, start_fine, stop_coarse, stop_fine]

    # Get the optimal coarse threshold for the middle of the range
    mid_threshold = int((start + stop) / 2)
    mid_coarses, mid_fines = get_possible_thresholds(mid_threshold)
    index = np.where(np.absolute(mid_fines - 256) == np.min(np.absolute(mid_fines - 256)))[0][0]
    mid_coarse = mid_coarses[index]

    # Get all possible coarse/fine thresholds for the start and end value of the middle coarse threshold
    mid_start_thresholds_coarse, mid_start_thresholds_fine = get_possible_thresholds((mid_coarse * 80) * 2)
    mid_end_thresholds_coarse, mid_end_thresholds_fine = get_possible_thresholds((mid_coarse * 80 + 255.5) * 2)

    # Generate the list of coarse jumps between the start and the lower end of the middle range
    jump_down = recursive_jumps(start_coarse, mid_coarse, 0, 'down', mid_start_thresholds_coarse, mid_start_thresholds_fine)

    # Generate the list of coarse jumps between the stop and the upper end of the middle range
    jump_up = recursive_jumps(stop_coarse, mid_coarse, 511, 'up', mid_end_thresholds_coarse, mid_end_thresholds_fine)

    # Combine the results to the full jump list including start and stop thresholds
    jump_list = [start_coarse, start_fine]
    try: # Catch if there are no down-jumps
        jump_list.extend(jump_down)
    except:
        pass
    try: # Catch if there are no up-jumps
        jump_list.extend(jump_up)
    except:
        pass
    jump_list.extend([stop_coarse, stop_fine])
    
    return jump_list

def create_threshold_list(jump_list):
    '''
        Based on a list of necessary jumps in a threshold range, generate a full list of coarse
        and fine thresholds to cover the range.
    '''
    # Split the jump_list in fine and coarse thresholds
    fine_thresholds = jump_list[1::2]
    coarse_thresholds = jump_list[0::2]
    coarse_list = []
    fine_list = []

    # Go through the list of jumps
    for i in range(1, len(fine_thresholds), 2):
        # In the last step the fine threshold range must be 1 bigger to cover the full range
        if i == len(fine_thresholds) - 1:
            step_fine_list = np.arange(fine_thresholds[i-1], fine_thresholds[i]+1, dtype=np.uint16)
            step_coarse_list = np.full(len(step_fine_list), coarse_thresholds[i], dtype=np.uint8)
        else:
            step_fine_list = np.arange(fine_thresholds[i-1], fine_thresholds[i], dtype=np.uint16)
            step_coarse_list = np.full(len(step_fine_list), coarse_thresholds[i], dtype=np.uint8)
    
        # Extend the existing the coarse and fine lists with the list of the current step
        coarse_list.extend(step_coarse_list)
        fine_list.extend(step_fine_list)

    # Create threshold list array
    threshold_list = np.empty((2, len(coarse_list)))
    threshold_list[0] = coarse_list
    threshold_list[1] = fine_list
    threshold_list = threshold_list.T
    return threshold_list

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
    equal_path = os.path.join(user_path, 'equalisations')
    if not os.path.exists(equal_path):
        os.makedirs(equal_path)
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
    appdata_path = os.path.join(user_path, 'appdata')
    if not os.path.exists(appdata_path):
        os.makedirs(appdata_path)

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

def get_equal_path():
    user_path = os.path.expanduser('~')
    user_path = os.path.join(user_path, 'Timepix3')
    equal_path = os.path.join(user_path, 'equalisations')
    return equal_path

class DeltaTemplate(Template):
    delimiter = "%"

def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)
