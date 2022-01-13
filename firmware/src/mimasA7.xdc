
# set_property CFGBVS VCCO [current_design]
# set_property CONFIG_VOLTAGE 3.3 [current_design]
# set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]
# set_property INTERNAL_VREF 0.750 [get_iobanks 34]

set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]

create_clock -period 10.000 -name CLK100 -add [get_ports CLK100_SYS]
# create_clock -period 8.000 -name rgmii_rxc -add [get_ports gmii_rx_clk]

# #Oscillator 100MHz
set_property -dict {PACKAGE_PIN H4 IOSTANDARD LVCMOS33} [get_ports CLK100_SYS]

# # Reset push button
set_property -dict {PACKAGE_PIN M2 IOSTANDARD LVCMOS33} [get_ports RESET]


####################################################################################################################
#                                               LEDs                                                               #
####################################################################################################################
set_property -dict {PACKAGE_PIN K17 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports {LED[0]}]
set_property -dict {PACKAGE_PIN J17 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports {LED[1]}]
set_property -dict {PACKAGE_PIN L14 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports {LED[2]}]
set_property -dict {PACKAGE_PIN L15 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports {LED[3]}]
set_property -dict {PACKAGE_PIN L16 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports {LED[4]}]
set_property -dict {PACKAGE_PIN K16 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports {LED[5]}]
set_property -dict {PACKAGE_PIN M15 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports {LED[6]}]
set_property -dict {PACKAGE_PIN M16 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports {LED[7]}]

# set_property -dict  { PACKAGE_PIN "J20"  IOSTANDARD LVCMOS33   SLEW FAST} [get_ports {CLK40}];

####################################################################################################################
#                                               Gigabit Ethernet                                                   #
####################################################################################################################
set_property -dict {PACKAGE_PIN P16 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports mdio_phy_mdio]
set_property -dict {PACKAGE_PIN R19 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports mdio_phy_mdc]
set_property -dict {PACKAGE_PIN R14 IOSTANDARD LVCMOS33 SLEW FAST} [get_ports phy_rst_n]

set_property -dict {PACKAGE_PIN V18 IOSTANDARD LVCMOS33 SLEW FAST DRIVE 4} [get_ports {rgmii_txd[0]}]
set_property -dict {PACKAGE_PIN U18 IOSTANDARD LVCMOS33 SLEW FAST DRIVE 4} [get_ports {rgmii_txd[1]}]
set_property -dict {PACKAGE_PIN V17 IOSTANDARD LVCMOS33 SLEW FAST DRIVE 4} [get_ports {rgmii_txd[2]}]
set_property -dict {PACKAGE_PIN U17 IOSTANDARD LVCMOS33 SLEW FAST DRIVE 4} [get_ports {rgmii_txd[3]}]
set_property -dict {PACKAGE_PIN T20 IOSTANDARD LVCMOS33 SLEW FAST DRIVE 4} [get_ports rgmii_tx_ctl]
set_property -dict {PACKAGE_PIN U20 IOSTANDARD LVCMOS33 SLEW FAST DRIVE 4} [get_ports rgmii_txc]

set_property -dict {PACKAGE_PIN AB18 IOSTANDARD LVCMOS33} [get_ports {rgmii_rxd[0]}]
set_property -dict {PACKAGE_PIN W20 IOSTANDARD LVCMOS33} [get_ports {rgmii_rxd[1]}]
set_property -dict {PACKAGE_PIN W17 IOSTANDARD LVCMOS33} [get_ports {rgmii_rxd[2]}]
set_property -dict {PACKAGE_PIN V20 IOSTANDARD LVCMOS33} [get_ports {rgmii_rxd[3]}]
set_property -dict {PACKAGE_PIN Y19 IOSTANDARD LVCMOS33} [get_ports rgmii_rx_ctl]
set_property -dict {PACKAGE_PIN W19 IOSTANDARD LVCMOS33} [get_ports rgmii_rxc]

create_clock -period 8.000 -name rxc125 -add [get_ports rgmii_rxc]

set_clock_groups -asynchronous -group {CLK40_MMCM} -group {CLK320_MMCM CLK32_MMCM} -group {rxc125 CLK125PHYRXPLL CLK125PHYTXPLL} -group {BUS_CLK_PLL}


