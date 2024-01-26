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


DACs
----
There are several DACs on each Timepix3 to set internal voltages and currents (based on the Timepix3 manual):

.. table:: DACs
    :align: center

    =================  ====  =======  ========  =================
    Name               Bits  LSB      DACOut    Function
    =================  ====  =======  ========  =================
    Ibias_Preamp_ON    8     20 nA    5 µA/V    Controls the bias current of the front-end preamplifier. Impacts Peaking time, gain and noise of front-end.
    Ibias_Preamp_OFF   4     20 nA    5 µA/V    Controls the bias current of the front-end preamplifier. Impacts Peaking time, gain and noise of front-end.
    VPreamp_NCAS       8     5 mV     1 V/V     From TPX1 manual be carefull! (The cascode controlled by the Vcas 8-bit DAC helps to reduce the input capacitance of the preamplifier, improving the SNR but reducing the output voltage dynamic range)
    Ibias_Ikrum        8     240 pA   ?         Constant current for discharging the pixel capacitor. Impacts the number of ToT clock cycles for charge pulses.
    Vfbk               8     5 mV     1 V/V     From TPX1 manual be carefull! (A voltage DAC (Vfbk) controls the Vfbk node. This node sets a DC output voltage to allow a bigger dynamic range whether holes or electrons are being collected and it is controlled by means of an 8-bit voltage DAC with a rail-to-rail dynamic range).
    Vthreshold_fine    9     500 µV   1 V/V     Sets the global threshold of the chip. Coarse and fine are additive.
    Vthreshold_coarse  4     80 mV    1 V/V     Sets the global threshold of the chip. Coarse and fine are additive.
    Ibias_DiscS1_ON    8     20 nA    5 µA/V    Sets the bias current on the first stage of the front-end discriminator. Impacts DiscS1 current is proportional to PixelDAC current; Discriminator timer jitter.
    Ibias_DiscS1_OFF   4     20 nA    5 µA/V    Sets the bias current on the first stage of the front-end discriminator. Impacts DiscS1 current is proportional to PixelDAC current; Discriminator timer jitter.
    Ibias_DiscS2_ON    8     13 nA    3.3 µA/V  Sets the bias current on the second stage of the front-end discriminator. Impacts Discriminator timer jitter.
    Ibias_DiscS2_OFF   4     13 nA    3.3 µA/V  Sets the bias current on the second stage of the front-end discriminator. Impacts Discriminator timer jitter.
    Ibias_PixelDAC     8     1.08 nA  270 nA/V  Range adjustment of the pixel thresholds. PixelDAC current is proportional to DiscS1 current.
    Ibias_TPbufferIn   8     40 nA    ?         Seems not to affect internal Testpulses
    Ibias_TPbufferOut  8     1 µA     ?         Seems not to affect internal Testpulses
    VTP_coarse         8     5 mV     1 V/V     Sets the levels for internal test pulses. Multiplexing between coarse and fine.
    VTP_fine           9     2.5 mV   1 V/V     Sets the levels for internal test pulses. Multiplexing between coarse and fine.
    Ibias_CP_PLL       8     600 nA   ?         ?
    PLL_Vcntrl         8     5.7 mV   1 V/V     ?
    =================  ====  =======  ========  =================

.. note::

  Some DACs have an `ON` and an `OFF` state. If power pulsing is active
  (currently not implemented in this readout system) the `ON` state is used if
  the power pulsing periphery is on and the `OFF` state is used i the periphery
  is off. If the power pulsing is inactive always the `ON` state is used.

There are the following SenseDACs (The DACs can be additionally used as SenseDACs):

.. table:: SenseDACs
    :align: center

    =================  =================
    Name               Function
    =================  =================
    PLL_Vcntrl         PLL Vcntrl Out if SelectVcntrl_PLL_DAC=1
    BandGap_output     Band Gap output voltage (637mV)
    BandGap_Temp       Band Gap temperature voltage
    Ibias_dac          Biasing DAC voltage (1.16V)
    Ibias_dac_cas      Biasing DAC voltage cascode (950mV)
    SenseOFF           Deactivates DACOut pad
    =================  =================
