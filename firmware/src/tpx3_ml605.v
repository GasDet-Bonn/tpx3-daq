

`timescale 1ns / 1ps

`define BOARD_ID 3 

`include "tpx3_sfp.v"

module tpx3_ml605 (

        input  wire       CLK200_P,
        input  wire       CLK200_N,

        output wire [7:0] LED,

        input  wire       SFP_RX_P,
        input  wire       SFP_RX_N,
        output wire       SFP_TX_P,
        output wire       SFP_TX_N,
        
        input  wire       SFP_CLK_P,
        input  wire       SFP_CLK_N,

        input wire TPX3_1_PLLOut_N,
        input wire TPX3_1_PLLOut_P,
        input wire TPX3_1_ClkOut_N,
        input wire TPX3_1_ClkOut_P,

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

        input wire [7:0] TPX3_1_DataOut_N, TPX3_1_DataOut_P,
        
        output wire [3:0] FMC_LED,
        //inout wire [4:0] FMC_LEMO,
    
        output wire Data_MUX_select,
        output wire [0:0] LINKUP,
        output wire PHY_RESET_N
        
    );

    
    wire RX_READY, ETH_STATUS_OK;
    
    tpx3_sfp tpx3_sfp (
        .CLK200_P               (CLK200_P               ),
        .CLK200_N               (CLK200_N               ),

        .SFP_RX_P               (SFP_RX_P               ),
        .SFP_RX_N               (SFP_RX_N               ),
        .SFP_TX_P               (SFP_TX_P               ),
        .SFP_TX_N               (SFP_TX_N               ),
        
        .SFP_CLK_P              (SFP_CLK_P              ),
        .SFP_CLK_N              (SFP_CLK_N              ),

        .TPX3_1_ClkInRefPLL_N   (TPX3_1_ClkInRefPLL_N   ),
        .TPX3_1_ClkInRefPLL_P   (TPX3_1_ClkInRefPLL_P   ),
        .TPX3_1_ClkIn40_N       (TPX3_1_ClkIn40_N       ),
        .TPX3_1_ClkIn40_P       (TPX3_1_ClkIn40_P       ),
        .TPX3_1_Reset_N         (TPX3_1_Reset_N         ),
        .TPX3_1_Reset_P         (TPX3_1_Reset_P         ),

        .TPX3_1_ExtTPulse_N     (TPX3_1_ExtTPulse_N     ),
        .TPX3_1_ExtTPulse_P     (TPX3_1_ExtTPulse_P     ),
        .TPX3_1_T0_Sync_N       (TPX3_1_T0_Sync_N       ),
        .TPX3_1_T0_Sync_P       (TPX3_1_T0_Sync_P       ),
        .TPX3_1_EnableIn_N      (TPX3_1_EnableIn_N      ),
        .TPX3_1_EnableIn_P      (TPX3_1_EnableIn_P      ),
        .TPX3_1_DataIn_N        (TPX3_1_DataIn_N        ),
        .TPX3_1_DataIn_P        (TPX3_1_DataIn_P        ),
        .TPX3_1_Shutter_N       (TPX3_1_Shutter_N       ),
        .TPX3_1_Shutter_P       (TPX3_1_Shutter_P       ),
        .TPX3_1_ENPowerPulsing_N(TPX3_1_ENPowerPulsing_N),
        .TPX3_1_ENPowerPulsing_P(TPX3_1_ENPowerPulsing_P),

        .TPX3_1_DataOut_N       (TPX3_1_DataOut_N       ),
        .TPX3_1_DataOut_P       (TPX3_1_DataOut_P       ),
        
        .Data_MUX_select(Data_MUX_select),
        .PHY_RESET_N(PHY_RESET_N),
        
        .ETH_STATUS_OK(ETH_STATUS_OK),
        .RX_READY(RX_READY)
        
        );

    assign FMC_LED =  {RX_READY, 3'b0};
    assign LINKUP[0] = RX_READY; 
    
    assign LED[0] = ETH_STATUS_OK;
    assign LED[1] = RX_READY;
    assign LED[7:2] = 0;
    
endmodule
