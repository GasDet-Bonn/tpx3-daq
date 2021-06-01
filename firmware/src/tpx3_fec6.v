

`timescale 1ns / 1ps

`define BOARD_ID 2 //"FECv6"

`define FECv6

`define host

`include "tpx3_sfp.v"

module tpx3_fec6 (

        input  wire       CLK200_P,
        input  wire       CLK200_N,

        output wire [1:0] LED,

        input  wire       SFP0_RX_P,
        input  wire       SFP0_RX_N,
        output wire       SFP0_TX_P,
        output wire       SFP0_TX_N,
        
        input  wire       SFP_CLK_P,
        input  wire       SFP_CLK_N,

        //input wire TPX3_1_PLLOut_N,
        //input wire TPX3_1_PLLOut_P,
        //input wire TPX3_1_ClkOut_N,
        //input wire TPX3_1_ClkOut_P,

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
		  `ifdef host
		      output wire       TPX3_1_T0_Sync_Ext1,
            output wire       TPX3_1_T0_Sync_Ext2,
            output wire       TPX3_1_Reset_Ext1,
            output wire       TPX3_1_Reset_Ext2,
	     `elsif client
		      input wire       TPX3_1_T0_Sync_Ext1,
				input wire       TPX3_1_T0_Sync_Ext2,
            input wire       TPX3_1_Reset_Ext1,
				input wire       TPX3_1_Reset_Ext2,
	     `endif

        input wire [7:0] TPX3_1_DataOut_N, TPX3_1_DataOut_P,
        
        output wire GOE,
        output wire CLKUWIRE,
        output wire LEUWIRE,
        output wire PLL_SYNC,
        output wire DATAUWIRE,
        output wire SELF_RSTN,
        output wire GBTSW,
        output wire SFP0_SDA,
        output wire SFP0_SCL,
		  
		  //TLU
		  input wire TLU_RJ45_TRIGGER_P,
		  input wire TLU_RJ45_TRIGGER_N,
		  input wire TLU_RJ45_RESET_P,
		  input wire TLU_RJ45_RESET_N,
		  output wire TLU_RJ45_BUSY_P,
		  output wire TLU_RJ45_BUSY_N,
		  output wire TLU_RJ45_CLK_P,
		  output wire TLU_RJ45_CLK_N

    );

    assign GOE = 1'b0;
    assign CLKUWIRE = 1'b0;
    assign LEUWIRE = 1'b0;
    assign PLL_SYNC = 1'b0;
    assign DATAUWIRE = 1'b0;
    assign SELF_RSTN = 1'b0;
    assign GBTSW = 1'b0;
    
    assign SFP0_SDA = 1'b1;
    assign SFP0_SCL = 1'b1;
    
    wire RX_READY, ETH_STATUS_OK;
    
    tpx3_sfp tpx3_sfp (
        .CLK200_P               (CLK200_P               ),
        .CLK200_N               (CLK200_N               ),

        .SFP_RX_P               (SFP0_RX_P               ),
        .SFP_RX_N               (SFP0_RX_N               ),
        .SFP_TX_P               (SFP0_TX_P               ),
        .SFP_TX_N               (SFP0_TX_N               ),
        
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
		  `ifdef host
		      .TPX3_1_T0_Sync_Ext1    (TPX3_1_T0_Sync_Ext1    ),
			   .TPX3_1_T0_Sync_Ext2    (TPX3_1_T0_Sync_Ext2    ),
		      .TPX3_1_Reset_Ext1      (TPX3_1_Reset_Ext1      ),
		      .TPX3_1_Reset_Ext2      (TPX3_1_Reset_Ext2      ),
	     `elsif client
		      .TPX3_1_T0_Sync_Ext1    (TPX3_1_T0_Sync_Ext1    ),
            .TPX3_1_Reset_Ext1      (TPX3_1_Reset_Ext1      ),
	     `endif

        .TPX3_1_DataOut_N       (TPX3_1_DataOut_N       ),
        .TPX3_1_DataOut_P       (TPX3_1_DataOut_P       ),
        
        .ETH_STATUS_OK(ETH_STATUS_OK),
        .RX_READY(RX_READY),
		  
		  //TLU
		  .TLU_RJ45_TRIGGER_P (TLU_RJ45_TRIGGER_P ),
		  .TLU_RJ45_TRIGGER_N (TLU_RJ45_TRIGGER_N ),
		  .TLU_RJ45_RESET_P   (TLU_RJ45_RESET_P   ),
		  .TLU_RJ45_RESET_N   (TLU_RJ45_RESET_N   ),
		  .TLU_RJ45_BUSY_P    (TLU_RJ45_BUSY_P    ),
		  .TLU_RJ45_BUSY_N    (TLU_RJ45_BUSY_N    ),
		  .TLU_RJ45_CLK_P     (TLU_RJ45_CLK_P     ),
		  .TLU_RJ45_CLK_N     (TLU_RJ45_CLK_N     )
        
        );

    assign LED[0] = ETH_STATUS_OK;
    assign LED[1] = RX_READY;
    
endmodule
