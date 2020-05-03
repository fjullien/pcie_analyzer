# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *
from migen.genlib.cdc import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import stream

from pcie_analyzer.common import *

# +----------+--------+------------+-------+---------------------------------------+
# | Encoding | Symbol | Name       | Value | Description                           |
# +--------------------------------------------------------------------------------+
# |  K28.5   | COM    | Comma      | 0xBC  | Used for Lane and Link initialization |
# |          |        |            |       | and management                        |
# +--------------------------------------------------------------------------------+
# |  K27.7   | STP    | Start TlP  | 0xFB  | Marks the start of a Transaction      |
# |          |        |            |       | Layer Packet                          |
# +--------------------------------------------------------------------------------+
# |  K28.2   | SDP    | Start DllP | 0x5C  | Marks the start of a Data Link Layer  |
# |          |        |            |       | Packet                                |
# +--------------------------------------------------------------------------------+
# |  K29.7   | END    | End        | 0xFD  | Marks the end of a Transaction Layer  |
# |          |        |            |       | Packet or a Data Link Layer Packet    |
# +--------------------------------------------------------------------------------+
# |  K30.7   | EDB    | EnD Bad    | 0xFE  | Marks the end of a nullified TLP      |
# +--------------------------------------------------------------------------------+
# |  K23.7   | PAD    | Pad        | 0xF7  | Used in Framing and Link Width and    |
# |          |        |            |       | Lane ordering negotiations            |
# +--------------------------------------------------------------------------------+
# |  K28.0   | SKP    | Skip       | 0x1C  | Used for compensating for different   |
# |          |        |            |       | bit rates for two communicating Ports |
# +--------------------------------------------------------------------------------+
# |  K28.1   | FTS    | Fast Train | 0x3C  | Used within an Ordered Set to exit    |
# |          |        | Sequence   |       | from L0s to L0                        |
# +--------------------------------------------------------------------------------+
# |  K28.3   | IDL    | Idle       | 0x7C  | Used in the Electrical Idle Ordered   |
# |          |        |            |       | Set (EIOS)                            |
# +--------------------------------------------------------------------------------+
# |  K28.4   |        |            | 0x9C  | Reserved                              |
# +--------------------------------------------------------------------------------+
# |  K28.6   |        |            | 0xDC  | Reserved                              |
# +--------------------------------------------------------------------------------+
# |  K28.7   | EIE    | Electrical | 0xFC  | Reserved in 2.5 GT/s                  |
# |          |        | Idle Exit  |       | Used in the Electrical Idle Exit      |
# |          |        |            |       | Ordered Set (EIEOS) and sent prior    |
# |          |        |            |       | to sending FTS at data rates other    |
# |          |        |            |       | than 2.5 GT/s                         |
# +----------+--------+------------+-------+---------------------------------------+

# *********************************************************
# *                                                       *
# *                     Definitions                       *
# *                                                       *
# *********************************************************
class state(IntEnum):
    SKIP = 0
    FTS  = 1
    TS1  = 2
    TS2  = 3
    TLP  = 4
    DLLP = 5
    IDLE = 6

filter_fifo_layout = [
    ("data" , 16),
    ("ctrl" , 2),
    ("osets", 2),
    ("type" , 4),
    ("ts"   , 32),
    ("error", 1),
]

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************

# *********************************************************
# *                                                       *
# *                      Filter                           *
# *                                                       *
# *********************************************************

