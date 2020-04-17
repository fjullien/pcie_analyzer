#!/usr/bin/env python3

# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

import csv

from migen import *
from migen.fhdl import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *
from litex.soc.interconnect import csr
from litex.soc.interconnect import csr_bus

from pcie_analyzer.trigger.trigger import *
from pcie_analyzer.common import *

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************

def make_data(time, ctrl, data):
    return (time << 18) + (ctrl << 16) + data

def make_mem_data(dc, ctrl, data):
    return (dc << 18) + (ctrl << 16) + data

# *********************************************************
# *                                                       *
# *                  Simulation datas                     *
# *                                                       *
# *********************************************************

# data ----------------+
# ctrl ----------+     |
# time -------+  |     |
#             |  |     |
#             |  |     |
#             v  v     v
data = [
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 3, 0xbc1c),
    make_data(0, 3, 0x1c1c),
    make_data(0, 0, 0xAABB),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
    make_data(0, 1, 0x00bc),
    make_data(0, 3, 0x1c1c),
    make_data(0, 2, 0x1c00),
    make_data(0, 0, 0xbb1c),
    make_data(0, 0, 0x0000),
    make_data(0, 0, 0x0000),
]

#  data       ---------------------------------+
#  ctrl       --------------------------+      |
#  don't care ----------------------+   |      |
#  address    --+                   |   |      |
#               |                   |   |      |
#               v                   v   v      v
mem_data =    [(0, make_mem_data(0b01, 0b11, 0xbc1c)),
               (1, make_mem_data(0b11, 0b11, 0x1c1c)),
               (2, make_mem_data(0b11, 0b00, 0x00BB)),
]

# *********************************************************
# *                                                       *
# *                     Test bench                        *
# *                                                       *
# *********************************************************

class TB(Module):
    def __init__(self):

        self.submodules.streamer = PacketStreamer(filter_layout)
        self.submodules.trigger = Trigger("sys")

        self.specials.wrport = self.trigger.mem.get_port(write_capable=True, clock_domain="sys")

        self.comb += [
            self.streamer.source.connect(self.trigger.sink),
        ]

# *********************************************************
# *                                                       *
# *                         Main                          *
# *                                                       *
# *********************************************************

def main_generator(dut):

    # Fill trigger memory
    for (addr, dat) in mem_data:
        yield dut.wrport.adr.eq(addr)
        yield dut.wrport.dat_w.eq(dat)
        yield dut.wrport.we.eq(1)
        yield
    yield dut.wrport.we.eq(0)

    # Configure trigger
    yield from dut.trigger.size.write(len(mem_data))
    yield from dut.trigger.armed.write(1)

    packet = Packet(data)
    dut.streamer.send(packet)

    yield dut.trigger.enable.eq(1)
    yield dut.trigger.source.ready.eq(1)

    for i in range(1000):

        # If trigged, rearm
        if i == 50:
            yield dut.trigger.source.ready.eq(0)

        if((yield dut.trigger.trigged.status)):
            yield from dut.trigger.armed.write(0)
            yield from dut.trigger.armed.write(0)
            yield from dut.trigger.armed.write(0)
            yield from dut.trigger.armed.write(0)
            yield from dut.trigger.armed.write(0)
            yield from dut.trigger.armed.write(0)
            yield from dut.trigger.armed.write(1)
        yield

# *********************************************************
# *                                                       *
# *                   Run simulation                      *
# *                                                       *
# *********************************************************

if __name__ == "__main__":
    tb = TB()
    generators = {
        "sys" :   [main_generator(tb),
                   tb.streamer.generator()]
    }
    clocks = {"sys": 10}

    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
