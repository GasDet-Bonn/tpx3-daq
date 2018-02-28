

`include "utils/bus_to_ip.v"
 
`include "gpio/gpio.v"

`include "spi/spi.v"
`include "spi/spi_core.v"
`include "spi/blk_mem_gen_8_to_1_2k.v"
`include "utils/cdc_pulse_sync.v"
`include "utils/CG_MOD_pos.v"

module tpx3_core (
    input wire          BUS_CLK,
    input wire          BUS_RST,
    input wire  [31:0]  BUS_ADD,
    inout wire   [31:0] BUS_DATA,
    input wire          BUS_RD,
    input wire          BUS_WR,
    output wire         BUS_BYTE_ACCESS,

    input wire CLK40,
	 
	output wire ExtTPulse, 
	output wire T0_Sync, 
	output wire EnableIn, 
	output wire DataIn,  
	output wire Shutter, 
	output wire Reset, 
	output wire ENPowerPulsing,
    output wire Data_MUX_select,
    
    output wire [7:0] LED
    
);

    // MODULE ADREESSES //
    localparam GPIO_BASEADDR = 32'h1000;
    localparam GPIO_HIGHADDR = 32'h2000-1;
    
    localparam SPI_BASEADDR = 32'h2000; //0x1000
    localparam SPI_HIGHADDR = 32'h3000-1;   //0x300f
    
    //localparam FIFO_BASEADDR = 32'h8000;
    //localparam FIFO_HIGHADDR = 32'h9000-1;
    
    //localparam FIFO_BASEADDR_DATA = 32'h8000_0000;
    //localparam FIFO_HIGHADDR_DATA = 32'h9000_0000;
    
    localparam ABUSWIDTH = 32;
    assign BUS_BYTE_ACCESS = BUS_ADD < 32'h8000_0000 ? 1'b1 : 1'b0;
    

    /////////////
    // MODULES //
    /////////////
    wire [15:0] GPIO;
    gpio
    #(
        .BASEADDR(GPIO_BASEADDR),
        .HIGHADDR(GPIO_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH),
        .IO_WIDTH(16),
        .IO_DIRECTION(16'hffff)
    ) gpio
    (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(BUS_RST),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA(BUS_DATA[7:0]),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),
        .IO(GPIO)
    );
    
	 
	assign Reset = GPIO[0];
	assign EnableIn = GPIO[1];
	assign Shutter = GPIO[2];
	assign ExtTPulse = GPIO[3];
	assign T0_Sync = GPIO[4]; 
	assign ENPowerPulsing = GPIO[5];
   assign Data_MUX_select = GPIO[6];
	assign LED = GPIO[15:8];
    
    wire SCLK, SDI, SDO, SEN, SLD;
    
    spi
    #(
        .BASEADDR(SPI_BASEADDR),
        .HIGHADDR(SPI_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH),
        .MEM_BYTES(1024) 
    )  i_spi
    (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(BUS_RST),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA(BUS_DATA[7:0]),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),
        
        .SPI_CLK(CLK40),
        .EXT_START(1'b0),
        
        .SCLK(SCLK),
        .SDI(SDI),
        .SDO(SDO),
        .SEN(SEN),
        .SLD(SLD)
    );
    assign DataIn = SDI;
    assign SDO = SDI;

endmodule
