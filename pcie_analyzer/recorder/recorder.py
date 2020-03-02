# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import stream

from litedram.frontend.dma import LiteDRAMDMAWriter

import sys
sys.path.append("..")
from common import *

# *********************************************************
# *                                                       *
# *                     Recorder                          *
# *                                                       *
# *********************************************************

class RingRecorder(Module, AutoCSR):
    def __init__(self, dram_port, base, length):
        self.start    = CSR()             # Start recorder
        self.stop     = CSR()             # Stop recorder
        self.finished = CSRStatus()       # Capture finished
        self.size     = CSRStorage(32)    # Post trigger size
        self.offset   = CSRStorage(32)    # Trigger offset

        self.trigAddr = Signal(32)
        self.enable   = Signal()

        self.source = source = stream.Endpoint([("address", dram_port.address_width),
                                                ("data", dram_port.data_width)])
        self.sink   = sink   = stream.Endpoint(trigger_layout)

        # # #

        addr     = Signal(32)
        count    = Signal(32)
        addrIncr = dram_port.data_width//8

        self.submodules.stride = stream.StrideConverter(trigger_layout, recorder_layout, reverse=False)
        self.submodules.fifo   = ResetInserter()(stream.SyncFIFO(recorder_layout, 1024, buffered=True))

        self.comb += [
            sink.connect(self.stride.sink, omit={"valid"}),
            self.stride.source.connect(self.fifo.sink),
            source.address.eq(addr),
            source.data.eq(self.fifo.source.payload.raw_bits()),
            self.stride.sink.valid.eq(self.enable),
        ]

        # FSM
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        fsm.act("IDLE",
            self.fifo.reset.eq(1),
            NextValue(addr, base),
            NextValue(count, 0),
            If(self.start.re,
                NextValue(self.finished.status, 0),
                NextValue(self.enable, 1),
                NextState("FILL_PRE_TRIG")
            )
        )

        fsm.act("FILL_PRE_TRIG",
            source.valid.eq(self.fifo.source.valid),
            self.fifo.source.ready.eq(source.ready),
            If(source.valid & source.ready,
                NextValue(addr, addr + addrIncr),
                NextValue(count, count + 1),
                If(count == self.offset.storage,
                    NextValue(count, 0),
                    NextState("WAIT_TRIGGER")
                )
            )
        )

        fsm.act("WAIT_TRIGGER",
            source.valid.eq(self.fifo.source.valid),
            self.fifo.source.ready.eq(source.ready),
            If(source.valid & source.ready,
                NextValue(addr, addr + addrIncr),
                If(addr == (base + length - addrIncr),
                    NextValue(addr, base),
                ),
                If(self.fifo.source.trig != 0,
                    NextValue(self.trigAddr, addr),
                    NextState("FILL_POST_TRIG")
                )
            )
        )

        fsm.act("FILL_POST_TRIG",
            source.valid.eq(self.fifo.source.valid),
            self.fifo.source.ready.eq(source.ready),
            If(source.valid & source.ready,
                NextValue(addr, addr + addrIncr),
                If(addr == (base + length - addrIncr),
                    NextValue(addr, base),
                ),
                NextValue(count, count + 1),
                If(count == self.size.storage,
                    NextState("DONE")
                )
            )
        )

        fsm.act("DONE",
            NextValue(self.enable, 0),
            NextValue(self.finished.status, 1),
            If(self.stop.re,

                NextState("IDLE")
            )
        )