# ###################################################################################################################
# #                                              Header P13                                                         #
# ###################################################################################################################
# #set_property -dict  { PACKAGE_PIN "F19"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[0]}];                       # IO_L18P_T2_16                 Sch = GPIO_21_P
# #set_property -dict  { PACKAGE_PIN "F20"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[1]}];                       # IO_L18N_T2_16                 Sch = GPIO_21_N
# #set_property -dict  { PACKAGE_PIN "E19"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[2]}];                       # IO_L14P_T2_SRCC_16            Sch = GPIO_22_P
# #set_property -dict  { PACKAGE_PIN "D19"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[3]}];                       # IO_L14N_T2_SRCC_16            Sch = GPIO_22_N
# set_property -dict  { PACKAGE_PIN "D20"} [get_ports {TPX3_1_DataOut_P[3]}];                       # IO_L19P_T3_16                 Sch = GPIO_23_P
# set_property -dict  { PACKAGE_PIN "C20"} [get_ports {TPX3_1_DataOut_N[3]}];                       # IO_L19N_T3_VREF_16            Sch = GPIO_23_N
# #set_property -dict  { PACKAGE_PIN "C22"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[6]}];                       # IO_L20P_T3_16                 Sch = GPIO_24_P
# #set_property -dict  { PACKAGE_PIN "B22"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[7]}];                       # IO_L20N_T3_16                 Sch = GPIO_24_N

# #set_property -dict  { PACKAGE_PIN "F18"} [get_ports {TPX3_1_ClkOut_P}];                       # IO_L15P_T2_DQS_16             Sch = GPIO_25_P
# #set_property -dict  { PACKAGE_PIN "E18"} [get_ports {TPX3_1_ClkOut_N}];                       # IO_L15N_T2_DQS_16             Sch = GPIO_25_N

# set_property -dict  { PACKAGE_PIN "C18"} [get_ports {TPX3_1_DataOut_P[0]}];                      # IO_L13P_T2_MRCC_16            Sch = GPIO_26_P
# set_property -dict  { PACKAGE_PIN "C19"} [get_ports {TPX3_1_DataOut_N[0]}];                      # IO_L13N_T2_MRCC_16            Sch = GPIO_26_N
# set_property -dict  { PACKAGE_PIN "D17"} [get_ports {TPX3_1_DataOut_P[1]}];                      # IO_L12P_T1_MRCC_16            Sch = GPIO_27_P
# set_property -dict  { PACKAGE_PIN "C17"} [get_ports {TPX3_1_DataOut_N[1]}];                      # IO_L12N_T1_MRCC_16            Sch = GPIO_27_N
# set_property -dict  { PACKAGE_PIN "B20"} [get_ports {TPX3_1_DataOut_P[2]}];                      # IO_L16P_T2_16                 Sch = GPIO_28_P
# set_property -dict  { PACKAGE_PIN "A20"} [get_ports {TPX3_1_DataOut_N[2]}];                      # IO_L16N_T2_16                 Sch = GPIO_28_N

# set_property -dict  { PACKAGE_PIN "B17"} [get_ports {TPX3_1_T0_Sync_P}];                      # IO_L11P_T1_SRCC_16            Sch = GPIO_29_P
# set_property -dict  { PACKAGE_PIN "B18"} [get_ports {TPX3_1_T0_Sync_N}];                      # IO_L11N_T1_SRCC_16            Sch = GPIO_29_N
# set_property -dict  { PACKAGE_PIN "A18"} [get_ports {TPX3_1_ENPowerPulsing_P}];                      # IO_L17P_T2_16                 Sch = GPIO_30_P
# set_property -dict  { PACKAGE_PIN "A19"} [get_ports {TPX3_1_ENPowerPulsing_N}];                      # IO_L17N_T2_16                 Sch = GPIO_30_N
# set_property -dict  { PACKAGE_PIN "E16"} [get_ports {TPX3_1_DataOut_P[4]}];                      # IO_L5P_T0_16                  Sch = GPIO_31_P
# set_property -dict  { PACKAGE_PIN "D16"} [get_ports {TPX3_1_DataOut_N[4]}];                      # IO_L5N_T0_16                  Sch = GPIO_31_N
# set_property -dict  { PACKAGE_PIN "B15"} [get_ports {TPX3_1_DataOut_P[5]}];                      # IO_L7P_T1_16                  Sch = GPIO_32_P
# set_property -dict  { PACKAGE_PIN "B16"} [get_ports {TPX3_1_DataOut_N[5]}];                      # IO_L7N_T1_16                  Sch = GPIO_32_N

