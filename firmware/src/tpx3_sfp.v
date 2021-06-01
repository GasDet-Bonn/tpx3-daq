

`timescale 1ns / 1ps

`include "tpx3_core.v"

`include "../lib/si_udp/si_udp.v"
`include "../lib/si_udp/verilog-ethernet/rtl/eth_mac_1g_fifo.v"
`include "../lib/si_udp/verilog-ethernet/rtl/eth_mac_1g.v"
`include "../lib/si_udp/verilog-ethernet/rtl/axis_gmii_rx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/axis_gmii_tx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/lfsr.v"
`include "../lib/si_udp/verilog-ethernet/rtl/eth_axis_rx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/eth_axis_tx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/udp_complete.v"
`include "../lib/si_udp/verilog-ethernet/rtl/udp_checksum_gen.v"
`include "../lib/si_udp/verilog-ethernet/rtl/udp.v"
`include "../lib/si_udp/verilog-ethernet/rtl/udp_ip_rx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/udp_ip_tx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/ip_complete.v"
`include "../lib/si_udp/verilog-ethernet/rtl/ip.v"
`include "../lib/si_udp/verilog-ethernet/rtl/ip_eth_rx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/ip_eth_tx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/ip_arb_mux_2.v"
`include "../lib/si_udp/verilog-ethernet/rtl/ip_mux_2.v"
`include "../lib/si_udp/verilog-ethernet/rtl/arp.v"
`include "../lib/si_udp/verilog-ethernet/rtl/arp_cache.v"
`include "../lib/si_udp/verilog-ethernet/rtl/arp_eth_rx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/arp_eth_tx.v"
`include "../lib/si_udp/verilog-ethernet/rtl/eth_arb_mux_2.v"
`include "../lib/si_udp/verilog-ethernet/rtl/eth_mux_2.v"
`include "../lib/si_udp/verilog-ethernet/lib/axis/rtl/arbiter.v"
`include "../lib/si_udp/verilog-ethernet/lib/axis/rtl/priority_encoder.v"
`include "../lib/si_udp/verilog-ethernet/lib/axis/rtl/axis_fifo.v"
`include "../lib/si_udp/verilog-ethernet/lib/axis/rtl/axis_async_frame_fifo.v"

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
		  `ifdef host
		      output wire       TPX3_1_T0_Sync_Ext1,
            output wire       TPX3_1_T0_Sync_Ext2,
            output wire       TPX3_1_Reset_Ext1,
            output wire       TPX3_1_Reset_Ext2,
	     `elsif client
		      input wire       TPX3_1_T0_Sync_Ext1,
            input wire       TPX3_1_Reset_Ext1,
	     `endif
        input wire [7:0] TPX3_1_DataOut_N, TPX3_1_DataOut_P,

        output wire       ETH_STATUS_OK,
        output wire       RX_READY,

        output wire Data_MUX_select,
		  
		  //TLU
		  input wire TLU_RJ45_TRIGGER_P,
		  input wire TLU_RJ45_TRIGGER_N,
		  input wire TLU_RJ45_RESET_P,
		  input wire TLU_RJ45_RESET_N,
		  output wire TLU_RJ45_BUSY_P,
		  output wire TLU_RJ45_BUSY_N,
		  output wire TLU_RJ45_CLK_P,
		  output wire TLU_RJ45_CLK_N
    );


    // Clock and reset
    wire CLK200_SYS;

    // Internal 125 MHz clock
    wire CLK125;
    wire rst_125mhz_int;

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
        .CLKOUT3_DIVIDE    (1          ),
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
        .CLKOUT3  (            ),
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

    sync_reset #(.N(4)) sync_reset_125mhz_inst (
        .clk           (CLK125        ),
        .rst           (~mmcm_locked  ),
        .sync_reset_out(rst_125mhz_int)
    );

    // SGMII interface to PHY
    wire phy_gmii_rst_int;
    wire phy_gmii_clk_en_int;
    wire [7:0] phy_gmii_txd_int;
    wire phy_gmii_tx_en_int;
    wire phy_gmii_tx_er_int;
    wire [7:0] phy_gmii_rxd_int;
    wire phy_gmii_rx_dv_int;
    wire phy_gmii_rx_er_int;

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
        .rst           (rst_125mhz_int  ),
        .sync_reset_out(phy_gmii_rst_int)
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
        .pma_reset            ( rst_125mhz_int| phy_rst ),
        // GMII Interface
        //.sgmii_clk_r           (),
        //.sgmii_clk_f           (),
        //.sgmii_clk_en          (phy_gmii_clk_en_int),
        .gmii_txd             ( phy_gmii_txd_int        ),
        .gmii_tx_en           ( phy_gmii_tx_en_int      ),
        .gmii_tx_er           ( phy_gmii_tx_er_int      ),
        .gmii_rxd             ( phy_gmii_rxd_int        ),
        .gmii_rx_dv           ( phy_gmii_rx_dv_int      ),
        .gmii_rx_er           ( phy_gmii_rx_er_int      ),
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
        .reset                ( rst_125mhz_int | phy_rst),
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


    wire [31:0] BUS_ADD, BUS_DATA;
    wire BUS_RD, BUS_WR, BUS_CLK, BUS_RST, BUS_BYTE_ACCESS;

    si_udp si_udp_inst (

        .clk_125mhz     (CLK125            ),
        .rst_125mhz     (rst_125mhz_int    ),

        .phy_gmii_clk   (CLK125            ),
        .phy_gmii_rst   (phy_gmii_rst_int  ),
        .phy_gmii_clk_en(1'b1              ),

        .phy_gmii_rxd   (phy_gmii_rxd_int  ),
        .phy_gmii_rx_dv (phy_gmii_rx_dv_int),
        .phy_gmii_rx_er (phy_gmii_rx_er_int),
        .phy_gmii_txd   (phy_gmii_txd_int  ),
        .phy_gmii_tx_en (phy_gmii_tx_en_int),
        .phy_gmii_tx_er (phy_gmii_tx_er_int),
        .phy_reset_n    (PHY_RESET_N       ),

        .BUS_CLK        (BUS_CLK           ),
        .BUS_RST        (BUS_RST           ),
        .BUS_ADD        (BUS_ADD           ),
        .BUS_DATA       (BUS_DATA          ),
        .BUS_RD         (BUS_RD            ),
        .BUS_WR         (BUS_WR            ),
        .BUS_BYTE_ACCESS(BUS_BYTE_ACCESS   )
    );

    wire TPX3_1_ClkInRefPLL_reg, TPX3_1_ClkIn40_reg;
	 
    `ifdef ML605 
        ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkInRefPLL ( .Q(TPX3_1_ClkInRefPLL_reg), .C(CLK320), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));
    `elsif FECv6
        ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkInRefPLL ( .Q(TPX3_1_ClkInRefPLL_reg), .C(CLK40), .CE(1'b1), .D1(1'b1), .D2(1'b0), .R(1'b0), .S(1'b0));
    `endif

    OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_inst_TPX3_1_ClkInRefPLL ( .O(TPX3_1_ClkInRefPLL_P), .OB(TPX3_1_ClkInRefPLL_N), .I(TPX3_1_ClkInRefPLL_reg) );
	
    `ifdef ML605
        ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkIn40 ( .Q(TPX3_1_ClkIn40_reg), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));
    `elsif FECv6
        ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkIn40 ( .Q(TPX3_1_ClkIn40_reg), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));
    `endif

    OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_inst_TPX3_1_ClkIn40 ( .O(TPX3_1_ClkIn40_P), .OB(TPX3_1_ClkIn40_N), .I(TPX3_1_ClkIn40_reg) );


    wire TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn, TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing;
    wire [6:0] to_out_buf, to_out_buf_n, to_out_buf_p;

    `ifdef ML605
        assign to_out_buf = {TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn, TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing};
	 `elsif FECv6
	     `ifdef host
            assign to_out_buf = {!TPX3_1_ExtTPulse, !TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn, TPX3_1_Shutter, !TPX3_1_Reset, !TPX3_1_ENPowerPulsing};
		  `elsif client
	         assign to_out_buf = {!TPX3_1_ExtTPulse, !TPX3_1_T0_Sync_Ext1, TPX3_1_EnableIn, TPX3_1_DataIn, TPX3_1_Shutter, !TPX3_1_Reset_Ext1, !TPX3_1_ENPowerPulsing};
		  `endif
    `endif
    
	assign {TPX3_1_ExtTPulse_N, TPX3_1_T0_Sync_N, TPX3_1_EnableIn_N, TPX3_1_DataIn_N, TPX3_1_Shutter_N, TPX3_1_Reset_N, TPX3_1_ENPowerPulsing_N} = to_out_buf_n;
    assign {TPX3_1_ExtTPulse_P, TPX3_1_T0_Sync_P, TPX3_1_EnableIn_P, TPX3_1_DataIn_P, TPX3_1_Shutter_P, TPX3_1_Reset_P, TPX3_1_ENPowerPulsing_P} = to_out_buf_p;
	 `ifdef host
	     assign TPX3_1_T0_Sync_Ext1 = TPX3_1_T0_Sync;
	     assign TPX3_1_T0_Sync_Ext2 = TPX3_1_T0_Sync;
	     assign TPX3_1_Reset_Ext1 = TPX3_1_Reset;
	     assign TPX3_1_Reset_Ext2 = TPX3_1_Reset;
    `elsif client
	     assign TPX3_1_T0_Sync_Ext = TPX3_1_T0_Sync_Ext1;
	     assign TPX3_1_Reset_Ext = TPX3_1_Reset_Ext1;
	 `endif

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
	 
	 wire TLU_RJ45_RESET;
	 wire TLU_RJ45_CLK;
	 wire TLU_RJ45_TRIGGER;
	 wire TLU_RJ45_BUSY;
	 
	 IBUFDS #(.IOSTANDARD("DEFAULT")) IBUFDS_tlu_trigger (.O(TLU_RJ45_TRIGGER), .I(TLU_RJ45_TRIGGER_P), .IB(TLU_RJ45_TRIGGER_N));
	 OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_tlu_busy (.O(TLU_RJ45_BUSY_P), .OB(TLU_RJ45_BUSY_N), .I(TLU_RJ45_BUSY));
	 IBUFDS #(.IOSTANDARD("DEFAULT")) IBUFDS_tlu_reset(.O(TLU_RJ45_RESET), .I(TLU_RJ45_RESET_P), .IB(TLU_RJ45_RESET_N));
	 OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_tlu_clk(.O(TLU_RJ45_CLK_P), .OB(TLU_RJ45_CLK_N), .I(TLU_RJ45_CLK));

    IDELAYCTRL IDELAYCTRL_inst (
        .RDY   (             ), // 1-bit Ready output
        .REFCLK( CLK200_SYS  ), // 1-bit Reference clock input
        .RST   ( ~mmcm_locked)  // 1-bit Reset input
    );

    tpx3_core tpx3_core_inst(
        .BUS_CLK        (BUS_CLK              ),
        .BUS_RST        (BUS_RST              ),
        .BUS_ADD        (BUS_ADD              ),
        .BUS_DATA       (BUS_DATA             ),
        .BUS_RD         (BUS_RD               ),
        .BUS_WR         (BUS_WR               ),
        .BUS_BYTE_ACCESS(BUS_BYTE_ACCESS      ),

        .CLK40          (CLK40                ),
        .CLK320         (CLK320               ),
        .CLK32          (CLK32                ),

        .RX_DATA        (RX_DATA              ),
        .ExtTPulse      (TPX3_1_ExtTPulse     ),
		  `ifdef host
		      .T0_Sync        (TPX3_1_T0_Sync       ),
	     `elsif client
		      .T0_Sync        (TPX3_1_T0_Sync_Ext   ),
	     `endif
        .EnableIn       (TPX3_1_EnableIn      ),
        .DataIn         (TPX3_1_DataIn        ),
        .Shutter        (TPX3_1_Shutter       ),
		  `ifdef host
		      .Reset          (TPX3_1_Reset         ),
	     `elsif client
		      .Reset          (TPX3_1_Reset_Ext     ),
	     `endif
        .ENPowerPulsing (TPX3_1_ENPowerPulsing),
        .Data_MUX_select(Data_MUX_select      ),

        .LED            (                     ),
        .RX_READY       (RX_READY             ),
		  
		  //TLU
		  .TLU_RJ45_TRIGGER (TLU_RJ45_TRIGGER   ),
		  .TLU_RJ45_RESET   (TLU_RJ45_RESET     ),
		  .TLU_RJ45_BUSY    (TLU_RJ45_BUSY      ),
		  .TLU_RJ45_CLK     (TLU_RJ45_CLK       ),
		  
		  .FIFO_FULL        (1'b0               )
    );

    wire CLK40_OUT;
    ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_CLK40_OUT ( .Q(CLK40_OUT), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0));

    //assign LED = {pcspma_status_vector[0],basex_or_sgmii};
	 /*
    wire [35:0] control_bus;
    chipscope_icon ichipscope_icon
    (
        .CONTROL0(control_bus)
    );
    chipscope_ila ichipscope_ila
    (
        .CONTROL(control_bus                                ),
        .CLK    (CLK125                                     ),
        //.TRIG0({pcspma_status_vector, phy_gmii_rxd_int, phy_gmii_rx_dv_int, phy_gmii_rx_er_int, phy_gmii_clk_en_int, phy_gmii_rst_int,mmcm_locked})
        .TRIG0  ({cnt[15:0], basex_or_sgmii, phy_rst, ETH_STATUS_OK})
    );
	 */

endmodule
