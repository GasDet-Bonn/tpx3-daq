Chip and Readout settings
=========================

Via the CLI and the GUI it is possible to change several settings of the Timepix3 ASICs,

.. _generalsettings:

General settings
----------------

There are the following general settings:

  * Polarity: selects if either positive or negative charge is collected by the
    pixels.
  * Fast IO: selects if the last four bits of the hit data is used for the fast
    TOA (ON) which results in a time binning of 1.56 ns or if they are used as 
    an hit counter (OFF).
  * Operation mode: selects the operation mode for readouts. There are the
    following modes:

    * ToT and ToA
    * Only ToA
    * Event count and Integral ToT
  
  * TP_Period: sets the time between edges of the testpulses.
  * Readout speed: sets the time in seconds in which data is combined to one
    data chunk.
  * TP_Ext_Int: selection if internal (OFF) or external (ON) testpulses are
    used.
  * AckCommand enable: selection if the Timepix3 should respond to each
    command with an `acknowledge` response (ON) additionally to the
    `Ènd_of_command` response or not (OFF).
  * ClkOut_frequency_src: sets the clock frequency for the ClkOut pad of the
    ASIC.
  * Sense DAC: selects a DAC or a monitoring voltage that is put to the
    `SenseDAC` pad of the ASIC.
  * Chip links: the individual output links of the ASIC can be switched off and
    on. Only links that are accessible via the firmware are shown.