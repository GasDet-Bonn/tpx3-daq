/**
 * ------------------------------------------------------------
 * Copyright (c) All rights reserved 
 * SiLab, Institute of Physics, University of Bonn
 * ------------------------------------------------------------
 */
`timescale 1ps/1ps
`default_nettype none

module receiver_logic
(
    input wire              RESET,
    input wire              WCLK,
    input wire              FCLK,
    input wire              BUS_CLK,
    input wire              RX_DATA,
    input wire              read,
    output wire  [24:0]     data,
    output wire             empty,
    output wire             full,
    output wire             rec_sync_ready,
    output reg  [7:0]       lost_err_cnt,
    output reg  [7:0]       decoder_err_cnt,
    output reg [15:0]       fifo_size,
    input wire              invert_rx_data,
    input wire              enable_rx,
    input wire              FIFO_CLK,
	input wire              err_reset
);

wire RESET_WCLK;
cdc_reset_sync rst_pulse_sync (.clk_in(BUS_CLK), .pulse_in(RESET), .clk_out(WCLK), .pulse_out(RESET_WCLK));

reg enable_rx_buf, enable_rx_buf2, enable_rx_wclk;
always @ (posedge WCLK)
begin
    enable_rx_buf <= enable_rx;
    enable_rx_buf2 <= enable_rx_buf;
    enable_rx_wclk <= enable_rx_buf2;
end

// 8b/10b record sync
wire [9:0] data_8b10b;
reg decoder_err;
rec_sync rec_sync_inst (
    .reset(RESET_WCLK),
    .datain(invert_rx_data ? ~RX_DATA : RX_DATA),
    .data(data_8b10b),
    .WCLK(WCLK),
    .FCLK(FCLK),
    .rec_sync_ready(rec_sync_ready),
    .decoder_err(decoder_err)
);

wire write_8b10b;
assign write_8b10b = rec_sync_ready & enable_rx_wclk;

reg [9:0] data_to_dec;
integer i;
always @ (*) begin
    for (i=0; i<10; i=i+1)
        data_to_dec[(10-1)-i] = data_8b10b[i];
end

reg dispin;
wire dispout;
always@(posedge WCLK) begin
    if(RESET_WCLK)
        dispin <= 1'b0;
    else// if(write_8b10b)
        dispin <= dispout;
    // if(RESET_WCLK)
        // dispin <= 1'b0;
    // else 
        // if(write_8b10b)
            // dispin <= ~dispout;
        // else
            // dispin <= dispin;
end

wire dec_k;
wire [7:0] dec_data;
wire code_err, disp_err;
decode_8b10b decode_8b10b_inst (
    .datain(data_to_dec),
    .dispin(dispin),
    .dataout({dec_k,dec_data}), // control character, data out
    .dispout(dispout),
    .code_err(code_err),
    .disp_err(disp_err)
);

always@(negedge WCLK) begin // avoid glitches from code_err or disp_err
    if(RESET_WCLK)
        decoder_err <= 1'b0;
    else
        decoder_err <= code_err | disp_err;
end
// Invalid symbols may or may not cause
// disparity errors depending on the symbol
// itself and the disparities of the previous and
// subsequent symbols. For this reason,
// DISP_ERR should always be combined
// with CODE_ERR to detect all errors.

always@(posedge WCLK) begin
    if(RESET_WCLK || err_reset)
        decoder_err_cnt <= 0;
    else
        if(decoder_err && write_8b10b && decoder_err_cnt != 8'hff)
            decoder_err_cnt <= decoder_err_cnt + 1;
        else 
            decoder_err_cnt <= decoder_err_cnt;
end

reg [2:0] byte_sel;
always@(posedge WCLK) begin
    if(RESET_WCLK || (write_8b10b && dec_k) || (write_8b10b && dec_k==0 && byte_sel==5))
        byte_sel <= 0;
    else if(write_8b10b)
        byte_sel <= byte_sel + 1;
    // if(RESET_WCLK || (write_8b10b && dec_k) || (write_8b10b && dec_k==0 && byte_sel==2))
        // byte_sel <= 0;
    // else
        // if(write_8b10b)
            // byte_sel <= byte_sel + 1;
        // else
            // byte_sel <= byte_sel;
end

reg [7:0] data_dec_in [5:0];
always@(posedge WCLK) begin
    if(RESET_WCLK)
        for (i=0; i<3; i=i+1)
            data_dec_in[i] <= 8'b0;
    else
        if(write_8b10b && dec_k==0)
            data_dec_in[byte_sel] <= dec_data;
end

reg [1:0] write_dec_in; 
always@(posedge WCLK) begin
    if(RESET_WCLK)
        write_dec_in <= 0;
    else
        if(write_8b10b && dec_k==0 && byte_sel==2)
            write_dec_in[0] <= 1;
        else if(write_8b10b && dec_k==0 && byte_sel==5)
            write_dec_in[1] <= 1;
        else begin
            write_dec_in <= 0;
        end
end

wire fifo_empty, fifo_full;

always@(posedge WCLK) begin
    if(RESET_WCLK || err_reset)
        lost_err_cnt <= 0;
    else
        if(fifo_full && (|write_dec_in) && lost_err_cnt != 8'hff)
            lost_err_cnt <= lost_err_cnt + 1;
        else
            lost_err_cnt <= lost_err_cnt;
end

wire [24:0] cdc_data_out;
wire [24:0] wdata;
assign wdata = write_dec_in[0] ? {1'b1, data_dec_in[0],data_dec_in[1],data_dec_in[2]} : {1'b0, data_dec_in[3],data_dec_in[4],data_dec_in[5]};

// generate delayed and long reset
reg [5:0] rst_cnt;
always@(posedge BUS_CLK) begin
    if(RESET)
        rst_cnt <= 5'd8;
    else if(rst_cnt != 5'd7)
        rst_cnt <= rst_cnt +1;
end
wire rst_long = rst_cnt[5];

//assign FIFO_CLK = BUS_CLK;

wire [10:0] fifo_size_int;
wire [24:0] fifo_data;

gerneric_fifo #(
    .DATA_SIZE(25),
    .DEPTH(1024*8*4)
) fifo (
    .clk(WCLK),
    .reset(RESET_WCLK),
    .write(|write_dec_in),
    .read(!full),
    .data_in(wdata),
    .full(fifo_full),
    .empty(fifo_empty),
    .data_out(fifo_data), 
    .size(fifo_size_int)
);

cdc_syncfifo #(
    .DSIZE(25),
    .ASIZE(4)
) cdc_syncfifo (
    .rdata(data),
    .wfull(full),
    .rempty(empty),
    .wdata(fifo_data),
    .winc(!fifo_empty),
    .wclk(WCLK),
    .wrst(RESET_WCLK),
    .rinc(read),
    .rclk(FIFO_CLK),
    .rrst(rst_long)
);

always @(posedge FIFO_CLK) begin
    fifo_size <= {5'b0, fifo_size_int};
end

endmodule
