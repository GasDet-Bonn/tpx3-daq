

`timescale 1ns / 1ps

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

`include "sync_reset.v"

`include "coregen/gig_eth_pcs_pma_v11_5/example_design/sgmii_adapt/gig_eth_pcs_pma_v11_5_clk_gen.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/sgmii_adapt/gig_eth_pcs_pma_v11_5_johnson_cntr.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/sgmii_adapt/gig_eth_pcs_pma_v11_5_rx_rate_adapt.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/sgmii_adapt/gig_eth_pcs_pma_v11_5_sgmii_adapt.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/sgmii_adapt/gig_eth_pcs_pma_v11_5_tx_rate_adapt.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/transceiver/gig_eth_pcs_pma_v11_5_double_reset.v"
//`include "coregen/gig_eth_pcs_pma_v11_5/example_design/transceiver/gig_eth_pcs_pma_v11_5_gtwizard_gtrxreset_seq.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/transceiver/gig_eth_pcs_pma_v11_5_rx_elastic_buffer.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/transceiver/gig_eth_pcs_pma_v11_5_v6_gtxwizard.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/transceiver/gig_eth_pcs_pma_v11_5_v6_gtxwizard_gtx.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/transceiver/gig_eth_pcs_pma_v11_5_v6_gtxwizard_top.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/gig_eth_pcs_pma_v11_5_block.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/gig_eth_pcs_pma_v11_5_reset_sync.v"
`include "coregen/gig_eth_pcs_pma_v11_5/example_design/gig_eth_pcs_pma_v11_5_sync_block.v"
//`include "coregen/gig_eth_pcs_pma_v11_5.v"

`include "../lib/SiTCP_Netlist_for_Virtex6/TIMER.v"
`include "../lib/SiTCP_Netlist_for_Virtex6/SiTCP_XC6V_32K_BBT_V110.V"
`include "../lib/SiTCP_Netlist_for_Virtex6/WRAP_SiTCP_GMII_XC6V_32K.V"

`include "../lib/extra/rbcp_to_sbus.v"

