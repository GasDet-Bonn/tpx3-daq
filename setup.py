#!/usr/bin/env python

from __future__ import absolute_import
from setuptools import setup
from setuptools import find_packages

import tpx3
from symbol import except_clause

import os

version = tpx3.__version__

author = ''
author_email = ''

# Requirements
install_requires = ['basil-daq==3.0.1', 'bitarray>=0.8.1', 'matplotlib',
                    'numpy', 'online_monitor>=0.4.0<0.5',
                    'pixel_clusterizer==3.1.3', 'tables', 'pyyaml', 'pyzmq',
                    'scipy', 'numba', 'tqdm']
setup(
    name='tpx3-daq',
    version=version,
    description='DAQ for Timepix3 ASIC',
    url='https://github.com/SiLab-Bonn/tpx3-daq',
    license='',
    long_description='',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    python_requires=">=3.0",
    packages=find_packages(),
    setup_requires=['online_monitor>=0.4.0<0.5'],
    include_package_data=True,
    platforms='any',
    entry_points={
        'console_scripts': [
            'tpx3_monitor = tpx3.online_monitor.start_tpx3_monitor:main'
        ]
    },

)

try:
    from online_monitor.utils import settings
    # Get the absoulte path of this package
    package_path = os.path.dirname(tpx3.__file__)
    # Add online_monitor plugin folder to entity search paths
    settings.add_producer_sim_path(os.path.join(package_path,
                                                'online_monitor'))
    settings.add_converter_path(os.path.join(package_path,
                                             'online_monitor'))
    settings.add_receiver_path(os.path.join(package_path,
                                            'online_monitor'))
except ImportError:
    pass

# Setup folder structure in user home folder
user_path = os.path.expanduser('~')
user_path = os.path.join(user_path, 'Timepix3')
if not os.path.exists(user_path):
    os.makedirs(user_path)
backup_path = os.path.join(user_path, 'backups')
if not os.path.exists(backup_path):
    os.makedirs(backup_path)
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
