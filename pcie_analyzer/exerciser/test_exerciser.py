#!/usr/bin/env python3

# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

import csv

from migen import *
from migen.fhdl import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from pcie_analyzer.exerciser.exerciser import *
from pcie_analyzer.descrambler.descrambler import *

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************

def make_mem_data(dc, ctrl, data):
    return (dc << 18) + (ctrl << 16) + data

# *********************************************************
# *                                                       *
# *                  Simulation datas                     *
# *                                                       *
# *********************************************************

#  data       ---------------------------------+
#  ctrl       --------------------------+      |
#  osets      ----------------------+   |      |
#  address    --+                   |   |      |
#               |                   |   |      |
#               v                   v   v      v
mem_data =    [(0, make_mem_data(0b00, 0b00, 0x1122)),
               (1, make_mem_data(0b00, 0b00, 0x3344)),
               (2, make_mem_data(0b00, 0b00, 0x5566)),
               (3, make_mem_data(0b00, 0b00, 0x7788)),
]

# *********************************************************
# *                                                       *
# *                     Test bench                        *
# *                                                       *
# *********************************************************

class TB(Module):
    def __init__(self):

        self.submodules.exerciser = Exerciser("sys")
        self.submodules.descrambler_test = Descrambler("sys")
        self.submodules.detect = DetectOrderedSets()

        self.specials.wrport = self.exerciser.mem.get_port(write_capable=True, clock_domain="sys")

        self.comb += [
            self.detect.sink.data.eq(self.exerciser.source.data),
            self.detect.sink.ctrl.eq(self.exerciser.source.ctrl),
            self.detect.sink.valid.eq(self.exerciser.source.valid),

            self.descrambler_test.sink.valid.eq(1),
            self.descrambler_test.sink.data.eq(self.detect.source.data),
            self.descrambler_test.sink.ctrl.eq(self.detect.source.ctrl),
            self.descrambler_test.sink.osets.eq(self.detect.source.osets),
            self.descrambler_test.sink.type.eq(self.detect.source.type),
            self.descrambler_test.source.ready.eq(1),
        ]

# *********************************************************
# *                                                       *
# *                         Main                          *
# *                                                       *
# *********************************************************

def main_generator(dut):

    # Fill insert memory
    for (addr, dat) in mem_data:
        yield dut.wrport.adr.eq(addr)
        yield dut.wrport.dat_w.eq(dat)
        yield dut.wrport.we.eq(1)
        yield
    yield dut.wrport.we.eq(0)

    # Configure insert size
    yield from dut.exerciser.size.write(len(mem_data))

    for i in range(400):
        if (i == 180):
            yield from dut.exerciser.insert.write(1)
        if (i == 250):
            yield from dut.exerciser.insert.write(0)
        yield

# *********************************************************
# *                                                       *
# *                   Run simulation                      *
# *                                                       *
# *******************************************************

if __name__ == "__main__":
    tb = TB()
    generators = {
        "sys" :   [main_generator(tb)]
    }
    clocks = {"sys": 10}

    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