`include "utils/fifo_32_to_8.v"

module tpx3_sfp (

        input  wire       CLK200_P,
        input  wire       CLK200_N,

        input  wire       SFP_RX_P,
        input  wire       SFP_RX_N,
        output wire       SFP_TX_P,
        output wire       SFP_TX_N,
        input  wire       SFP_CLK_P,
        input  wire       SFP_CLK_N,

        output wire       PHY_RESET_N,

        //input wire TPX3_1_PLLOut_N,
        //input wire TPX3_1_PLLOut_P,
        //input wire TPX3_1_ClkOut_N,
        //input wire TPX3_1_ClkOut_P,

        output wire       TPX3_1_ClkInRefPLL_N,
        output wire       TPX3_1_ClkInRefPLL_P,
        output wire       TPX3_1_ClkIn40_N,
        output wire       TPX3_1_ClkIn40_P,
        output wire       TPX3_1_Reset_N,
        output wire       TPX3_1_Reset_P,

        output wire       TPX3_1_ExtTPulse_N,
        output wire       TPX3_1_ExtTPulse_P,
        output wire       TPX3_1_T0_Sync_N,
        output wire       TPX3_1_T0_Sync_P,
        output wire       TPX3_1_EnableIn_N,
        output wire       TPX3_1_EnableIn_P,
        output wire       TPX3_1_DataIn_N,
        output wire       TPX3_1_DataIn_P,
        output wire       TPX3_1_Shutter_N,
        output wire       TPX3_1_Shutter_P,
        output wire       TPX3_1_ENPowerPulsing_N,
        output wire       TPX3_1_ENPowerPulsing_P,

        input wire [7:0] TPX3_1_DataOut_N, TPX3_1_DataOut_P,

        output wire       ETH_STATUS_OK,
        output wire [7:0] RX_READY,

        output wire Data_MUX_select
    
    );


    // Clock and reset
    wire CLK200_SYS;

    // Internal 125 MHz clock
    wire CLK125;
    wire rst_125mhz;

    wire mmcm_rst = 1'b0;                                                                                                                                                                              //RST;//reset;
    wire mmcm_locked;
    wire mmcm_clkfb;

    IBUFGDS clk_ibufgds_inst(
        .I (CLK200_P  ),
        .IB(CLK200_N  ),
        .O (CLK200_SYS)
    );

    wire CLK40_MMCM;
    wire CLK320_MMCM;
    wire CLK32_MMCM;
    wire CLKBUS_MMCM;

    // MMCM instance
    // 200 MHz in, 125 MHz out
    // PFD range: 10 MHz to 450 MHz
    // VCO range: 600 MHz to 1200 MHz
    // M = 5, D = 1 sets Fvco = 1000 MHz (in range)
    // Divide by 8 to get output frequency of 125 MHz
    MMCM_BASE #(
        .BANDWIDTH         ("OPTIMIZED"),
        .CLKOUT0_DIVIDE_F  (3          ),
        .CLKOUT0_DUTY_CYCLE(0.5        ),
        .CLKOUT0_PHASE     (0          ),
        .CLKOUT1_DIVIDE    (24         ),
        .CLKOUT1_DUTY_CYCLE(0.5        ),
        .CLKOUT1_PHASE     (0          ),
        .CLKOUT2_DIVIDE    (30         ),
        .CLKOUT2_DUTY_CYCLE(0.5        ),
        .CLKOUT2_PHASE     (0          ),
        .CLKOUT3_DIVIDE    (7          ),
        .CLKOUT3_DUTY_CYCLE(0.5        ),
        .CLKOUT3_PHASE     (0          ),
        .CLKOUT4_DIVIDE    (1          ),
        .CLKOUT4_DUTY_CYCLE(0.5        ),
        .CLKOUT4_PHASE     (0          ),
        .CLKOUT5_DIVIDE    (1          ),
        .CLKOUT5_DUTY_CYCLE(0.5        ),
        .CLKOUT5_PHASE     (0          ),
        .CLKOUT6_DIVIDE    (1          ),
        .CLKOUT6_DUTY_CYCLE(0.5        ),
        .CLKOUT6_PHASE     (0          ),
        .CLKFBOUT_MULT_F   (24         ),
        .CLKFBOUT_PHASE    (0          ),
        .DIVCLK_DIVIDE     (5          ),
        .REF_JITTER1       (0.100      ),
        .CLKIN1_PERIOD     (5.0        ),
        .STARTUP_WAIT      ("FALSE"    ),
        .CLKOUT4_CASCADE   ("FALSE"    )
    )
    clk_mmcm_inst (
        .CLKIN1   ( CLK200_SYS ),
        .CLKFBIN  ( mmcm_clkfb ),
        .RST      ( mmcm_rst   ),
        .PWRDWN   ( 1'b0       ),
        .CLKOUT0  ( CLK320_MMCM),
        .CLKOUT0B (            ),
        .CLKOUT1  ( CLK40_MMCM ),
        .CLKOUT1B (            ),
        .CLKOUT2  ( CLK32_MMCM ),
        .CLKOUT2B (            ),
        .CLKOUT3  ( CLKBUS_MMCM),
        .CLKOUT3B (            ),
        .CLKOUT4  (            ),
        .CLKOUT5  (            ),
        .CLKOUT6  (            ),
        .CLKFBOUT ( mmcm_clkfb ),
        .CLKFBOUTB(            ),
        .LOCKED   ( mmcm_locked)
    );

    wire CLK40, CLK320, CLK32;
    BUFG clk_40mhz_bufg_inst (
        .I(CLK40_MMCM),
        .O(CLK40     )
    );

    BUFG clk_320mhz_bufg_inst (
        .I(CLK320_MMCM),
        .O(CLK320     )
    );

    BUFG clk_64mhz_bufg_inst (
        .I(CLK32_MMCM),
        .O(CLK32     )
    );

    wire BUS_CLK;
    BUFG clk_bus_bufg_inst (
        .I(CLKBUS_MMCM),
        .O(BUS_CLK)
    );

    sync_reset #(.N(4)) sync_reset_125mhz_inst (
        .clk           (CLK125        ),
        .rst           (~mmcm_locked  ),
        .sync_reset_out(rst_125mhz)
    );

    // SGMII interface to PHY
    wire gmii_rst;
    wire gmii_clk_en;
    wire [7:0] gmii_txd;
    wire gmii_tx_en;
    wire gmii_tx_er;
    wire [7:0] gmii_rxd;
    wire gmii_rx_dv;
    wire gmii_rx_er;

    wire CLK125_MGT;
    wire CLK125_PHY;

    IBUFDS_GTXE1 phy_sgmii_ibufds_mgtrefclk (
        .CEB   ( 1'b0      ),
        .I     ( SFP_CLK_P ),
        .IB    ( SFP_CLK_N ),
        .O     ( CLK125_MGT),
        .ODIV2 (           )
    );

    BUFG phy_sgmii_bufg_userclk2 (
        .I (CLK125_PHY),
        .O (CLK125    )
    );

    sync_reset #(.N(4)) sync_reset_pcspma_inst (
        .clk           (CLK125          ),
        .rst           (rst_125mhz  ),
        .sync_reset_out(gmii_rst)
    );

    wire [15:0] pcspma_status_vector;

    //wire pcspma_status_link_status = pcspma_status_vector[0];
    //wire pcspma_status_link_synchronization = pcspma_status_vector[1];
    //wire pcspma_status_rudi_c = pcspma_status_vector[2];
    //wire pcspma_status_rudi_i = pcspma_status_vector[3];
    //wire pcspma_status_rudi_invalid = pcspma_status_vector[4];
    //wire pcspma_status_rxdisperr = pcspma_status_vector[5];
    //wire pcspma_status_rxnotintable = pcspma_status_vector[6];
    //wire pcspma_status_phy_link_status = pcspma_status_vector[7];
    //wire [1:0] pcspma_status_remote_fault_encdg = pcspma_status_vector[9:8];
    //wire [1:0] pcspma_status_speed = pcspma_status_vector[11:10];
    //wire pcspma_status_duplex = pcspma_status_vector[12];
    //wire pcspma_status_remote_fault = pcspma_status_vector[13];
    //wire [1:0] pcspma_status_pause = pcspma_status_vector[15:14];

    wire [4:0] pcspma_config_vector;

    assign pcspma_config_vector[4] = 1'b1; // autonegotiation enable
    assign pcspma_config_vector[3] = 1'b0; // isolate
    assign pcspma_config_vector[2] = 1'b0; // power down
    assign pcspma_config_vector[1] = 1'b0; // loopback enable
    assign pcspma_config_vector[0] = 1'b0; // unidirectional enable

    wire [15:0] pcspma_an_config_vector;

    //assign pcspma_an_config_vector[15] = 1'b1;                                                                                                                                                         // SGMII link status
    //assign pcspma_an_config_vector[14] = 1'b1;                                                                                                                                                         // SGMII Acknowledge
    //assign pcspma_an_config_vector[13:12] = 2'b01;                                                                                                                                                     // full duplex
    //assign pcspma_an_config_vector[11:10] = 2'b10;                                                                                                                                                     // SGMII speed
    //assign pcspma_an_config_vector[9] = 1'b0;                                                                                                                                                          // reserved
    //assign pcspma_an_config_vector[8:7] = 2'b00;                                                                                                                                                       // pause frames - SGMII reserved
    //assign pcspma_an_config_vector[6] = 1'b0;                                                                                                                                                          // reserved
    //assign pcspma_an_config_vector[5] = 1'b0;                                                                                                                                                          // full duplex - SGMII reserved
    //assign pcspma_an_config_vector[4:1] = 4'b0000;                                                                                                                                                     // reserved
    //assign pcspma_an_config_vector[0] = 1'b1;                                                                                                                                                          // SGMII
    assign  pcspma_an_config_vector = 16'b0000000000100001;

    reg phy_rst;
    reg basex_or_sgmii;
    initial basex_or_sgmii = 1;

    gig_eth_pcs_pma_v11_5_block
    eth_pcspma (
        // Transceiver Interface
        .mgtrefclk            ( CLK125_MGT              ),
        .gtx_reset_clk        ( CLK125                  ),
        .txp                  ( SFP_TX_P                ),
        .txn                  ( SFP_TX_N                ),
        .rxp                  ( SFP_RX_P                ),
        .rxn                  ( SFP_RX_N                ),
        .txoutclk             ( CLK125_PHY              ),
        .userclk2             ( CLK125                  ),
        .pma_reset            ( rst_125mhz| phy_rst ),
        // GMII Interface
        //.sgmii_clk_r           (),
        //.sgmii_clk_f           (),
        //.sgmii_clk_en          (gmii_clk_en),
        .gmii_txd             ( gmii_txd        ),
        .gmii_tx_en           ( gmii_tx_en      ),
        .gmii_tx_er           ( gmii_tx_er      ),
        .gmii_rxd             ( gmii_rxd        ),
        .gmii_rx_dv           ( gmii_rx_dv      ),
        .gmii_rx_er           ( gmii_rx_er      ),
        .gmii_isolate         (                         ),
        // Management: Alternative to MDIO Interface
        .configuration_vector ( pcspma_config_vector    ),

        .an_interrupt         (                         ),
        .an_adv_config_vector ( pcspma_an_config_vector ),
        .an_restart_config    ( 1'b0                    ),
        //.link_timer_value      (9'd50),

        .link_timer_basex     ( 9'b100111101            ),
        .link_timer_sgmii     ( 9'b000110010            ),
        .basex_or_sgmii       ( basex_or_sgmii          ), //1000BASE-X (0) or SGMII (1)

        // Speed Control
        .speed_is_10_100      ( 1'b0                    ), //(pcspma_status_speed != 2'b10),
        .speed_is_100         ( 1'b0                    ), //(pcspma_status_speed == 2'b01),
        // General IO's
        .status_vector        ( pcspma_status_vector    ),
        .reset                ( rst_125mhz | phy_rst),
        .signal_detect        ( 1'b1                    )
    );


    //TRY TO RESET AND CHANGE THE MODE
    assign ETH_STATUS_OK = pcspma_status_vector[0];

    reg [48:0] cnt;
    localparam CNT_PHY_RST = 8000*4096;
    initial cnt = 100;

    always@(posedge CLK125)
        if(cnt == CNT_PHY_RST)
            cnt <= 0;
        else if (!ETH_STATUS_OK)
            cnt <= cnt +1;

    always@(posedge CLK125)
        phy_rst <= (cnt < 16);

    always@(posedge CLK125)
        if(cnt == 0)
            basex_or_sgmii <= !basex_or_sgmii;


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

    WRAP_SiTCP_GMII_XC6V_32K sitcp(
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
        .GMII_RSTn(PHY_RESET_N)        ,    // out    : PHY reset !!!!!!!!!!!!!!!!!!!!!!!!!
        .GMII_1000M(1'b1)            ,    // in     : GMII mode (0:MII, 1:GMII)
        // TX 
        .GMII_TX_CLK(CLK125)       ,    // in     : Tx clock
        .GMII_TX_EN(gmii_tx_en)      ,    // out    : Tx enable
        .GMII_TXD(gmii_txd)          ,    // out    : Tx data[7:0]
        .GMII_TX_ER(gmii_tx_er)      ,    // out    : TX error
        // RX
        .GMII_RX_CLK(CLK125)       ,    // in     : Rx clock
        .GMII_RX_DV(gmii_rx_dv)      ,    // in     : Rx data valid
        .GMII_RXD(gmii_rxd)          ,    // in     : Rx data[7:0]
        .GMII_RX_ER(gmii_rx_er)      ,    // in     : Rx error
        .GMII_CRS(1'b0)          ,    // in     : Carrier sense
        .GMII_COL(1'b0)          ,    // in     : Collision detected
        // Management IF
        .GMII_MDC()      ,    // out    : Clock for MDIO
        .GMII_MDIO_IN(1'b0)    ,    // in     : Data
        .GMII_MDIO_OUT()   ,    // out    : Data
        .GMII_MDIO_OE()    ,    // out    : MDIO output enable
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

    // IOBUF iobuf_mdio(
    //     .O(mdio_gem_i),
    //     .IO(mdio_phy_mdio),
    //     .I(mdio_gem_o),
    //     .T(mdio_gem_t)
    // );

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
	 
    `ifdef ML605 
        ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkInRefPLL ( .Q(TPX3_1_ClkInRefPLL_reg), .C(CLK320), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));
    `elsif FECv6
        ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkInRefPLL ( .Q(TPX3_1_ClkInRefPLL_reg), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));
    `endif

    OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_inst_TPX3_1_ClkInRefPLL ( .O(TPX3_1_ClkInRefPLL_P), .OB(TPX3_1_ClkInRefPLL_N), .I(TPX3_1_ClkInRefPLL_reg) );
	
    `ifdef ML605
        ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkIn40 ( .Q(TPX3_1_ClkIn40_reg), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));
    `elsif FECv6
        ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkIn40 ( .Q(TPX3_1_ClkIn40_reg), .C(CLK40), .CE(1'b1), .D1(1'b1), .D2(1'b0), .R(1'b0), .S(1'b0));
    `endif

    OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_inst_TPX3_1_ClkIn40 ( .O(TPX3_1_ClkIn40_P), .OB(TPX3_1_ClkIn40_N), .I(TPX3_1_ClkIn40_reg) );


    wire TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn, TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing;
    wire [6:0] to_out_buf, to_out_buf_n, to_out_buf_p;

    `ifdef ML605
        assign to_out_buf = {TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn, TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing};
    `elsif FECv6
        assign to_out_buf = {!TPX3_1_ExtTPulse, TPX3_1_T0_Sync, !TPX3_1_EnableIn, !TPX3_1_DataIn, !TPX3_1_Shutter, !TPX3_1_Reset, TPX3_1_ENPowerPulsing};
    `endif
    
	assign {TPX3_1_ExtTPulse_N, TPX3_1_T0_Sync_N, TPX3_1_EnableIn_N, TPX3_1_DataIn_N, TPX3_1_Shutter_N, TPX3_1_Reset_N, TPX3_1_ENPowerPulsing_N} = to_out_buf_n;
    assign {TPX3_1_ExtTPulse_P, TPX3_1_T0_Sync_P, TPX3_1_EnableIn_P, TPX3_1_DataIn_P, TPX3_1_Shutter_P, TPX3_1_Reset_P, TPX3_1_ENPowerPulsing_P} = to_out_buf_p;
    genvar h;
    generate
        for (h = 0; h < 7; h = h + 1) begin: out_buf_gen
            wire ddr_buf_out;
            ODDR #(.DDR_CLK_EDGE("SAME_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst ( .Q(ddr_buf_out), .C(CLK40), .CE(1'b1), .D1(to_out_buf[h]), .D2(to_out_buf[h]), .R(1'b0), .S(1'b0));
            OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_inst( .O(to_out_buf_p[h]), .OB(to_out_buf_n[h]), .I(ddr_buf_out) );
        end
    endgenerate

    wire [7:0] RX_DATA;
    genvar k;
    generate
        for (k = 0; k < 8; k = k + 1) begin: in_buf_gen
            IBUFDS #(.IOSTANDARD("DEFAULT")) IBUFDS_inst_rx ( .O(RX_DATA[k]), .I(TPX3_1_DataOut_P[k]), .IB(TPX3_1_DataOut_N[k]) );
        end
    endgenerate

    IDELAYCTRL IDELAYCTRL_inst (
        .RDY   (             ), // 1-bit Ready output
        .REFCLK( CLK200_SYS  ), // 1-bit Reference clock input
        .RST   ( ~mmcm_locked)  // 1-bit Reset input
    );

    tpx3_core tpx3_core_inst (
        .BUS_CLK        (BUS_CLK              ),
        .BUS_RST        (BUS_RST              ),
        .BUS_ADD        (BUS_ADD              ),
        .BUS_DATA_IN    (BUS_DATA_IN          ),
        .BUS_DATA_OUT   (BUS_DATA_OUT         ),
        .BUS_RD         (BUS_RD               ),
        .BUS_WR         (BUS_WR               ),

        .ARB_READY_OUT(ARB_READY_OUT),
        .ARB_WRITE_OUT(ARB_WRITE_OUT),
        .ARB_DATA_OUT(ARB_DATA_OUT),

        .CLK40          (CLK40                ),
        .CLK320         (CLK320               ),
        .CLK32          (CLK32                ),

        .RX_DATA        (RX_DATA              ),
        .ExtTPulse      (TPX3_1_ExtTPulse     ),
        .T0_Sync        (TPX3_1_T0_Sync       ),
        .EnableIn       (TPX3_1_EnableIn      ),
        .DataIn         (TPX3_1_DataIn        ),
        .Shutter        (TPX3_1_Shutter       ),
        .Reset          (TPX3_1_Reset         ),
        .ENPowerPulsing (TPX3_1_ENPowerPulsing),
        .Data_MUX_select(Data_MUX_select      ),

        .LED            (                     ),
        .RX_READY       (RX_READY             )

    );


    wire ARB_READY_OUT,ARB_WRITE_OUT;
    wire [31:0] ARB_DATA_OUT;

    wire fifo_empty, fifo_full;
    fifo_32_to_8 #(
        .DEPTH(2*1024)
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

    wire CLK40_OUT;
    ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_CLK40_OUT ( .Q(CLK40_OUT), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));

endmodule
