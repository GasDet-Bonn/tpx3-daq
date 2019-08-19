
`timescale 1ps / 1ps 

`define BOARD_ID 1

`include "tpx3_core.v"

`include "utils/RAMB16_S1_S9_sim.v"
`include "utils/clock_divider.v"
`include "utils/IDDR_sim.v"
`include "utils/clock_multiplier.v"

`default_nettype wire

/////////

`define TPX2_PRESYNC_WIDTH		48
`define TPX2_DATAINPERIPHERY_WIDTH	16

`define CORNER "MINIMUM"

`define SIMULATE_RTL
`define SIMULATE_PLL

`include "Periphery_XL_TR32_Prepared.v"

module tb (
    input wire          BUS_CLK,
    input wire          BUS_RST,
    input wire  [31:0]  BUS_ADD,
    inout wire   [31:0] BUS_DATA,
    input wire          BUS_RD,
    input wire          BUS_WR,
    output wire         BUS_BYTE_ACCESS

);

wire ClkOut_p;
    
wire TPX3_1_ExtTPulse, TPX3_1_T0_Sync, TPX3_1_EnableIn, TPX3_1_DataIn,  TPX3_1_Shutter, TPX3_1_Reset, TPX3_1_ENPowerPulsing;
wire Data_MUX_select;
wire [7:0] RX_DATA;

reg CLK40, CLK320;
wire CLK32;

initial CLK40 = 0; 
always #12.5ns CLK40 =  ! CLK40; 

//initial CLK320 = 0; 
//always #1.5625ns CLK320 =  ! CLK320; 


clock_multiplier #( .MULTIPLIER(2)  ) i_clock_multiplier( .CLK(ClkOut_p),                      .CLOCK(CLK320)  );
    
clock_divider #(.DIVISOR(10)  ) clock_divisor_1 ( .CLK(CLK320), .RESET(1'b0), .CE(), .CLOCK(CLK32)   ); 
wire [7:0] DataOut_p;

tpx3_core fpga (
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
    .RX_DATA(DataOut_p[0])

);

wire ExtTpulse_n, ExtTpulse_p;
wire T0_Sync_n, T0_Sync_p;
wire EnableIn_n, EnableIn_p;
wire DataIn_n, DataIn_p;
wire Shutter_n, Shutter_p;
wire Reset_n, Reset_p;
wire EnablePowerPulsing_n, EnablePowerPulsing_p;

wire ClkIn40_n, ClkIn40_p;
wire ClkInRefPLL_40_p, ClkInRefPLL_40_n;

assign ExtTpulse_n = !TPX3_1_ExtTPulse;
assign ExtTpulse_p = TPX3_1_ExtTPulse;

assign T0_Sync_n = !TPX3_1_T0_Sync;
assign T0_Sync_p = TPX3_1_T0_Sync;

//assign EnableIn_n = TPX3_1_EnableIn;
//assign EnableIn_p = !TPX3_1_EnableIn;

assign EnableIn_n = !TPX3_1_EnableIn;
assign EnableIn_p = TPX3_1_EnableIn;


assign DataIn_n = !TPX3_1_DataIn;
assign DataIn_p = TPX3_1_DataIn;

assign Shutter_n = !TPX3_1_Shutter;
assign Shutter_p = TPX3_1_Shutter;

assign Reset_n = !TPX3_1_Reset;
assign Reset_p = TPX3_1_Reset;

assign EnablePowerPulsing_n = !TPX3_1_ENPowerPulsing;
assign EnablePowerPulsing_p = TPX3_1_ENPowerPulsing;

assign ClkIn40_n = !CLK40;
assign ClkIn40_p = CLK40;

assign ClkInRefPLL_40_n = !CLK40;
assign ClkInRefPLL_40_p = CLK40;

Periphery_XL_TR32_Prepared tpx3(
     .A_Ibias_DiscS1cas_ON(A_Ibias_DiscS1cas_ON), 
     .A_Ibias_DiscS2cas_ON(A_Ibias_DiscS2cas_ON), 
     .A_Ibias_Ikrum(A_Ibias_Ikrum), 
     .A_Ibias_PixelDAC(A_Ibias_PixelDAC),
     .A_Ibias_PixelDACcas(A_Ibias_PixelDACcas), 
     .A_Ibias_Preampcas_ON(A_Ibias_Preampcas_ON), 
     .A_VPreamp_NCAS(A_VPreamp_NCAS), 
     .A_VTP_coarse(A_VTP_coarse), 
     .A_VTP_fine(A_VTP_fine), 
     .A_VThreshold(A_VThreshold), 
     .A_Vcntrl_To_Column(A_Vcntrl_To_Column), 
     .A_Vfbk(A_Vfbk), 
     .ClkOut_n(ClkOut_n), 
     .ClkOut_p(ClkOut_p),  
     .DACOut_out(DACOut_out), 
     .DataOut_n(DataOut_n), 
     .DataOut_p(DataOut_p), 
     .DiscS1PP_col(DiscS1PP_col), .DiscS2PP_col(DiscS2PP_col), 
     .PLLOut_n(PLLOut_n), .PLLOut_p(PLLOut_p), 
     .PreampPP_col(PreampPP_col),  
     .ClkIn40_n(ClkIn40_n), .ClkIn40_p(ClkIn40_p),
     .DataIn_n(DataIn_n), .DataIn_p(DataIn_p), 
     .EnableIn_p(EnableIn_p), 
     .EnablePowerPulsing_n(EnablePowerPulsing_n), 
     .EnablePowerPulsing_p(EnablePowerPulsing_p), 
     .EnableIn_n(EnableIn_n), .ExtDACIn(ExtDACIn), 
     .ExtTpulse_n(ExtTpulse_n), .ExtTpulse_p(ExtTpulse_p), 
     .Reset_n(Reset_n), .Reset_p(Reset_p), .SLVS_Term(SLVS_Term), 
     .Shutter_n(Shutter_n), .Shutter_p(Shutter_p), 
     .T0_Sync_n(T0_Sync_n), .T0_Sync_p(T0_Sync_p), 
     .ClkInRefPLL_40_p(ClkInRefPLL_40_p),.ClkInRefPLL_40_n(ClkInRefPLL_40_n)
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
//initial enc_data = { {33{K285P,K285N}}};
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
