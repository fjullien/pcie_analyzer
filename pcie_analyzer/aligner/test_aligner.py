#!/usr/bin/env python3

# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *
from migen.fhdl import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from aligner import *

import sys
sys.path.append("..")
from common import *

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************
def make_data(typ, osets, ctrl, data):
    return (typ << 20) + (osets << 18) + (ctrl << 16) + data


# *********************************************************
# *                                                       *
# *                  Simulation datas                     *
# *                                                       *
# *********************************************************

# data -------------------+
# ctrl -------------+     |
# ostets --------+  |     |
# type   -----+  |  |     |
#             |  |  |     |
#             v  v  v     v
data = [
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    # UNALIGNED
    make_data(1, 1, 1, 0x00bc),
    make_data(1, 3, 3, 0x1c1c),
    make_data(1, 2, 2, 0x1c00),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 1, 0x00bc),
    make_data(0, 0, 3, 0x1c1c),
    make_data(0, 0, 2, 0x1c00),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 1, 0x00bc),
    make_data(0, 0, 3, 0x1c1c),
    make_data(0, 0, 3, 0x1cbc),
    make_data(0, 0, 3, 0x1c1c),
    make_data(0, 0, 2, 0x1c00),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x8899),
    make_data(0, 0, 0, 0x7766),
    make_data(0, 0, 0, 0x1122),
    make_data(0, 0, 0, 0xaabb),
    make_data(0, 0, 3, 0xbc1c),
    make_data(0, 0, 3, 0x1c1c),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0xccdd),
    make_data(0, 0, 3, 0xbc1c),
    make_data(0, 0, 3, 0x1c1c),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 0, 0x0000),
    make_data(0, 0, 1, 0x00bc),
    make_data(0, 0, 3, 0x1c1c),
    make_data(0, 0, 3, 0x1cbc),
    make_data(0, 0, 3, 0x1c1c),
    make_data(0, 0, 2, 0x1c00),
    make_data(0, 0, 0, 0x0000),



]

# *********************************************************
# *                                                       *
# *                     Test bench                        *
# *                                                       *
# *********************************************************

class TB(Module):
    def __init__(self):

        self.submodules.streamer = PacketStreamer(descrambler_layout)
        self.submodules.aligner = Aligner()

        self.comb += [
            self.streamer.source.connect(self.aligner.sink),
            self.aligner.source.ready.eq(1),
        ]

# *********************************************************
# *                                                       *
# *                         Main                          *
# *                                                       *
# *********************************************************

def main_generator(dut):

    packet = Packet(data)
    dut.streamer.send(packet)

    for i in range(200):
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
