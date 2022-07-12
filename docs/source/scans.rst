Scans
=====

Within the software one can find several scans that are needed to prepare
Timepix3 ASICs for data taking and to test them.

Hardware Init
-------------

This scan checks the data links of the readout board for connections to
Timepix3 ASICs. It checks which links are active and for each ative link
the following parameters are checked at set for operation:
   - ChipID of the connected Timepix3
   - Output data link of the connected Timepix3
   - The data delay (shift of the sampling clock) to sample the data
     without errors
   - The edge of data sampling (0 - rising edge; 1 - falling edge)
   - Inversion of the sampled data (0 - non inverted; 1 - inverted)
   - Status code of the link:
        0) Link not connected
        1) Link connected, active and no errors
        2) Link connected, inactive and no errors
        3) Link connected, active but no suitable sampling settings was found
        4) Link connected, inactive but no suitable sampling settings was found
        5) Link connected, active but but sees unexpected data
        6) Link connected, inactive but but sees unexpected data
        7) Link connected, active but problems during reading the ChipID
        8) Link connected, inactive but problems during reading the ChipID
        9) Link not implemented in firmware


PixelDAC
--------

This scan optimises the value of the IBias_PixelDAC DAC which influences the
range and step size of the PixelDACs (individual pixel thresholds). Thus, it is
needed for an optimal equalisation of the pixel matrix. The scan gets the
following arguments:
    - Start Threshold: the lower value of the threshold range that is scanned
    - Stop Threshold: the upper value of the threshold range that is scanned
    - Number of injections: number of testpulses per pixel and per threshold
      step to get the threshold s-curves.
    - Column offset: offset the mask column of the scan if you know that
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
