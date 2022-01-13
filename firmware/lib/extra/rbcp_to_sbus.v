/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */
`timescale 1ps/1ps
`default_nettype none


module rbcp_to_bus (
    input wire BUS_RST,
    input wire BUS_CLK,

    input wire RBCP_ACT,
    input wire [31:0] RBCP_ADDR,
    input wire [7:0] RBCP_WD,
    input wire RBCP_WE,
    input wire RBCP_RE,
    output reg RBCP_ACK,
    output wire [7:0] RBCP_RD,

    output wire          BUS_WR,
    output wire          BUS_RD,
    output wire [31:0]   BUS_ADD,

    output wire  [7:0]  BUS_DATA_IN,
    input wire   [7:0]  BUS_DATA_OUT

    //FUTURE
    //input wire BUS_ACK_REQ
    //input wire BUS_ACK
);

always @(posedge BUS_CLK) begin
    if(BUS_RST)
        RBCP_ACK <= 0;
    else begin
        if (RBCP_ACK == 1)
            RBCP_ACK <= 0;
        else
            RBCP_ACK <= RBCP_WE | RBCP_RE;
    end
end

assign BUS_ADD = RBCP_ADDR;
assign BUS_WR = RBCP_WE & RBCP_ACT;
assign BUS_RD = RBCP_RE & RBCP_ACT;

assign BUS_DATA_IN = RBCP_WD[7:0];
assign RBCP_RD[7:0] = BUS_DATA_OUT;

endmodule
