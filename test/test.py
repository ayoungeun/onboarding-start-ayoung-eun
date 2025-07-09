# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

# Constants
FREQUENCY = 3000
RISING = 1
FALLING = 0

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


async def await_edge(dut, signal, num, start_sim_time, timeout, edge_type):
    while signal.value[num] != edge_type: 
        await(RisingEdge(dut.clk))
        # assert (cocotb.utils.get_sim_time(units="ns") - start_sim_time < timeout), "Timeout occured"
        if(cocotb.utils.get_sim_time(units="ns") - start_sim_time > timeout):
            return 1
    return 0

async def test_frequency(dut, signal, num, timeout_ms):  
    timeout = timeout_ms * 1000000 # convert to ns
    start_sim_time = cocotb.utils.get_sim_time(units="ns")

    # Wait for next rising edge
    status = await await_edge(dut, signal, num, start_sim_time, timeout, RISING)
    status = await await_edge(dut, signal, num, start_sim_time, timeout, FALLING)
    
    # Timeout occured
    if(status):
        return 0
    
    status = await await_edge(dut, signal, num, start_sim_time, timeout, RISING)

    # First rising edge
    risingEdge1 = cocotb.utils.get_sim_time(units="ns")

    # Wait for next rising edge
    status = await await_edge(dut, signal, num, start_sim_time, timeout, FALLING)
    status = await await_edge(dut, signal, num, start_sim_time, timeout, RISING)

    # Second rising edge
    risingEdge2 = cocotb.utils.get_sim_time(units="ns")

    # Timeout occured
    if(status != 0):
        return 0

    period = risingEdge2 - risingEdge1
    period = period / (1e9) # convert to seconds

    frequency = 1 / period
    return frequency

@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Starting PWM Frequency test...")

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

    # Write PWM 50% duty cycle to each output port
    await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction
    
    await send_spi_transaction(dut, 1, 0x04, 0x80)  # 50% duty cycle

    # Test the frequency for each output port
    # Starting uo_out tests!
    dut._log.info("Testing uo_out ports:")

    for i in range(0, 8):
        frequency = await test_frequency(dut, dut.uo_out, i, 1)
        dut._log.info(f"- Frequency test: uo_out[{i}] = {frequency:.2f} Hz")
        assert (frequency >= FREQUENCY * 0.99 and frequency <= FREQUENCY * 1.01), f"Acceptable range: [2970, 3030], got {frequency}"
        await ClockCycles(dut.clk, 5)

    # Starting uio_out tests!
    dut._log.info("Testing uio_out ports:")
    
    for i in range(0, 8):
        frequency = await test_frequency(dut, dut.uio_out, i, 1)
        dut._log.info(f"- Frequency test: uio_out[{i}] = {frequency:.2f} Hz")
        assert (frequency >= FREQUENCY * 0.99 and frequency <= FREQUENCY * 1.01), f"Acceptable range: [2970, 3030], got {frequency}"
        await ClockCycles(dut.clk, 5)

    dut._log.info("PWM Frequency test completed successfully")


async def test_duty_cycle(dut, signal, num, timeout_ms):
    timeout = timeout_ms * 1000000 # convert to ns
    start_sim_time = cocotb.utils.get_sim_time(units="ns")

    # Wait for next rising edge
    await await_edge(dut, signal, num, start_sim_time, timeout, RISING)
    await await_edge(dut, signal, num, start_sim_time, timeout, FALLING)
    await await_edge(dut, signal, num, start_sim_time, timeout, RISING)

    # First rising edge
    risingEdge1 = cocotb.utils.get_sim_time(units="ns")

    # Wait for falling edge
    await await_edge(dut, signal, num, start_sim_time, timeout, FALLING)
    fallingEdge = cocotb.utils.get_sim_time(units="ns")

    await await_edge(dut, signal, num, start_sim_time, timeout, RISING)

    # Second rising edge
    risingEdge2 = cocotb.utils.get_sim_time(units="ns")

    period = risingEdge2 - risingEdge1
    high_time = fallingEdge - risingEdge1 # both in seconds

    duty_cycle = (high_time / period) * 100

    return duty_cycle

@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Starting PWM Duty Cycle test...")

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

    test_cycles = [(0, 0x00), (50, 0x80), (100, 0xFF), (83, 0xD4)] # sorry Im lazy

    # Write PWM 50% duty cycle to each output port
    await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x01, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await send_spi_transaction(dut, 1, 0x03, 0xFF)  # Write transaction
    
    # Test the duty cycle for each output port
    for duty_cycle in test_cycles:
        await send_spi_transaction(dut, 1, 0x04, duty_cycle[1])

        # Starting uo_out tests!
        dut._log.info(f"Testing uo_out ports: {duty_cycle[0]}%")

        for i in range(0, 8):
            result = await test_duty_cycle(dut, dut.uo_out, i, 1)
            dut._log.info(f"- Duty cycle: uo_out[{i}] = {result}%")
            assert (result >= duty_cycle[0] * 0.99 and result <= duty_cycle[0] * 1.01), f"Expected {duty_cycle[0]}%, got {result}"
            await ClockCycles(dut.clk, 5)

        # Starting uio_out tests!
        dut._log.info(f"Testing uio_out ports: {duty_cycle[0]}%")
        
        for i in range(0, 8):
            result = await test_duty_cycle(dut, dut.uio_out, i, 1)
            dut._log.info(f"- Duty cycle: uio_out[{i}] = {result}%")
            assert (result >= duty_cycle[0] * 0.99 and result <= duty_cycle[0] * 1.01), f"Expected {duty_cycle[0]}%, got {result}"
            await ClockCycles(dut.clk, 5)

    dut._log.info("PWM Duty Cycle test completed successfully")






