# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *
from migen.genlib.cdc import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import stream

from litedram.frontend.dma import LiteDRAMDMAWriter

from pcie_analyzer.common import *
from pcie_analyzer.recorder.stream2 import StrideConverter2

# *********************************************************
# *                                                       *
# *                     Recorder                          *
# *                                                       *
# *********************************************************

class RingRecorder(Module, AutoCSR):
    def __init__(self, clock_domain, dram_port, base, length):

        # *********************************************************
        # *                    Interface                          *
        # *********************************************************
        self.start    = CSR()             # Start recorder
        self.stop     = CSR()             # Stop recorder
        self.finished = CSRStatus()       # Capture finished
        self.size     = CSRStorage(32)    # Post trigger size
        self.offset   = CSRStorage(32)    # Trigger offset (Pre trigger size)
        self.trigAddr = CSRStatus(32)     # Trigger storage address
        self.state    = CSRStatus(3)      # Etats FSM
        self.mode     = CSRStorage()      # 0 = RAW, 1 = FRAME
        self.preCount = CSRStatus(32)     # Frames written to memory
        self.postCount= CSRStatus(32)     # Frames written to memory

        self.base     = CSRConstant(base)
        self.length   = CSRConstant(length)
        self.dw       = CSRConstant(dram_port.data_width)

        self.enableTrigger = Signal()     # Signal to enable the trigger
        self.forced        = Signal()     # Another recorder ask us to record datas
        self.record        = Signal()     # Start the other recorder
        self.trigExt       = Signal()     # Another recorder has trigged

        self.source = source = stream.Endpoint([("address", dram_port.address_width),
                                                ("data", dram_port.data_width)])
        self.sink   = sink   = stream.Endpoint(trigger_layout)

        # *********************************************************
        # *                      Signals                          *
        # *********************************************************
        addr      = Signal(dram_port.address_width)
        first     = Signal()
        ext_trig  = Signal()
        count     = Signal(32)
        sof_count = Signal(3)

        _trigExt  = Signal()
        _start    = Signal()
        _stop     = Signal()
        _finished = Signal()
        _size     = Signal(32)
        _offset   = Signal(32)
        _trigAddr = Signal(32)
        _state    = Signal(3)
        _forced   = Signal()
        _mode     = Signal()
        _preCount = Signal(32)
        _postCount= Signal(32)
        
        # *********************************************************
        # *                      Constants                        *
        # *********************************************************
        ADDRINCR = dram_port.data_width//8

        # Count mode
        RAW_MODE   = 0
        FRAME_MODE = 1

        # Reserve 5 bits to indicate the number of valid chunks in record
        VALID_TOKEN_BITS = 5

        # Reserve 3 bits to indicate the number of SOF in this block
        SOF_COUNT_BITS = 3

        # Meta data position in DDR bloc write
        RECORD_START = -1

        VALID_TOKEN_COUNT_START = RECORD_START
        VALID_TOKEN_COUNT_END = RECORD_START - VALID_TOKEN_BITS
        VALID_TOKEN_COUNT = slice(VALID_TOKEN_COUNT_END,VALID_TOKEN_COUNT_START)

        TRIG_EXT = VALID_TOKEN_COUNT_END - 1

        SOF_COUNT_START = TRIG_EXT
        SOF_COUNT_END = TRIG_EXT - SOF_COUNT_BITS
        SOF_COUNT = slice(SOF_COUNT_END,SOF_COUNT_START)

        print("Memory data width        = {:d} bits".format(dram_port.data_width))

        trigger_nbits = len(stream.Endpoint(trigger_layout).payload.raw_bits())
        print("Trigger stream data size = {:d} bits".format(trigger_nbits))

        recorder_reserved_bits = len(first) + VALID_TOKEN_BITS + len(_trigExt) + SOF_COUNT_BITS

        data_per_chunk   = (dram_port.data_width - recorder_reserved_bits) // trigger_nbits
        print("Chunks per block         = {:d} ({:d} bits)".format(data_per_chunk, data_per_chunk * trigger_nbits))
        print("Bits unused              = {:d}".format(dram_port.data_width -
                                                       recorder_reserved_bits -
                                                       (data_per_chunk * trigger_nbits)))

        self.nb       = CSRConstant(data_per_chunk)

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
        self.specials += MultiReg(self.forced, _forced, clock_domain)
        self.specials += MultiReg(self.mode.storage, _mode, clock_domain)
        self.specials += MultiReg(self.trigExt, _trigExt, clock_domain)
        self.specials += MultiReg(_preCount, self.preCount.status, "sys")
        self.specials += MultiReg(_postCount, self.postCount.status, "sys")
        
        # *********************************************************
        # *                     Submodules                        *
        # *********************************************************
        # Remove sof and eof from trigger_layout
        #fifo_layout = trigger_layout[:-2]

        stride = ResetInserter()(StrideConverter2(trigger_layout, recorder_layout(data_per_chunk), reverse=False, report_valid_token_count=True))
        self.submodules.stride = ClockDomainsRenamer(clock_domain)(stride)

        fifo = ResetInserter()(stream.SyncFIFO(trigger_layout, 1024, buffered=True))
        self.submodules.fifo   = ClockDomainsRenamer(clock_domain)(fifo)

        # *********************************************************
        # *                    Combinatorial                      *
        # *********************************************************
        self.comb += [
            sink.connect(self.fifo.sink),
            self.fifo.source.connect(stride.sink),
            source.valid.eq(stride.source.valid),
            stride.source.ready.eq(source.ready),
            source.address.eq(addr[log2_int(ADDRINCR):32]),
            source.data.eq(stride.source.payload.raw_bits()),

            source.data[RECORD_START].eq(first), # The MSb indicates the start of the recording
                                                 # In case we read data back, and this bit is set, we know
                                                 # we didn't cycle over the circular buffer

            source.data[VALID_TOKEN_COUNT].eq(stride.valid_token_count),
            source.data[TRIG_EXT].eq(ext_trig),
            source.data[SOF_COUNT].eq(sof_count),
        ]

        # *********************************************************
        # *                    Synchronous                        *
        # *********************************************************
        sync = getattr(self.sync, clock_domain)
        sync += [
            # Count SOF
            If(stride.sink.valid & stride.sink.ready & stride.sink.sof, sof_count.eq(sof_count + 1)),

            # DRAM address increment
            If(stride.source.valid & stride.source.ready,
                first.eq(0),
                ext_trig.eq(0),
                #If at the same time we get a SOF entering the converter, count it
                If(stride.sink.valid & stride.sink.ready & stride.sink.sof,
                    sof_count.eq(1),
                ).Else(
                    sof_count.eq(0),
                ),
                addr.eq(addr + ADDRINCR),
            ),

            # DRAM address wrap
            If(addr == (base + length - ADDRINCR), addr.eq(base)),

            If(_trigExt & (_state == 6), ext_trig.eq(1)),

            If(_state == 0,
                addr.eq(base),
                first.eq(1),
            ),
        ]

        # *********************************************************
        # *                        FSM                            *
        # *********************************************************
        fsm = FSM(reset_state="IDLE")
        self.submodules.fsm = ClockDomainsRenamer(clock_domain)(fsm)

        fsm.act("IDLE",
            NextValue(_state, 0),
            NextValue(count, 0),
            NextValue(self.record, 0),
            NextValue(stride.flush, 0),
            NextValue(self.enableTrigger, 0),
            NextValue(_finished, 1),

            If(_start,
                NextValue(_finished, 0),
                NextState("FILL_PRE_TRIG"),
                NextValue(self.record, 1),
                stride.reset.eq(1),
                NextValue(_preCount, 0),
                NextValue(_postCount, 0),
            ),
            If(_forced,
                NextValue(_finished, 0),
                stride.reset.eq(1),
                NextState("FORCED"),
                NextValue(_preCount, 0),
                NextValue(_postCount, 0),
            ),
        )

        fsm.act("FILL_PRE_TRIG",
            NextValue(_state, 1),
            NextValue(self.fifo.reset, 0),

            If(count == _offset,
                NextValue(count, 0),
                NextValue(self.enableTrigger, 1),
                NextState("WAIT_TRIGGER")
            ).Else(
                If(stride.sink.ready & stride.sink.valid,
                    If(_mode == RAW_MODE,
                        NextValue(count, count + 1),
                        NextValue(_preCount, _preCount + 1),
                    ).Else(
                        If(fifo.source.eof,
                            NextValue(count, count + 1),
                            NextValue(_preCount, _preCount + 1),
                        )
                    )
                )
            ),
            If(_stop,
                NextValue(stride.flush, 1),
                NextValue(self.fifo.reset, 1),
                NextState("ABORT")
            )
        )

        fsm.act("WAIT_TRIGGER",
            NextValue(_state, 2),

            If(stride.sink.ready & stride.sink.valid,
                If(fifo.source.trig & fifo.source.valid,
                    NextValue(count, 0),
                    # If stride is complete, this next data will be in the
                    # next address block
                    If(stride.valid_token_count == data_per_chunk,
                        NextValue(_trigAddr, addr + ADDRINCR),
                    ).Else(
                        NextValue(_trigAddr, addr),
                    ),
                    NextState("FILL_POST_TRIG")
                )
            ),
            If(_stop,
                NextValue(stride.flush, 1),
                NextValue(self.fifo.reset, 1),
                NextState("ABORT")
            )
        )

        fsm.act("FILL_POST_TRIG",
            NextValue(_state, 3),

            If(count == _size,
                NextValue(stride.flush, 1),
                NextValue(self.fifo.reset, 1),
                NextState("DONE")
            ).Else(
                If(stride.sink.ready & stride.sink.valid,
                    If(_mode == RAW_MODE,
                        NextValue(count, count + 1),
                        NextValue(_postCount, _postCount + 1),
                    ).Else(
                        If(fifo.source.eof,
                            NextValue(count, count + 1),
                            NextValue(_postCount, _postCount + 1),
                        )
                    )
                )
            ),

            If(_stop,
                NextValue(stride.flush, 1),
                NextValue(self.fifo.reset, 1),
                NextState("ABORT")
            )
        )

        fsm.act("DONE",
            NextValue(_state, 4),
            NextValue(self.enableTrigger, 0),
            NextValue(_finished, 1),
            NextValue(self.fifo.reset, 1),
            NextValue(self.record, 0),
            NextValue(stride.flush, 0),
            If(_stop,
                NextState("IDLE")
            )
        )

        fsm.act("ABORT",
            NextValue(_state, 5),
            NextValue(self.enableTrigger, 0),
            NextValue(_finished, 1),
            NextValue(self.fifo.reset, 1),
            NextValue(self.record, 0),
            NextValue(_trigAddr, addr),
            NextValue(stride.flush, 0),
            NextState("IDLE")
        )

        fsm.act("FORCED",
            NextValue(_state, 6),
            NextValue(self.fifo.reset, 0),
            If(_trigExt, NextValue(_trigAddr, addr)),
            If(_forced == 0,
                NextValue(stride.flush, 1),
                NextState("IDLE"),
            )
        )
