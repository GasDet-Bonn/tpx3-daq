

`timescale 1ns / 1ps

`define BOARD_ID 4 //"MIMASA7"

`define MIMASA7

`include "tpx3_core.v"

// `include "../lib/si_udp/si_udp.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/eth_mac_1g_fifo.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/eth_mac_1g.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/axis_gmii_rx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/axis_gmii_tx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/lfsr.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/eth_axis_rx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/eth_axis_tx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/udp_complete.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/udp_checksum_gen.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/udp.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/udp_ip_rx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/udp_ip_tx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/ip_complete.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/ip.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/ip_eth_rx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/ip_eth_tx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/ip_arb_mux_2.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/ip_mux_2.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/arp.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/arp_cache.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/arp_eth_rx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/arp_eth_tx.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/eth_arb_mux_2.v"
// `include "../lib/si_udp/verilog-ethernet/rtl/eth_mux_2.v"
// `include "../lib/si_udp/verilog-ethernet/lib/axis/rtl/arbiter.v"
// `include "../lib/si_udp/verilog-ethernet/lib/axis/rtl/priority_encoder.v"
// `include "../lib/si_udp/verilog-ethernet/lib/axis/rtl/axis_fifo.v"
// `include "../lib/si_udp/verilog-ethernet/lib/axis/rtl/axis_async_frame_fifo.v"
 
`include "../lib/extra/rgmii_io_adv.v"
`include "utils/reset_gen.v"
`include "sync_reset.v"

`include "utils/clock_divider.v"

