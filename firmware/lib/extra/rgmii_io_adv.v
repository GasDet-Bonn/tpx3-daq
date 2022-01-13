///////////////////////////////////////////////////////////////////////////////
//
// Module: rgmii_io_adv.v
// Project: NetFPGA
// Description: Instantiate the IO flops for the rgmii interface for one TEMAC.
//
// See the Xilinx TriMode Ethernet MAC USer Guide (UG138) for details
//
///////////////////////////////////////////////////////////////////////////////


module rgmii_io_adv #(parameter RXDELAY = 13)
                     (output wire [3:0] rgmii_txd,
                      output wire rgmii_tx_ctl,
                      output wire rgmii_txc,
                      input wire [3:0] rgmii_rxd,
                      input wire rgmii_rx_ctl,
                      input wire rgmii_rxc,             // Internal RGMII receiver clock
                      input wire [7:0] gmii_txd,        // Internal gmii_txd signal.
                      input wire gmii_tx_en,
                      input wire gmii_tx_er,
                      output wire gmii_col,
                      output wire gmii_crs,
                      output reg [7:0] gmii_rxd,        // RGMII double data rate data valid.
                      output reg gmii_rx_dv,            // gmii_rx_dv_ibuf registered in IOBs.
                      output reg gmii_rx_er,            // gmii_rx_er_ibuf registered in IOBs.
                      output reg eth_link_status,
                      output reg [1:0] eth_clock_speed,
                      output reg eth_duplex_status,
                      input wire tx_clk,                // Internal RGMII transmitter clock.
                      input wire tx_clk90,              // Internal RGMII transmitter clock w/ 90 deg phase
                      output wire rx_clk,
                      input wire reset);
    
    
    reg [7:0] gmii_txd_rising;     // gmii_txd signal registered on the rising edge of tx_clk.
    reg       gmii_tx_en_rising;   // gmii_tx_en signal registered on the rising edge of tx_clk.
    reg       rgmii_tx_ctl_rising; // RGMII control signal registered on the rising edge of tx_clk.
    reg [3:0] gmii_txd_falling;    // gmii_txd signal registered on the falling edge of tx_clk
    
    reg       rgmii_tx_ctl_falling;// RGMII control signal registered on the falling edge of tx_clk.
    
    wire [3:0] rgmii_txd_obuf;     // RGMII transmit data output.
    
    
    //reg [7:0]  rgmii_rxd_ddr;
    //reg        rgmii_rx_dv_ddr;    // Inverted version of the rx_rgmii_clk_int signal.
    //reg        rgmii_rx_ctl_ddr;   // RGMII double data rate data.
    wire [7:0]  rgmii_rxd_reg;      // RGMII double data rate data valid.
    wire        rgmii_rx_dv_reg;    // RGMII double data rate control signal.
    wire        rgmii_rx_ctl_reg;   // RGMII data. gmii_tx_en signal.
    
    //----------------------------------------------------------------
    // Transmit interface
    //----------------------------------------------------------------
    
    //----------------------------------------------------------------
    // Tx clock.
    // Instantiate a DDR output register.  This is a good way to drive
    // RGMII_TXC since the clock-to-PAD delay will be the same as that
    // for data driven from IOB Ouput flip-flops eg rgmii_rxd[3:0].
    // This is set to produce a 90 degree phase shifted clock w.r.t.
    // gtx_clk_bufg so that the clock edges are centralised within the
    // rgmii_txd[3:0] valid window.
    //----------------------------------------------------------------
    
    wire rgmii_txc_obuf;
    ODDR #(
    .DDR_CLK_EDGE("OPPOSITE_EDGE"),
    .INIT(1'b0),
    .SRTYPE("SYNC")
    ) ODDR_inst (
    .Q(rgmii_txc_obuf),
    .C(tx_clk90),
    .CE(1'b1),
    .D1(1'b1),
    .D2(1'b0),
    .R(1'b0),
    .S(1'b0)
    );
    
    //  drive clock through Output Buffers and onto PADS.
    OBUF drive_rgmii_txc     (.I(rgmii_txc_obuf),     .O(rgmii_txc));
    
    //-------------------------------------------------------------------
    // RGMII Transmitter Logic :
    // drive TX signals through IOBs onto RGMII interface
    //-------------------------------------------------------------------
    
    // Encode rgmii ctl signal
    wire rgmii_tx_ctl_int;
    assign rgmii_tx_ctl_int = gmii_tx_en ^ gmii_tx_er;
    
    // Register all output signals on rising edge of gtx_clk_bufg
    always @(posedge tx_clk or posedge reset)
    begin
        if (reset)
        begin
            gmii_txd_rising     <= 8'b0;
            gmii_tx_en_rising   <= 1'b0;
            rgmii_tx_ctl_rising <= 1'b0;
        end
        else
        begin
            gmii_txd_rising     <= gmii_txd;
            gmii_tx_en_rising   <= gmii_tx_en;
            rgmii_tx_ctl_rising <= rgmii_tx_ctl_int;
        end
    end
    
    wire not_tx_rgmii_clk_int;
    assign not_tx_rgmii_clk_int = ~(tx_clk);
    
    // Register falling edge RGMII output signals on rising edge of not_gtx_clk_bufg
    always @(posedge not_tx_rgmii_clk_int or posedge reset)
    begin
        if (reset)
        begin
            gmii_txd_falling     <= 4'b0;
            rgmii_tx_ctl_falling <= 1'b0;
        end
        else
        begin
            gmii_txd_falling     <= gmii_txd_rising[7:4];
            rgmii_tx_ctl_falling <= rgmii_tx_ctl_rising;
        end
    end
    
    ODDR #(
    .DDR_CLK_EDGE("OPPOSITE_EDGE"),
    .INIT(1'b0),
    .SRTYPE("SYNC")
    ) ODDR_rgmii_txd_out3 (
    .Q(rgmii_txd_obuf[3]),
    .C(tx_clk),
    .CE(1'b1),
    .D1(gmii_txd_rising[3]),
    .D2(gmii_txd_falling[3]),
    .R(reset),
    .S(1'b0)
    );
    
    ODDR #(
    .DDR_CLK_EDGE("OPPOSITE_EDGE"),
    .INIT(1'b0),
    .SRTYPE("SYNC")
    ) ODDR_rgmii_txd_out2 (
    .Q(rgmii_txd_obuf[2]),
    .C(tx_clk),
    .CE(1'b1),
    .D1(gmii_txd_rising[2]),
    .D2(gmii_txd_falling[2]),
    .R(reset),
    .S(1'b0)
    );
    
    ODDR #(
    .DDR_CLK_EDGE("OPPOSITE_EDGE"),
    .INIT(1'b0),
    .SRTYPE("SYNC")
    ) ODDR_rgmii_txd_out1 (
    .Q(rgmii_txd_obuf[1]),
    .C(tx_clk),
    .CE(1'b1),
    .D1(gmii_txd_rising[1]),
    .D2(gmii_txd_falling[1]),
    .R(reset),
    .S(1'b0)
    );
    
    ODDR #(
    .DDR_CLK_EDGE("OPPOSITE_EDGE"),
    .INIT(1'b0),
    .SRTYPE("SYNC")
    ) ODDR_rgmii_txd_out0 (
    .Q(rgmii_txd_obuf[0]),
    .C(tx_clk),
    .CE(1'b1),
    .D1(gmii_txd_rising[0]),
    .D2(gmii_txd_falling[0]),
    .R(reset),
    .S(1'b0)
    );
    
    wire rgmii_tx_ctl_obuf;
    ODDR #(
    .DDR_CLK_EDGE("OPPOSITE_EDGE"),
    .INIT(1'b0),
    .SRTYPE("SYNC")
    ) ODDR_rgmii_txd_ctl
    (
    .Q(rgmii_tx_ctl_obuf),
    .C(tx_clk),
    .CE(1'b1),
    .D1(gmii_tx_en_rising),
    .D2(rgmii_tx_ctl_falling),
    .R(reset),
    .S(1'b0)
    );
    
    
    //  Drive RGMII Tx signals through Output Buffers and onto PADS.
    OBUF drive_rgmii_tx_ctl  (.I(rgmii_tx_ctl_obuf),     .O(rgmii_tx_ctl));
    
    OBUF drive_rgmii_txd3    (.I(rgmii_txd_obuf[3]),     .O(rgmii_txd[3]));
    OBUF drive_rgmii_txd2    (.I(rgmii_txd_obuf[2]),     .O(rgmii_txd[2]));
    OBUF drive_rgmii_txd1    (.I(rgmii_txd_obuf[1]),     .O(rgmii_txd[1]));
    OBUF drive_rgmii_txd0    (.I(rgmii_txd_obuf[0]),     .O(rgmii_txd[0]));
    
    
    //----------------------------------------------------------------
    // Receive interface
    //----------------------------------------------------------------
    
    
    //-------------------------------------------------------------------
    // RGMII Receiver Logic : receive RGMII_RX signals through IOBs from
    // RGMII interface and convert to gmii_rx signals.
    //-------------------------------------------------------------------
    
    //  Drive input RGMII Rx signals from PADS through Input Buffers.
    
    wire [3:0] rgmii_rxd_ibuf, rgmii_rxd_delay;
    wire rgmii_rx_ctl_ibuf, rgmii_rx_ctl_delay;
    
    wire rgmii_rxc_ibuf, rgmii_rxc_bufio, rgmii_rxc_dly;
    IBUF ibuf_rgmii_rxc (.I(rgmii_rxc), .O(rgmii_rxc_ibuf));

    IDELAYE2 #(
    .IDELAY_TYPE("FIXED"),
    .IDELAY_VALUE(16),
    .SIGNAL_PATTERN("DATA")
    )
    delay_rgmii_rxc (
    .IDATAIN       (rgmii_rxc_ibuf),
    .DATAOUT       (rgmii_rxc_dly),
    .DATAIN        (1'b0),
    .C             (1'b0),
    .CE            (1'b0),
    .INC           (1'b0),
    .CINVCTRL      (1'b0),
    .CNTVALUEIN    (5'h0),
    .CNTVALUEOUT   (),
    .LD            (1'b0),
    .LDPIPEEN      (1'b0),
    .REGRST        (1'b0)
    );

    BUFIO bufio_rxc(.I(rgmii_rxc_dly), .O(rgmii_rxc_bufio));
    
    //BUFR bufr_rgmii_rx_clk (.I(rgmii_rxc_ibuf), .CE(1'b1), .CLR(1'b0), .O(rx_clk));
    
    BUFG bufr_rgmii_rx_clk (.I(rgmii_rxc_dly), .O(rx_clk));
    
    
    IBUF drive_rgmii_rx_ctl (.I(rgmii_rx_ctl), .O(rgmii_rx_ctl_ibuf));
    
    IDELAYE2 #(
    .IDELAY_TYPE("FIXED"),
    .IDELAY_VALUE(RXDELAY),
    .SIGNAL_PATTERN("DATA")
    )
    delay_rgmii_rx_ctl (
    .IDATAIN       (rgmii_rx_ctl_ibuf),
    .DATAOUT       (rgmii_rx_ctl_delay),
    .DATAIN        (1'b0),
    .C             (1'b0),
    .CE            (1'b0),
    .INC           (1'b0),
    .CINVCTRL      (1'b0),
    .CNTVALUEIN    (5'h0),
    .CNTVALUEOUT   (),
    .LD            (1'b0),
    .LDPIPEEN      (1'b0),
    .REGRST        (1'b0)
    );
    
    IDDR #(
    .DDR_CLK_EDGE("OPPOSITE_EDGE"),
    .INIT_Q1(1'b0),
    .INIT_Q2(1'b0),
    .SRTYPE("SYNC")
    ) IDDR_rgmii_rx_ctl (
    .Q1(rgmii_rx_dv_reg), // 1-bit output for positive edge of clock
    .Q2(rgmii_rx_ctl_reg), // 1-bit output for negative edge of clock
    .C(rgmii_rxc_bufio),   // 1-bit clock input
    .CE(1'b1), // 1-bit clock enable input
    .D(rgmii_rx_ctl_delay),   // 1-bit DDR data input
    .R(1'b0),   // 1-bit reset
    .S(1'b0)    // 1-bit set
    );
    
    
    genvar j;
    generate for (j = 0; j<4; j = j+1)
    begin : rxdata_bus
    
    IBUF drive_rgmii_rxd   (.I(rgmii_rxd[j]), .O(rgmii_rxd_ibuf[j]));
    
    IDELAYE2 #(
    .IDELAY_TYPE("FIXED"),
    .IDELAY_VALUE(RXDELAY),
    .SIGNAL_PATTERN("DATA")
    )
    delay_rgmii_rxd (
    .IDATAIN       (rgmii_rxd_ibuf[j]),
    .DATAOUT       (rgmii_rxd_delay[j]),
    .DATAIN        (1'b0),
    .C             (1'b0),
    .CE            (1'b0),
    .INC           (1'b0),
    .CINVCTRL      (1'b0),
    .CNTVALUEIN    (5'h0),
    .CNTVALUEOUT   (),
    .LD            (1'b0),
    .LDPIPEEN      (1'b0),
    .REGRST        (1'b0)
    );
    
    IDDR #(
    .DDR_CLK_EDGE("OPPOSITE_EDGE"),
    .INIT_Q1(1'b0),
    .INIT_Q2(1'b0),
    .SRTYPE("SYNC")
    ) IDDR_rgmii_rxd (
    .Q1(rgmii_rxd_reg[j]), // 1-bit output for positive edge of clock
    .Q2(rgmii_rxd_reg[j+4]), // 1-bit output for negative edge of clock
    .C(rgmii_rxc_bufio),   // 1-bit clock input
    .CE(1'b1), // 1-bit clock enable input
    .D(rgmii_rxd_delay[j]),   // 1-bit DDR data input
    .R(reset),   // 1-bit reset
    .S(1'b0)    // 1-bit set
    );
    end
    endgenerate
    
    // Register all input signals on rising edge of gmii_rx_clk_bufg to syncronise.
    always @(posedge rx_clk or posedge reset)
    begin
        if (reset)
        begin
            gmii_rxd[7:0] <= 8'b0;
            gmii_rx_dv    <= 1'b0;
            gmii_rx_er    <= 1'b0;
        end
        else
        begin
            gmii_rxd[7:0] <= rgmii_rxd_reg[7:0];
            gmii_rx_dv    <= rgmii_rx_dv_reg;
            gmii_rx_er    <= rgmii_rx_ctl_reg ^ rgmii_rx_dv_reg;
        end
    end
    
    
    //--------------------------------------------------------------------
    // RGMII Inband Status Registers
    // extract the inband status from received rgmii data
    //--------------------------------------------------------------------
    
    // Enable inband status registers during Interframe Gap
    wire inband_ce;
    assign inband_ce = !(gmii_rx_dv || gmii_rx_er);
    
    always @(posedge rx_clk or posedge reset)
    begin
        if (reset)
        begin
            eth_link_status      <= 1'b0;
            eth_clock_speed[1:0] <= 2'b0;
            eth_duplex_status    <= 1'b0;
        end
        else
            if (inband_ce)
            begin
                eth_link_status      <= gmii_rxd[0];
                eth_clock_speed[1:0] <= gmii_rxd[2:1];
                eth_duplex_status    <= gmii_rxd[3];
            end
    end
    
    assign gmii_col = (gmii_tx_en | gmii_tx_er) & (gmii_rx_dv | gmii_rx_er);
    assign gmii_crs = (gmii_tx_en | gmii_tx_er) | (gmii_rx_dv | gmii_rx_er);
    
endmodule // rgmii_io