# set_property -dict  { PACKAGE_PIN "A15"} [get_ports {TPX3_1_DataOut_P[6]}];                      # IO_L9P_T1_DQS_16              Sch = GPIO_33_P
# set_property -dict  { PACKAGE_PIN "A16"} [get_ports {TPX3_1_DataOut_N[6]}];                      # IO_L9N_T1_DQS_16              Sch = GPIO_33_N
# set_property -dict  { PACKAGE_PIN "C14"} [get_ports {TPX3_1_DataOut_P[7]}];                      # IO_L3P_T0_DQS_16              Sch = GPIO_34_P
# set_property -dict  { PACKAGE_PIN "C15"} [get_ports {TPX3_1_DataOut_N[7]}];                      # IO_L3N_T0_DQS_16              Sch = GPIO_34_N

# set_property -dict  { PACKAGE_PIN "A13"} [get_ports {TPX3_1_ExtTPulse_P}];                      # IO_L10P_T1_16                 Sch = GPIO_35_P
# set_property -dict  { PACKAGE_PIN "A14"} [get_ports {TPX3_1_ExtTPulse_N}];                      # IO_L10N_T1_16                 Sch = GPIO_35_N
# set_property -dict  { PACKAGE_PIN "C13"} [get_ports {TPX3_1_Reset_P}];                      # IO_L8P_T1_16                  Sch = GPIO_36_P
# set_property -dict  { PACKAGE_PIN "B13"} [get_ports {TPX3_1_Reset_N}];                      # IO_L8N_T1_16                  Sch = GPIO_36_N

# set_property -dict  { PACKAGE_PIN "D14"} [get_ports {TPX3_1_DataIn_P}];                      # IO_L6P_T0_16                  Sch = GPIO_37_P
# set_property -dict  { PACKAGE_PIN "D15"} [get_ports {TPX3_1_DataIn_N}];                      # IO_L6N_T0_VREF_16             Sch = GPIO_37_N
# set_property -dict  { PACKAGE_PIN "E13"} [get_ports {TPX3_1_EnableIn_P}];                      # IO_L4P_T0_16                  Sch = GPIO_38_P
# set_property -dict  { PACKAGE_PIN "E14"} [get_ports {TPX3_1_EnableIn_N}];                      # IO_L4N_T0_16                  Sch = GPIO_38_N

# set_property -dict  { PACKAGE_PIN "F13"} [get_ports {TPX3_1_ClkIn40_P}];                      # IO_L1P_T0_16                  Sch = GPIO_39_P
# set_property -dict  { PACKAGE_PIN "F14"} [get_ports {TPX3_1_ClkIn40_N}];                      # IO_L1N_T0_16                  Sch = GPIO_39_N
# set_property -dict  { PACKAGE_PIN "F16"} [get_ports {TPX3_1_Shutter_P}];                      # IO_L2P_T0_16                  Sch = GPIO_40_P
# set_property -dict  { PACKAGE_PIN "E17"} [get_ports {TPX3_1_Shutter_N}];                      # IO_L2N_T0_16                  Sch = GPIO_40_N

# #set_property IOSTANDARD LVDS [get_ports TPX3_*]




###################################################################################################################
#                                              Header P13                                                         #
###################################################################################################################
#set_property -dict  { PACKAGE_PIN "F19"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[0]}];                       # IO_L18P_T2_16                 Sch = GPIO_21_P
#set_property -dict  { PACKAGE_PIN "F20"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[1]}];                       # IO_L18N_T2_16                 Sch = GPIO_21_N
#set_property -dict  { PACKAGE_PIN "E19"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[2]}];                       # IO_L14P_T2_SRCC_16            Sch = GPIO_22_P
#set_property -dict  { PACKAGE_PIN "D19"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[3]}];                       # IO_L14N_T2_SRCC_16            Sch = GPIO_22_N
set_property -dict {PACKAGE_PIN D20} [get_ports {TPX3_1_DataOut_P[3]}]
set_property -dict {PACKAGE_PIN C20} [get_ports {TPX3_1_DataOut_N[3]}]
#set_property -dict  { PACKAGE_PIN "C22"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[6]}];                       # IO_L20P_T3_16                 Sch = GPIO_24_P
#set_property -dict  { PACKAGE_PIN "B22"   IOSTANDARD LVCMOS33   SLEW FAST } [get_ports {P13[7]}];                       # IO_L20N_T3_16                 Sch = GPIO_24_N

set_property -dict {PACKAGE_PIN F18} [get_ports {TPX3_1_DataOut_P[2]}]
set_property -dict {PACKAGE_PIN E18} [get_ports {TPX3_1_DataOut_N[2]}]

