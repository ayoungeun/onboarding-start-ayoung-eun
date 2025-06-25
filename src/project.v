/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_uwasic_onboarding_ayoung_eun (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // All output pins must be assigned. If not used, assign to 0.
  assign uo_out  = ui_in + uio_in;  // Example: ou_out is the sum of ui_in and uio_in
  assign uio_out = 0;
  assign uio_oe  = 0;

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, clk, rst_n, 1'b0};

  reg [7:0] spi_data;

      // Registers or data interface
    reg[2:0] sclk_sync;
    reg[1:0] COPI_sync;
    reg[1:0] nCS_sync;
    reg[5:0] rising_counter, falling_counter;
    reg[15:0] spi_buf;
    //Only checking nCS_sync[1] to nCS_sync[0] for posedge detection, I do not thing reg is required.
    wire nCS_posedge = (nCS_sync[1] == 1'b0 && nCS_sync[0] == 1'b1); 
    //need to pass it

  always @(posedge clk) begin
    if(!rst_n) begin
        for (integer i; i<2; i = i + 1) begin
            sclk_sync[i] <= 0;
            nCS_sync[i] <= 0;
            COPI_sync[i] <= 0;
        end
        sclk_sync[2] <=0;
    end
    else begin
        sclk_sync[0] <= ui_in[0];
        sclk_sync[1] <= sclk_sync[0];
        sclk_sync[2] <= sclk_sync[1];
        COPI_sync[0] <= ui_in[1]; 
        COPI_sync[1] <= COPI_sync[0];
        nCS_sync[0] <= ui_in[2];
        nCS_sync[1] <= nCS_sync[0];
    end
end


    // Instantiate the SPI peripheral module
    spi_peripheral spi (
        .clk(clk),
        .rst_n(rst_n),
        .sclk(ui_in[0]),
        .COPI(ui_in[1]),
        .nSC(ui_in[2]),
        .received_data(spi_data)
    );

    assign spi_data_out = spi_data;

endmodule