`default_nettype wire
`include "../lib/SiTCP_Netlist_for_Artix7/TIMER.v"
`include "../lib/SiTCP_Netlist_for_Artix7/SiTCP_XC7A_32K_BBT_V110.V"
`include "../lib/SiTCP_Netlist_for_Artix7/WRAP_SiTCP_GMII_XC7A_32K.V"
`default_nettype none

`include "../lib/extra/rbcp_to_sbus.v"
`include "utils/fifo_32_to_8.v"

module tpx3_daq (input wire CLK100_SYS,
                 input wire RESET,
                 output wire [3:0] rgmii_txd,
                 output wire rgmii_tx_ctl,
                 output wire rgmii_txc,
                 input wire [3:0] rgmii_rxd,
                 input wire rgmii_rx_ctl,
                 input wire rgmii_rxc,
                 output wire mdio_phy_mdc,
                 inout wire mdio_phy_mdio,
                 output wire phy_rst_n,

                 output wire TPX3_1_ClkIn40_N,
                 output wire TPX3_1_ClkIn40_P,
                 output wire TPX3_1_Reset_N,
                 output wire TPX3_1_Reset_P,
                 output wire TPX3_1_ExtTPulse_N,
                 output wire TPX3_1_ExtTPulse_P,
                 output wire TPX3_1_T0_Sync_N,
                 output wire TPX3_1_T0_Sync_P,
                 output wire TPX3_1_EnableIn_N,
                 output wire TPX3_1_EnableIn_P,
                 output wire TPX3_1_DataIn_N,
                 output wire TPX3_1_DataIn_P,
                 output wire TPX3_1_Shutter_N,
                 output wire TPX3_1_Shutter_P,
                 output wire TPX3_1_ENPowerPulsing_N,
                 output wire TPX3_1_ENPowerPulsing_P,
                 input wire [7:0] TPX3_1_DataOut_N,TPX3_1_DataOut_P,

                 output wire [7:0] LED
    );
  
    // Clock and reset
    
    wire mmcm_rst = 1'b0;                                                                                                                                                                              //RST;//reset;
    wire mmcm_locked;
    wire mmcm_clkfb;
    
    wire CLK40_MMCM;
    wire CLK320_MMCM;
    wire CLK32_MMCM;
    wire CLK200_MMCM;
    wire CLK40PS_MMCM;

    wire CLK160_MMCM, CLK160;
    wire BUS_CLK_PLL;
    
    wire RESET_N;
    assign RESET_N = ~RESET;
    
    MMCM_BASE #(
        .BANDWIDTH         ("OPTIMIZED"),
        .CLKOUT0_DIVIDE_F  (3),
        .CLKOUT0_DUTY_CYCLE(0.5),
        .CLKOUT0_PHASE     (0),

        .CLKOUT1_DIVIDE    (24),
        .CLKOUT1_DUTY_CYCLE(0.5),
        .CLKOUT1_PHASE     (0),

        .CLKOUT2_DIVIDE    (30),
        .CLKOUT2_DUTY_CYCLE(0.5),
        .CLKOUT2_PHASE     (0),

        .CLKOUT3_DIVIDE    (5),
        .CLKOUT3_DUTY_CYCLE(0.5),
        .CLKOUT3_PHASE     (0),

        .CLKOUT4_DIVIDE    (6),
        .CLKOUT4_DUTY_CYCLE(0.5),
        .CLKOUT4_PHASE     (0),

        .CLKOUT5_DIVIDE    (24),
        .CLKOUT5_DUTY_CYCLE(0.5),
        .CLKOUT5_PHASE     (120),

        .CLKOUT6_DIVIDE    (7),
        .CLKOUT6_DUTY_CYCLE(0.5),
        .CLKOUT6_PHASE     (0),
        
        .CLKFBOUT_MULT_F   (48),
        .CLKFBOUT_PHASE    (0),
        .DIVCLK_DIVIDE     (5),
        
        .REF_JITTER1       (0.100),
        .CLKIN1_PERIOD     (10.0),
        .STARTUP_WAIT      ("FALSE"),
        .CLKOUT4_CASCADE   ("FALSE")
    )
    clk_mmcm_inst (
        .CLKIN1   (CLK100_SYS),
        .CLKFBIN  (mmcm_clkfb),
        .RST      (mmcm_rst),
        .PWRDWN   (1'b0),
        .CLKOUT0  (CLK320_MMCM),
        .CLKOUT0B (),
        .CLKOUT1  (CLK40_MMCM),
        .CLKOUT1B (),
        .CLKOUT2  (CLK32_MMCM),
        .CLKOUT2B (),
        .CLKOUT3  (CLK200_MMCM),
        .CLKOUT3B (),
        .CLKOUT4  (CLK160_MMCM),
        .CLKOUT5  (CLK40PS_MMCM),
        .CLKOUT6  (BUS_CLK_PLL),
        .CLKFBOUT (mmcm_clkfb),
        .CLKFBOUTB(),
        .LOCKED   (mmcm_locked)
    );
    
    wire CLK40, CLK320, CLK32, CLK40_90, BUS_CLK;
    BUFG clk_40mhz_bufg_inst (.I(CLK40PS_MMCM), .O(CLK40_90));
    BUFG clk_40mhz_90_bufg_inst (.I(CLK40_MMCM), .O(CLK40));
    BUFG clk_160mhz_bufg_inst (.I(CLK160_MMCM), .O(CLK160));
    BUFG clk_320mhz_bufg_inst (.I(CLK320_MMCM), .O(CLK320));
    BUFG clk_64mhz_bufg_inst (.I(CLK32_MMCM), .O(CLK32));
    BUFG clk_bus_clk_bufg_inst (.I(BUS_CLK_PLL), .O(BUS_CLK));

    wire CLK125PHYTXPLL, CLK125PHYTX90PLL, CLK200PLL;
    wire PLL_FEEDBACK, LOCKED;
    wire CLK125RX;

    PLLE2_BASE #(
        .BANDWIDTH("OPTIMIZED"),    // OPTIMIZED, HIGH, LOW
        .CLKFBOUT_MULT(8),         // Multiply value for all CLKOUT, (2-64)
        .CLKFBOUT_PHASE(0.0),       // Phase offset in degrees of CLKFB, (-360.000-360.000). //0
        .CLKIN1_PERIOD(8),     // Input clock period in ns to ps resolution (i.e. 33.333 is 30 MHz).
        
        .CLKOUT0_DIVIDE(8),         // Divide amount for CLKOUT0 (1-128)
        .CLKOUT0_DUTY_CYCLE(0.5),   // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT0_PHASE(90), //`PHASE_RX),        // Phase offset for CLKOUT0 (-360.000-360.000). //270 /335.7
        
        .CLKOUT1_DIVIDE(8),         // Divide amount for CLKOUT0 (1-128)
        .CLKOUT1_DUTY_CYCLE(0.5),   // Duty cycle for CLKOUT0 (0.001-0.999).
        //.CLKOUT1_PHASE(`PHASE_TX),        // Phase offset for CLKOUT0 (-360.000-360.000). //90 202 , 185 - okbit 225 - ok a bit
        .CLKOUT1_PHASE(190),        // Phase offset for CLKOUT0 (-360.000-360.000). //90 202 , 185 - okbit 225 - ok a bit
        
        .CLKOUT2_DIVIDE(5),         // Divide amount for CLKOUT0 (1-128)
        .CLKOUT2_DUTY_CYCLE(0.5),   // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT2_PHASE(0.0),        // Phase offset for CLKOUT0 (-360.000-360.000).
        
        .CLKOUT3_DIVIDE(1),         // Divide amount for CLKOUT0 (1-128)
        .CLKOUT3_DUTY_CYCLE(0.5),   // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT3_PHASE(0.0),       // Phase offset for CLKOUT0 (-360.000-360.000).
        
        .CLKOUT4_DIVIDE(1),         // Divide amount for CLKOUT0 (1-128)
        .CLKOUT4_DUTY_CYCLE(0.5),   // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT4_PHASE(0.0),     // Phase offset for CLKOUT0 (-360.000-360.000).     // resolution is 45°/[CLKOUTn_DIVIDE]
        
        .CLKOUT5_DIVIDE(10),        // Divide amount for CLKOUT0 (1-128)
        .CLKOUT5_DUTY_CYCLE(0.5),   // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT5_PHASE(0.0),        // Phase offset for CLKOUT0 (-360.000-360.000).
        
        .DIVCLK_DIVIDE(1),          // Master division value, (1-56)
        .REF_JITTER1(0.0),          // Reference input jitter in UI, (0.000-0.999).
        .STARTUP_WAIT("FALSE")      // Delay DONE until PLL Locks, ("TRUE"/"FALSE")
    )
    PLLE2_BASE_inst (
        .CLKOUT0(CLK125PHYTXPLL),
        .CLKOUT1(CLK125PHYTX90PLL),
        .CLKOUT2(CLK200PLL),
        .CLKOUT3(),
        .CLKOUT4(),
        .CLKOUT5(),
        .CLKFBOUT(PLL_FEEDBACK),
        .LOCKED(LOCKED),   
        .CLKIN1(CLK125RX),
        .PWRDWN(0),
        .RST(1'b0),
        .CLKFBIN(PLL_FEEDBACK)
    );
    
    wire CLK_PHY125TX, CLK_PHY125TX90, CLK200;
    BUFG BUFG_PHY125RX (.I(CLK125PHYTXPLL), .O(CLK_PHY125TX));
    BUFG BUFG_PHY125TX (.I(CLK125PHYTX90PLL), .O(CLK_PHY125TX90));
    BUFG BUFG_CLK200 (.O(CLK200), .I(CLK200PLL));
    
    wire phy_gmii_rst;
    reset_gen reset_gen (.CLK(CLK125RX), .RST(phy_gmii_rst));
    wire reset_tx;
    reset_gen reset_gen_tx (.CLK(CLK_PHY125TX), .RST(reset_tx));
    
    // -------  RGMII interface  ------- //
    wire   link_status;
    wire  [1:0] clock_speed;
    wire   duplex_status;
    
    wire   gmii_tx_en;
    wire  [7:0] gmii_txd;
    wire   gmii_tx_er;
    wire   gmii_crs;
    wire   gmii_col;
    wire   gmii_rx_clk;
    wire   gmii_rx_dv;
    wire  [7:0] gmii_rxd;
    wire   gmii_rx_er;
    
    //rgmii_io_adv  #(.RXDELAY(`PHASE_RX) ) rgmii
    rgmii_io_adv  #(.RXDELAY(19) ) rgmii
    (
    .rgmii_txd(rgmii_txd),
    .rgmii_tx_ctl(rgmii_tx_ctl),
    .rgmii_txc(rgmii_txc),
    
    .rgmii_rxd(rgmii_rxd),
    .rgmii_rx_ctl(rgmii_rx_ctl),
    .rgmii_rxc(rgmii_rxc),
    
    .gmii_txd(gmii_txd),
    .gmii_tx_en(gmii_tx_en),
    .gmii_tx_er(gmii_tx_er),
    .gmii_col(gmii_col),
    .gmii_crs(gmii_crs),
    .gmii_rxd(gmii_rxd),
    .gmii_rx_dv(gmii_rx_dv),
    .gmii_rx_er(gmii_rx_er),
    
    .eth_link_status(link_status),
    .eth_clock_speed(clock_speed),
    .eth_duplex_status(duplex_status),
    
    .tx_clk(CLK_PHY125TX),
    .tx_clk90(CLK_PHY125TX90),
    .rx_clk(CLK125RX),
    .reset(1'b0)
    );
    
    wire [31:0] BUS_ADD, BUS_DATA_OUT, BUS_DATA_IN;
    wire BUS_RD, BUS_WR, BUS_RST, BUS_BYTE_ACCESS;

    wire SiTCP_RST;
    wire TCP_CLOSE_REQ;

    wire RBCP_ACT, RBCP_WE, RBCP_RE;
    wire [7:0] RBCP_WD, RBCP_RD;
    wire [31:0] RBCP_ADDR;
    wire RBCP_ACK;

    wire TCP_TX_WR;
    wire TCP_TX_FULL;
    wire [7:0] TCP_TX_DATA;

    assign BUS_RST = SiTCP_RST;
    wire RST;
    assign RST = ~mmcm_locked ;

     wire   mdio_gem_i;
     wire   mdio_gem_o;
     wire   mdio_gem_t;
     
    WRAP_SiTCP_GMII_XC7A_32K sitcp(
        .CLK(BUS_CLK)                ,    // in     : System Clock >129MHz
        .RST(RST)                    ,    // in     : System reset
        // Configuration parameters
        .FORCE_DEFAULTn(1'b0)        ,    // in     : Load default parameters
        .EXT_IP_ADDR({8'd192, 8'd168, 8'd10, 8'd23}),   //IP address[31:0] default: 192.168.10.23. If jumpers are set: 192.168.[11..25].23
        .EXT_TCP_PORT(16'd24)        ,    // in     : TCP port #[15:0]
        .EXT_RBCP_PORT(16'd4660)     ,    // in     : RBCP port #[15:0]
        .PHY_ADDR(5'd3)              ,    // in     : PHY-device MIF address[4:0]
        // EEPROM
        .EEPROM_CS()    ,    // out    : Chip select
        .EEPROM_SK()    ,    // out    : Serial data clock
        .EEPROM_DI()    ,    // out    : Serial write data
        .EEPROM_DO(1'd0)    ,    // in     : Serial read data
        // User data, initial values are stored in the EEPROM, 0xFFFF_FC3C-3F
        .USR_REG_X3C()               ,    // out    : Stored at 0xFFFF_FF3C
        .USR_REG_X3D()               ,    // out    : Stored at 0xFFFF_FF3D
        .USR_REG_X3E()               ,    // out    : Stored at 0xFFFF_FF3E
        .USR_REG_X3F()               ,    // out    : Stored at 0xFFFF_FF3F
        // MII interface
        .GMII_RSTn(phy_rst_n)        ,    // out    : PHY reset
        .GMII_1000M(1'b1)            ,    // in     : GMII mode (0:MII, 1:GMII)
        // TX 
        .GMII_TX_CLK(CLK_PHY125TX)       ,    // in     : Tx clock
        .GMII_TX_EN(gmii_tx_en)      ,    // out    : Tx enable
        .GMII_TXD(gmii_txd)          ,    // out    : Tx data[7:0]
        .GMII_TX_ER(gmii_tx_er)      ,    // out    : TX error
        // RX
        .GMII_RX_CLK(CLK_PHY125TX)       ,    // in     : Rx clock
        .GMII_RX_DV(gmii_rx_dv)      ,    // in     : Rx data valid
        .GMII_RXD(gmii_rxd)          ,    // in     : Rx data[7:0]
        .GMII_RX_ER(gmii_rx_er)      ,    // in     : Rx error
        .GMII_CRS(gmii_crs)          ,    // in     : Carrier sense
        .GMII_COL(gmii_col)          ,    // in     : Collision detected
        // Management IF
        .GMII_MDC(mdio_phy_mdc)      ,    // out    : Clock for MDIO
        .GMII_MDIO_IN(mdio_gem_i)    ,    // in     : Data
        .GMII_MDIO_OUT(mdio_gem_o)   ,    // out    : Data
        .GMII_MDIO_OE(mdio_gem_t)    ,    // out    : MDIO output enable
        // User I/F
        .SiTCP_RST(SiTCP_RST)        ,    // out    : Reset for SiTCP and related circuits
        // TCP connection control
        .TCP_OPEN_REQ(1'b0)          ,    // in     : Reserved input, shoud be 0
        .TCP_OPEN_ACK()  ,    // out    : Acknowledge for open (=Socket busy)
        .TCP_ERROR()        ,    // out    : TCP error, its active period is equal to MSL
        .TCP_CLOSE_REQ(TCP_CLOSE_REQ),    // out    : Connection close request
        .TCP_CLOSE_ACK(TCP_CLOSE_REQ),    // in     : Acknowledge for closing
        // FIFO I/F
        .TCP_RX_WC(1'b1)             ,    // in     : Rx FIFO write count[15:0] (Unused bits should be set 1)
        .TCP_RX_WR()        ,    // out    : Write enable
        .TCP_RX_DATA()    ,    // out    : Write data[7:0]
        .TCP_TX_FULL(TCP_TX_FULL)    ,    // out    : Almost full flag
        .TCP_TX_WR(TCP_TX_WR)        ,    // in     : Write enable
        .TCP_TX_DATA(TCP_TX_DATA)    ,    // in     : Write data[7:0]
        // RBCP
        .RBCP_ACT(RBCP_ACT)          ,    // out    : RBCP active
        .RBCP_ADDR(RBCP_ADDR)        ,    // out    : Address[31:0]
        .RBCP_WD(RBCP_WD)            ,    // out    : Data[7:0]
        .RBCP_WE(RBCP_WE)            ,    // out    : Write enable
        .RBCP_RE(RBCP_RE)            ,    // out    : Read enable
        .RBCP_ACK(RBCP_ACK)          ,    // in     : Access acknowledge
        .RBCP_RD(RBCP_RD)                 // in     : Read data[7:0]
    );

    IOBUF iobuf_mdio(
        .O(mdio_gem_i),
        .IO(mdio_phy_mdio),
        .I(mdio_gem_o),
        .T(mdio_gem_t)
    );

    rbcp_to_bus rbcp_to_bus(
        .BUS_RST(BUS_RST),
        .BUS_CLK(BUS_CLK),

        .RBCP_ACT(RBCP_ACT),
        .RBCP_ADDR(RBCP_ADDR),
        .RBCP_WD(RBCP_WD),
        .RBCP_WE(RBCP_WE),
        .RBCP_RE(RBCP_RE),
        .RBCP_ACK(RBCP_ACK),
        .RBCP_RD(RBCP_RD),

        .BUS_WR(BUS_WR),
        .BUS_RD(BUS_RD),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA_IN    (BUS_DATA_IN),
        .BUS_DATA_OUT   (BUS_DATA_OUT)
    ); 

    wire TPX3_1_ClkInRefPLL_reg, TPX3_1_ClkIn40_reg;
    
    ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC")) ODDR_inst_TPX3_1_ClkIn40 (.Q(TPX3_1_ClkIn40_P), .C(CLK40_90), .CE(1'b1), .D1(1'b1), .D2(1'b0), .R(1'b0), .S(1'b0));          //ENABLE?
    ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC")) ODDR_inst_TPX3_1_ClkIn40_N (.Q(TPX3_1_ClkIn40_N), .C(CLK40_90), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));          //ENABLE?
    
    wire TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn, TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing;
    wire [6:0] to_out_buf, to_out_buf_n, to_out_buf_p;
    
    assign to_out_buf    = {!TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, !TPX3_1_DataIn, !TPX3_1_Shutter, !TPX3_1_Reset, TPX3_1_ENPowerPulsing};
    assign {TPX3_1_ExtTPulse_N, TPX3_1_T0_Sync_N, TPX3_1_EnableIn_P, TPX3_1_DataIn_N, TPX3_1_Shutter_N, TPX3_1_Reset_P, TPX3_1_ENPowerPulsing_N} = to_out_buf_n;
    assign {TPX3_1_ExtTPulse_P, TPX3_1_T0_Sync_P, TPX3_1_EnableIn_N, TPX3_1_DataIn_P, TPX3_1_Shutter_P, TPX3_1_Reset_N, TPX3_1_ENPowerPulsing_P} = to_out_buf_p;
    genvar h;
    
    generate
    for (h = 0; h < 7; h = h + 1) begin: out_buf_gen
        wire ddr_buf_out;
        
        ODDR #(.DDR_CLK_EDGE("SAME_EDGE"), .INIT(1'b0), .SRTYPE("SYNC")) ODDR_inst_p (.Q(to_out_buf_p[h]), .C(CLK40), .CE(1'b1), .D1(to_out_buf[h]), .D2(to_out_buf[h]), .R(1'b0), .S(1'b0));
        ODDR #(.DDR_CLK_EDGE("SAME_EDGE"), .INIT(1'b0), .SRTYPE("SYNC")) ODDR_inst_n (.Q(to_out_buf_n[h]), .C(CLK40), .CE(1'b1), .D1(~to_out_buf[h]), .D2(~to_out_buf[h]), .R(1'b0), .S(1'b0));
        end
    endgenerate
    
    wire [7:0] RX_DATA;
    genvar k;
    generate
        for (k = 0; k < 8; k = k + 1) begin: in_buf_gen
            IBUFDS #(.IOSTANDARD("LVDS_25"), .DIFF_TERM("TRUE")) IBUFDS_inst_rx (.O(RX_DATA[k]), .I(TPX3_1_DataOut_P[k]), .IB(TPX3_1_DataOut_N[k]));
        end
    endgenerate
    
    IDELAYCTRL IDELAYCTRL_inst (
        .RDY   (), // 1-bit Ready output
        .REFCLK(CLK200), // 1-bit Reference clock input
        .RST   (~mmcm_locked)  // 1-bit Reset input
    );


    // ---

    wire [7:0] RX_READY;

    tpx3_core #(.RX_CH_NO(1)) tpx3_core( 
    .BUS_CLK        (BUS_CLK),
    .BUS_RST        (BUS_RST),
    .BUS_ADD        (BUS_ADD),
    .BUS_DATA_IN    (BUS_DATA_IN),
    .BUS_DATA_OUT   (BUS_DATA_OUT),
    .BUS_RD         (BUS_RD),
    .BUS_WR         (BUS_WR),

    .ARB_READY_OUT(ARB_READY_OUT),
    .ARB_WRITE_OUT(ARB_WRITE_OUT),
    .ARB_DATA_OUT(ARB_DATA_OUT),

    .CLK40          (CLK40),
    .CLK320         (CLK320),
    .CLK32          (CLK32),
    
    .RX_DATA        (RX_DATA),
    .ExtTPulse      (TPX3_1_ExtTPulse),
    .T0_Sync        (TPX3_1_T0_Sync),
    .EnableIn       (TPX3_1_EnableIn),
    .DataIn         (TPX3_1_DataIn),
    .Shutter        (TPX3_1_Shutter),
    .Reset          (TPX3_1_Reset),
    .ENPowerPulsing (TPX3_1_ENPowerPulsing),
    .Data_MUX_select(),
    
    .LED            (),
    .RX_READY       (RX_READY)
    
    );
    
    wire ARB_READY_OUT,ARB_WRITE_OUT;
    wire [31:0] ARB_DATA_OUT;

    wire fifo_empty, fifo_full;
    fifo_32_to_8 #(
        .DEPTH(1*1024)
    ) data_fifo (
        .RST(BUS_RST),
        .CLK(BUS_CLK),

        .WRITE(ARB_WRITE_OUT),
        .READ(TCP_TX_WR),
        .DATA_IN(ARB_DATA_OUT),
        .FULL(fifo_full),
        .EMPTY(fifo_empty),
        .DATA_OUT(TCP_TX_DATA)
    );

    assign TCP_TX_WR = !TCP_TX_FULL && !fifo_empty;
    assign ARB_READY_OUT = !fifo_full;



    //wire CLK40_OUT;
    //ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC")) ODDR_inst_CLK40_OUT (.Q(CLK40_OUT), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));
    
    assign LED = RX_READY;

endmodule
