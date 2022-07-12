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
