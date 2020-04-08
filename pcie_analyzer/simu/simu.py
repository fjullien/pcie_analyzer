#!/usr/bin/env python3

# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

import csv

from migen import *
from migen.fhdl import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

import sys
sys.path.append("..")
from common import *
sys.path.append("../descrambler")
from descrambler import *
sys.path.append("../aligner")
from aligner import *
sys.path.append("../filter")
from filters import *
sys.path.append("../trigger")
from trigger import *
sys.path.append("../recorder")
from recorder import *

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
    return ((ctrl & 1) << 17)+ ((ctrl >> 1) << 16) + ((data << 8) & 0xff00) + (data >> 8)

def make_mem_data(dc, ctrl, data):
    return (dc << 18) + (ctrl << 16) + data

class DummyPort():
    def __init__(self, aw, dw):
        self.address_width = aw
        self.data_width = dw

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
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(1, 0x00bc),
    make_data(3, 0x1c1c),
    make_data(2, 0x1c00),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(1, 0x00bc),
    make_data(3, 0x1c1c),
    make_data(3, 0x1cfb),
    make_data(0, 0x0102),
    make_data(0, 0x0304),
    make_data(0, 0x0506),
    make_data(2, 0xfd00),
    make_data(0, 0x0000),
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
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
    make_data(0, 0x0000),
]

# *********************************************************
# *                                                       *
# *                  Simulation datas                     *
# *                                                       *
# *********************************************************

# data -----------------+
# ctrl -----------+     |
#                 |     |
#                 v     v
startup = [
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000),
        make_data(0, 0x0000)
]

idle = [
        make_data(0, 0x0000)
]

skip = [
        make_data(3, 0xbc1c),
        make_data(3, 0x1c1c),
]

fts = [
        make_data(3, 0xbc3c),
        make_data(3, 0x3c3c),
]

tlp = [
        make_data(2, 0xfb11),
        make_data(0, 0x0000),
        make_data(0, 0xAAAA),
        make_data(0, 0xAAAA),
        make_data(0, 0x1111),
        make_data(0, 0x2222),
        make_data(0, 0x3333),
        make_data(0, 0x0000),
        make_data(0, 0xAABB),
        make_data(1, 0x00fd)
]


dllp = [
        make_data(2, 0x5c11),
        make_data(0, 0x0000),
        make_data(0, 0xAAAA),
        make_data(0, 0xAAAA),
        make_data(0, 0x1111),
        make_data(0, 0x2222),
        make_data(0, 0xAAAA),
        make_data(0, 0xAAAA),
        make_data(0, 0x1111),
        make_data(0, 0x2222),
        make_data(0, 0x3333),
        make_data(0, 0x0000),
        make_data(0, 0xAABB),
        make_data(1, 0x00fd)
]

unfinished_dllp = [
        make_data(2, 0x5c11),
        make_data(0, 0x0000),
        make_data(0, 0xAAAA),
        make_data(0, 0xAAAA),
        make_data(0, 0x1111),
        make_data(0, 0x2222),
        make_data(0, 0xAAAA),
        make_data(0, 0xAAAA),
]

unfinished_tlp = [
        make_data(2, 0xfb11),
        make_data(0, 0x0000),
        make_data(0, 0xAAAA),
        make_data(0, 0xAAAA),
        make_data(0, 0x1111),
        make_data(0, 0x2222),
        make_data(0, 0x3333),
        make_data(0, 0x4444),
]

#  data       ---------------------------------+
#  ctrl       --------------------------+      |
#  don't care ----------------------+   |      |
#  address    --+                   |   |      |
#               |                   |   |      |
#               v                   v   v      v
mem_data =    [(0, make_mem_data(0b01, 0b10, 0x5c11)),
               (1, make_mem_data(0b11, 0b00, 0x4a4a)),
               (2, make_mem_data(0b11, 0b00, 0x00BB)),
]

# *********************************************************
# *                                                       *
# *                     Test bench                        *
# *                                                       *
# *********************************************************


