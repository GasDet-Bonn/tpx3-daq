
`timescale 1ns / 1ps 

`include "tpx3_core.v"

`include "utils/RAMB16_S1_S9_sim.v"

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

reg CLK40;

initial CLK40 = 0; 
always #25  CLK40 =  ! CLK40; 
 
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
    .Data_MUX_select(Data_MUX_select)

);

initial begin
    $dumpfile("/tmp/tpx3.vcd");
    $dumpvars(0);
end

endmodule
