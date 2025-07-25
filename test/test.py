# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray
from cocotb.utils import get_sim_time

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")


async def detect_rising_edge(dut, signal,timeout, bit=0):
    # Wait for the rising edge
    for each in range(timeout):
        await ClockCycles(dut.clk, 1)
        curr = int(signal.value) & (1 << bit) # Manually check the bit
        if (curr != 0):
            return cocotb.utils.get_sim_time(units="ns")
        
    raise RuntimeError("Timeout waiting for rising edge")

async def detect_falling_edge(dut, signal,timeout, bit=0):
    # Wait for the falling edge
    for each in range(timeout):
        await ClockCycles(dut.clk, 1)
        curr = int(signal.value) & (1 << bit) # Manually check the bit
        if (curr == 0):
            return cocotb.utils.get_sim_time(units="ns")
        
    raise RuntimeError("Timeout waiting for falling edge")
    
@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("test_pwm_freq")

    # Clock setup
    clock = Clock(dut.clk, 100, units="ns")  # 10 MHz
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x04, 0x80)  # Stabilize

    dut._log.info("Let frequency test begin")

    # Sync throwaway
    await detect_rising_edge(dut, dut.uo_out, timeout=10000, bit=0)
    await detect_falling_edge(dut, dut.uo_out, timeout=10000, bit=0)
    await detect_rising_edge(dut, dut.uo_out, timeout=10000, bit=0)

    for bit in range (8):
        t1 = await detect_rising_edge(dut, dut.uo_out, timeout=10000, bit=bit)
        t2 = await detect_falling_edge(dut, dut.uo_out, timeout=10000, bit=bit)
        t3 = await detect_rising_edge(dut, dut.uo_out, timeout=10000, bit=bit)
        period_ns = t3 - t1
        freq = 1e9 / period_ns
        dut._log.info(f"Bit {bit} frequency = {freq:.2f} Hz")
        assert 2970 < freq < 3030, f"Got {freq:.2f} Hz on bit {bit}"
        dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("test_pwm_duty")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction

    dut._log.info("Let duty cycle test begin")
    duty_cycles = [
        (0x00, "0%"),
        (0x40, "25%"),
        (0x80, "50%"),
        (0xC0, "75%"),
        (0xFF, "100%"),
    ]

    for value, label in duty_cycles:
        await send_spi_transaction(dut, 1, 0x04, value)
        dut._log.info(f"Set PWM duty cycle to {label} (0x{value:02X})")
        #sync throwaway

        #Catch cases where the duty cycle is 0% or 100%
        # If the duty cycle is 0%, the first rising edge will not be detected
        # If the duty cycle is 100%, the first falling edge will not be detected
        try:
            await detect_rising_edge(dut, dut.uo_out, timeout=10000, bit=0)  # Rising
        except RuntimeError:
            dut._log.warning(f"0% duty cycle")
            continue

        try:
            await detect_falling_edge(dut, dut.uo_out, timeout=10000, bit=0)  # Rising
        except RuntimeError:
            dut._log.warning(f"100% duty cycle")
            continue

        await detect_rising_edge(dut, dut.uo_out, timeout=10000, bit=0)  # Rising again       
        for bit in range (8):
            t1 = await detect_rising_edge(dut, dut.uo_out, timeout=10000, bit=bit)
            t2 = await detect_falling_edge(dut, dut.uo_out, timeout=10000, bit=bit)
            t3 = await detect_rising_edge(dut, dut.uo_out, timeout=10000, bit=bit)
            high_time = t2 - t1
            period_ns = t3 - t1
            duty_cycle = (high_time / period_ns) * 100
            dut._log.info(f"Bit {bit} duty cycle = {duty_cycle:.2f} %")
    await ClockCycles(dut.clk, 100)

    dut._log.info("PWM Duty Cycle test completed successfully")