set_property -dict {PACKAGE_PIN C18} [get_ports {TPX3_1_DataOut_P[1]}]
set_property -dict {PACKAGE_PIN C19} [get_ports {TPX3_1_DataOut_N[1]}]
set_property -dict {PACKAGE_PIN D17} [get_ports {TPX3_1_DataOut_P[0]}]
set_property -dict {PACKAGE_PIN C17} [get_ports {TPX3_1_DataOut_N[0]}]
#set_property -dict  { PACKAGE_PIN "B20"} [get_ports {TPX3_1_ClkOut_P }];                      # IO_L16P_T2_16                 Sch = GPIO_28_P
#set_property -dict  { PACKAGE_PIN "A20"} [get_ports {TPX3_1_ClkOut_N}];                      # IO_L16N_T2_16                 Sch = GPIO_28_N

set_property -dict {PACKAGE_PIN B17 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_T0_Sync_P]
set_property -dict {PACKAGE_PIN B18 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_T0_Sync_N]
set_property -dict {PACKAGE_PIN A18 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_ENPowerPulsing_P]
set_property -dict {PACKAGE_PIN A19 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_ENPowerPulsing_N]
set_property -dict {PACKAGE_PIN E16} [get_ports {TPX3_1_DataOut_P[4]}]
set_property -dict {PACKAGE_PIN D16} [get_ports {TPX3_1_DataOut_N[4]}]
set_property -dict {PACKAGE_PIN B15} [get_ports {TPX3_1_DataOut_P[5]}]
set_property -dict {PACKAGE_PIN B16} [get_ports {TPX3_1_DataOut_N[5]}]

set_property -dict {PACKAGE_PIN A15} [get_ports {TPX3_1_DataOut_P[6]}]
set_property -dict {PACKAGE_PIN A16} [get_ports {TPX3_1_DataOut_N[6]}]
set_property -dict {PACKAGE_PIN C14} [get_ports {TPX3_1_DataOut_P[7]}]
set_property -dict {PACKAGE_PIN C15} [get_ports {TPX3_1_DataOut_N[7]}]

#IN
set_property -dict {PACKAGE_PIN A13 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_ExtTPulse_P]
set_property -dict {PACKAGE_PIN A14 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_ExtTPulse_N]
set_property -dict {PACKAGE_PIN C13 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_Reset_P]
set_property -dict {PACKAGE_PIN B13 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_Reset_N]

set_property -dict {PACKAGE_PIN D14 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_Shutter_P]
set_property -dict {PACKAGE_PIN D15 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_Shutter_N]
set_property -dict {PACKAGE_PIN E13 IOSTANDARD LVCMOS25 SLEW SLOW} [get_ports TPX3_1_ClkIn40_P]
set_property -dict {PACKAGE_PIN E14 IOSTANDARD LVCMOS25 SLEW SLOW} [get_ports TPX3_1_ClkIn40_N]

set_property -dict {PACKAGE_PIN F13 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_EnableIn_P]
set_property -dict {PACKAGE_PIN F14 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_EnableIn_N]
set_property -dict {PACKAGE_PIN F16 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_DataIn_P]
set_property -dict {PACKAGE_PIN E17 IOSTANDARD LVCMOS25 SLEW FAST} [get_ports TPX3_1_DataIn_N]

#set_property -dict  { PACKAGE_PIN "E19"  IOSTANDARD LVCMOS25   SLEW FAST} [get_ports {CLK40}];


#set_property IOSTANDARD LVDS [get_ports TPX3_*]


#set_property OFFCHIP_TERM NONE [get_ports rgmii_txd[2]]
#set_property DRIVE 16 [get_ports {rgmii_txd[3]}]
#set_property DRIVE 16 [get_ports {rgmii_txd[2]}]
#set_property DRIVE 16 [get_ports {rgmii_txd[1]}]
#set_property DRIVE 16 [get_ports {rgmii_txd[0]}]
#set_property PULLDOWN true [get_ports {rgmii_rxd[3]}]
#set_property PULLDOWN true [get_ports {rgmii_rxd[2]}]
#set_property PULLDOWN true [get_ports {rgmii_rxd[1]}]
#set_property PULLDOWN true [get_ports {rgmii_rxd[0]}]
#set_property PULLUP true [get_ports {rgmii_txd[3]}]
#set_property PULLUP true [get_ports {rgmii_txd[2]}]
#set_property PULLUP true [get_ports {rgmii_txd[1]}]
#set_property PULLUP true [get_ports {rgmii_txd[0]}]
