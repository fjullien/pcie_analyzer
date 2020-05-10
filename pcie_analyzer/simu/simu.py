#!/usr/bin/env python3

# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

import csv

from migen import *
from migen.fhdl import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *

from litedram.common import LiteDRAMNativePort

from pcie_analyzer.capture_pipeline.capture_pipeline import *
from pcie_analyzer.common import *

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
mem_data =    [(0, make_mem_data(0b00, 0b11, 0xbc1c)),
               # ~ (1, make_mem_data(0b11, 0b00, 0x4a4a)),
               # ~ (2, make_mem_data(0b11, 0b00, 0x00BB)),
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
        case = random.randint(0, 6)
        if case == 0:
            print("SKIP, ", end = '')
            data_raw += skip
        if case == 1:
            print("IDLE, ", end = '')
            for k in range(random.randint(1, 128)):
                data_raw += idle
        if case == 2:
            print("FTS, ", end = '')
            data_raw += fts
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

class TB(Module):
    def __init__(self):
        self.submodules.rx_streamer = PacketStreamer(gtp_layout)
        self.submodules.tx_streamer = PacketStreamer(gtp_layout)
        self.time = 0

        # ---------- RX -------------
        RX_RING_BUFFER_BASE_ADDRESS = 0
        RX_RING_BUFFER_SIZE         = 0x100000

        rx_port = LiteDRAMNativePort("write", address_width=32, data_width=256)

        self.submodules.rx_capture = CapturePipeline("sys",
                                                     rx_port,
                                                     RX_RING_BUFFER_BASE_ADDRESS,
                                                     RX_RING_BUFFER_SIZE)

        self.specials.rx_trig_wrport = self.rx_capture.trigger.mem.get_port(write_capable=True, clock_domain="sys")

        # ---------- TX -------------
        TX_RING_BUFFER_BASE_ADDRESS = 0x100000
        TX_RING_BUFFER_SIZE         = 0x100000

        tx_port = LiteDRAMNativePort("write", address_width=32, data_width=256)

        self.submodules.tx_capture = CapturePipeline("sys",
                                                     tx_port,
                                                     TX_RING_BUFFER_BASE_ADDRESS,
                                                     TX_RING_BUFFER_SIZE)

        self.specials.tx_trig_wrport = self.tx_capture.trigger.mem.get_port(write_capable=True, clock_domain="sys")

        self.comb += [
            self.tx_capture.forced.eq(self.rx_capture.record),
            self.rx_capture.forced.eq(self.tx_capture.record),
            
            self.tx_capture.trigExt.eq(self.rx_capture.trigOut),
            self.rx_capture.trigExt.eq(self.tx_capture.trigOut),

            self.rx_streamer.source.connect(self.rx_capture.sink),
            self.tx_streamer.source.connect(self.tx_capture.sink),
            
            
            
            
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
        gtp_rx_data = generates_random_stream(50)
        rx_packet = Packet(gtp_rx_data)
        gtp_tx_data = generates_random_stream(50)
        tx_packet = Packet(gtp_tx_data)

    yield from dut.rx_capture.simu.write(0)
    yield from dut.tx_capture.simu.write(0)

    # Fill trigger memory
    for (addr, dat) in mem_data:
        yield dut.rx_trig_wrport.adr.eq(addr)
        yield dut.rx_trig_wrport.dat_w.eq(dat)
        yield dut.rx_trig_wrport.we.eq(1)
        yield
    yield dut.rx_trig_wrport.we.eq(0)

    # Arm trigger
    yield from dut.rx_capture.trigger.size.write(len(mem_data))
    yield from dut.rx_capture.trigger.armed.write(1)

    dut.rx_streamer.send(rx_packet)
    dut.tx_streamer.send(tx_packet)
 
    # Configure and enable filter
    yield from dut.rx_capture.filter.filterConfig.write(0xffffffff)
    yield from dut.rx_capture.filter.tlpDllpTimeoutCnt.write(32)
    yield from dut.rx_capture.filter.filterEnable.write(1)

    yield from dut.tx_capture.filter.filterConfig.write(0xffffffff)
    yield from dut.tx_capture.filter.tlpDllpTimeoutCnt.write(32)
    yield from dut.tx_capture.filter.filterEnable.write(1)

    # Record mod 0 = RAW, 1 = FRAME
    yield from dut.rx_capture.recorder.mode.write(1)

    # Trigger offset from the storage windows start (a.k.a pre trigger size)
    yield from dut.rx_capture.recorder.offset.write(10)

    # Post trigger size
    yield from dut.rx_capture.recorder.size.write(10)

    # Start recorder
    yield from dut.rx_capture.recorder.start.write(1)

    # Time stamp generator for filter
    for i in range(max(len(values), len(gtp_rx_data))):      
        yield dut.rx_capture.time.eq((yield dut.rx_capture.time) + 1)
        yield dut.tx_capture.time.eq((yield dut.tx_capture.time) + 1)
 #       if i == 200:
 #           yield from dut.rx_capture.recorder.stop.write(1)
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
                   tb.rx_streamer.generator(),
                   tb.tx_streamer.generator()]
    }
    clocks = {"sys": 10}

    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