class Filter(Module, AutoCSR):
    def __init__(self, clock_domain, fifo_size):

        # *********************************************************
        # *                    Interface                          *
        # *********************************************************
        self.filterEnable      = CSRStorage()
        self.filterConfig      = CSRStorage(32)  # Filter configuration
        self.tlpDllpTimeoutCnt = CSRStorage(32)  # Payload size used for error detection

        self.ts           = Signal(32)      # Global time stamp

        self.source       = source = stream.Endpoint(filter_layout)
        self.sink         = sink   = stream.Endpoint(descrambler_layout)

        # *********************************************************
        # *                      Signals                          *
        # *********************************************************
        _ts           = Signal(32)
        _filterConfig = Signal(32)
        _tlpDllpTimeoutCnt  = Signal(32)

        _filterEnable = Signal()

        skipEnabled  = Signal()
        ftsEnabled   = Signal()
        tlpEnabled   = Signal()
        dllpEnabled  = Signal()
        ts1Enabled   = Signal()
        ts2Enabled   = Signal()
        idleEnabled  = Signal()

        count        = Signal(8)
        insert_ts    = Signal()
        state_after  = Signal(4)
        last_ts      = Signal(32)
        payload_cnt  = Signal(32)
        from_error   = Signal()

        # *********************************************************
        # *                         CDC                           *
        # *********************************************************
        self.specials += MultiReg(self.ts, _ts, clock_domain)
        self.specials += MultiReg(self.filterConfig.storage, _filterConfig, clock_domain)
        self.specials += MultiReg(self.filterEnable.storage, _filterEnable, clock_domain)
        self.specials += MultiReg(self.tlpDllpTimeoutCnt.storage, _tlpDllpTimeoutCnt, clock_domain)

        # *********************************************************
        # *                     Submodules                        *
        # *********************************************************
        fifo = ResetInserter()(stream.SyncFIFO(filter_fifo_layout, fifo_size))
        self.submodules.fifo   = ClockDomainsRenamer(clock_domain)(fifo)

        buf_in = stream.Buffer(descrambler_layout)
        self.submodules += ClockDomainsRenamer(clock_domain)(buf_in)

        buf_out = stream.Buffer(filter_fifo_layout)
        self.submodules += ClockDomainsRenamer(clock_domain)(buf_out)

        # *********************************************************
        # *                    Combinatorial                      *
        # *********************************************************
        self.comb += [
            sink.connect(buf_in.sink),
            buf_in.source.connect(fifo.sink, omit={"valid", "ts", "error"}),
            self.sink.ready.eq(1),

            fifo.source.connect(buf_out.sink),

            skipEnabled.eq(_filterConfig[0]),
            ftsEnabled.eq( _filterConfig[1]),
            tlpEnabled.eq( _filterConfig[2]),
            dllpEnabled.eq(_filterConfig[3]),
            ts1Enabled.eq( _filterConfig[4]),
            ts2Enabled.eq( _filterConfig[5]),
            idleEnabled.eq( _filterConfig[6]),
        ]

        # *********************************************************
        # *                        FSM                            *
        # *********************************************************
        fsmWriter = FSM(reset_state="NO_FILTER")
        self.submodules.fsmWriter = ClockDomainsRenamer(clock_domain)(fsmWriter)

        fsmReader = FSM(reset_state="NO_FILTER")
        self.submodules.fsmReader = ClockDomainsRenamer(clock_domain)(fsmReader)

        # *********************************************************
        # *                  Filter control                       *
        # *********************************************************
        fsmWriter.act("NO_FILTER",
            NextValue(fifo.sink.valid, 0),
            NextValue(buf_out.source.ready, 0),
            If(_filterEnable,
                self.fifo.reset.eq(1),
                NextState("FIND_DELIMITER"),
            )
        )

