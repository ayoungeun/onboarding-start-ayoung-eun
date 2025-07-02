default_nettype none

module spi_peripheral (
    input  wire clk,        // system clock
    input  wire rst_n,      // active-low reset
    // SPI interface
    input  wire sclk,       // SPI clock from master
    input  wire COPI,       // data from master
    input  wire nCS,        // slave select, active low
    output reg [7:0] outtopwm,
    output reg [7:0] outtopwm2
);
    localparam MAX_ADDR = 4; // Or whatever your max address is
    localparam SPI_BITS = 16; // Total bits per SPI transaction (e.g., 16 for 2 bytes)

    // Synchronizers for asynchronous inputs
    reg [2:0] sclk_sync;
    reg [1:0] COPI_sync;
    reg [1:0] nCS_sync;

    // SPI state and data registers
    reg [SPI_BITS-1:0] spi_buf; // Buffer to store received SPI data
    reg [4:0] bit_counter;    // Counts bits received (e.g., up to 16 for 2 bytes)

    // Transaction control flags
    reg transaction_ready;
    reg transaction_processed;

    // Asynchronous input synchronization
    always @(posedge clk) begin
        if(!rst_n) begin
            sclk_sync <= 'd0;
            COPI_sync <= 'd0;
            nCS_sync <= 'd0;
        end
        else begin
            sclk_sync <= { sclk_sync[1:0], sclk };
            COPI_sync <= { COPI_sync[0], COPI };
            nCS_sync <= { nCS_sync[0], nCS };
        end
    end

    // SPI data reception and transaction management
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_buf <= {SPI_BITS{1'b0}}; // Reset spi_buf
            bit_counter <= 0;
            transaction_ready <= 1'b0;
            transaction_processed <= 1'b0;
        end else begin
            // Detect nCS going low (start of new transaction)
            if (nCS_sync[1] == 1'b1 && nCS_sync[0] == 1'b0) begin // nCS falling edge
                bit_counter <= 0;
                spi_buf <= {SPI_BITS{1'b0}}; // Clear buffer for new transaction
                transaction_ready <= 1'b0;
                transaction_processed <= 1'b0; // Reset processed flag for new transaction
            end
            // When nCS is low (transaction active)
            else if (nCS_sync[1] == 1'b0 && nCS_sync[0] == 1'b0) begin
                // Mode 0: reads COPI data on rising edge of SCLK
                if (sclk_sync[1] == 1'b1 && sclk_sync[0] == 1'b0) begin // Rising edge of SCLK
                    if (bit_counter < SPI_BITS) begin
                        spi_buf <= {spi_buf[SPI_BITS-2:0], COPI_sync[1]};
                        bit_counter <= bit_counter + 1;
                    end
                end
            end
            // Detect nCS going high (end of transaction)
            else if (nCS_sync[1] == 1'b0 && nCS_sync[0] == 1'b1) begin // nCS rising edge
                // A transaction just ended. Validate if the correct number of bits were received.
                if (bit_counter == SPI_BITS) begin // Check if all expected bits were received
                    transaction_ready <= 1'b1;
                end else begin
                    // Invalid transaction (e.g., incorrect number of bits), discard
                    transaction_ready <= 1'b0;
                end
                // Reset bit_counter for next transaction (important for proper re-initialization)
                bit_counter <= 0;
            end
        end
    end

    // Data processing and output assignment
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            outtopwm <= 8'b0;
            outtopwm2 <= 8'b0;
            transaction_processed <= 1'b0;
        end else begin
            if (transaction_ready && !transaction_processed) begin
                if ((spi_buf[0] == 1'b1) && (spi_buf[7:1] <= MAX_ADDR)) begin
                    outtopwm2 <= spi_buf[7:0];   // First 8 bits received (e.g., command/address)
                    outtopwm  <= spi_buf[15:8];  // Second 8 bits received (e.g., data)
                    transaction_processed <= 1'b1; // Mark as processed
                end else begin
                end
            end else if (transaction_processed) begin
                transaction_ready <= 1'b0; // Clear the ready flag after a cycle of processing
            end
        end
    end

endmodule