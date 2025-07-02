`default_nettype none

module spi_peripheral (
    input  wire clk,       // system clock
    input  wire rst_n,     // active-low reset
    // SPI interface
    input  wire sclk,      // SPI clock from master
    input  wire COPI,      // data from master
    input  wire nCS,      // slave select, active low
    output  reg [7:0] outtopwm,
    output  reg [7:0] outtopwm2
);
    localparam MAX_ADDR = 4;
    reg transaction_ready;
    reg transaction_processed;
    reg[2:0] sclk_sync;
    reg[1:0] COPI_sync;
    reg[1:0] nCS_sync;
    reg[5:0] rising_counter, falling_counter;
    reg[15:0] spi_buf;
    reg isthisin;
    //need to pass it

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

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        rising_counter <= 0;
        falling_counter <= 0;
        transaction_ready <= 1'b0;  
        // omitted code
    end else if (nCS_sync[1] == 1'b0 && rising_counter <= 15 && falling_counter <= 15) begin
        isthisin <= 1'b1;
        //(2nd oldest = HIGH) AND (1st oldest = LOW)
        //mode 0: reads COPI data on rising edge of SCLK
        if (sclk_sync[1] == 1'b1 && sclk_sync[0] == 1'b0) begin
            spi_buf <= {spi_buf[14:0], COPI_sync[1]}; // Shift in the COPI data bit
            rising_counter <= rising_counter + 1;
        //(2nd oldest = LOW) AND (1st oldest = HIGH)
        //mode 0: shift out COPI data on falling edge of SCLK
        end else if (sclk_sync[1] == 1'b0 && sclk_sync[0] == 1'b1) begin
            falling_counter <= falling_counter + 1;
        end 
        
        $display("Shifted in: spi_buf=%h, rising_counter=%d, COPI=%b", spi_buf, rising_counter, COPI_sync[1]);

    end else begin
        // When nCS goes high (transaction ends), validate the complete transaction
        if (nCS_sync[1] == 1'b0 && nCS_sync[0] == 1'b1 && ~transaction_processed) begin
            isthisin <= 1'b0;
            transaction_ready <= 1'b1;
        end else if (transaction_processed) begin
            // Clear ready flag once processed
            transaction_ready <= 1'b0;
        end
        // ignore transactions with address outside of bounds
    end
end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            transaction_processed <= 1'b0;
            outtopwm <= 8'b0;
            outtopwm2 <= 8'b0;
        end else if (transaction_ready && !transaction_processed) begin
            if ((spi_buf[0] == 1'b1) && (spi_buf[7:1] <= MAX_ADDR)) begin
                transaction_processed <= 1'b1;      
            end else begin
                transaction_processed <= 1'b0;
            end 
        end else if (!transaction_ready && transaction_processed) begin
                outtopwm  <= spi_buf[7:0];
                outtopwm2 <= spi_buf[15:8];
            transaction_processed <= 1'b0;
        end
    end

endmodule