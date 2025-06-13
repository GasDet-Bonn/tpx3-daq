

`include "gpio/gpio_core.v"
`include "gpio/gpio_sbus.v"

`include "spi/spi_core.v"
`include "../lib/extra/spi_sbus.v"
`include "spi/blk_mem_gen_8_to_1_2k.v"

`include "utils/cdc_pulse_sync.v"
`include "utils/CG_MOD_pos.v"

`include "utils/cdc_syncfifo.v"
`include "utils/generic_fifo.v"
`include "utils/cdc_reset_sync.v"

`include "pulse_gen/pulse_gen_core.v"
`include "../lib/extra/pulse_gen_sbus.v"

`include "../lib/tpx3_timestamp/timestamp_core.v"
`include "../lib/tpx3_timestamp/timestamp_sbus.v"

`include "rrp_arbiter/rrp_arbiter.v"

`include "utils/sbus_to_ip.v"
`include "utils/3_stage_synchronizer.v"

`include "../lib/tpx3_rx/tpx3_rx_sbus.v"
`include "../lib/tpx3_rx/tpx3_rx_core.v"
`include "../lib/tpx3_rx/receiver_logic.v"
`include "../lib/tpx3_rx/rec_sync.v"
`include "../lib/tpx3_rx/decode_8b10b.v"
`include "utils/flag_domain_crossing.v"

`define FW_VERSION 4

