Scans
=====

Within the software one can find several scans that are needed to prepare
Timepix3 ASICs for data taking and to test them.

Hardware Init
-------------

This scan checks the data links of the readout board for connections to
Timepix3 ASICs. It checks which links are active and for each active link
the following parameters are checked at set for operation:

  * ChipID of the connected Timepix3
  * Output data link of the connected Timepix3
  * The data delay (shift of the sampling clock) to sample the data
    without errors
  * The edge of data sampling (0 - rising edge; 1 - falling edge)
  * Inversion of the sampled data (0 - non inverted; 1 - inverted)
  * Status code of the link:

    0. Link not connected
    1. Link connected, active and no errors
    2. Link connected, inactive and no errors
    3. Link connected, active but no suitable sampling settings was found
    4. Link connected, inactive but no suitable sampling settings was found
    5. Link connected, active but but sees unexpected data
    6. Link connected, inactive but but sees unexpected data
    7. Link connected, active but problems during reading the ChipID
    8. Link connected, inactive but problems during reading the ChipID
    9. Link not implemented in firmware

The expected amount of available links depends on the readout board and the
used intermediate and carrier boards (nc = not compatible):

.. table:: Expected links
    :align: center

    =======================  ======================  ================  ===============
    Expected links per chip  Single Chip IB/Carrier  SPIDR IB/Carrier  IAXO Kapton PCB
    =======================  ======================  ================  ===============
    **MIMAS A7**             2                       nc                2              
    **SRS v6**               8                       nc                2              
    **ML605**                nc                      8                 nc             
    =======================  ======================  ================  ===============


PixelDAC
--------

This scan optimises the value of the IBias_PixelDAC DAC which influences the
range and step size of the PixelDACs (individual pixel thresholds). Thus, it is
needed for an optimal equalisation of the pixel matrix. The scan gets the
following arguments:

  * Start Threshold: the lower value of the threshold range that is scanned
  * Stop Threshold: the upper value of the threshold range that is scanned
  * Number of injections: number of testpulses per pixel and per threshold
    step to get the threshold s-curves.
  * Column offset: offset the mask column of the scan if you know that
    certain columns are broken. To speed up the scan only 1/16 of the Timepix3
    is scanned and thus with broken columns an offset is needed to maximize
    the number of scanned pixels.

The scan will start at a default value of 127 for the IBias_PixelDAC and there
it performs two threshold scans: one with all active pixels set to the minimum
pixel threshold and one with all active pixels set to the maximum pixel
threshold. For both scans and all active pixels s-curves are fitted and the per
pixel results are put in two histograms for the different pixel thresholds.
Based on the width and the distance of both distributions a new value for the 
IBias_PixelDAC is calculated and the process is repeated until an optimal
overlap of both distributions is reached.

Equalisation
------------

This scan optimises the PixelDACs (pixel thresholds, sometimes THS) of the pixels
to achieve a uniform response of the pixel matrix. There are two equalisation
approaches:

  * Equalisation based on Noise: threshold scans are performed at the noise
    peak of the chip (set the threshold range accordingly) to investigate the
    pixel threshold behaviour with noise hits. `Note: Equalisations with this
    approach are still in development and may not deliver reliable results yet.`
  * Equalisation based on testpulse injections: threshold scans are performed
    at a given test pulse amplitude as set via VTP_coarse and VTP_fine in the
    DAC settings (set the threshold range accordingly) to investigate the
    pixel threshold behaviour with testpulse hits.

The scan gets the following arguments:

  * Start Threshold: the lower value of the threshold range that is scanned
  * Stop Threshold: the upper value of the threshold range that is scanned
  * Mask steps: number of steps that are needed to scan the full matrix. The
    matrix is not completely active at the same time to reduce cross talk and
    to prevent running in the power limit. More steps make the scan more
    accurate but also increase the scan time.

Within the scan two threshold scans of the given threshold range are performed.
One at the minimum pixel threshold and one at the maximum pixel threshold.
Based on the resulting threshold distributions the optimal pixel threshold for
all pixels are calculated and stored in an equalisation HDF5 file.

ToT Calibration
---------------

This scan performs a calibration of the time over threshold (ToT) to charge in
electrons. The scan gets the following arguments:

  * Start testpulse fine: the lower value of the fine testpulse range
  * Stop testpulse fine: the upper value of the fine testpulse range
  * Masks steps: number of steps that are needed to scan the full matrix. The
    matrix is not completely active at the same time to reduce cross talk and
    to prevent running in the power limit. More steps make the scan more
    accurate but also increase the scan time.

Note that the amplitude of the testpulses is always dependent on the fine and
the coarse testpulse DACs as testpulses are generated by multiplexing between
these DACs. Therefore the scan not only depends on the given range of the fine
testpulse DAC but also on the coarse testpulse DAC which is set via the DAC
settings.

The scan injects per pixel and per amplitude 10 testpulse and records the ToT
measured in the pixels. To avoid noise and threshold effects only pixels that
saw exactly 10 pulses are taken into account. To generate the calibration curve
the mean ToT per pixel is calculated followed by the mean ToT of the whole chip.

.. note::

  This scan is dependent on the global threshold of the chip. So if you change
  the threshold for data taking the scan needs to be repeated. Also for the
  calibration of a chip a reasonable threshold is needed.

