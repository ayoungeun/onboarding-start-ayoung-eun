module spi_peripheral (
    input  wire clk,       // system clock
    input  wire rst_n,     // active-low reset
    // SPI interface
    input  wire sclk,      // SPI clock from master
    input  wire COPI,      // data from master
    input  wire nCS,      // slave select, active low
    output reg  [15:0] spi_out
);
    reg transaction_ready;
    reg transaction_processed;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        
        rising_counter <= 0;
        falling_counter <= 0;
        transaction_ready <= 1'b0;
        // omitted code
    end else if (nCS_sync[1] == 1'b0) begin
        //(2nd oldest = HIGH) AND (1st oldest = LOW)
        //mode 0: reads COPI data on rising edge of SCLK
        if (rising_counter < 16 && sclk_sync[1] == 1'b1 && sclk_sync[0] == 1'b0) begin
            spi_buf <= {spi_buf[14:0], COPI_sync[1]}; // Shift in the COPI data bit
            rising_counter <= rising_counter + 1;
        //(2nd oldest = LOW) AND (1st oldest = HIGH)
        //mode 0: shift out COPI data on falling edge of SCLK
        end else if (falling_counter < 16 && sclk_sync[1] == 1'b0 && sclk_sync[0] == 1'b1) begin
            falling_counter <= falling_counter + 1;
        end else if (rising_counter == 16 && falling_counter == 16) begin
            // Transaction is complete after 16 bits
            transaction_ready <= 1'b1; // Set ready flag
        end

    end else begin
        // When nCS goes high (transaction ends), validate the complete transaction
        if (nCS_posedge) begin

            transaction_ready <= 1'b1;
        end else if (transaction_processed) begin
            // Clear ready flag once processed
            transaction_ready <= 1'b0;
        end
        // ignore transactions with address outside of bounds
    end
end

// Update registers only after the complete transaction has finished and been validated
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        // omitted code
        transaction_processed <= 1'b0;
    end else if (transaction_ready && !transaction_processed) begin
        // Transaction is ready and not yet processed
        // Update registers *only after the entire transaction completes* (on `nCS` rising edge).
        // Use flags like `transaction_ready` to avoid partial updates.
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