module tpx3_core (
        input  wire        BUS_CLK,
        input  wire        BUS_RST,
        input  wire [31:0] BUS_ADD,
        input  wire [7:0] BUS_DATA_IN,
        output wire [7:0] BUS_DATA_OUT,
        input  wire        BUS_RD,
        input  wire        BUS_WR,

        input wire ARB_READY_OUT,
        output wire ARB_WRITE_OUT,
        output wire [31:0] ARB_DATA_OUT,

        input wire CLK40, CLK32, CLK320, CLK640,
		  
		output wire        CH1,
		output wire        CH2,
		output wire        CH3,
		output wire        CH4,

        output wire        ExtTPulse,
        output wire        T0_Sync,
        output wire        EnableIn,
        output wire        DataIn,
        output wire        Shutter,
        output wire        Reset,
        output wire        ENPowerPulsing,
        output wire        Data_MUX_select,

        input  wire [7:0]  RX_DATA,

        output wire [7:0]  LED,
        output wire [7:0]  RX_READY


    );

    /////////////////////////
    // VERSION/BOARD READBACK
    ////////////////////////
    reg [7:0] BUS_DATA_OUT_REG;
    wire [7:0] VER_DATA_OUT;
    always @ (posedge BUS_CLK) begin
        if(BUS_RD) begin
            if(BUS_ADD == 0)
                BUS_DATA_OUT_REG <= `FW_VERSION;
            else if(BUS_ADD == 1)
                BUS_DATA_OUT_REG <= `BOARD_ID;
        end
    end
    
    reg READ_VER;
    always @ (posedge BUS_CLK)
        if(BUS_RD & BUS_ADD < 7)
            READ_VER <= 1;
        else
            READ_VER <= 0;

    assign VER_DATA_OUT = READ_VER ? BUS_DATA_OUT_REG : 8'h00;
    
    //////////////////////
    // MODULE ADREESSES //
    //////////////////////
    localparam GPIO_BASEADDR = 16'h1000;
    localparam GPIO_HIGHADDR = 16'h2000-1;

    localparam SPI_BASEADDR = 16'h2000;   //0x1000
    localparam SPI_HIGHADDR = 16'h3000-1; //0x300f

    localparam TIMESTAMP_BASEADDR = 16'h3000; 
    localparam TIMESTAMP_HIGHADDR = 16'h4000-1; 

    localparam TS_PULSE_BASEADDR = 16'h4000;
    localparam TS_PULSE_HIGHADDR = 16'h5000-1;
	 
	localparam TIMESTAMP2_BASEADDR = 16'h5000; 
    localparam TIMESTAMP2_HIGHADDR = 16'h6000-1; 

    localparam RX_BASEADDR = 16'h6000;
    localparam RX_HIGHADDR = 16'h8500-1;

    parameter RX_CH_NO = 24;
    parameter ABUSWIDTH = 16;

    wire [7:0] GPIO_DATA_OUT, SPI_DATA_OUT, PG_DATA_OUT, TS_DATA_OUT, TS2_DATA_OUT;
    wire [7:0] TPX3_DATA_OUT [7:0];

    wire [31:0] FIFO_DATA_OUT;
    wire [7:0]  TPX3_DATA_OUT_OR;
    assign TPX3_DATA_OUT_OR = TPX3_DATA_OUT[7] | TPX3_DATA_OUT[6] | TPX3_DATA_OUT[5] | TPX3_DATA_OUT[4] | TPX3_DATA_OUT[3] | TPX3_DATA_OUT[2] | TPX3_DATA_OUT[1] | TPX3_DATA_OUT[0] ;
    assign BUS_DATA_OUT = {VER_DATA_OUT | GPIO_DATA_OUT | SPI_DATA_OUT | TPX3_DATA_OUT_OR | PG_DATA_OUT | TS_DATA_OUT | TS2_DATA_OUT} ;

    /////////////
    // MODULES //
    /////////////
    wire [15:0] GPIO;
    gpio_sbus
    #(
        .BASEADDR    (GPIO_BASEADDR),
        .HIGHADDR    (GPIO_HIGHADDR),
        .ABUSWIDTH   (ABUSWIDTH    ),
        .IO_WIDTH    (16           ),
        .IO_DIRECTION(16'hffff     )
    ) gpio
    (
        .BUS_CLK (BUS_CLK       ),
        .BUS_RST (BUS_RST       ),
        .BUS_ADD (BUS_ADD      ),
        .BUS_DATA_IN  (BUS_DATA_IN[7:0]  ),
        .BUS_DATA_OUT (GPIO_DATA_OUT[7:0]),
        .BUS_RD  (BUS_RD       ),
        .BUS_WR  (BUS_WR       ),
        .IO      (GPIO          )
    );

    assign Reset = GPIO[0];
    //assign EnableIn = GPIO[1];
    assign Shutter = GPIO[2];
    assign ExtTPulse = GPIO[3];
    assign T0_Sync = GPIO[4];
    assign ENPowerPulsing = GPIO[5];
    assign Data_MUX_select = GPIO[6];
    assign LED = GPIO[15:8];
    wire CNT_FIFO_EN;
    assign CNT_FIFO_EN = GPIO[7];

    wire SCLK, SDI, SDO, SEN, SLD;
    spi
    #(
        .BASEADDR (SPI_BASEADDR),
        .HIGHADDR (SPI_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH   ),
        .MEM_BYTES(1024        )
    ) spi
    (
        .BUS_CLK  (BUS_CLK      ),
        .BUS_RST  (BUS_RST      ),
        .BUS_ADD  (BUS_ADD      ),
        .BUS_DATA_IN  (BUS_DATA_IN[7:0]),
        .BUS_DATA_OUT (SPI_DATA_OUT[7:0]),
        .BUS_RD   (BUS_RD       ),
        .BUS_WR   (BUS_WR       ),

        .SPI_CLK  (CLK40        ),
        .EXT_START(1'b0         ),

        .SCLK     (SCLK         ),
        .SDI      (SDI          ),
        .SDO      (SDO          ),
        .SEN      (SEN          ),
        .SLD      (SLD          )
    );
    assign DataIn = SDI;
    assign SDO = SDI;
    assign EnableIn = ~SEN;

    wire [7:0] TPX_FIFO_READ;
    wire [7:0] TPX_FIFO_EMPTY;
    wire [31:0] TPX_FIFO_DATA [7:0];
    wire [7:0] RX_READY_RX;
	 
	 reg BLINK_REG;
	 wire BLINK;
	 assign BLINK = BLINK_REG;
	 
	 reg [26:0] CNT_BLINK;
	 initial CNT_BLINK = 0;
	 always@(posedge BUS_CLK)
        if(CNT_BLINK == 100000000)
            CNT_BLINK <= 0;
		  else
		      CNT_BLINK <= CNT_BLINK + 1;
				
	 always@(posedge BUS_CLK)
	     if(CNT_BLINK < 50000000)
            BLINK_REG <= 0;
		  else
		      BLINK_REG <= 1;
    
    genvar ch;
    generate
        for (ch = 0; ch < 8; ch = ch + 1) begin: tpx3rx_gen
            if (ch < RX_CH_NO) begin
                tpx3_rx_sbus #(
                    .BASEADDR       (RX_BASEADDR + ch*32'h100),
                    .HIGHADDR       (RX_BASEADDR + 32'h100 + ch*32'h100 - 1),
                    .DATA_IDENTIFIER(         ch),
                    .ABUSWIDTH      (ABUSWIDTH  )
                ) tpx3_rx (

                    .RX_CLKX2            ( CLK320          ),
                    .RX_CLKW             ( CLK32           ),
                    .RX_DATA             ( RX_DATA[ch]     ),

                    .RX_READY            ( RX_READY_RX[ch]  ),
                    .RX_8B10B_DECODER_ERR(                 ),
                    .RX_FIFO_OVERFLOW_ERR(                 ),

                    .FIFO_READ           ( TPX_FIFO_READ[ch] ),
                    .FIFO_EMPTY          ( TPX_FIFO_EMPTY[ch] ),
                    .FIFO_DATA           ( TPX_FIFO_DATA[ch] ),

                    .RX_FIFO_FULL        (                 ),
                    .RX_ENABLED          (                 ),

                    .BUS_CLK             ( BUS_CLK         ),
                    .BUS_RST             ( BUS_RST         ),
                    .BUS_ADD             ( BUS_ADD         ),
                    .BUS_DATA_IN         ( BUS_DATA_IN[7:0]),
                    .BUS_DATA_OUT        ( TPX3_DATA_OUT[ch] ),
                    .BUS_RD              ( BUS_RD          ),
                    .BUS_WR              ( BUS_WR          )
                );
					 assign RX_READY[ch] = RX_READY_RX[ch];
            end else begin
                assign TPX_FIFO_EMPTY[ch] = 1;
					 assign RX_READY[ch] = BLINK;
            end

    end
    endgenerate
    
    wire PULSE;
    pulse_gen_sbus
    #(
        .BASEADDR(TS_PULSE_BASEADDR),
        .HIGHADDR(TS_PULSE_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH)
    ) ts_pulse_gen
    (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(BUS_RST),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA_IN(BUS_DATA_IN[7:0]),
        .BUS_DATA_OUT(PG_DATA_OUT),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),

        .PULSE_CLK(CLK40),
        .EXT_START(!T0_Sync),
        .PULSE(PULSE)
    );

    wire TS_FIFO_READ, TS_FIFO_EMPTY;
    wire [31:0] TS_FIFO_DATA;

    timestamp_sbus
    #(
        .BASEADDR(TIMESTAMP_BASEADDR),
        .HIGHADDR(TIMESTAMP_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH),
        .IDENTIFIER(7'b0100000)
    ) timestamp
    (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(T0_Sync),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA_IN(BUS_DATA_IN[7:0]),
        .BUS_DATA_OUT(TS_DATA_OUT),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),

        .CLK(CLK40),
        .DI(PULSE),
        //.EXT_TIMESTAMP(TIMESTAMP),
        //.TIMESTAMP_OUT(TIMESTAMP_OUT),
        .EXT_ENABLE(!T0_Sync),

        .FIFO_READ(TS_FIFO_READ),
        .FIFO_EMPTY(TS_FIFO_EMPTY),
        .FIFO_DATA(TS_FIFO_DATA)
    );
	 
    assign CH1 = 1'b0;
	assign CH2 = 1'b0;
	assign CH3 = 1'b0;
	assign CH4 = 1'b0;
	 
	wire TS2_FIFO_READ, TS2_FIFO_EMPTY;
    wire [31:0] TS2_FIFO_DATA;
	 
	reg shutter_timer = 1'b0;
	 
	reg last_shutter = 0;
    reg first_rising_edge = 0;

    always @(posedge CLK40) begin
        if (Shutter && !last_shutter) begin
            if (!first_rising_edge) begin
					 shutter_timer <= 1;
                first_rising_edge <= 1;
            end else begin
					 shutter_timer <= 0;
            end
        end else begin
				shutter_timer <= 0;
            first_rising_edge <= 0;
        end
        last_shutter <= Shutter;
    end

    timestamp_sbus
    #(
        .BASEADDR(TIMESTAMP2_BASEADDR),
        .HIGHADDR(TIMESTAMP2_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH),
        .IDENTIFIER(7'b0100001)
    ) timestamp2
    (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(T0_Sync),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA_IN(BUS_DATA_IN[7:0]),
        .BUS_DATA_OUT(TS2_DATA_OUT),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),

        .CLK(CLK640),
        .DI(shutter_timer),
        //.EXT_TIMESTAMP(TIMESTAMP),
        //.TIMESTAMP_OUT(TIMESTAMP_OUT),
        .EXT_ENABLE(!T0_Sync),

        .FIFO_READ(TS2_FIFO_READ),
        .FIFO_EMPTY(TS2_FIFO_EMPTY),
        .FIFO_DATA(TS2_FIFO_DATA)
    );

    wire CNT_FIFO_READ;
    reg [31:0] CNT_FIFO_DATA;
    always@(posedge BUS_CLK)
        if(BUS_RST)
            CNT_FIFO_DATA <= 0;
        else if(CNT_FIFO_READ)
            CNT_FIFO_DATA <= CNT_FIFO_DATA + 1;


    wire [10:0] READ_GRANT;

    rrp_arbiter #(
        .WIDTH(11)
    ) rrp_arbiter (
        .RST       (BUS_RST                         ),
        .CLK       (BUS_CLK                         ),

        .WRITE_REQ ({~TPX_FIFO_EMPTY, ~TS_FIFO_EMPTY, ~TS2_FIFO_EMPTY, CNT_FIFO_EN}),
        .HOLD_REQ  ({11'b0}                          ),
        .DATA_IN   ({TPX_FIFO_DATA[7], TPX_FIFO_DATA[6], TPX_FIFO_DATA[5], TPX_FIFO_DATA[4], TPX_FIFO_DATA[3], TPX_FIFO_DATA[2], TPX_FIFO_DATA[1], TPX_FIFO_DATA[0], TS_FIFO_DATA, TS2_FIFO_DATA, CNT_FIFO_DATA}),
        .READ_GRANT(READ_GRANT                      ),

        .READY_OUT (ARB_READY_OUT                   ),
        .WRITE_OUT (ARB_WRITE_OUT                   ),
        .DATA_OUT  (ARB_DATA_OUT                    )
    );

    assign CNT_FIFO_READ = READ_GRANT[0];
    assign TS2_FIFO_READ = READ_GRANT[1];
	assign TS_FIFO_READ = READ_GRANT[2];
    assign TPX_FIFO_READ = READ_GRANT[10:3];


endmodule
