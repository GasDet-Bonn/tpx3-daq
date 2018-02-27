

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

module tpx3 (
    
    input  wire       sys_clk_p, //CLK 200MHz
    input  wire       sys_clk_n,
    input  wire       reset,
    
    input  wire [7:0] sw,
    output wire       ledu,
    output wire       ledl,
    output wire       ledd,
    output wire       ledr,
    output wire       ledc,
    output wire [7:0] led,
    
    input  wire       phy_sgmii_rx_p,
    input  wire       phy_sgmii_rx_n,
    output wire       phy_sgmii_tx_p,
    output wire       phy_sgmii_tx_n,
    input  wire       phy_sgmii_clk_p,
    input  wire       phy_sgmii_clk_n,
    output wire       phy_reset_n,
    
    
    output wire [3:0] FMC_LED,
    inout wire [4:0] FMC_LEMO,
    
    input wire TPX3_1_PLLOut_N,
    input wire TPX3_1_PLLOut_P,
    input wire TPX3_1_ClkOut_N,
    input wire TPX3_1_ClkOut_P,
    
    output wire TPX3_1_ClkInRefPLL_N,
    output wire TPX3_1_ClkInRefPLL_P,
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

    output wire Data_MUX_select

);

// Clock and reset

wire sys_clk_ibufg;
wire sys_clk_bufg;
wire clk_125mhz_mmcm_out;

// Internal 125 MHz clock
wire clk_125mhz_int;
wire rst_125mhz_int;

wire mmcm_rst = reset;
wire mmcm_locked;
wire mmcm_clkfb;

IBUFGDS
clk_ibufgds_inst(
    .I(sys_clk_p),
    .IB(sys_clk_n),
    .O(sys_clk_ibufg)
);

// MMCM instance
// 200 MHz in, 125 MHz out
// PFD range: 10 MHz to 450 MHz
// VCO range: 600 MHz to 1200 MHz
// M = 5, D = 1 sets Fvco = 1000 MHz (in range)
// Divide by 8 to get output frequency of 125 MHz
MMCM_BASE #(
    .BANDWIDTH("OPTIMIZED"),
    .CLKOUT0_DIVIDE_F(25),
    .CLKOUT0_DUTY_CYCLE(0.5),
    .CLKOUT0_PHASE(0),
    .CLKOUT1_DIVIDE(1),
    .CLKOUT1_DUTY_CYCLE(0.5),
    .CLKOUT1_PHASE(0),
    .CLKOUT2_DIVIDE(1),
    .CLKOUT2_DUTY_CYCLE(0.5),
    .CLKOUT2_PHASE(0),
    .CLKOUT3_DIVIDE(1),
    .CLKOUT3_DUTY_CYCLE(0.5),
    .CLKOUT3_PHASE(0),
    .CLKOUT4_DIVIDE(1),
    .CLKOUT4_DUTY_CYCLE(0.5),
    .CLKOUT4_PHASE(0),
    .CLKOUT5_DIVIDE(1),
    .CLKOUT5_DUTY_CYCLE(0.5),
    .CLKOUT5_PHASE(0),
    .CLKOUT6_DIVIDE(1),
    .CLKOUT6_DUTY_CYCLE(0.5),
    .CLKOUT6_PHASE(0),
    .CLKFBOUT_MULT_F(5),
    .CLKFBOUT_PHASE(0),
    .DIVCLK_DIVIDE(1),
    .REF_JITTER1(0.100),
    .CLKIN1_PERIOD(5.0),
    .STARTUP_WAIT("FALSE"),
    .CLKOUT4_CASCADE("FALSE")
)
clk_mmcm_inst (
    .CLKIN1(sys_clk_ibufg),
    .CLKFBIN(mmcm_clkfb),
    .RST(mmcm_rst),
    .PWRDWN(1'b0),
    .CLKOUT0(clk_40mhz_mmcm_out),
    .CLKOUT0B(),
    .CLKOUT1(),
    .CLKOUT1B(),
    .CLKOUT2(),
    .CLKOUT2B(),
    .CLKOUT3(),
    .CLKOUT3B(),
    .CLKOUT4(),
    .CLKOUT5(),
    .CLKOUT6(),
    .CLKFBOUT(mmcm_clkfb),
    .CLKFBOUTB(),
    .LOCKED(mmcm_locked)
);

wire CLK40;
BUFG
clk_40mhz_bufg_inst (
    .I(clk_40mhz_mmcm_out),
    .O(CLK40)
);

sync_reset #(
    .N(4)
)
sync_reset_125mhz_inst (
    .clk(clk_125mhz_int),
    .rst(~mmcm_locked),
    .sync_reset_out(rst_125mhz_int)
);

// GPIO
assign ledu = 0;
assign ledl = 0;
assign ledd = 0;
assign ledr = 0;
assign ledc = 0;

