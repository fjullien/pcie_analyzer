#!/usr/bin/env python3

# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

import csv
import random

from migen import *
from migen.fhdl import *

from litex.soc.interconnect.stream import *
from litex.soc.interconnect.stream_sim import *
from litex.soc.interconnect import csr
from litex.soc.interconnect import csr_bus

from pcie_analyzer.filters.filters import *
from pcie_analyzer.common import *

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

startup = [
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
        make_data(osetsType.DATA, 0, 0, 0x0000)
]

empty_1 = [
        make_data(osetsType.DATA, 0, 0, 0x0000)
]

skip = [
        make_data(osetsType.SKIP, 3, 3, 0xbc1c),
        make_data(osetsType.SKIP, 3, 3, 0x1c1c),
]

idle = [
        make_data(osetsType.IDLE, 3, 3, 0xbc7c),
        make_data(osetsType.IDLE, 3, 3, 0x7c7c),
]

fts = [
        make_data(osetsType.FTS, 3, 3, 0xbc3c),
        make_data(osetsType.FTS, 3, 3, 0x3c3c),
]

tlp = [
        make_data(osetsType.DATA, 0, 2, 0xfb11),
        make_data(osetsType.DATA, 0, 0, 0x0000),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0x1111),
        make_data(osetsType.DATA, 0, 0, 0x2222),
        make_data(osetsType.DATA, 0, 0, 0x3333),
        make_data(osetsType.DATA, 0, 0, 0x0000),
        make_data(osetsType.DATA, 0, 0, 0xAABB),
        make_data(osetsType.DATA, 0, 1, 0x00fd)
]


dllp = [
        make_data(osetsType.DATA, 0, 2, 0x5c11),
        make_data(osetsType.DATA, 0, 0, 0x0000),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0x1111),
        make_data(osetsType.DATA, 0, 0, 0x2222),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0x1111),
        make_data(osetsType.DATA, 0, 0, 0x2222),
        make_data(osetsType.DATA, 0, 0, 0x3333),
        make_data(osetsType.DATA, 0, 0, 0x0000),
        make_data(osetsType.DATA, 0, 0, 0xAABB),
        make_data(osetsType.DATA, 0, 1, 0x00fd)
]

unfinished_dllp = [
        make_data(osetsType.DATA, 0, 2, 0x5c11),
        make_data(osetsType.DATA, 0, 0, 0x0000),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0x1111),
        make_data(osetsType.DATA, 0, 0, 0x2222),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
]

unfinished_tlp = [
        make_data(osetsType.DATA, 0, 2, 0xfb11),
        make_data(osetsType.DATA, 0, 0, 0x0000),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0xAAAA),
        make_data(osetsType.DATA, 0, 0, 0x1111),
        make_data(osetsType.DATA, 0, 0, 0x2222),
        make_data(osetsType.DATA, 0, 0, 0x3333),
        make_data(osetsType.DATA, 0, 0, 0x4444),
]

last = 0
index = 0
j = 0
error = 0

def check_data(dut, data, log=False):
    global last
    global index
    global j
    global error

    valid = (yield dut.filter.source.valid)

    if valid:
        if j == len(data):
            print("---------------- ERROR -----------\n")
            print("Too much data received\n")
            print("---------------- ERROR -----------\n")
            exit()
        index += 1
        if index > 3:
          val = (yield dut.filter.source.data)
          if (yield dut.filter.source.time) == 0:
            if log:
                print("{:2} - {:04X} - expected = {:04X} - [{}]".format(index, val, data[j] & 0xffff, j))
            if (data[j] & 0xffff) != val:
                ts = (yield dut.filter.ts)
                print("---------------- ERROR -----------\n")
                print("Received {:04X} Expected {:04X} - {}\n".format(val, data[j] & 0xffff, ts))
                print("---------------- ERROR -----------\n")
                error = 1
            j += 1
          else:
            if log:
                print("{:2} - {:04X} - time".format(index, val))

    if ~valid & last & log:
        print("")

    last = valid

def generates_random_stream(number, tlp_dllp_max_size, filter_config):
    data_raw = []
    data_check = []
    unfinished = 0
    payload = 0
    data_raw += startup

    print("")

    for i in range(number):
        case = random.randint(0, 8)
        if case == 0:
            print("SKIP, ", end = '')
            unfinished = 0
            data_raw += skip
            if filter_config & 1:
                data_check += skip
        if case == 1:
            print("FTS, ", end = '')
            unfinished = 0
            data_raw += fts
            data_check += fts
        if case == 2:
            print("EMPTY, ", end = '')
            data_raw += empty_1
            if unfinished &  (payload < tlp_dllp_max_size - len(unfinished_tlp) + 2):
                payload += 1
                data_check += empty_1
        if case == 3:
            print("IDLE, ", end = '')
            for k in range(random.randint(0, 256)):
                data_raw += empty_1
                if unfinished &  (payload < tlp_dllp_max_size - len(unfinished_tlp) + 2):
                    payload += 1
                    data_check += empty_1
        if case == 4:
            print("TLP, ", end = '')
            unfinished = 0
            data_raw += tlp
            data_check += tlp
        if case == 5:
            print("DLLP, ", end = '')
            unfinished = 0
            data_raw += tlp
            data_check += tlp
        if case == 6:
            print("IDLE, ", end = '')
            unfinished = 0
            data_raw += idle
            data_check += idle
        if case == 7:
            print("UNFINISHED TLP, ", end = '')
            unfinished = 1
            payload = 0
            data_raw += unfinished_tlp
            data_check += unfinished_tlp
        if case == 8:
            unfinished = 1
            payload = 0
            print("UNFINISHED DLLP, ", end = '')
            data_raw += unfinished_dllp
            data_check += unfinished_dllp

    # We don't want to finish on an unfinished packet
    data_raw += skip
    if filter_config & 1:
        data_check += skip

    data_raw += startup

    print("")
    print("")

    return (data_raw, data_check)

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

tlp_dllp_max_size = 32
filter_config = 0xfffffffe

def main_generator(dut):
    global error
    yield from dut.filter.filterEnable.write(1)
    yield from dut.filter.filterConfig.write(filter_config)

    (data, check) = generates_random_stream(200, tlp_dllp_max_size, filter_config)

    # ~ data = startup + unfinished_tlp + startup + startup + startup + startup + startup + startup
    # ~ check = unfinished_tlp
    # ~ for i in range(26):
        # ~ check += empty_1

    packet = Packet(data)
    dut.streamer.send(packet)

    yield from dut.filter.tlpDllpTimeoutCnt.write(tlp_dllp_max_size)

    for i in range(len(data) + 100):
        yield dut.filter.ts.eq((yield dut.filter.ts) + 1)
        yield from check_data(dut, check, 0)
        if error:
            yield
            yield
            yield
            exit()
        yield

    if j == len(check):
        print("---------------- FINISHED OK -----------\n")
    else:
        print("---------------- ERROR -----------\n")
        print("Missing datas\n")
        print("---------------- ERROR -----------\n")

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
