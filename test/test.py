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




async def detect_rising_edge(dut, signal,timeout=1000, bit=0):
    # Wait for the rising edge
    for each in range(timeout):
        curr = int(dut.uo_out.value) & (1 << bit) #Manually check the bit
        if (curr == 1):
            return cocotb.utils.get_sim_time(units="ns")
    raise RuntimeError("Timeout waiting for rising edge")

async def detect_rising_edge(dut, signal,timeout=1000, bit=0):
    # Wait for the rising edge
    for each in range(timeout):
        curr = int(dut.uo_out.value) & (1 << bit) #Manually check the bit
        if (curr == 0):
            return cocotb.utils.get_sim_time(units="ns")
    raise RuntimeError("Timeout waiting for rising edge")
    

async def measure_duty(dut, signal, timeout=1000):
    # Wait for the first rising edge
    await RisingEdge(signal)
    t1 = get_sim_time(units="ns")  # capture time in nanoseconds
    await FallingEdge(signal)
    fall_t = get_sim_time(units="ns")  # capture time in nanoseconds

    # Wait for the second rising edge
    await RisingEdge(signal)
    t2 = get_sim_time(units="ns")

    # Calculate the clock period
    high_time = fall_t - t1
    period_ns = t2 - t1
    duty_cycle = high_time / period_ns
    
@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("test_pwm_freq")

    # Clock setup
    clock = Clock(dut.clk, 100, units="ns")  # 10 MHz
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x04, 0x80)  # Stable
    await ClockCycles(dut.clk, 10000)

    dut._log.info("Let frequency test begin")

    for bit in range(8):
    try:
        t1 = await detect_rising_edge(dut, dut.uo_out[0], timeout=10000, bit=bit)
        t2 = await detect_falling_edge(dut, dut.uo_out[0], timeout=10000, bit=bit)
        t3 = await detect_rising_edge(dut, dut.uo_out[0], timeout=10000, bit=bit)
        dut._log.info(f"Got {t1} ns and {t3} ns")
        period_ns = t3 - t1
        freq = 1e9 / period_ns
        dut._log.info(f"Bit {bit} frequency = {freq:.2f} Hz")
        assert 2900 < freq < 3100, f"Got {freq:.2f} Hz on bit {bit}"
        dut._log.info("PWM Frequency test completed successfully")
        return
    except RuntimeError:
        dut._log.info(f"Bit {bit}: No rising edge detected")




@cocotb.test()
async def test_pwm_duty(dut):
    # Write your test here

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

    duty_cycles = [
        (0x00, "0%"),
        (0x40, "25%"),
        (0x80, "50%"),
        (0xFF, "100%")
    ]

    for value, label in duty_cycles:
        await send_spi_transaction(dut, 1, 0x04, value)
        dut._log.info(f"Set PWM duty cycle to {label} (0x{value:02X})")
        #Wait for the rising edge/falling edge for 5 times, you can then conclude that it is duty cycle 0% or 100%.

        dut._log.info("uio_out ports")
        await ClockCycles(dut.clk, 5)

        dut._log.info("uo_out ports")
        await ClockCycles(dut.clk, 5)

    await ClockCycles(dut.clk, 100)


    dut._log.info("PWM Duty Cycle test completed successfully")