# ********************************************************************
# * Writing side of the FIFO.                                        *
# * All frames are written to the FIFO, software IDLE are removed.   *
# * A timestamp is added to each symbol to keep track of the timing. *
# ********************************************************************

        # *********************************************************
        # *               Detect frames delimiter                 *
        # *********************************************************
        fsmWriter.act("FIND_DELIMITER",
            NextValue(fifo.sink.valid, 0),
            NextValue(fifo.sink.error, 0),

            # Ordered sets
            If(sink.osets & (sink.data[8:16] == COM.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(fifo.sink.ts, _ts),
                NextState("ORDERED_SETS"),
            ),

            # TLP
            If((sink.ctrl == 0b10) & (sink.data[8:16] == STP.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(fifo.sink.ts, _ts),
                NextValue(payload_cnt, 0),
                NextState("TLP"),
            ),

            # DLLP
            If((sink.ctrl == 0b10) & (sink.data[8:16] == SDP.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(fifo.sink.ts, _ts),
                NextValue(payload_cnt, 0),
                NextState("DLLP"),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *             An ordered set is detected                *
        # *********************************************************
        fsmWriter.act("ORDERED_SETS",
            NextValue(fifo.sink.ts, _ts),
            NextValue(fifo.sink.error, 0),

            # We are done
            If(sink.osets == 0,
                NextValue(fifo.sink.valid, 0),
                NextState("FIND_DELIMITER"),
            ),

            # It's a nested frame. Get directly to TLP
            If(sink.ctrl[1] & (sink.data[8:16] == STP.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(payload_cnt, 0),
                NextState("TLP"),
            ),

            # It's a nested frame. Get directly to DLLP
            If(sink.ctrl[1] & (sink.data[8:16] == SDP.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(payload_cnt, 0),
                NextState("DLLP"),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *                An TLP is detected                     *
        # *********************************************************
        fsmWriter.act("TLP",
            NextValue(fifo.sink.ts, _ts),
            NextValue(fifo.sink.error, 0),
            NextValue(payload_cnt, payload_cnt + 1),

            # By default, is we have a K symbol before END, that's an error
            If((sink.ctrl[0] & (sink.data[0:8] != END.value)) | sink.ctrl[1] | (payload_cnt > _tlpDllpTimeoutCnt),
                NextValue(fifo.sink.error, 1),
                NextValue(fifo.sink.valid, 1),
                NextState("FIND_DELIMITER"),
            ).Else(
                NextValue(fifo.sink.error, 0),
            ),

            If((buf_in.source.ctrl[0]) & (buf_in.source.data[0:8] == END.value),
                NextValue(fifo.sink.valid, 0),
                NextValue(fifo.sink.error, 0),
                NextState("FIND_DELIMITER"),
            ),

            If(sink.ctrl[1] & (sink.data[8:16] == STP.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(payload_cnt, 0),
                NextState("TLP"),
            ),

            If(sink.ctrl[1] & (sink.data[8:16] == SDP.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(payload_cnt, 0),
                NextState("DLLP"),
            ),

            If(sink.osets & (sink.data[8:16] == COM.value),
                NextValue(fifo.sink.valid, 1),
                NextState("ORDERED_SETS"),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *                An DLLP is detected                    *
        # *********************************************************
        fsmWriter.act("DLLP",
            NextValue(fifo.sink.ts, _ts),
            NextValue(fifo.sink.error, 0),
            NextValue(payload_cnt, payload_cnt + 1),

            # By default, is we have a K symbol before END, that's an error
            If((sink.ctrl[0] & (sink.data[0:8] != END.value)) | sink.ctrl[1]| (payload_cnt > _tlpDllpTimeoutCnt),
                NextValue(fifo.sink.error, 1),
                NextValue(fifo.sink.valid, 1),
                NextState("FIND_DELIMITER"),
            ).Else(
                NextValue(fifo.sink.error, 0),
            ),

            If((buf_in.source.ctrl[0]) & (buf_in.source.data[0:8] == END.value),
                NextValue(fifo.sink.valid, 0),
                NextValue(fifo.sink.error, 0),
                NextState("FIND_DELIMITER"),
            ),

            If(sink.ctrl[1] & (sink.data[8:16] == STP.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(payload_cnt, 0),
                NextState("TLP"),
            ),

            If(sink.ctrl[1] & (sink.data[8:16] == SDP.value),
                NextValue(fifo.sink.valid, 1),
                NextValue(payload_cnt, 0),
                NextState("DLLP"),
            ),

            If(sink.osets & (sink.data[8:16] == COM.value),
                NextValue(fifo.sink.valid, 1),
                NextState("ORDERED_SETS"),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

# ******************************************************************
# * Reading side of the FIFO.                                      *
# * Filtering takes place on the reading side of the FIFO.         *
# * A timestamp is added to each frame (or frame group) to keep    *
# * track of the timing.                                           *
# ******************************************************************

        # *********************************************************
        # *                   Filtering control                   *
        # *********************************************************
        fsmReader.act("NO_FILTER",
            NextValue(source.data, sink.data),
            NextValue(source.ctrl, sink.ctrl),
            NextValue(source.valid, sink.valid),
            NextValue(source.time, 0),
            If(_filterEnable,
                NextState("FILTER"),
            )
        )

        # *********************************************************
        # *                   Frame filtering                     *
        # *********************************************************
        fsmReader.act("FILTER",
            NextValue(source.valid, 0),
            NextValue(source.time, 0),
            NextValue(buf_out.source.ready, 0),
            NextValue(from_error, 0),

            If(from_error,
                NextValue(buf_out.source.ready, 1),
            ),

            If(buf_out.source.valid,

                # Don't insert a new timestamp
                If(last_ts == buf_out.source.ts,
                    insert_ts.eq(0),
                ).Else(
                    insert_ts.eq(1),
                    NextValue(last_ts, buf_out.source.ts),
                ),

                # ---- SKIP ----
                If(buf_out.source.osets & (buf_out.source.type == osetsType.SKIP) & (buf_out.source.data[8:16] == COM.value),
                    If(insert_ts,
                        NextValue(source.data, buf_out.source.ts[16:32]),
                        # When this frame is disabled, we need to change last_ts
                        # in order to force ts insertion on the next frame.
                        If(skipEnabled,
                            NextValue(source.valid, 1),
                            NextValue(source.time, 1),
                        ).Else(
                            NextValue(last_ts, 0),
                        ),
                        NextValue(buf_out.source.ready, 0),
                        NextValue(state_after, state.SKIP),
                        NextState("TIMESTAMP_LSB"),
                    ).Else(
                        NextValue(count, 0),
                        NextValue(buf_out.source.ready, 1),
                        NextState("SKIP"),
                    )
                ),

                # ---- IDLE ----
                If(buf_out.source.osets & (buf_out.source.type == osetsType.IDLE) & (buf_out.source.data[8:16] == COM.value),
                    If(insert_ts,
                        NextValue(source.data, buf_out.source.ts[16:32]),
                        # When this frame is disabled, we need to change last_ts
                        # in order to force ts insertion on the next frame.
                        If(idleEnabled,
                            NextValue(source.valid, 1),
                            NextValue(source.time, 1),
                        ).Else(
                            NextValue(last_ts, 0),
                        ),
                        NextValue(buf_out.source.ready, 0),
                        NextValue(state_after, state.IDLE),
                        NextState("TIMESTAMP_LSB"),
                    ).Else(
                        NextValue(count, 0),
                        NextValue(buf_out.source.ready, 1),
                        NextState("IDLE"),
                    )
                ),

                # ---- FTS ----
                If(buf_out.source.osets & (buf_out.source.type == osetsType.FTS) & (buf_out.source.data[8:16] == COM.value),
                    If(insert_ts,
                        NextValue(source.data, buf_out.source.ts[16:32]),
                        If(ftsEnabled,
                            NextValue(source.valid, 1),
                            NextValue(source.time, 1),
                        ).Else(
                            NextValue(last_ts, 0),
                        ),

                        NextValue(buf_out.source.ready, 0),
                        NextValue(state_after, state.FTS),
                        NextState("TIMESTAMP_LSB"),
                    ).Else(
                        NextValue(count, 0),
                        NextValue(buf_out.source.ready, 1),
                        NextState("FTS"),
                    )
                ),

                # ---- TS1 ----
                If(buf_out.source.osets & (buf_out.source.type == osetsType.TS1) & (buf_out.source.data[8:16] == COM.value),
                    If(insert_ts,
                        NextValue(source.data, buf_out.source.ts[16:32]),
                        If(ftsEnabled,
                            NextValue(source.valid, 1),
                            NextValue(source.time, 1),
                        ).Else(
                            NextValue(last_ts, 0),
                        ),

                        NextValue(buf_out.source.ready, 0),
                        NextValue(state_after, state.TS1),
                        NextState("TIMESTAMP_LSB"),
                    ).Else(
                        NextValue(count, 0),
                        NextValue(buf_out.source.ready, 1),
                        NextState("TS1"),
                    )
                ),

                # ---- TS2 ----
                If(buf_out.source.osets & (buf_out.source.type == osetsType.TS2) & (buf_out.source.data[8:16] == COM.value),
                    If(insert_ts,
                        NextValue(source.data, buf_out.source.ts[16:32]),
                        If(ftsEnabled,
                            NextValue(source.valid, 1),
                            NextValue(source.time, 1),
                        ).Else(
                            NextValue(last_ts, 0),
                        ),

                        NextValue(buf_out.source.ready, 0),
                        NextValue(state_after, state.TS2),
                        NextState("TIMESTAMP_LSB"),
                    ).Else(
                        NextValue(count, 0),
                        NextValue(buf_out.source.ready, 1),
                        NextState("TS2"),
                    )
                ),

                # ---- TLP ----
                If(buf_out.source.ctrl[1] & (buf_out.source.data[8:16] == STP.value),
                    If(insert_ts,
                        NextValue(source.data, buf_out.source.ts[16:32]),
                        If(tlpEnabled,
                            NextValue(source.valid, 1),
                            NextValue(source.time, 1),
                        ).Else(
                            NextValue(last_ts, 0),
                        ),
                        NextValue(buf_out.source.ready, 0),
                        NextValue(state_after, state.TLP),
                        NextState("TIMESTAMP_LSB"),
                    ).Else(
                        NextValue(count, 0),
                        NextValue(buf_out.source.ready, 1),
                        NextState("TLP"),
                    )
                ),

                # ---- DLLP ----
                If(buf_out.source.ctrl[1] & (buf_out.source.data[8:16] == SDP.value),
                    If(insert_ts,
                        NextValue(source.data, buf_out.source.ts[16:32]),
                        If(dllpEnabled,
                            NextValue(source.valid, 1),
                            NextValue(source.time, 1),
                        ).Else(
                            NextValue(last_ts, 0),
                        ),
                        NextValue(buf_out.source.ready, 0),
                        NextValue(state_after, state.DLLP),
                        NextState("TIMESTAMP_LSB"),
                    ).Else(
                        NextValue(count, 0),
                        NextValue(buf_out.source.ready, 1),
                        NextState("DLLP"),
                    )
                )
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *            Insert LSB part of timestamp               *
        # *********************************************************
        fsmReader.act("TIMESTAMP_LSB",
            NextValue(source.data, buf_out.source.ts[0:16]),
            NextValue(count, 0),
            NextValue(buf_out.source.ready, 1),

            If((state_after == state.SKIP),
                If(skipEnabled,
                    NextValue(source.valid, 1),
                ),
                NextState("SKIP"),
            ),

            If((state_after == state.IDLE),
                If(ftsEnabled,
                    NextValue(source.valid, 1),
                ),
                NextState("IDLE"),
            ),

            If((state_after == state.FTS),
                If(ftsEnabled,
                    NextValue(source.valid, 1),
                ),
                NextState("FTS"),
            ),

            If((state_after == state.TS1),
                If(ts1Enabled,
                    NextValue(source.valid, 1),
                ),
                NextState("TS1"),
            ),

            If((state_after == state.TS2),
                If(ts2Enabled,
                    NextValue(source.valid, 1),
                ),
                NextState("TS2"),
            ),

            If((state_after == state.DLLP),
                If(dllpEnabled,
                    NextValue(source.valid, 1),
                ),
                NextState("DLLP"),
            ),

            If((state_after == state.TLP),
                If(tlpEnabled,
                    NextValue(source.valid, 1),
                ),
                NextState("TLP"),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *            Read a SKIP from the FIFO                  *
        # *********************************************************
        fsmReader.act("SKIP",
            NextValue(source.data, buf_out.source.data),
            NextValue(source.ctrl, buf_out.source.ctrl),
            NextValue(count, count + 1),
            NextValue(source.valid, 1),
            NextValue(last_ts, last_ts + 1),
            NextValue(source.time, 0),
            If(count == 1,
                NextValue(buf_out.source.ready, 0),
                NextValue(source.valid, 0),
                NextState("FILTER"),
            ),

            If(skipEnabled,
                NextValue(source.valid, 1),
            ).Else(
                NextValue(source.valid, 0),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *            Read a IDLE from the FIFO                   *
        # *********************************************************
        fsmReader.act("IDLE",
            NextValue(source.data, buf_out.source.data),
            NextValue(source.ctrl, buf_out.source.ctrl),
            NextValue(count, count + 1),
            NextValue(source.valid, 1),
            NextValue(last_ts, last_ts + 1),
            NextValue(source.time, 0),
            If(count == 1,
                NextValue(buf_out.source.ready, 0),
                NextValue(source.valid, 0),
                NextState("FILTER"),
            ),

            If(idleEnabled,
                NextValue(source.valid, 1),
            ).Else(
                NextValue(source.valid, 0),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *            Read a FTS from the FIFO                   *
        # *********************************************************
        fsmReader.act("FTS",
            NextValue(source.data, buf_out.source.data),
            NextValue(source.ctrl, buf_out.source.ctrl),
            NextValue(count, count + 1),
            NextValue(source.valid, 1),
            NextValue(last_ts, last_ts + 1),
            NextValue(source.time, 0),
            If(count == 1,
                NextValue(buf_out.source.ready, 0),
                NextValue(source.valid, 0),
                NextState("FILTER"),
            ),

            If(ftsEnabled,
                NextValue(source.valid, 1),
            ).Else(
                NextValue(source.valid, 0),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *            Read a TS1 from the FIFO                   *
        # *********************************************************
        fsmReader.act("TS1",
            NextValue(source.data, buf_out.source.data),
            NextValue(source.ctrl, buf_out.source.ctrl),
            NextValue(count, count + 1),
            NextValue(source.valid, 1),
            NextValue(last_ts, last_ts + 1),
            NextValue(source.time, 0),
            If(count == 7,
                NextValue(buf_out.source.ready, 0),
                NextValue(source.valid, 0),
                NextState("FILTER"),
            ),

            If(ts1Enabled,
                NextValue(source.valid, 1),
            ).Else(
                NextValue(source.valid, 0),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *            Read a TS2 from the FIFO                   *
        # *********************************************************
        fsmReader.act("TS2",
            NextValue(source.data, buf_out.source.data),
            NextValue(source.ctrl, buf_out.source.ctrl),
            NextValue(count, count + 1),
            NextValue(source.valid, 1),
            NextValue(last_ts, last_ts + 1),
            NextValue(source.time, 0),
            If(count == 7,
                NextValue(buf_out.source.ready, 0),
                NextValue(source.valid, 0),
                NextState("FILTER"),
            ),

            If(ts2Enabled,
                NextValue(source.valid, 1),
            ).Else(
                NextValue(source.valid, 0),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *            Read a TLP from the FIFO                   *
        # *********************************************************
        fsmReader.act("TLP",
            NextValue(source.data, buf_out.source.data),
            NextValue(source.ctrl, buf_out.source.ctrl),
            NextValue(count, count + 1),
            NextValue(source.valid, 1),
            NextValue(last_ts, last_ts + 1),
            NextValue(source.time, 0),
            If((buf_out.source.ctrl[0] & (buf_out.source.data[0:8] == END.value)) | fifo.source.error,
                NextValue(buf_out.source.ready, 0),
                NextValue(source.valid, 0),
                NextState("FILTER"),
                If(fifo.source.error,
                    NextValue(from_error, 1),
                ),
            ),

            If(tlpEnabled,
                NextValue(source.valid, 1),
            ).Else(
                NextValue(source.valid, 0),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )

        # *********************************************************
        # *            Read a DLLP from the FIFO                  *
        # *********************************************************
        fsmReader.act("DLLP",
            NextValue(source.data, buf_out.source.data),
            NextValue(source.ctrl, buf_out.source.ctrl),
            NextValue(count, count + 1),
            NextValue(source.valid, 1),
            NextValue(last_ts, last_ts + 1),
            NextValue(source.time, 0),
            If((buf_out.source.ctrl[0] & (buf_out.source.data[0:8] == END.value)) | fifo.source.error,
                NextValue(buf_out.source.ready, 0),
                NextValue(source.valid, 0),
                NextState("FILTER"),
                If(fifo.source.error,
                    NextValue(from_error, 1),
                ),
            ),

            If(dllpEnabled,
                NextValue(source.valid, 1),
            ).Else(
                NextValue(source.valid, 0),
            ),

            If(~_filterEnable,
                NextState("NO_FILTER"),
            )
        )