// SGMII interface to PHY
wire phy_gmii_clk_int;
wire phy_gmii_rst_int;
wire phy_gmii_clk_en_int;
wire [7:0] phy_gmii_txd_int;
wire phy_gmii_tx_en_int;
wire phy_gmii_tx_er_int;
wire [7:0] phy_gmii_rxd_int;
wire phy_gmii_rx_dv_int;
wire phy_gmii_rx_er_int;

wire phy_sgmii_mgtrefclk;
wire phy_sgmii_txoutclk;
wire phy_sgmii_userclk2;

assign clk_125mhz_int = phy_sgmii_userclk2;

IBUFDS_GTXE1
phy_sgmii_ibufds_mgtrefclk (
    .CEB   (1'b0),
    .I     (phy_sgmii_clk_p),
    .IB    (phy_sgmii_clk_n),
    .O     (phy_sgmii_mgtrefclk),
    .ODIV2 ()
);

BUFG
phy_sgmii_bufg_userclk2 (
    .I     (phy_sgmii_txoutclk),
    .O     (phy_sgmii_userclk2)
);

assign phy_gmii_clk_int = phy_sgmii_userclk2;

sync_reset #(
    .N(4)
)
sync_reset_pcspma_inst (
    .clk(phy_gmii_clk_int),
    .rst(rst_125mhz_int),
    .sync_reset_out(phy_gmii_rst_int)
);

wire [15:0] pcspma_status_vector;

wire pcspma_status_link_status              = pcspma_status_vector[0];
wire pcspma_status_link_synchronization     = pcspma_status_vector[1];
wire pcspma_status_rudi_c                   = pcspma_status_vector[2];
wire pcspma_status_rudi_i                   = pcspma_status_vector[3];
wire pcspma_status_rudi_invalid             = pcspma_status_vector[4];
wire pcspma_status_rxdisperr                = pcspma_status_vector[5];
wire pcspma_status_rxnotintable             = pcspma_status_vector[6];
wire pcspma_status_phy_link_status          = pcspma_status_vector[7];
wire [1:0] pcspma_status_remote_fault_encdg = pcspma_status_vector[9:8];
wire [1:0] pcspma_status_speed              = pcspma_status_vector[11:10];
wire pcspma_status_duplex                   = pcspma_status_vector[12];
wire pcspma_status_remote_fault             = pcspma_status_vector[13];
wire [1:0] pcspma_status_pause              = pcspma_status_vector[15:14];

wire [4:0] pcspma_config_vector;

assign pcspma_config_vector[4] = 1'b1; // autonegotiation enable
assign pcspma_config_vector[3] = 1'b0; // isolate
assign pcspma_config_vector[2] = 1'b0; // power down
assign pcspma_config_vector[1] = 1'b0; // loopback enable
assign pcspma_config_vector[0] = 1'b0; // unidirectional enable

wire [15:0] pcspma_an_config_vector;

assign pcspma_an_config_vector[15]    = 1'b1;    // SGMII link status
assign pcspma_an_config_vector[14]    = 1'b1;    // SGMII Acknowledge
assign pcspma_an_config_vector[13:12] = 2'b01;   // full duplex
assign pcspma_an_config_vector[11:10] = 2'b10;   // SGMII speed
assign pcspma_an_config_vector[9]     = 1'b0;    // reserved
assign pcspma_an_config_vector[8:7]   = 2'b00;   // pause frames - SGMII reserved
assign pcspma_an_config_vector[6]     = 1'b0;    // reserved
assign pcspma_an_config_vector[5]     = 1'b0;    // full duplex - SGMII reserved
assign pcspma_an_config_vector[4:1]   = 4'b0000; // reserved
assign pcspma_an_config_vector[0]     = 1'b1;    // SGMII

