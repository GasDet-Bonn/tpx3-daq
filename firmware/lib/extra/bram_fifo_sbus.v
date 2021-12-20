/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */
`default_nettype none

module bram_fifo_sbus #(
    parameter   BASEADDR = 32'h0000,
    parameter   HIGHADDR = 32'h0000,
    parameter   ABUSWIDTH = 32,

    parameter   BASEADDR_DATA = 32'h0000,
    parameter   HIGHADDR_DATA = 32'h0000,

    parameter   DEPTH = 32'h8000*8,

    parameter   FIFO_ALMOST_FULL_THRESHOLD = 95, // in percent
    parameter   FIFO_ALMOST_EMPTY_THRESHOLD = 5 // in percent
) (

    input wire                  BUS_CLK,
    input wire                  BUS_RST,
    input wire [ABUSWIDTH-1:0]  BUS_ADD,
    input wire [31:0]           BUS_DATA_IN,
    output wire [31:0]          BUS_DATA_OUT,
    input wire                  BUS_RD,
    input wire                  BUS_WR,

    output wire                 FIFO_READ_NEXT_OUT,
    input wire                  FIFO_EMPTY_IN,
    input wire [31:0]           FIFO_DATA,

    output wire                 FIFO_NOT_EMPTY,
    output wire                 FIFO_FULL,
    output wire                 FIFO_NEAR_FULL,
    output wire                 FIFO_READ_ERROR
);

wire IP_RD, IP_WR;
wire [ABUSWIDTH-1:0] IP_ADD;
wire [7:0] IP_DATA_IN;
wire [7:0] IP_DATA_OUT, BUS_DATA_OUT_CONTROL;

sbus_to_ip #(
    .BASEADDR(BASEADDR),
    .HIGHADDR(HIGHADDR),
    .ABUSWIDTH(ABUSWIDTH)
) sbus_to_ip_control (
    .BUS_CLK(BUS_CLK),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA_IN(BUS_DATA_IN[7:0]),
    .BUS_DATA_OUT(BUS_DATA_OUT_CONTROL),
    .IP_RD(IP_RD),
    .IP_WR(IP_WR),
    .IP_ADD(IP_ADD),
    .IP_DATA_IN(IP_DATA_IN),
    .IP_DATA_OUT(IP_DATA_OUT)
);

wire IP_RD_DATA, IP_WR_DATA;
wire [31:0] IP_DATA_OUT_DATA, IP_DATA_IN_DATA, BUS_DATA_OUT_DATA;

sbus_to_ip #(
    .BASEADDR(BASEADDR_DATA),
    .HIGHADDR(HIGHADDR_DATA) ,
    .ABUSWIDTH(ABUSWIDTH),
    .DBUSWIDTH(32)
) sbus_to_ip_data (
    .BUS_CLK(BUS_CLK),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_ADD(BUS_ADD),


    .BUS_DATA_IN(BUS_DATA_IN),
    .BUS_DATA_OUT(BUS_DATA_OUT_DATA),

    .IP_RD(IP_RD_DATA),
    .IP_WR(IP_WR_DATA),
    .IP_ADD(),
    .IP_DATA_IN(IP_DATA_IN_DATA),
    .IP_DATA_OUT(IP_DATA_OUT_DATA)
);

assign BUS_DATA_OUT = {24'b0,BUS_DATA_OUT_CONTROL} | BUS_DATA_OUT_DATA;

bram_fifo_core #(
    .DEPTH(DEPTH),
    .FIFO_ALMOST_FULL_THRESHOLD(FIFO_ALMOST_FULL_THRESHOLD),
    .FIFO_ALMOST_EMPTY_THRESHOLD(FIFO_ALMOST_EMPTY_THRESHOLD),
    .ABUSWIDTH(ABUSWIDTH)
) i_bram_fifo (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(IP_ADD),

    .BUS_RD(IP_RD),
    .BUS_WR(IP_WR),

    .BUS_DATA_IN(IP_DATA_IN),
    .BUS_DATA_OUT(IP_DATA_OUT),

    .BUS_RD_DATA(IP_RD_DATA),
    .BUS_WR_DATA(IP_WR_DATA),

    .BUS_DATA_IN_DATA(IP_DATA_IN_DATA),
    .BUS_DATA_OUT_DATA(IP_DATA_OUT_DATA),

    .FIFO_READ_NEXT_OUT(FIFO_READ_NEXT_OUT),
    .FIFO_EMPTY_IN(FIFO_EMPTY_IN),
    .FIFO_DATA(FIFO_DATA),

    .FIFO_NOT_EMPTY(FIFO_NOT_EMPTY),
    .FIFO_FULL(FIFO_FULL),
    .FIFO_NEAR_FULL(FIFO_NEAR_FULL),
    .FIFO_READ_ERROR(FIFO_READ_ERROR)
);

endmodule
