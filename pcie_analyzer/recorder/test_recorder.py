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
    for i in range(2000):
        trig = 0
        if i == 250:
            trig = 1
        if i == 1200:
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

        RX_RING_BUFFER_BASE_ADDRESS = 0
        RX_RING_BUFFER_SIZE         = 0x1000

        TX_RING_BUFFER_BASE_ADDRESS = 0x1000
        TX_RING_BUFFER_SIZE         = 0x1000

        # Number of trigger_layout we want to put in recorder_layout
        STRIDE_MULTIPLIER        = 12

        self.submodules.rx_streamer = PacketStreamer(trigger_layout)
        self.submodules.rx_recorder = RingRecorder("sys", port, RX_RING_BUFFER_BASE_ADDRESS, RX_RING_BUFFER_SIZE, STRIDE_MULTIPLIER)
        self.submodules.tx_streamer = PacketStreamer(trigger_layout)
        self.submodules.tx_recorder = RingRecorder("sys", port, TX_RING_BUFFER_BASE_ADDRESS, TX_RING_BUFFER_SIZE, STRIDE_MULTIPLIER)

        self.comb += [
            self.rx_streamer.source.connect(self.rx_recorder.sink),
            self.tx_streamer.source.connect(self.tx_recorder.sink),
            self.tx_recorder.force.eq(self.rx_recorder.enable),
            self.rx_recorder.force.eq(self.tx_recorder.enable),
        ]

# *********************************************************
# *                                                       *
# *                         Main                          *
# *                                                       *
# *********************************************************

def main_generator(dut):

    fill_data_list()

    packet = Packet(data_list)
    dut.rx_streamer.send(packet)
    dut.tx_streamer.send(packet)

    yield from dut.rx_recorder.offset.write(0x200)
    yield from dut.rx_recorder.size.write(0x100)

    yield from dut.tx_recorder.offset.write(0xc0)
    yield from dut.tx_recorder.size.write(0x100)

    yield dut.tx_recorder.source.ready.eq(1)

    delay = 0

    for i in range(1500):
        if i == 20:
            yield from dut.rx_recorder.start.write(1)
            
        if (i > 150) and (i < 200):
            yield dut.rx_recorder.source.ready.eq(0)
        else:
            yield dut.rx_recorder.source.ready.eq(1)

        if (yield dut.rx_recorder.finished.status):
            delay = delay + 1
            if (delay == 100):
                yield from dut.rx_recorder.stop.write(1)

        if i == 1000:
            yield from dut.tx_recorder.start.write(1)
        if (yield dut.tx_recorder.finished.status):
            delay = delay + 1
            if (delay == 100):
                yield from dut.tx_recorder.stop.write(1)

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
                   tb.rx_streamer.generator(),
                   tb.tx_streamer.generator()]
    }
    clocks = {"sys": 10}

    run_simulation(tb, generators, clocks, vcd_name="sim.vcd")
