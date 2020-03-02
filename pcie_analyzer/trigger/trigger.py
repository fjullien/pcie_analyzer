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
K_WORD     = slice(16,18)

DONT_CARE  = 18

CTRL_LOWER_K = 0
CTRL_UPPER_K = 1

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

        # *********************************************************
        # *                    Interface                          *
        # *********************************************************
        self.armed     = CSRStorage()    # Trigger is armed
        self.trigged   = CSRStatus()     # Pattern found
        self.size      = CSRStorage(8)   # Pattern size - 1

        self.enable   = Signal()

        self.sink   =   sink = stream.Endpoint(descrambler_layout)
        self.source = source = stream.Endpoint(trigger_layout)

        # *********************************************************
        # *                      Signals                          *
        # *********************************************************
        data0    = Signal(16)
        data1    = Signal(16)
        ctrl0    = Signal(2)
        ctrl1    = Signal(2)
        matches  = Signal(8)
        addr     = Signal(log2_int(mem_size))

        _armed   = Signal()
        _trigged = Signal()
        _size    = Signal(8)

        # *********************************************************
        # *                         CDC                           *
        # *********************************************************
        self.specials += MultiReg(self.armed.storage, _armed, clock_domain)
        self.specials += MultiReg(_trigged, self.trigged.status, "sys")
        self.specials += MultiReg(self.size.storage, _size, clock_domain)

        # *********************************************************
        # *                     Specials                          *
        # *********************************************************
        self.specials.mem = Memory(19, mem_size)
        self.specials.rdport = self.mem.get_port(write_capable=False, async_read=True, clock_domain=clock_domain)

        # *********************************************************
        # *                    Synchronous                        *
        # *********************************************************
        sync = getattr(self.sync, clock_domain)
        sync += [
            data0.eq(self.sink.data),
            data1.eq(data0),
            ctrl0.eq(self.sink.ctrl),
            ctrl1.eq(ctrl0),
         ]

        # *********************************************************
        # *                    Combinatorial                      *
        # *********************************************************
        self.comb += [
            self.source.data.eq(data1),
            self.source.ctrl.eq(ctrl1),
            self.rdport.adr.eq(addr),
            self.sink.ready.eq(1),
        ]

        # *********************************************************
        # *                        FSM                            *
        # *********************************************************
        fsm = ResetInserter()(FSM(reset_state="IDLE"))
        self.submodules.fsm = ClockDomainsRenamer(clock_domain)(fsm)
        self.comb += self.fsm.reset.eq(~self.enable)

        fsm.act("IDLE",
            If(_armed,
                NextValue(addr, 0),
                NextValue(matches, 0),
                NextState("FIRST")
            )
        )

        fsm.act("FIRST",
            # If we search "bc1c" we are in this situation: bc1c 1c1c xxxx
            If((self.rdport.dat_r[DATA_WORD] == data1) &
               (self.rdport.dat_r[K_WORD]    == ctrl1),
                # Full word match
                NextValue(matches, matches + 1),
                NextValue(addr, addr + 1),
                NextState("ALIGNED_CHECK")
            ).Else(
                # If we search "bc1c" we are in this situation: xxbc 1c1c 1cxx
                If((self.rdport.dat_r[UPPER_BYTE] == data1[LOWER_BYTE])   &
                   (self.rdport.dat_r[LOWER_BYTE] == data0[UPPER_BYTE])   &
                   (self.rdport.dat_r[UPPER_K]    == ctrl1[CTRL_LOWER_K]) &
                   (self.rdport.dat_r[LOWER_K]    == ctrl0[CTRL_UPPER_K]),
                        # Half word match
                        NextValue(matches, matches + 1),
                        NextValue(addr, addr + 1),
                        NextState("UNALIGNED_CHECK")
                )
            )
        )

        fsm.act("ALIGNED_CHECK",
            If(matches == _size,
                NextState("DONE"),
                NextValue(_trigged, 1),
                self.source.trig.eq(1),
            ).Else(
                If(((self.rdport.dat_r[DATA_WORD] == data1)  &
                    (self.rdport.dat_r[K_WORD]    == ctrl1)) |
                    (self.rdport.dat_r[DONT_CARE] == 1),
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
            If(matches == _size,
                NextState("DONE"),
                NextValue(_trigged, 1),
                self.source.trig.eq(1),
            ).Else(
                If(((self.rdport.dat_r[UPPER_BYTE] == data1[LOWER_BYTE])    &
                    (self.rdport.dat_r[LOWER_BYTE] == data0[UPPER_BYTE])    &
                    (self.rdport.dat_r[UPPER_K]    == ctrl1[CTRL_LOWER_K])  &
                    (self.rdport.dat_r[LOWER_K]    == ctrl0[CTRL_UPPER_K])) |
                    (self.rdport.dat_r[DONT_CARE]  == 1),
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
            NextValue(_trigged, 0),
            NextState("IDLE")
        )