.. note::

  After each hit there needs to be sufficient time for the pixels to count the
  ToT. It can happen that the time is to short, as the readout of data is
  triggered by the end of the testpulses. This leads to a saturation of the
  calibration curve. If this happens increase the `TP_Period` in the settings
  and repeat the scan.

THL Scan
--------

This scan iterates over a range of thresholds while injecting a given amount of
testpulses. For each pixel and threshold iteration the number of measured
testpulses in the HitCounter mode of the Timepix3 is recoded. The scan gets the
following arguments:

  * Start Threshold: the lower value of the threshold range that is scanned
  * Stop Threshold: the upper value of the threshold range that is scanned
  * Number of injections: the number of testpulse injections per pixel and
    per threshold step.
  * Mask steps: number of steps that are needed to scan the full matrix. The
    matrix is not completely active at the same time to reduce cross talk and
    to prevent running in the power limit. More steps make the scan more
    accurate but also increase the scan time.

The amplitude of the testpulses is set via the VTP_coarse and VTP_fine DACs
within the DACs settings. The pulses are generated by multiplexing between
these two DACs.

As result of the scan a s-curve shape is expected: in some range of the
threshold all injected pulses are recorded and thus a plateau in the hits per
threshold distribution is visible. With increasing thresholds some of the
pulses are below the threshold so that the number of recorded pulses
decreases. At some point all pluses will be below the threshold which leads
to a second plateau at zero recorded hits.

The analysis of the scan fits the s-curves for all pixels individually and puts
the results (mean and width of the curves) into histograms.

Testpulse Scan
--------------

This scan iterates over a range of testpulse amplitudes while injecting a given
amount of testpulses. For each pixel and testpulse iteration the number of measured
testpulses in the HitCounter mode of the Timepix3 is recoded. The scan gets the
following arguments:

  * Start Testpulse: the lower value of the VTP_fine range that is scanned
  * Stop Testpulse: the upper value of the VTP_fine range that is scanned
  * Number of injections: the number of testpulse injections per pixel and
    per threshold step.
  * Mask steps: number of steps that are needed to scan the full matrix. The
    matrix is not completely active at the same time to reduce cross talk and
    to prevent running in the power limit. More steps make the scan more
    accurate but also increase the scan time.

The threshold for the scan is set by the Vthreshold_fine and Vthreshold_coarse
DACs within the DACs settings. Also the VTP_coarse (the second level of the
testpulses) is set there. The pulses are generated by multiplexing between
VTP_coarse and VTP_fine.

As result of the scan a s-curve shape is expected: in some range of the
testpulse all injected pulses are recorded and thus a plateau in the hits per
testpulse amplitude distribution is visible. With decreasing amplitudes some of
the pulses are below the threshold so that the number of recorded pulses
decreases. At some point all pluses will be below the threshold which leads
to a second plateau at zero recorded hits.

The analysis of the scan fits the s-curves for all pixels individually and puts
the results (mean and width of the curves) into histograms.

THL Calibration
---------------

This scan performs a calibration of the threshold (THL) DAC values to charge in
electrons. The scan gets the following arguments:

  * Start Threshold: the lower value of the threshold range that is scanned
  * Stop Threshold: the upper value of the threshold range that is scanned
  * Number of injections: the number of testpulse injections per pixel and
    per threshold step.
  * Mask steps: number of steps that are needed to scan the full matrix. The
    matrix is not completely active at the same time to reduce cross talk and
    to prevent running in the power limit. More steps make the scan more
    accurate but also increase the scan time.
  * Pulse height steps: the number of different testpulse amplitudes that are
    scanned. Each amplitude leads to one calibration data point.

The scan performs for each pulse height step a THL scan. The mean of its
threshold distribution form then together with the testpulse amplitude a data
point for the threshold calibration. For the amplitudes the VTP_coarse is
always set to 100 (500 mV). The VTP_fine is calculated as follows (iteration
starts a 0):

.. math::
  \begin{align}
    \text{VTP fine} = 240 + \frac{100}{\text{Pulse height steps}} \cdot \text{iteration}
  \end{align}

As result of the calibration a linear function is expected and thus fitted to
the calibration data points.

Noise Scan
----------

This scan iterates over a range of thresholds in the HitCounter mode and
without testpulses and records for every threshold how many pixels saw hits and
how many hits in total were seen. Compared to other scans this scan is not
performed with mask steps but with the complete matrix active at all times.
The scan gets the following arguments:

  * Start Threshold: the lower value of the threshold range that is scanned
  * Stop Threshold: the upper value of the threshold range that is scanned
  * Shutter time: the time in seconds for which the shutter for each threshold
    is opened.

The purpose of this scan is to estimate a good setting (low threshold and low
number of noise hits) for the threshold for data taking. Therefore the scan
should be performed close to the noise peak of the chip as far away from this
there wont be any hits. This is also dependent on the shutter time as the
expected number of noise hits for a given threshold rises with the time.
Therefore the time should be selected such that the scan result is reasonable
for the application of the chip.

.. Note::
  This scan is optimized for time and thus it does not do multiple readouts per
  threshold. This leads to statistical fluctuations of the results.

Readout
-------

With the readout "scan" pixel data is recorded in the mode which is set in the
chip settings (ToA & ToT, only ToA or HitCounter and iToT). The only possible
argument is the length of the run. If its set to 0 the readout runs indefinitely
until it is stopped by the user. Within a readout testpulses are inactive and
the most recent equalisation and mask are used.
