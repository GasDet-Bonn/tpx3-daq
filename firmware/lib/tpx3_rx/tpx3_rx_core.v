/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */
`timescale 1ps/1ps
`default_nettype none

module tpx3_rx_core
#(
    parameter           DATA_IDENTIFIER = 0,
    parameter           ABUSWIDTH = 32
)
(
    input wire RX_CLKX2,
    input wire RX_CLKW,
    input wire RX_DATA,
    
    output wire RX_READY,
    output wire RX_8B10B_DECODER_ERR,
    output wire RX_FIFO_OVERFLOW_ERR,

    input wire FIFO_CLK,
    input wire FIFO_READ,
    output wire FIFO_EMPTY,
    output wire [31:0] FIFO_DATA,

    output wire RX_FIFO_FULL,
    output wire RX_ENABLED,

    input wire BUS_CLK,
    input wire [ABUSWIDTH-1:0] BUS_ADD,
    input wire [7:0] BUS_DATA_IN,
    output reg [7:0] BUS_DATA_OUT,
    input wire BUS_RST,
    input wire BUS_WR,
    input wire BUS_RD
);

localparam VERSION = 1;

// 0 - soft reset
// 1 - status
// 2-3 fifo size
// 4 - decoder_err_cnt
// 5 - lost_err_cnt

// reset sync and registers
// when write to addr = 0 then reset
wire SOFT_RST;
assign SOFT_RST = (BUS_ADD==0 && BUS_WR);

wire RST;
assign RST = BUS_RST | SOFT_RST; 


wire [15:0] fifo_size; // BUS_ADD==3, 4
reg [15:0] fifo_size_buf;
wire [7:0] decoder_err_cnt; // BUS_ADD==5
reg [7:0] decoder_err_cnt_buf;
wire [7:0] lost_err_cnt; // BUS_ADD==6
reg [7:0] lost_err_cnt_buf;
wire [4:0] CONF_RX_DATA_DLY;
wire [0:0] CONF_SAMPLING_EDGE;

reg [7:0] status_regs [7:0];

wire CONF_EN_INVERT_RX_DATA; // BUS_ADD==2 BIT==1
assign CONF_EN_INVERT_RX_DATA = status_regs[2][1];
wire CONF_EN_RX; // BUS_ADD==2 BIT==2
assign CONF_EN_RX = status_regs[2][2];
assign RX_ENABLED = CONF_EN_RX;
assign CONF_RX_DATA_DLY = status_regs[7][4:0];
assign CONF_SAMPLING_EDGE = status_regs[7][5];
wire CONF_ERROR_RESET; // BUS_ADD==7 BIT==6
assign CONF_ERROR_RESET = status_regs[7][6];

always @(posedge BUS_CLK) begin
    if(RST) begin
        status_regs[2] <= 8'b0000_0000; // disable Rx by default
        status_regs[7] <= 8'b0000_0000;
    end
    else if(BUS_WR && BUS_ADD < 8)
        status_regs[BUS_ADD[2:0]] <= BUS_DATA_IN;
end

always @ (posedge BUS_CLK) begin
    if(BUS_RD) begin
        if(BUS_ADD == 0)
            BUS_DATA_OUT <= VERSION;
        else if(BUS_ADD == 2)
            BUS_DATA_OUT <= {status_regs[2][7:1], RX_READY};
        else if(BUS_ADD == 3)
            BUS_DATA_OUT <= fifo_size[7:0];
        else if(BUS_ADD == 4)
            BUS_DATA_OUT <= fifo_size_buf[15:8];
        else if(BUS_ADD == 5)
            BUS_DATA_OUT <= decoder_err_cnt_buf;
        else if(BUS_ADD == 6)
            BUS_DATA_OUT <= lost_err_cnt_buf;
        else if(BUS_ADD == 7)
            BUS_DATA_OUT <= {2'b0, CONF_SAMPLING_EDGE, CONF_RX_DATA_DLY};        
        else
            BUS_DATA_OUT <= 8'b0;
    end
end

wire ready_rec;
assign RX_READY = (ready_rec==1'b1) ? 1'b1 : 1'b0;
assign RX_8B10B_DECODER_ERR = (decoder_err_cnt!=8'b0);
assign RX_FIFO_OVERFLOW_ERR = (lost_err_cnt!=8'b0);

wire [24:0] FE_DATA;
wire [6:0] DATA_HEADER;
assign DATA_HEADER = DATA_IDENTIFIER;
assign FIFO_DATA = {DATA_HEADER, FE_DATA};


always @ (posedge BUS_CLK)
begin
    if (BUS_ADD == 3 && BUS_RD)
        fifo_size_buf <= fifo_size;
end

always @ (posedge BUS_CLK)
begin
    decoder_err_cnt_buf <= decoder_err_cnt;
end

always @ (posedge BUS_CLK)
begin
    lost_err_cnt_buf <= lost_err_cnt;
end

wire RX_DATA_DLY;

reg  CONF_RX_DATA_DLY_WR;
always @ (posedge BUS_CLK)
    CONF_RX_DATA_DLY_WR <= BUS_WR & (BUS_ADD == 7);

`ifdef COCOTB_SIM
     assign RX_DATA_DLY = RX_DATA;
`else
    IODELAYE1 #(
        .CINVCTRL_SEL("FALSE"),
        .DELAY_SRC("I"),
        .HIGH_PERFORMANCE_MODE("TRUE"), 
        .IDELAY_TYPE("VAR_LOADABLE"), 
        .IDELAY_VALUE(0),
        .ODELAY_TYPE("FIXED"),
        .ODELAY_VALUE(0),
        .REFCLK_FREQUENCY(200.0),
        .SIGNAL_PATTERN("DATA")
    )
    IODELAYE1_RX (
        .CNTVALUEOUT(),
        .DATAOUT(RX_DATA_DLY),
        .C(BUS_CLK),
        .CE(1'b0),
        .CINVCTRL(1'b0),
        .CLKIN(1'b0),
        .CNTVALUEIN(CONF_RX_DATA_DLY[4:0]),
        .DATAIN(1'b0),
        .IDATAIN(RX_DATA),
        .INC(1'b0),
        .ODATAIN(1'b0),
        .RST(CONF_RX_DATA_DLY_WR),
        .T(1'b1)

    );
`endif
   

wire Q1, Q2;
IDDR 
`ifndef COCOTB_SIM
    #(.DDR_CLK_EDGE("SAME_EDGE")) 
`endif
IDDR_RX (
    .Q1(Q1),
    .Q2(Q2),
    .C(RX_CLKX2),
    .CE(1'b1),
    .D(RX_DATA_DLY),
    .R(1'b0),
    .S(1'b0) 
);

wire RX_DATA_DDR;
assign RX_DATA_DDR = CONF_SAMPLING_EDGE ? Q1 : Q2;

receiver_logic receiver_logic 
(
    .RESET(RST),
    
    .WCLK(RX_CLKW),
    .FCLK(RX_CLKX2),
    .BUS_CLK(BUS_CLK),
    .RX_DATA(RX_DATA_DDR),
    
    .read(FIFO_READ),
    .data(FE_DATA),
    .empty(FIFO_EMPTY),
    .full(RX_FIFO_FULL),
    .rec_sync_ready(ready_rec),
    .lost_err_cnt(lost_err_cnt),
    .decoder_err_cnt(decoder_err_cnt),
    .fifo_size(fifo_size),
    .invert_rx_data(CONF_EN_INVERT_RX_DATA),
    .enable_rx(CONF_EN_RX),
    .FIFO_CLK(FIFO_CLK),
	.err_reset(CONF_ERROR_RESET)
);

endmodule
