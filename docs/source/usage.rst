Usage
=====

.. _installation:

Installation
------------

Installation of the software:
.. code-block:: console

   mkdir miniconda
   curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh
   bash miniconda.sh -u -b -p miniconda
   export PATH=~/miniconda/bin:$PATH
   conda update --yes conda
   conda install --yes numpy bitarray pytest pytest-cov pyyaml scipy numba pytables pyqt matplotlib tqdm pyzmq blosc psutil setuptools
   pip install basil_daq==3.2.0
   mkdir tpx3-daq
   git clone https://github.com/SiLab-Bonn/tpx3-daq.git tpx3-daq/
   cd tpx3-daq
   python setup.py develop

Additional steps for using the GUI:
.. code-block:: console

   sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
   pip install pycairo
   pip install PyGObject

If there are problems with the online monitor try:
.. code-block:: console

   sudo apt install libxcb-xinerama0

For the ethernet connection to the readout board setup a static ip network with
the following settings:
.. code-block:: console
   Manual IPv4
   IP: 192.168.10.1
   Mask: 255.255.255.0
   IPv6 Off

.. note::

   If you are using the MIMAS A7 readout board you need to comment out the data
   links ``RX2`` to ``RX7`` in ``tpx3/tpx3.yml``.