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

from recorder import *

import sys
sys.path.append("..")
from common import *

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************

def make_data_stride(dataList):
    data = 0
    ctrl = 0
    trig = 0
    for _trig, _ctrl, _data in dataList:
        data = (data << 16) + _data
        ctrl = (ctrl << 2) + _ctrl
        trig = (trig << 1) + _trig
    retval = (trig << 216) + (ctrl << 192) + data
    #print("{:64x}".format(retval))
    #print("{:3x} {:6x} {:48x}".format(trig, ctrl, data))
    return retval

def make_data(trig, ctrl, data):
    return (trig << 18) + (ctrl << 16) + data

# *********************************************************
# *                                                       *
# *                  Simulation datas                     *
# *                                                       *
# *********************************************************

# data ---------------------+
# ctrl --------------+      |
# trig----------+    |      |
#               |    |      |
#               v    v      v
data_stride = [
    make_data_stride([(1, 0b10, 0xAA00),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (1, 0b01, 0x00BB)]),
    make_data_stride([(1, 0b10, 0xAA00),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (0, 0b00, 0x0000),
                      (1, 0b01, 0x00BB)]),
]

# data ----------------+
# ctrl ----------+     |
# trig -------+  |     |
#             |  |     |
#             v  v     v
data = [
    make_data(0, 0, 0x1111),
    make_data(0, 0, 0x1111),
    make_data(0, 0, 0x1111),
    make_data(0, 3, 0x1111),
    make_data(0, 3, 0x1111),
    make_data(0, 0, 0x1111),
    make_data(0, 0, 0x1111),
    make_data(0, 0, 0x1111),
    make_data(0, 0, 0x1111),
    make_data(0, 0, 0x1111),
    make_data(0, 0, 0x1111),
    make_data(0, 0, 0x1111),

    make_data(0, 0, 0x2222),
    make_data(0, 0, 0x2222),
    make_data(0, 0, 0x2222),
    make_data(0, 0, 0x2222),
    make_data(0, 0, 0x2222),
    make_data(0, 0, 0x2222),
    make_data(0, 1, 0x2222),
    make_data(0, 3, 0x2222),
    make_data(0, 3, 0x2222),
    make_data(0, 3, 0x2222),
    make_data(0, 0, 0x2222),
    make_data(0, 0, 0x2222),

    make_data(0, 0, 0x3333),
    make_data(0, 0, 0x3333),
    make_data(0, 0, 0x3333),
    make_data(0, 0, 0x3333),
    make_data(0, 0, 0x3333),
    make_data(0, 0, 0x3333),
    make_data(0, 1, 0x3333),
    make_data(0, 3, 0x3333),
    make_data(0, 3, 0x3333),
    make_data(0, 3, 0x3333),
    make_data(0, 0, 0x3333),
    make_data(0, 0, 0x3333),

    make_data(0, 0, 0x4444),
    make_data(0, 0, 0x4444),
    make_data(0, 0, 0x4444),
    make_data(0, 0, 0x4444),
    make_data(0, 0, 0x4444),
    make_data(0, 0, 0x4444),
    make_data(0, 1, 0x4444),
    make_data(0, 3, 0x4444),
    make_data(0, 3, 0x4444),
    make_data(0, 3, 0x4444),
    make_data(0, 0, 0x4444),
    make_data(0, 0, 0x4444),

    make_data(0, 0, 0x5555),
    make_data(0, 0, 0x5555),
    make_data(0, 0, 0x5555),
    make_data(0, 0, 0x5555),
    make_data(0, 0, 0x5555),
    make_data(0, 0, 0x5555),
    make_data(0, 1, 0x5555),
    make_data(0, 3, 0x5555),
    make_data(0, 3, 0x5555),
    make_data(0, 3, 0x5555),
    make_data(0, 0, 0x5555),
    make_data(0, 0, 0x5555),

    make_data(1, 0, 0x6666),
    make_data(0, 0, 0x6666),
    make_data(0, 0, 0x6666),
    make_data(0, 0, 0x6666),
    make_data(0, 0, 0x6666),
    make_data(0, 0, 0x6666),
    make_data(0, 1, 0x6666),
    make_data(0, 3, 0x6666),
    make_data(0, 3, 0x6666),
    make_data(0, 3, 0x6666),
    make_data(0, 0, 0x6666),
    make_data(0, 0, 0x6666),

]

data_list = []

def fill_data_list():
    for i in range(800):
        trig = 0
        if i == 180:
            trig = 1
        data_list.append(make_data(trig, 0b11, i))

# *********************************************************
# *                                                       *
# *                     Test bench                        *
# *                                                       *
# *********************************************************

class DummyPort():
    def __init__(self, aw, dw):
        self.address_width = aw
        self.data_width = dw

class TB(Module):
    def __init__(self):

        port = DummyPort(32, 256)

        RING_BUFFER_BASE_ADDRESS = 0x1000
        RING_BUFFER_SIZE         = 0x100

        # Number of trigger_layout we want to put in recorder_layout
        STRIDE_MULTIPLIER        = 12

        self.submodules.streamer = PacketStreamer(trigger_layout)
        self.submodules.recorder = RingRecorder("sys", port, RING_BUFFER_BASE_ADDRESS, RING_BUFFER_SIZE, STRIDE_MULTIPLIER)

        self.comb += [
            self.streamer.source.connect(self.recorder.sink),
        ]

# *********************************************************
# *                                                       *
# *                         Main                          *
# *                                                       *
# *********************************************************

def main_generator(dut):

    fill_data_list()

    packet = Packet(data_list)
    dut.streamer.send(packet)

    yield from dut.recorder.offset.write(4)

    delay = 0

    for i in range(1000):
        if i == 20:
            yield from dut.recorder.start.write(1)
            
        if (i > 150) and (i < 200):
            yield dut.recorder.source.ready.eq(0)
        else:
            yield dut.recorder.source.ready.eq(1)

        if (yield dut.recorder.finished.status):
            delay = delay + 1
            if (delay == 100):
                yield from dut.recorder.stop.write(1)
            if (delay == 150):
                yield from dut.recorder.start.write(1)

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
