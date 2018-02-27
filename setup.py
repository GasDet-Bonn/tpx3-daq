#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages

import tpx3
from symbol import except_clause

version = tpx3.__version__

author = ''
author_email = ''

# Requirements
install_requires = ['basil-daq==2.4.11', 'bitarray>=0.8.1', 'matplotlib',
                    'numpy', 'online_monitor==0.3.1',
                    'pixel_clusterizer==3.1.3', 'tables', 'pyyaml', 'pyzmq',
                    'scipy', 'numba', 'tqdm']
setup(
    name='tpx3-daq',
    version=version,
    description='DAQ for TimePix3 ASIC',
    url='https://github.com/SiLab-Bonn/tpx3-daq',
    license='',
    long_description='',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    packages=find_packages(),
    include_package_data=True,
    platforms='any'
)