gig_eth_pcs_pma_v11_5_block
eth_pcspma (
    // Transceiver Interface
    .mgtrefclk             (phy_sgmii_mgtrefclk),
    .gtx_reset_clk         (clk_125mhz_int),
    .txp                   (phy_sgmii_tx_p),
    .txn                   (phy_sgmii_tx_n),
    .rxp                   (phy_sgmii_rx_p),
    .rxn                   (phy_sgmii_rx_n),
    .txoutclk              (phy_sgmii_txoutclk),
    .userclk2              (phy_sgmii_userclk2),
    .pma_reset             (rst_125mhz_int),
    // GMII Interface
    .sgmii_clk_r           (),
    .sgmii_clk_f           (),
    .sgmii_clk_en          (phy_gmii_clk_en_int),
    .gmii_txd              (phy_gmii_txd_int),
    .gmii_tx_en            (phy_gmii_tx_en_int),
    .gmii_tx_er            (phy_gmii_tx_er_int),
    .gmii_rxd              (phy_gmii_rxd_int),
    .gmii_rx_dv            (phy_gmii_rx_dv_int),
    .gmii_rx_er            (phy_gmii_rx_er_int),
    .gmii_isolate          (),
    // Management: Alternative to MDIO Interface
    .configuration_vector  (pcspma_config_vector),
    .an_interrupt          (),
    .an_adv_config_vector  (pcspma_an_config_vector),
    .an_restart_config     (1'b0),
    .link_timer_value      (9'd50),
    // Speed Control
    .speed_is_10_100       (pcspma_status_speed != 2'b10),
    .speed_is_100          (pcspma_status_speed == 2'b01),
    // General IO's
    .status_vector         (pcspma_status_vector),
    .reset                 (rst_125mhz_int),
    .signal_detect         (1'b1)
);

wire [31:0]  BUS_ADD, BUS_DATA;
wire BUS_RD, BUS_WR, BUS_CLK, BUS_RST, BUS_BYTE_ACCESS;

si_udp si_udp_inst (
    
    .clk_125mhz(clk_125mhz_int),
    .rst_125mhz(rst_125mhz_int),

    .phy_gmii_clk(phy_gmii_clk_int),
    .phy_gmii_rst(phy_gmii_rst_int),
    .phy_gmii_clk_en(phy_gmii_clk_en_int),
    .phy_gmii_rxd(phy_gmii_rxd_int),
    .phy_gmii_rx_dv(phy_gmii_rx_dv_int),
    .phy_gmii_rx_er(phy_gmii_rx_er_int),
    .phy_gmii_txd(phy_gmii_txd_int),
    .phy_gmii_tx_en(phy_gmii_tx_en_int),
    .phy_gmii_tx_er(phy_gmii_tx_er_int),
    .phy_reset_n(phy_reset_n),
    
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_BYTE_ACCESS(BUS_BYTE_ACCESS)
);

wire  TPX3_1_ClkInRefPLL_reg, TPX3_1_ClkIn40_reg;
ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkInRefPLL ( .Q(TPX3_1_ClkInRefPLL_reg), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0)); //ENABLE?
OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_inst_TPX3_1_ClkInRefPLL ( .O(TPX3_1_ClkInRefPLL_P), .OB(TPX3_1_ClkInRefPLL_N), .I(TPX3_1_ClkInRefPLL_reg)  );
ODDR #(.DDR_CLK_EDGE("OPPOSITE_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst_TPX3_1_ClkIn40 ( .Q(TPX3_1_ClkIn40_reg), .C(CLK40), .CE(1'b1), .D1(1'b0), .D2(1'b1), .R(1'b0), .S(1'b0)); //ENABLE?
OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_inst_TPX3_1_ClkIn40 ( .O(TPX3_1_ClkIn40_P), .OB(TPX3_1_ClkIn40_N), .I(TPX3_1_ClkIn40_reg)  );
 

wire TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn,  TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing;
wire [6:0] to_out_buf, to_out_buf_n, to_out_buf_p;
assign to_out_buf = {TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn,  TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing};
assign {TPX3_1_ExtTPulse_N, TPX3_1_T0_Sync_N, TPX3_1_EnableIn_N, TPX3_1_DataIn_N,  TPX3_1_Shutter_N, TPX3_1_Reset_N, TPX3_1_ENPowerPulsing_N} = to_out_buf_n;
assign {TPX3_1_ExtTPulse_P, TPX3_1_T0_Sync_P, TPX3_1_EnableIn_P, TPX3_1_DataIn_P,  TPX3_1_Shutter_P, TPX3_1_Reset_P, TPX3_1_ENPowerPulsing_P} = to_out_buf_p;
genvar h;
generate
  for (h = 0; h < 7; h = h + 1) begin: out_buf_gen
    wire ddr_buf_out;
    ODDR #(.DDR_CLK_EDGE("SAME_EDGE"), .INIT(1'b0), .SRTYPE("SYNC") ) ODDR_inst ( .Q(ddr_buf_out), .C(CLK40), .CE(1'b1), .D1(to_out_buf[h]), .D2(to_out_buf[h]), .R(1'b0), .S(1'b0));
    OBUFDS #(.IOSTANDARD("DEFAULT")) OBUFDS_inst( .O(to_out_buf_p[h]), .OB(to_out_buf_n[h]), .I(ddr_buf_out)  );
  end
endgenerate

    
tpx3_core tpx3_core_inst(
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_BYTE_ACCESS(BUS_BYTE_ACCESS),
    
	.CLK40(CLK40),
    .ExtTPulse(TPX3_1_ExtTPulse), 
	.T0_Sync(TPX3_1_T0_Sync), 
	.EnableIn(TPX3_1_EnableIn), 
	.DataIn(TPX3_1_DataIn),  
	.Shutter(TPX3_1_Shutter), 
	.Reset(TPX3_1_Reset), 
	.ENPowerPulsing(TPX3_1_ENPowerPulsing),
    .Data_MUX_select(Data_MUX_select),
    
    .LED(led)

);


assign FMC_LEMO[4:0] = {TPX3_1_DataIn, TPX3_1_Shutter, TPX3_1_EnableIn, TPX3_1_Reset, CLK40};
assign FMC_LED = led[3:0];
    
endmodule