def generates_random_stream(number):
    data_raw = []
    data_raw += startup

    print("")

    for i in range(number):
        case = random.randint(0, 7)
        if case == 0:
            print("SKIP, ", end = '')
            data_raw += skip
        if case == 1:
            print("FTS, ", end = '')
            data_raw += fts
        if case == 2:
            print("IDLE, ", end = '')
            for k in range(random.randint(1, 128)):
                data_raw += idle
        if case == 3:
            print("TLP, ", end = '')
            data_raw += tlp
        if case == 4:
            print("DLLP, ", end = '')
            data_raw += tlp
        if case == 5:
            print("UNFINISHED TLP, ", end = '')
            data_raw += unfinished_tlp
        if case == 6:
            print("UNFINISHED DLLP, ", end = '')
            data_raw += unfinished_dllp

    # We don't want to finish on an unfinished packet
    if case > 4:
        print("SKIP")
        data_raw += skip

    data_raw += startup

    print("")
    print("")

    return data_raw

RX_RING_BUFFER_BASE_ADDRESS = 0
RX_RING_BUFFER_SIZE         = 0x1000

# Number of trigger_layout we want to put in recorder_layout
STRIDE_MULTIPLIER        = 12

class TB(Module):
    def __init__(self):
        self.submodules.streamer = PacketStreamer(gtp_layout)

        self.submodules.descrambler = Descrambler("sys")
        self.submodules.detect = DetectOrderedSets()
        
        self.submodules.aligner = Aligner()
        
        self.submodules.filter = Filter("sys", 2048)

        self.submodules.trigger = Trigger("sys", 128)
        self.specials.wrport = self.trigger.mem.get_port(write_capable=True, clock_domain="sys")

        port = DummyPort(32, 256)
        self.submodules.rx_recorder = RingRecorder("sys", port, RX_RING_BUFFER_BASE_ADDRESS, RX_RING_BUFFER_SIZE, STRIDE_MULTIPLIER)

        self.comb += [
            self.streamer.source.connect(self.detect.sink),
            self.detect.source.connect(self.descrambler.sink),
            self.descrambler.source.connect(self.aligner.sink),
            self.aligner.source.connect(self.filter.sink),
            self.filter.source.connect(self.trigger.sink),
            self.trigger.source.connect(self.rx_recorder.sink),
            
            self.rx_recorder.source.ready.eq(1),
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
        gtp_data = generates_random_stream(50)
        packet = Packet(gtp_data)

    # Fill trigger memory
    for (addr, dat) in mem_data:
        yield dut.wrport.adr.eq(addr)
        yield dut.wrport.dat_w.eq(dat)
        yield dut.wrport.we.eq(1)
        yield
    yield dut.wrport.we.eq(0)

    # Arm trigger
    yield from dut.trigger.size.write(len(mem_data))
    yield from dut.trigger.armed.write(1)

    dut.streamer.send(packet)

    # Configure and enable filter
    yield from dut.filter.filterConfig.write(0xFFFFFFFE)
    yield from dut.filter.tlpDllpTimeoutCnt.write(32)
    yield from dut.filter.filterEnable.write(1)
    yield dut.trigger.enable.eq(1)

    # Trigger offset from the storage windows start (a.k.a pre trigger size)
    yield from dut.rx_recorder.offset.write(0)

    # Post trigger size
    yield from dut.rx_recorder.size.write(0x100)

    # Start recorder
    yield from dut.rx_recorder.start.write(1)

    # Time stamp generator for filter
    for i in range(max(len(values), len(gtp_data))):      
        yield dut.filter.ts.eq((yield dut.filter.ts) + 1)
        yield

# *********************************************************
# *                                                       *
# *                   Run simulation                      *
# *                                                       *
# *******************************************************

if __name__ == "__main__":
    tb = TB()
    generators = {
        "sys" :   [main_generator(tb, csv=False),
                   tb.streamer.generator()]
    }
    clocks = {"sys": 10}

    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
