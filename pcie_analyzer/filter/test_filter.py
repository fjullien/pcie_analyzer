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

from filters import *

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

# data ------------------------------------+
# ctrl ------------------------------+     |
# osets --------------------------+  |     |
# type -----------------+         |  |     |
#                       |         |  |     |
#                       v         v  v     v
data = [
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0x1c1c),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0x1c1c),
    # ~ make_data(osetsType.FTS,  3, 3, 0xbc3c),
    # ~ make_data(osetsType.FTS,  3, 3, 0x3c3c),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.TS1,  3, 3, 0xbc11),
    # ~ make_data(osetsType.TS1,  3, 3, 0x2233),
    # ~ make_data(osetsType.TS1,  3, 3, 0x4455),
    # ~ make_data(osetsType.TS1,  3, 3, 0x4a4a),
    # ~ make_data(osetsType.TS1,  3, 3, 0x4a4a),
    # ~ make_data(osetsType.TS1,  3, 3, 0x4a4a),
    # ~ make_data(osetsType.TS1,  3, 3, 0x4a4a),
    # ~ make_data(osetsType.TS1,  3, 3, 0x4a4a),
    # ~ make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0x1c1c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0x1c1c),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 2, 0xfb11),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAABB),
    # ~ make_data(osetsType.DATA, 0, 1, 0x00fd),
    # ~ make_data(osetsType.DATA, 0, 2, 0xfb22),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xbc1c),
    make_data(osetsType.DATA, 0, 0, 0x2255),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.FTS,  3, 3, 0xbc3c),
    # ~ make_data(osetsType.FTS,  3, 3, 0x3c3c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0x1c1c),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 2, 0xfb11),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAAAA),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0xAABB),
    # ~ make_data(osetsType.DATA, 0, 1, 0x00fd),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.DATA, 0, 0, 0x0000),
    # ~ make_data(osetsType.FTS,  3, 3, 0xbc3c),
    # ~ make_data(osetsType.FTS,  3, 3, 0x3c3c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    # ~ make_data(osetsType.SKIP, 3, 3, 0x1c1c),

    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),

    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),

    make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    make_data(osetsType.SKIP, 3, 3, 0x1c1c),
    make_data(osetsType.FTS,  3, 3, 0xbc3c),
    make_data(osetsType.FTS,  3, 3, 0x3c3c),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),

    make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    make_data(osetsType.SKIP, 3, 3, 0x1c1c),
    make_data(osetsType.DATA, 0, 2, 0xfb11),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0x1111),
    make_data(osetsType.DATA, 0, 0, 0x2222),
    make_data(osetsType.DATA, 0, 0, 0x3333),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xAABB),
    make_data(osetsType.DATA, 0, 1, 0x00fd),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 2, 0xfb11),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0x1111),
    make_data(osetsType.DATA, 0, 0, 0x2222),
    make_data(osetsType.DATA, 0, 0, 0x3333),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xAABB),
    make_data(osetsType.DATA, 0, 1, 0x00fd),
    make_data(osetsType.SKIP, 3, 3, 0xbc1c),
    make_data(osetsType.SKIP, 3, 3, 0x1c1c),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 2, 0x5c11),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0x1111),
    make_data(osetsType.DATA, 0, 0, 0x2222),
    make_data(osetsType.DATA, 0, 0, 0x3333),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xAABB),
    make_data(osetsType.DATA, 0, 1, 0x00fd),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 2, 0xfb11),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0xAAAA),
    make_data(osetsType.DATA, 0, 0, 0x1111),
    make_data(osetsType.DATA, 0, 0, 0x2222),
    make_data(osetsType.DATA, 0, 0, 0x3333),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0xAABB),
    make_data(osetsType.DATA, 0, 1, 0x00fd),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
    make_data(osetsType.DATA, 0, 0, 0x0000),
]

# *********************************************************
# *                                                       *
# *                     Test bench                        *
# *                                                       *
# *********************************************************

class TB(Module):
    def __init__(self):

        self.submodules.streamer = PacketStreamer(descrambler_layout)
        self.submodules.filter = Filter("sys", 128)

        self.comb += [
            self.streamer.source.connect(self.filter.sink),
            self.filter.source.ready.eq(1),
        ]

# *********************************************************
# *                                                       *
# *                         Main                          *
# *                                                       *
# *********************************************************

def main_generator(dut):

    packet = Packet(data)
    dut.streamer.send(packet)

    yield from dut.filter.filterConfig.write(4)

    for i in range(150):
        if i == 20:
            yield from dut.filter.filterEnable.write(1)
        yield dut.filter.ts.eq((yield dut.filter.ts) + 1)
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
