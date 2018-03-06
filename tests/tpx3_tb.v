
`timescale 1ns / 1ps 

`include "tpx3_core.v"

`include "utils/RAMB16_S1_S9_sim.v"
`include "utils/clock_divider.v"

module tb (
    input wire          BUS_CLK,
    input wire          BUS_RST,
    input wire  [31:0]  BUS_ADD,
    inout wire   [31:0] BUS_DATA,
    input wire          BUS_RD,
    input wire          BUS_WR,
    output wire         BUS_BYTE_ACCESS

);

wire TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn,  TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing;
wire Data_MUX_select;
wire [7:0] RX_DATA;

reg CLK40, CLK320;
wire CLK32;

initial CLK40 = 0; 
always #25 CLK40 =  ! CLK40; 

initial CLK320 = 0; 
always #3.125 CLK320 =  ! CLK320; 

clock_divider #(.DIVISOR(10)  ) clock_divisor_1 ( .CLK(CLK320), .RESET(1'b0), .CE(), .CLOCK(CLK32)   ); 

tpx3_core dut (
    .BUS_CLK(BUS_CLK),
    .BUS_RST(BUS_RST),
    .BUS_ADD(BUS_ADD),
    .BUS_DATA(BUS_DATA),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_BYTE_ACCESS(BUS_BYTE_ACCESS),
    
	.CLK40(CLK40),
    .CLK320(CLK320),
    .CLK32(CLK32),
    
    .ExtTPulse(TPX3_1_ExtTPulse), 
	.T0_Sync(TPX3_1_T0_Sync), 
	.EnableIn(TPX3_1_EnableIn), 
	.DataIn(TPX3_1_DataIn),  
	.Shutter(TPX3_1_Shutter), 
	.Reset(TPX3_1_Reset), 
	.ENPowerPulsing(TPX3_1_ENPowerPulsing),
    .Data_MUX_select(Data_MUX_select),
    .RX_DATA(RX_DATA)

);

//K.28.5
//localparam K285P = 10'b0011111010
//localparam K285N = 10'b1100000101


//'b10101111100';    % '10111100' -K28.5+ [700]
//'b01010000011';    % '10111100' +K28.5- [956]
//'b11101000110';    % '00000000' +D00.0+ [256]
//'b00010101110';    % '00000001' -D01.0- [1]
//'b11101010001';    % '00000001' +D01.0+ [257]
//'b00010111001';    % '00000000' -D00.0- [0]
//'b11101010010';    % '00000010' +D02.0+ [258]
//'b00010101101';    % '00000010' -D02.0- [2]
//'b10111101100';    % '11101100' -D12.7+ [236]
    
localparam K285P = 10'b0101111100;
localparam K285N = 10'b1010000011;
localparam D000P = 10'b1101000110;
localparam D010N = 10'b0010101110;
localparam D010P = 10'b1101010001;
localparam D000N = 10'b0010111001;
localparam D020P = 10'b1101010010;
localparam D020N = 10'b0010101101;
localparam D127P = 10'b0111101100;

localparam DSIZE = 66*10;

reg [DSIZE-1:0] enc_data;
initial enc_data = { {30{K285P,K285N}}, {D020P, D010P,D020P, D010P,D020P, D010P}};

always@(posedge CLK320)
    //enc_data[DSIZE-1:0] <= {enc_data[(DSIZE-2):0], enc_data[DSIZE-1]};
    enc_data[DSIZE-1:0] <= {enc_data[0], enc_data[(DSIZE-1):1]};

assign RX_DATA[0] = enc_data[0];

initial begin
    $dumpfile("/tmp/tpx3.vcd");
    $dumpvars(0);
end

endmodule
