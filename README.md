# tpx3-daq
[![Build Status](https://dev.azure.com/SiLab-Bonn/tpx3-daq/_apis/build/status/SiLab-Bonn.tpx3-daq?branchName=master)](https://dev.azure.com/SiLab-Bonn/tpx3-daq/_build/latest?definitionId=1&branchName=master)
[![Documentation Status](https://readthedocs.org/projects/tpx3-daq/badge/?version=latest)](https://tpx3-daq.readthedocs.io/en/latest/?badge=latest)

DAQ for the [Timepix3](https://medipix.web.cern.ch/technology-chip/timepix3-chip) chip based on the [Basil](https://github.com/SiLab-Bonn/basil) framework.

### Installation

- Install [conda](https://conda.io/miniconda.html) for python

- Install dependencies and tpx3-daq:
```
conda install numpy bitarray pyyaml scipy numba pytables matplotlib tqdm pyzmq blosc psutil
pip install git+https://github.com/SiLab-Bonn/tpx3-daq.git@master
```

### Usage

- Flash appropriate bit file (TBD)

- Run a scan (TBD):
```
tpx3 tune_noise
```
- For help, run (TBD):
```
tpx3 --help
```
- Use the online monitor:
```
tpx3_monitor
```
