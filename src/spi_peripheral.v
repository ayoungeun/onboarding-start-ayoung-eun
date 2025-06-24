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

localparam [7:0] MAX_ADDRESS = 8'h04; // Maximum valid address is 0x04
reg[2:0] sclk_sync;
reg[1:0] COPI_sync;
reg[1:0] nCS_sync;
reg[5:0] rising_counter, falling_counter;
reg transaction_ready;
reg transaction_processed;
//Only checking nCS_sync[1] to nCS_sync[0] for posedge detection, I do not thing reg is required.
wire nCS_posedge = (nCS_sync[1] == 1'b0 && nCS_sync[0] == 1'b1); 

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

always @(posedge clk) begin
    if (!rst_n) begin
        rising_counter <= 0;
        falling_counter <= 0;
    end else begin
        //(2nd oldest = HIGH) AND (1st oldest = LOW)
        if (sclk_sync[1] == 1'b1 && sclk_sync[0] == 1'b0) begin
            rising_counter <= rising_counter + 1;
        //(2nd oldest = LOW) AND (1st oldest = HIGH)
        end else if (sclk_sync[1] == 1'b0 && sclk_sync[0] == 1'b1) begin
            falling_counter <= falling_counter + 1;
        end
    end
end

// //Error cases
// if (rising_counter > 16 || falling_counter > 16) begin
// or less than 16 after all bit counts
//     // Handle error condition, e.g., reset counters or log error
//     rising_counter <= 0;
//     falling_counter <= 0;
// end

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        // omitted code
        transaction_ready <= 1'b0;
        // omitted code
    end else if (nCS_sync[1] == 1'b0) begin
        // omitted code
    end else begin
        // When nCS goes high (transaction ends), validate the complete transaction
        if (nCS_posedge) begin
            transaction_ready <= 1'b1;
        end else if (transaction_processed) begin
            // Clear ready flag once processed
            transaction_ready <= 1'b0;
        end
        // omitted code
    end
end

// Update registers only after the complete transaction has finished and been validated
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        // omitted code
        transaction_processed <= 1'b0;
    end else if (transaction_ready && !transaction_processed) begin
        // Transaction is ready and not yet processed
        // omitted code
        // Set the processed flag
        transaction_processed <= 1'b1;
    end else if (!transaction_ready && transaction_processed) begin
        // Reset processed flag when ready flag is cleared
        transaction_processed <= 1'b0;
    end
end
endmodule

//Things to do in future
/*
1. * Ensure you capture **16 total bits** (1 R/W + 7 address + 8 data).
2. **Address Validation**
   * Ignore transactions with addresses outside `0x00`–`0x04`.
   * Use a local parameter (e.g., `max_address`) for flexibility.
3. **Transaction Finalization**
   * Update registers *only after the entire transaction completes* (on `nCS` rising edge).
   * Use flags like `transaction_ready` to avoid partial updates.
   */