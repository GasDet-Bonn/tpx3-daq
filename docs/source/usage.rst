Usage
=====

.. _installation:

Installation
------------

Installation of the software:

First download the latest Miniforge3 release for your platform on https://conda-forge.org/miniforge/#latest-release and rename
the script to `miniforge.sh`. Continue in the shell with these commands:

.. code-block:: bash

   sudo apt update
   sudo apt upgrade
   sudo apt install curl libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
   mkdir miniforge
   bash miniforge.sh -u -b -p miniforge
   export PATH=<PATH_TO_MINIFORGE>/miniforge/bin:$PATH
   mamba update --yes mamba
   mamba install --yes numpy bitarray pytest pytest-cov pyyaml scipy numba pytables pyqt matplotlib tqdm pyzmq blosc psutil setuptools
   pip install git+https://github.com/magruber/basil.git@master
   pip install pycairo
   pip install PyGObject
   mkdir tpx3-daq
   git clone https://github.com/SiLab-Bonn/tpx3-daq.git tpx3-daq/
   cd tpx3-daq
   pip install -e .

If there are problems with the online monitor try:

.. code-block:: bash

   sudo apt install libxcb-xinerama0

For the ethernet connection to the readout board setup a static ip network with
the following settings:

   * Manual IPv4
   * IP: 192.168.10.1
   * Mask: 255.255.255.0
   * IPv6 Off
   * MTU: automatic

.. note::

   If you are using the MIMAS A7 readout board you need to comment out the data
   links ``RX2`` to ``RX7`` in ``tpx3/tpx3.yml``.