# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *
from migen.genlib.cdc import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import stream

import sys
sys.path.append("..")
from common import *

# *********************************************************
# *                                                       *
# *                     Definitions                       *
# *                                                       *
# *********************************************************

UPPER_BYTE = slice(8,16)
LOWER_BYTE = slice(0,8)
DATA_WORD  = slice(0,16)
UPPER_K    = 17
LOWER_K    = 16

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************

# *********************************************************
# *                                                       *
# *                      Trigger                          *
# *                                                       *
# *********************************************************

class Trigger(Module, AutoCSR):

    def __init__(self, clock_domain, mem_size=128):
        self.armed     = CSRStorage()    # Trigger is armed
        self.trigged   = CSRStatus()     # Pattern found
        self.size      = CSRStorage(8)   # Pattern size - 1
        
        self.sink   =   sink = stream.Endpoint(descrambler_layout)
        self.source = source = stream.Endpoint(trigger_layout)

        # # #

        data0    = Signal(16)
        data1    = Signal(16)
        ctrl0    = Signal(2)
        ctrl1    = Signal(2)
        matches  = Signal(8)
        addr     = Signal(log2_int(mem_size))

        _armed   = Signal()
        _trigged = Signal()
        _size    = Signal(8)

        self.specials += MultiReg(self.armed.storage, _armed, clock_domain)
        self.specials += MultiReg(_trigged, self.trigged.status, "sys")
        self.specials += MultiReg(self.size.storage, _size, clock_domain)

        self.specials.mem = Memory(18, mem_size)
        self.specials.rdport = self.mem.get_port(write_capable=False, async_read=True, clock_domain=clock_domain)

        self.sync += [
            data0.eq(self.sink.data),
            data1.eq(data0),
            ctrl0.eq(self.sink.ctrl),
            ctrl1.eq(ctrl0),
         ]

        self.comb += [
            self.source.data.eq(data1),
            self.source.ctrl.eq(ctrl1),
            self.rdport.adr.eq(addr),
            self.sink.ready.eq(1),
        ]

        # FSM
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")

        fsm.act("IDLE",
            If(_armed,
                NextValue(addr, 0),
                NextValue(matches, 0),
                NextState("FIRST")
            )
        )

        fsm.act("FIRST",
            # If we search "bc1c" we are in this situation: bc1c 1c1c xxxx
            If(self.rdport.dat_r[DATA_WORD] == data1,
                # Full word match
                NextValue(matches, matches + 1),
                NextValue(addr, addr + 1),
                NextState("ALIGNED_CHECK")
            ),
            # If we search "bc1c" we are in this situation: xxbc 1c1c 1cxx
            If((self.rdport.dat_r[UPPER_BYTE] == data1[LOWER_BYTE]) &
                (self.rdport.dat_r[LOWER_BYTE] == data0[UPPER_BYTE]),
                # Half word match
                NextValue(matches, matches + 1),
                NextValue(addr, addr + 1),
                NextState("UNALIGNED_CHECK")
            ),
        )

        fsm.act("ALIGNED_CHECK",
            If(matches == _size,
                NextState("DONE")
            ).Else(
                If(self.rdport.dat_r[DATA_WORD] == data1,
                    NextValue(matches, matches + 1),
                    NextValue(addr, addr + 1),
                    NextState("ALIGNED_CHECK")
                ).Else(
                    NextValue(matches, 0),
                    NextValue(addr, 0),
                    NextState("FIRST")
                )
            )
        )

        fsm.act("UNALIGNED_CHECK",
            If(matches == _size + 1,
                NextState("DONE")
            ).Else(
                If((self.rdport.dat_r[UPPER_BYTE] == data1[LOWER_BYTE]) &
                        (self.rdport.dat_r[LOWER_BYTE] == data0[UPPER_BYTE]),
                        # Half word match
                        NextValue(matches, matches + 1),
                        NextValue(addr, addr + 1),
                        NextState("UNALIGNED_CHECK")
                ).Else(
                        NextValue(matches, 0),
                        NextValue(addr, 0),
                        NextState("FIRST")
                )
            )
        )

        fsm.act("DONE",
            NextValue(_trigged, 1),
            If(_armed == 0,
                NextValue(_trigged, 0),
                NextState("IDLE")
            )
        )
