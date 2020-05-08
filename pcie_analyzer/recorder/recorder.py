# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *
from migen.genlib.cdc import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import stream

from litedram.frontend.dma import LiteDRAMDMAWriter

from pcie_analyzer.common import *

# *********************************************************
# *                                                       *
# *                     Recorder                          *
# *                                                       *
# *********************************************************

class RingRecorder(Module, AutoCSR):
    def __init__(self, clock_domain, dram_port, base, length, nb):
        
        # *********************************************************
        # *                    Interface                          *
        # *********************************************************
        self.start    = CSR()             # Start recorder
        self.stop     = CSR()             # Stop recorder
        self.finished = CSRStatus()       # Capture finished
        self.size     = CSRStorage(32)    # Post trigger size
        self.offset   = CSRStorage(32)    # Trigger offset
        self.trigAddr = CSRStatus(32)     # Trigger storage address
        self.state    = CSRStatus(3)      # Etats FSM
        self.count    = CSRStatus(32)     # Post trigger bytes count

        self.base     = CSRConstant(base)
        self.length   = CSRConstant(length)
        self.nb       = CSRConstant(nb)
        self.dw       = CSRConstant(dram_port.data_width)

        self.enableTrigger   = Signal()          # Signal to enable the trigger
        self.forced   = Signal()          # Another recorder ask us to record datas
        self.record   = Signal()          # Start the other recorder

        self.source = source = stream.Endpoint([("address", dram_port.address_width),
                                                ("data", dram_port.data_width)])
        self.sink   = sink   = stream.Endpoint(trigger_layout)

        # *********************************************************
        # *                      Signals                          *
        # *********************************************************
        addr      = Signal(dram_port.address_width)
        first     = Signal()

        _count    = Signal(32)
        _start    = Signal()
        _stop     = Signal()
        _finished = Signal()
        _size     = Signal(32)
        _offset   = Signal(32)
        _trigAddr = Signal(32)
        _state    = Signal(3)
        _forced   = Signal()

        # *********************************************************
        # *                      Constants                        *
        # *********************************************************
        addrIncr = dram_port.data_width//8

        # *********************************************************
        # *                         CDC                           *
        # *********************************************************
        self.specials += MultiReg(self.start.re, _start, clock_domain)
        self.specials += MultiReg(self.stop.re, _stop, clock_domain)
        self.specials += MultiReg(_finished, self.finished.status, "sys")
        self.specials += MultiReg(self.size.storage, _size, clock_domain)
        self.specials += MultiReg(self.offset.storage, _offset, clock_domain)
        self.specials += MultiReg(_trigAddr, self.trigAddr.status, "sys")
        self.specials += MultiReg(_state, self.state.status, "sys")
        self.specials += MultiReg(_count, self.count.status, "sys")
        self.specials += MultiReg(self.forced, _forced, clock_domain)

        # *********************************************************
        # *                     Submodules                        *
        # *********************************************************
        stride = ResetInserter()(stream.StrideConverter(trigger_layout, recorder_layout(nb), reverse=False))
        self.submodules.stride = ClockDomainsRenamer(clock_domain)(stride)

        fifo = ResetInserter()(stream.SyncFIFO(recorder_layout(nb), 1024, buffered=True))
        self.submodules.fifo   = ClockDomainsRenamer(clock_domain)(fifo)

        # *********************************************************
        # *                    Combinatorial                      *
        # *********************************************************
        self.comb += [
            sink.connect(self.stride.sink, omit={"valid"}),
            self.stride.source.connect(self.fifo.sink),
            source.address.eq(addr[log2_int(addrIncr):32]),
            source.data.eq(self.fifo.source.payload.raw_bits()),
            self.stride.sink.valid.eq(sink.valid),
            source.data[-1].eq(first), # The MSb indicates the start of the recording
                                       # In case we read data back, and this bit is set, we know
                                       # we didn't cycle over the circular buffer
        ]

        # *********************************************************
        # *                        FSM                            *
        # *********************************************************
        fsm = FSM(reset_state="IDLE")
        self.submodules.fsm = ClockDomainsRenamer(clock_domain)(fsm)

        fsm.act("IDLE",
            NextValue(_state, 0),
            self.fifo.reset.eq(1),
            NextValue(addr, base),
            NextValue(_count, 0),
            NextValue(self.record, 0),
            If(_start,
                NextValue(_finished, 0),
                NextState("FILL_PRE_TRIG"),
                NextValue(self.record, 1),
                NextValue(first, 1),
                self.stride.reset.eq(1),
            ),
            If(_forced,
                NextValue(_finished, 0),
                NextValue(self.enableTrigger, 1),
                NextState("FORCED"),
                NextValue(first, 1),
            ),
        )

        fsm.act("FILL_PRE_TRIG",
            NextValue(_state, 1),
            source.valid.eq(self.fifo.source.valid),
            self.fifo.source.ready.eq(source.ready),

            If(_count == _offset,
                NextValue(_count, 0),
                NextValue(self.enableTrigger, 1),
                NextState("WAIT_TRIGGER")
            ).Else(
                If(source.valid & source.ready,
                    NextValue(first, 0),
                    NextValue(addr, addr + addrIncr),
                    NextValue(_count, _count + addrIncr),
                )
            )
        )

        fsm.act("WAIT_TRIGGER",
            NextValue(_state, 2),
            source.valid.eq(self.fifo.source.valid),
            self.fifo.source.ready.eq(source.ready),
            If(source.valid & source.ready,
                NextValue(addr, addr + addrIncr),
                If(addr == (base + length - addrIncr),
                    NextValue(addr, base),
                ),
                If(self.fifo.source.trig != 0,
                    NextValue(_count, 0),
                    NextValue(_trigAddr, addr),
                    NextState("FILL_POST_TRIG")
                )
            ),
            If(_stop,
                NextState("ABORT")
            )
        )

        fsm.act("FILL_POST_TRIG",
            NextValue(_state, 3),
            source.valid.eq(self.fifo.source.valid),
            self.fifo.source.ready.eq(source.ready),
            If(source.valid & source.ready,
                NextValue(addr, addr + addrIncr),
                If(addr == (base + length - addrIncr),
                    NextValue(addr, base),
                ),
                NextValue(_count, _count + addrIncr),
                If(_count == _size,
                    NextState("DONE")
                )
            ),
            If(_stop,
                NextState("ABORT")
            )
        )

        fsm.act("DONE",
            NextValue(_state, 4),
            NextValue(self.enableTrigger, 0),
            NextValue(_finished, 1),
            If(_stop,
                NextState("IDLE")
            )
        )

        fsm.act("ABORT",
            NextValue(_state, 5),
            NextValue(self.enableTrigger, 0),
            NextValue(_finished, 1),
            NextState("IDLE")
        )

        fsm.act("FORCED",
            NextValue(_state, 6),
            source.valid.eq(self.fifo.source.valid),
            self.fifo.source.ready.eq(source.ready),
            If(source.valid & source.ready,
                NextValue(first, 0),
                NextValue(addr, addr + addrIncr),
                If(addr == (base + length - addrIncr),
                    NextValue(addr, base),
                ),
            ),
            If(_forced == 0,
                NextValue(self.enableTrigger, 0),
                NextValue(_finished, 1),
                NextState("IDLE"),
            )
        )
