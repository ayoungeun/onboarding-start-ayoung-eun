`default_nettype none

module spi_peripheral (
    input  wire clk,       // system clock
    input  wire rst_n,     // active-low reset
    // SPI interface
    input  wire sclk,      // SPI clock from master
    input  wire COPI,      // data from master
    input  wire nCS,      // slave select, active low
    output  reg [7:0] out_uo_out,
    output  reg [7:0] out_uio_out
    output  reg [7:0] out_PWM_uo_out,
    output  reg [7:0] out_PWM_uio_out,
    output  reg [7:0] out_duty_cycle,  

);
    localparam MAX_ADDR = 4;
    reg transaction_ready;
    reg transaction_processed;
    reg[2:0] sclk_sync;
    reg[1:0] COPI_sync;
    reg[1:0] nCS_sync;
    reg[5:0] rising_counter, falling_counter;
    reg[15:0] spi_buf;
    reg ncs_rise_detected;
    reg [1:0] count;
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


//Screw this, I will just use FSM if this doesn't work out.
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        rising_counter <= 0;
        transaction_ready <= 1'b0;
        transaction_processed <= 1'b0;
        outtopwm <= 8'b0;
        outtopwm2 <= 8'b0;
        ncs_rise_detected <= 0;
        count <= 0;
        spi_buf <= 16'b0;

    end else begin
        // SPI shift logic

        //nCS is down, we are ready to transmit.
        if (nCS_sync[1] == 1'b1 && nCS_sync[0] == 1'b0) begin 
            transaction_ready <= 1'b1;
            transaction_processed <= 1'b0;
            rising_counter <= 0;
            spi_buf <= 0;
        end

        if (transaction_ready) begin
        if (rising_counter < 16 && sclk_sync[1] == 1'b1 && sclk_sync[0] == 1'b0) begin
            spi_buf <= {spi_buf[14:0], COPI_sync[1]};
             rising_counter <= rising_counter + 1;
        end
        end


        //nCS is up, we are ready to process.
        if (nCS_sync[1] == 1'b0 && nCS_sync[0] == 1'b1 && rising_counter == 15) begin 
            $display("nCS is up = %d, spi_buf = %b", rising_counter, spi_buf);
                //if ((spi_buf[0] == 1'b1) && (spi_buf[7:1] <= MAX_ADDR)) begin
            transaction_processed <= 1'b1;      
                //end else begin
                //transaction_processed <= 1'b0;
                //end 
            transaction_ready <= 1'b0; // delayed
            //rising_counter <= 0; // reset the counter
        end



        if (transaction_processed) begin
            $display("transaction_processed");
            $display("rising_counter = %d, spi_buf = %b", rising_counter, spi_buf);

            if (spi_buf[15] == 1'b1) begin 
                if(spi_buf[14:8] == 7'b0000000) begin 
                    out_uo_out <= spi_buf[7:0];

                end else if (spi_buf[14:8] == 7'b0000001) begin 
                    out_uio_out <= spi_buf[7:0];

                end else if (spi_buf[14:8] == 7'b0000010) begin 
                    out_PWM_uo_out <= spi_buf[7:0];

                end else if (spi_buf[14:8] == 7'b0000011) begin 
                    out_PWM_uio_out <= spi_buf[7:0];

                end else if (spi_buf[14:8] == 7'b0000100) begin 
                    out_duty_cycle <= spi_buf[7:0];
                end

            end
            spi_buf <= 16'b0;
            transaction_processed <= 0;
        end

    end
end


// always @(posedge clk or negedge rst_n) begin
//     if (!rst_n) begin
//         rising_counter <= 0;
//         falling_counter <= 0;

//     end else if (nCS_sync[1] == 1'b0 && nCS_sync[0] == 1'b0) begin
 
//         if (sclk_sync[1] == 1'b1 && sclk_sync[0] == 1'b0) begin
//             spi_buf <= {spi_buf[14:0], COPI_sync[1]};
//             rising_counter <= rising_counter + 1;
//         end else if (sclk_sync[1] == 1'b0 && sclk_sync[0] == 1'b1) begin
//             falling_counter <= falling_counter + 1;
//         end 

//     end else begin
//         // When nCS goes high (transaction ends), validate the complete transaction
//         if (nCS_sync[1] == 1'b0 && nCS_sync[0] == 1'b1 && ~transaction_processed) begin
//             transaction_ready <= 1'b1;
//         end else if (transaction_processed) begin
//             // Clear ready flag once processed
//             transaction_ready <= 1'b0;
//         end
//     end
// end

//     always @(posedge clk or negedge rst_n) begin
//         if (!rst_n) begin
//             transaction_processed <= 1'b0;
//             outtopwm <= 8'b0;
//             outtopwm2 <= 8'b0;
//         end else if (transaction_ready && !transaction_processed) begin
//             if ((spi_buf[0] == 1'b1) && (spi_buf[7:1] <= MAX_ADDR)) begin
//                 transaction_processed <= 1'b1;      
//             end else begin
//                 transaction_processed <= 1'b0;
//             end 
//         end else if (!transaction_ready && transaction_processed) begin
//                 outtopwm  <= spi_buf[7:0];
//                 outtopwm2 <= spi_buf[15:8];
//             transaction_processed <= 1'b0;
//         end
//     end
 
endmodule