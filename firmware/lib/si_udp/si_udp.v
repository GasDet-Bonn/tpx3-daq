/*

Copyright (c) 2014-2017 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

*/

// Language: Verilog 2001

`timescale 1ns / 1ps

module si_udp
#(
    parameter                   MAC = 48'h02_00_00_00_00_00,
    parameter                   IP =  {8'd192, 8'd168, 8'd1,   8'd128},
    parameter                   PORT =  16'd1234
)
(
    /*
     * Clock: 125MHz
     * Synchronous reset
     */
    input  wire       clk_125mhz,
    input  wire       rst_125mhz,

    /*
     * Ethernet: 1000BASE-T SGMII
     */
    input  wire       phy_gmii_clk,
    input  wire       phy_gmii_rst,
    input  wire       phy_gmii_clk_en,
    input  wire [7:0] phy_gmii_rxd,
    input  wire       phy_gmii_rx_dv,
    input  wire       phy_gmii_rx_er,
    output wire [7:0] phy_gmii_txd,
    output wire       phy_gmii_tx_en,
    output wire       phy_gmii_tx_er,
    output wire       phy_reset_n,
    
     /*
     * Basil Bus
     */
    output wire          BUS_CLK,
    output wire          BUS_RST,
    output reg   [31:0]  BUS_ADD,
    inout wire   [31:0]  BUS_DATA,
    output wire          BUS_RD,
    output wire          BUS_WR,
    input wire           BUS_BYTE_ACCESS
    
);

// AXI between MAC and Ethernet modules
wire [7:0] rx_axis_tdata;
wire rx_axis_tvalid;
wire rx_axis_tready;
wire rx_axis_tlast;
wire rx_axis_tuser;

wire [7:0] tx_axis_tdata;
wire tx_axis_tvalid;
wire tx_axis_tready;
wire tx_axis_tlast;
wire tx_axis_tuser;

// Ethernet frame between Ethernet modules and UDP stack
wire rx_eth_hdr_ready;
wire rx_eth_hdr_valid;
wire [47:0] rx_eth_dest_mac;
wire [47:0] rx_eth_src_mac;
wire [15:0] rx_eth_type;
wire [7:0] rx_eth_payload_tdata;
wire rx_eth_payload_tvalid;
wire rx_eth_payload_tready;
wire rx_eth_payload_tlast;
wire rx_eth_payload_tuser;

wire tx_eth_hdr_ready;
wire tx_eth_hdr_valid;
wire [47:0] tx_eth_dest_mac;
wire [47:0] tx_eth_src_mac;
wire [15:0] tx_eth_type;
wire [7:0] tx_eth_payload_tdata;
wire tx_eth_payload_tvalid;
wire tx_eth_payload_tready;
wire tx_eth_payload_tlast;
wire tx_eth_payload_tuser;

// IP frame connections
wire rx_ip_hdr_valid;
wire rx_ip_hdr_ready;
wire [47:0] rx_ip_eth_dest_mac;
wire [47:0] rx_ip_eth_src_mac;
wire [15:0] rx_ip_eth_type;
wire [3:0] rx_ip_version;
wire [3:0] rx_ip_ihl;
wire [5:0] rx_ip_dscp;
wire [1:0] rx_ip_ecn;
wire [15:0] rx_ip_length;
wire [15:0] rx_ip_identification;
wire [2:0] rx_ip_flags;
wire [12:0] rx_ip_fragment_offset;
wire [7:0] rx_ip_ttl;
wire [7:0] rx_ip_protocol;
wire [15:0] rx_ip_header_checksum;
wire [31:0] rx_ip_source_ip;
wire [31:0] rx_ip_dest_ip;
wire [7:0] rx_ip_payload_tdata;
wire rx_ip_payload_tvalid;
wire rx_ip_payload_tready;
wire rx_ip_payload_tlast;
wire rx_ip_payload_tuser;

wire tx_ip_hdr_valid;
wire tx_ip_hdr_ready;
wire [5:0] tx_ip_dscp;
wire [1:0] tx_ip_ecn;
wire [15:0] tx_ip_length;
wire [7:0] tx_ip_ttl;
wire [7:0] tx_ip_protocol;
wire [31:0] tx_ip_source_ip;
wire [31:0] tx_ip_dest_ip;
wire [7:0] tx_ip_payload_tdata;
wire tx_ip_payload_tvalid;
wire tx_ip_payload_tready;
wire tx_ip_payload_tlast;
wire tx_ip_payload_tuser;

// UDP frame connections
wire rx_udp_hdr_valid;
wire rx_udp_hdr_ready;
wire [47:0] rx_udp_eth_dest_mac;
wire [47:0] rx_udp_eth_src_mac;
wire [15:0] rx_udp_eth_type;
wire [3:0] rx_udp_ip_version;
wire [3:0] rx_udp_ip_ihl;
wire [5:0] rx_udp_ip_dscp;
wire [1:0] rx_udp_ip_ecn;
wire [15:0] rx_udp_ip_length;
wire [15:0] rx_udp_ip_identification;
wire [2:0] rx_udp_ip_flags;
wire [12:0] rx_udp_ip_fragment_offset;
wire [7:0] rx_udp_ip_ttl;
wire [7:0] rx_udp_ip_protocol;
wire [15:0] rx_udp_ip_header_checksum;
wire [31:0] rx_udp_ip_source_ip;
wire [31:0] rx_udp_ip_dest_ip;
wire [15:0] rx_udp_source_port;
wire [15:0] rx_udp_dest_port;
wire [15:0] rx_udp_length;
wire [15:0] rx_udp_checksum;
wire [7:0] rx_udp_payload_tdata;
wire rx_udp_payload_tvalid;
wire rx_udp_payload_tready;
wire rx_udp_payload_tlast;
wire rx_udp_payload_tuser;

wire tx_udp_hdr_valid;
wire tx_udp_hdr_ready;
wire [5:0] tx_udp_ip_dscp;
wire [1:0] tx_udp_ip_ecn;
wire [7:0] tx_udp_ip_ttl;
wire [31:0] tx_udp_ip_source_ip;
wire [31:0] tx_udp_ip_dest_ip;
wire [15:0] tx_udp_source_port;
wire [15:0] tx_udp_dest_port;
wire [15:0] tx_udp_length;
wire [15:0] tx_udp_checksum;
wire [7:0] tx_udp_payload_tdata;
wire tx_udp_payload_tvalid;
wire tx_udp_payload_tready;
wire tx_udp_payload_tlast;
wire tx_udp_payload_tuser;

// Configuration
wire [47:0] local_mac   = MAC ; //48'h02_00_00_00_00_00;
wire [31:0] local_ip    = IP; //{8'd192, 8'd168, 8'd1,   8'd128};
wire [31:0] gateway_ip  = {8'd0, 8'd0, 8'd0,   8'd0}; //{8'd192, 8'd168, 8'd1,   8'd1};
wire [31:0] subnet_mask = {8'd0, 8'd0, 8'd0,   8'd0};

// IP ports not used
assign rx_ip_hdr_ready = 1;
assign rx_ip_payload_tready = 1;

assign tx_ip_hdr_valid = 0;
assign tx_ip_dscp = 0;
assign tx_ip_ecn = 0;
assign tx_ip_length = 0;
assign tx_ip_ttl = 0;
assign tx_ip_protocol = 0;
assign tx_ip_source_ip = 0;
assign tx_ip_dest_ip = 0;
assign tx_ip_payload_tdata = 0;
assign tx_ip_payload_tvalid = 0;
assign tx_ip_payload_tlast = 0;
assign tx_ip_payload_tuser = 0;

// Loop back UDP
wire match_cond = (rx_udp_dest_port == PORT) & (rx_udp_ip_dest_ip == local_ip);// & (rx_udp_eth_dest_mac == local_mac);

assign rx_udp_hdr_ready =  1;
assign tx_udp_ip_dscp = 0;
assign tx_udp_ip_ecn = 0;
assign tx_udp_ip_ttl = 64;
assign tx_udp_ip_source_ip = local_ip;
assign tx_udp_ip_dest_ip = rx_udp_ip_source_ip;
assign tx_udp_source_port = rx_udp_dest_port;
assign tx_udp_dest_port = rx_udp_source_port;
//assign tx_udp_length = rx_udp_length;
assign tx_udp_checksum = 0;

//
//
//TODO: check VERSION, ip, mac, mask on 0xffffffff?  
//TODO: timeouts
//

reg [31:0] req_cnt;
reg [7:0] siudp_cmd;
reg [31:0] siudp_addr, siudp_addr_last; 
wire [31:0] addr_tmp;
reg [31:0] siudp_size;
reg siudp_wr_active, siudp_rd_active;
reg [31:0] siudp_addr_avtive;
reg [31:0] siudp_data_rd_cnt;
reg [31:0] siudp_data_wr_cnt;
reg [7:0] siudp_confirm_data_out;

wire siudp_req;
wire siudp_pck_last, siudp_last, siudp_confirm_last;
reg [1:0] siudp_confirm_cnt;

localparam NOP_STATE = 0, WAIT_FOR_HEADER_RD_STATE = 1, DATA_RD_STATE = 2, DATA_WR_STATE=3, WAIT_FOR_HEADER_WR_STATE = 4, WR_CONFIRM_STATE = 5;
integer state, next_state;

always @(posedge clk_125mhz) 
     if (rst_125mhz)
        state <= NOP_STATE;
     else
        state <= next_state;
     
always@(*) begin
    next_state = state;
    case (state)
        NOP_STATE: 
            if (siudp_req & match_cond) begin
                if(siudp_cmd == SIUDP_RD_CMD)
                    next_state = WAIT_FOR_HEADER_RD_STATE;
                else if(siudp_cmd == SIUDP_WR_CMD)
                    next_state = DATA_WR_STATE;
                else
                    next_state = NOP_STATE;
            end
        WAIT_FOR_HEADER_RD_STATE: 
            if (tx_udp_hdr_ready)
                    next_state = DATA_RD_STATE;
        DATA_RD_STATE: 
            if (siudp_last & tx_udp_payload_tvalid)
                 next_state = NOP_STATE;
            else if (siudp_pck_last & tx_udp_payload_tvalid)
                next_state = WAIT_FOR_HEADER_RD_STATE;
        DATA_WR_STATE:
            if (rx_udp_payload_tlast & rx_udp_payload_tvalid)
                next_state = WAIT_FOR_HEADER_WR_STATE;
        WAIT_FOR_HEADER_WR_STATE:
            if (tx_udp_hdr_ready)
                next_state = WR_CONFIRM_STATE;
        WR_CONFIRM_STATE:
            if(siudp_confirm_last & tx_udp_payload_tready)
                next_state = NOP_STATE;
    endcase 
end

assign siudp_pck_last = (siudp_data_rd_cnt != 0 & siudp_data_rd_cnt % 1476 == 0);
assign siudp_last = (siudp_data_rd_cnt == siudp_size );
assign siudp_confirm_last = (state == WR_CONFIRM_STATE) & (siudp_confirm_cnt== 3);

assign siudp_req = (req_cnt == 8) & rx_udp_payload_tvalid;

wire read_data = (state == DATA_RD_STATE) & tx_udp_payload_tready & !siudp_last;

assign BUS_CLK = clk_125mhz;
assign BUS_RST = rst_125mhz;
assign BUS_RD = BUS_BYTE_ACCESS ? read_data : read_data & BUS_ADD[1:0] == 0;
assign BUS_WR = (state == DATA_WR_STATE) & rx_udp_payload_tvalid;
assign BUS_DATA = BUS_WR ? rx_udp_payload_tdata : 32'bz;

always@(posedge clk_125mhz)
    if(state == NOP_STATE & siudp_req & match_cond)
        BUS_ADD <= {siudp_addr[31:8], rx_udp_payload_tdata};
    else if(BUS_WR)
        BUS_ADD <= BUS_ADD +1;
    else if(read_data)
        BUS_ADD <= BUS_ADD +1;

always@(*) begin
    case (siudp_confirm_cnt)
        0: siudp_confirm_data_out = siudp_data_wr_cnt[31:24];
        1: siudp_confirm_data_out = siudp_data_wr_cnt[23:16];
        2: siudp_confirm_data_out = siudp_data_wr_cnt[15:8];
        3: siudp_confirm_data_out = siudp_data_wr_cnt[7:0];
    endcase 
end


always@(posedge clk_125mhz)
    if(state == NOP_STATE)
        siudp_confirm_cnt <= 0;
    else if(state == WR_CONFIRM_STATE & tx_udp_payload_tready)
        siudp_confirm_cnt <= siudp_confirm_cnt + 1;
   
always@(posedge clk_125mhz)
    if(state == NOP_STATE)
        siudp_data_wr_cnt <= 0;
    else if(BUS_WR)
        siudp_data_wr_cnt <= siudp_data_wr_cnt + 1;
        

localparam SIUDP_RD_CMD = 8'h01;
localparam SIUDP_WR_CMD = 8'h02;

always @(posedge clk_125mhz) begin
    if (rst_125mhz | (rx_udp_payload_tvalid & rx_udp_payload_tlast))
        req_cnt <= 0;
    else if(rx_udp_payload_tvalid & match_cond)
        req_cnt <= req_cnt +1;
end

always @(posedge clk_125mhz) begin
    if (state == NOP_STATE)
        siudp_data_rd_cnt <= 0;
    else if(read_data)
        siudp_data_rd_cnt <= siudp_data_rd_cnt +1;
end

always @(posedge clk_125mhz) begin
    if (rst_125mhz )
        siudp_cmd <= 0;
    else if(rx_udp_payload_tvalid & match_cond) begin
        case (req_cnt)
            0: siudp_cmd <= rx_udp_payload_tdata;
            1: siudp_size[31:24] <= rx_udp_payload_tdata;
            2: siudp_size[23:16] <= rx_udp_payload_tdata;
            3: siudp_size[15:8] <= rx_udp_payload_tdata;
            4: siudp_size[7:0] <= rx_udp_payload_tdata;
        endcase 
    end
end

always @(posedge clk_125mhz) begin
    if(rx_udp_payload_tvalid & req_cnt <= 8 & match_cond) begin
        case (req_cnt)
            0: siudp_addr <= 0;
            5: siudp_addr[31:24] <= rx_udp_payload_tdata;
            6: siudp_addr[23:16] <= rx_udp_payload_tdata;
            7: siudp_addr[15:8] <= rx_udp_payload_tdata;
            8: siudp_addr[7:0] <= rx_udp_payload_tdata;	
        endcase 
    end
end

reg [31:0] siudp_left_size;
always@(posedge clk_125mhz)
    if(next_state == WAIT_FOR_HEADER_RD_STATE)
        siudp_left_size <= siudp_size - siudp_data_rd_cnt;

reg bus_read_reg;
always@(posedge clk_125mhz)
    bus_read_reg <= BUS_RD;
        
reg [7:0] data_bus_reg [7:0];
always@(posedge clk_125mhz)
    if(bus_read_reg)
        {data_bus_reg[3],data_bus_reg[2],data_bus_reg[1], data_bus_reg[0]} <= BUS_DATA;
       
reg [31:0] addr_bus_reg;
always@(posedge clk_125mhz)
    if(read_data)
        addr_bus_reg <= BUS_ADD;
       
reg [7:0] data_to_read;
always@(*) begin
    if(BUS_BYTE_ACCESS==0) begin
        if(addr_bus_reg[1:0] == 0)
            data_to_read = BUS_DATA[7:0];
        else
            data_to_read = data_bus_reg[addr_bus_reg[1:0]];
    end
    else
        data_to_read = BUS_DATA[7:0];
end
       
assign tx_udp_payload_tlast = tx_udp_payload_tready & (siudp_pck_last | siudp_last | siudp_confirm_last);
assign tx_udp_payload_tvalid = tx_udp_payload_tready & (siudp_data_rd_cnt > 0 | (state == WR_CONFIRM_STATE) ); 
assign tx_udp_payload_tuser = 0;
assign tx_udp_length = (siudp_cmd == SIUDP_RD_CMD) ? (siudp_left_size > 1476 ? 1476 : siudp_left_size) : 16'd4;
assign tx_udp_payload_tdata = (state == WR_CONFIRM_STATE) ? siudp_confirm_data_out : data_to_read ; //siudp_size;//siudp_addr;

assign rx_udp_payload_tready = rx_udp_payload_tvalid;
assign rx_udp_payload_tuser = 0;

always @(posedge clk_125mhz) begin
    if (rst_125mhz | (tx_udp_payload_tlast & tx_udp_payload_tready))
        siudp_rd_active <= 0;
    else if(tx_udp_payload_tready & siudp_cmd == SIUDP_RD_CMD)
        siudp_rd_active <= 1;
    //else if(siudp_cmd == SIUDP_RD_CMD && siudp_addr
end


//check check port and ip ? and header_rady
// wait for it + time-out?
assign tx_udp_hdr_valid = (state == WAIT_FOR_HEADER_RD_STATE) || (state == WAIT_FOR_HEADER_WR_STATE); // & rx_udp_hdr_valid
//wait for tx_udp_hdr_valid
 
always @(posedge clk_125mhz) begin
    if (rst_125mhz | (tx_udp_payload_tlast & tx_udp_payload_tready))
        siudp_wr_active <= 0;
    else if(tx_udp_payload_tready & siudp_cmd == SIUDP_WR_CMD)
        siudp_wr_active <= 1;
end



assign phy_reset_n = ~rst_125mhz;


wire rx_error_bad_frame;
wire rx_error_bad_fcs;

eth_mac_1g_fifo #(
    .ENABLE_PADDING(1),
    .MIN_FRAME_LENGTH(64),
    .TX_FIFO_ADDR_WIDTH(12),
    .RX_FIFO_ADDR_WIDTH(12)
)
eth_mac_inst (
    .rx_clk(phy_gmii_clk),
    .rx_rst(phy_gmii_rst),
    .tx_clk(phy_gmii_clk),
    .tx_rst(phy_gmii_rst),
    .logic_clk(clk_125mhz),
    .logic_rst(rst_125mhz),

    .tx_axis_tdata(tx_axis_tdata),
    .tx_axis_tvalid(tx_axis_tvalid),
    .tx_axis_tready(tx_axis_tready),
    .tx_axis_tlast(tx_axis_tlast),
    .tx_axis_tuser(tx_axis_tuser),

    .rx_axis_tdata(rx_axis_tdata),
    .rx_axis_tvalid(rx_axis_tvalid),
    .rx_axis_tready(rx_axis_tready),
    .rx_axis_tlast(rx_axis_tlast),
    .rx_axis_tuser(rx_axis_tuser),

    .gmii_rxd(phy_gmii_rxd),
    .gmii_rx_dv(phy_gmii_rx_dv),
    .gmii_rx_er(phy_gmii_rx_er),
    .gmii_txd(phy_gmii_txd),
    .gmii_tx_en(phy_gmii_tx_en),
    .gmii_tx_er(phy_gmii_tx_er),

    .rx_clk_enable(phy_gmii_clk_en),
    .tx_clk_enable(phy_gmii_clk_en),
    .rx_mii_select(1'b0),
    .tx_mii_select(1'b0),

    .tx_fifo_overflow(),
    .tx_fifo_bad_frame(),
    .tx_fifo_good_frame(),
    .rx_error_bad_frame(rx_error_bad_frame),
    .rx_error_bad_fcs(rx_error_bad_fcs),
    .rx_fifo_overflow(),
    .rx_fifo_bad_frame(),
    .rx_fifo_good_frame(),

    .ifg_delay(12)
);

eth_axis_rx
eth_axis_rx_inst (
    .clk(clk_125mhz),
    .rst(rst_125mhz),
    // AXI input
    .input_axis_tdata(rx_axis_tdata),
    .input_axis_tvalid(rx_axis_tvalid),
    .input_axis_tready(rx_axis_tready),
    .input_axis_tlast(rx_axis_tlast),
    .input_axis_tuser(rx_axis_tuser),
    // Ethernet frame output
    .output_eth_hdr_valid(rx_eth_hdr_valid),
    .output_eth_hdr_ready(rx_eth_hdr_ready),
    .output_eth_dest_mac(rx_eth_dest_mac),
    .output_eth_src_mac(rx_eth_src_mac),
    .output_eth_type(rx_eth_type),
    .output_eth_payload_tdata(rx_eth_payload_tdata),
    .output_eth_payload_tvalid(rx_eth_payload_tvalid),
    .output_eth_payload_tready(rx_eth_payload_tready),
    .output_eth_payload_tlast(rx_eth_payload_tlast),
    .output_eth_payload_tuser(rx_eth_payload_tuser),
    // Status signals
    .busy(),
    .error_header_early_termination()
);

eth_axis_tx
eth_axis_tx_inst (
    .clk(clk_125mhz),
    .rst(rst_125mhz),
    // Ethernet frame input
    .input_eth_hdr_valid(tx_eth_hdr_valid),
    .input_eth_hdr_ready(tx_eth_hdr_ready),
    .input_eth_dest_mac(tx_eth_dest_mac),
    .input_eth_src_mac(tx_eth_src_mac),
    .input_eth_type(tx_eth_type),
    .input_eth_payload_tdata(tx_eth_payload_tdata),
    .input_eth_payload_tvalid(tx_eth_payload_tvalid),
    .input_eth_payload_tready(tx_eth_payload_tready),
    .input_eth_payload_tlast(tx_eth_payload_tlast),
    .input_eth_payload_tuser(tx_eth_payload_tuser),
    // AXI output
    .output_axis_tdata(tx_axis_tdata),
    .output_axis_tvalid(tx_axis_tvalid),
    .output_axis_tready(tx_axis_tready),
    .output_axis_tlast(tx_axis_tlast),
    .output_axis_tuser(tx_axis_tuser),
    // Status signals
    .busy()
);

udp_complete #(.UDP_CHECKSUM_PAYLOAD_FIFO_ADDR_WIDTH(12))
udp_complete_inst (
    .clk(clk_125mhz),
    .rst(rst_125mhz),
    // Ethernet frame input
    .input_eth_hdr_valid(rx_eth_hdr_valid),
    .input_eth_hdr_ready(rx_eth_hdr_ready),
    .input_eth_dest_mac(rx_eth_dest_mac),
    .input_eth_src_mac(rx_eth_src_mac),
    .input_eth_type(rx_eth_type),
    .input_eth_payload_tdata(rx_eth_payload_tdata),
    .input_eth_payload_tvalid(rx_eth_payload_tvalid),
    .input_eth_payload_tready(rx_eth_payload_tready),
    .input_eth_payload_tlast(rx_eth_payload_tlast),
    .input_eth_payload_tuser(rx_eth_payload_tuser),
    // Ethernet frame output
    .output_eth_hdr_valid(tx_eth_hdr_valid),
    .output_eth_hdr_ready(tx_eth_hdr_ready),
    .output_eth_dest_mac(tx_eth_dest_mac),
    .output_eth_src_mac(tx_eth_src_mac),
    .output_eth_type(tx_eth_type),
    .output_eth_payload_tdata(tx_eth_payload_tdata),
    .output_eth_payload_tvalid(tx_eth_payload_tvalid),
    .output_eth_payload_tready(tx_eth_payload_tready),
    .output_eth_payload_tlast(tx_eth_payload_tlast),
    .output_eth_payload_tuser(tx_eth_payload_tuser),
    // IP frame input
    .input_ip_hdr_valid(tx_ip_hdr_valid),
    .input_ip_hdr_ready(tx_ip_hdr_ready),
    .input_ip_dscp(tx_ip_dscp),
    .input_ip_ecn(tx_ip_ecn),
    .input_ip_length(tx_ip_length),
    .input_ip_ttl(tx_ip_ttl),
    .input_ip_protocol(tx_ip_protocol),
    .input_ip_source_ip(tx_ip_source_ip),
    .input_ip_dest_ip(tx_ip_dest_ip),
    .input_ip_payload_tdata(tx_ip_payload_tdata),
    .input_ip_payload_tvalid(tx_ip_payload_tvalid),
    .input_ip_payload_tready(tx_ip_payload_tready),
    .input_ip_payload_tlast(tx_ip_payload_tlast),
    .input_ip_payload_tuser(tx_ip_payload_tuser),
    // IP frame output
    .output_ip_hdr_valid(rx_ip_hdr_valid),
    .output_ip_hdr_ready(rx_ip_hdr_ready),
    .output_ip_eth_dest_mac(rx_ip_eth_dest_mac),
    .output_ip_eth_src_mac(rx_ip_eth_src_mac),
    .output_ip_eth_type(rx_ip_eth_type),
    .output_ip_version(rx_ip_version),
    .output_ip_ihl(rx_ip_ihl),
    .output_ip_dscp(rx_ip_dscp),
    .output_ip_ecn(rx_ip_ecn),
    .output_ip_length(rx_ip_length),
    .output_ip_identification(rx_ip_identification),
    .output_ip_flags(rx_ip_flags),
    .output_ip_fragment_offset(rx_ip_fragment_offset),
    .output_ip_ttl(rx_ip_ttl),
    .output_ip_protocol(rx_ip_protocol),
    .output_ip_header_checksum(rx_ip_header_checksum),
    .output_ip_source_ip(rx_ip_source_ip),
    .output_ip_dest_ip(rx_ip_dest_ip),
    .output_ip_payload_tdata(rx_ip_payload_tdata),
    .output_ip_payload_tvalid(rx_ip_payload_tvalid),
    .output_ip_payload_tready(rx_ip_payload_tready),
    .output_ip_payload_tlast(rx_ip_payload_tlast),
    .output_ip_payload_tuser(rx_ip_payload_tuser),
    // UDP frame input
    .input_udp_hdr_valid(tx_udp_hdr_valid),
    .input_udp_hdr_ready(tx_udp_hdr_ready),
    .input_udp_ip_dscp(tx_udp_ip_dscp),
    .input_udp_ip_ecn(tx_udp_ip_ecn),
    .input_udp_ip_ttl(tx_udp_ip_ttl),
    .input_udp_ip_source_ip(tx_udp_ip_source_ip),
    .input_udp_ip_dest_ip(tx_udp_ip_dest_ip),
    .input_udp_source_port(tx_udp_source_port),
    .input_udp_dest_port(tx_udp_dest_port),
    .input_udp_length(tx_udp_length),
    .input_udp_checksum(tx_udp_checksum),
    .input_udp_payload_tdata(tx_udp_payload_tdata),
    .input_udp_payload_tvalid(tx_udp_payload_tvalid),
    .input_udp_payload_tready(tx_udp_payload_tready),
    .input_udp_payload_tlast(tx_udp_payload_tlast),
    .input_udp_payload_tuser(tx_udp_payload_tuser),
    // UDP frame output
    .output_udp_hdr_valid(rx_udp_hdr_valid),
    .output_udp_hdr_ready(rx_udp_hdr_ready),
    .output_udp_eth_dest_mac(rx_udp_eth_dest_mac),
    .output_udp_eth_src_mac(rx_udp_eth_src_mac),
    .output_udp_eth_type(rx_udp_eth_type),
    .output_udp_ip_version(rx_udp_ip_version),
    .output_udp_ip_ihl(rx_udp_ip_ihl),
    .output_udp_ip_dscp(rx_udp_ip_dscp),
    .output_udp_ip_ecn(rx_udp_ip_ecn),
    .output_udp_ip_length(rx_udp_ip_length),
    .output_udp_ip_identification(rx_udp_ip_identification),
    .output_udp_ip_flags(rx_udp_ip_flags),
    .output_udp_ip_fragment_offset(rx_udp_ip_fragment_offset),
    .output_udp_ip_ttl(rx_udp_ip_ttl),
    .output_udp_ip_protocol(rx_udp_ip_protocol),
    .output_udp_ip_header_checksum(rx_udp_ip_header_checksum),
    .output_udp_ip_source_ip(rx_udp_ip_source_ip),
    .output_udp_ip_dest_ip(rx_udp_ip_dest_ip),
    .output_udp_source_port(rx_udp_source_port),
    .output_udp_dest_port(rx_udp_dest_port),
    .output_udp_length(rx_udp_length),
    .output_udp_checksum(rx_udp_checksum),
    .output_udp_payload_tdata(rx_udp_payload_tdata),
    .output_udp_payload_tvalid(rx_udp_payload_tvalid),
    .output_udp_payload_tready(rx_udp_payload_tready),
    .output_udp_payload_tlast(rx_udp_payload_tlast),
    .output_udp_payload_tuser(rx_udp_payload_tuser),
    // Status signals
    .ip_rx_busy(),
    .ip_tx_busy(),
    .udp_rx_busy(),
    .udp_tx_busy(),
    .ip_rx_error_header_early_termination(),
    .ip_rx_error_payload_early_termination(),
    .ip_rx_error_invalid_header(),
    .ip_rx_error_invalid_checksum(),
    .ip_tx_error_payload_early_termination(),
    .ip_tx_error_arp_failed(),
    .udp_rx_error_header_early_termination(),
    .udp_rx_error_payload_early_termination(),
    .udp_tx_error_payload_early_termination(),
    // Configuration
    .local_mac(local_mac),
    .local_ip(local_ip),
    .gateway_ip(gateway_ip),
    .subnet_mask(subnet_mask),
    .clear_arp_cache(0)
);

endmodule
