#!/usr/bin/env python3

# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

import csv

from migen import *
from migen.fhdl import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from descrambler import *

values=[]

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************

def load_values(dump):
    first = True
    f = open(dump, "r")
    reader = csv.reader(f)
    for row in reader:
        if first:
            first = False
            continue
        data = int('0x' + row[5], 16)
        ctrl = int('0x' + row[4], 16)
        values.append((ctrl << 16) + data)

def make_data(ctrl, data):
    return (ctrl << 16) + data

# *********************************************************
# *                                                       *
# *                  Simulation datas                     *
# *                                                       *
# *********************************************************

# data -------------+
#                   |
# ctrl -------+     |
#             |     |
#             v     v
gtp_data = [
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(3, 0xbc1c),
    make_data(3, 0x1c1c),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(1, 0x00bc),
    make_data(3, 0x1c1c),
    make_data(3, 0xbc1c),
    make_data(3, 0x1c1c),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
]

# *********************************************************
# *                                                       *
# *                     Test bench                        *
# *                                                       *
# *********************************************************

class TB(Module):
    def __init__(self):
        self.submodules.streamer = PacketStreamer([("data", 18)])

        self.submodules.descrambler = Descrambler()
        self.submodules.detect = DetectOrderedSets()

        self.comb += [
        
            self.detect.sink.data.eq(self.streamer.source.data[0:16]),
            self.detect.sink.ctrl.eq(self.streamer.source.data[16:18]),
            self.detect.sink.valid.eq(1),

            self.streamer.source.ready.eq(1),
            self.descrambler.sink.valid.eq(1),
            self.descrambler.sink.data.eq(self.detect.source.data),
            self.descrambler.sink.ctrl.eq(self.detect.source.ctrl),
            self.descrambler.sink.osets.eq(self.detect.source.osets),
            self.descrambler.sink.type.eq(self.detect.source.type),
            self.descrambler.source.ready.eq(1),
        ]

# *********************************************************
# *                                                       *
# *                         Main                          *
# *                                                       *
# *********************************************************

def main_generator(dut, csv=False):
    if csv:
        load_values("./reset.csv")
        packet = Packet(values)
    else:
        packet = Packet(gtp_data)

    dut.streamer.send(packet)

    for i in range(max(len(values), len(gtp_data))):
        yield

# *********************************************************
# *                                                       *
# *                   Run simulation                      *
# *                                                       *
# *******************************************************

if __name__ == "__main__":
    tb = TB()
    generators = {
        "sys" :   [main_generator(tb, csv=True),
                   tb.streamer.generator()]
    }
    clocks = {"sys": 10}

    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
