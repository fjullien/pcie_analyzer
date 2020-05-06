# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *
from migen.genlib.cdc import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import stream

from pcie_analyzer.common import *
from pcie_analyzer.descrambler.descrambler import *

SKIP_INTERVAL = 1400

class Exerciser(Module, AutoCSR):
    def __init__(self, clock_domain, mem_size=128):

        # *********************************************************
        # *                    Interface                          *
        # *********************************************************
        self.insert = CSRStorage()
        self.size   = CSRStorage(8)   # Pattern size - 1

        self.source = source = stream.Endpoint(gtp_layout)

        # *********************************************************
        # *                      Signals                          *
        # *********************************************************
        symbol_cnt  = Signal(16)
        free_cnt    = Signal(32)
        memory_cnt  = Signal(8)
        done        = Signal()

        _insert     = Signal()
        _size       = Signal(8)

        generator   = stream.Endpoint(descrambler_layout)

        # *********************************************************
        # *                         CDC                           *
        # *********************************************************
        self.specials += MultiReg(self.insert.storage, _insert, clock_domain)
        self.specials += MultiReg(self.size.storage, _size, clock_domain)

        # *********************************************************
        # *                     Specials                          *
        # *********************************************************
        self.specials.mem = Memory(20, mem_size)
        self.specials.rdport = self.mem.get_port(write_capable=False, async_read=True, clock_domain=clock_domain)

        # *********************************************************
        # *                     Submodules                        *
        # *********************************************************

        self.submodules.descrambler = Descrambler(clock_domain)

        # *********************************************************
        # *                    Combinatorial                      *
        # *********************************************************
        self.comb += [
            generator.connect(self.descrambler.sink),
            self.source.data.eq(Cat(self.descrambler.source.data[8:16], self.descrambler.source.data[0:8])),
            self.source.ctrl.eq(Cat(self.descrambler.source.ctrl[1], self.descrambler.source.ctrl[0])),
            self.source.valid.eq(1),
        ]

        # *********************************************************
        # *                        FSM                            *
        # *********************************************************
        fsm = FSM(reset_state="LSB")
        self.submodules.fsm = ClockDomainsRenamer(clock_domain)(fsm)

        fsm.act("LSB",
            NextValue(symbol_cnt, symbol_cnt + 1),
            NextValue(generator.data, free_cnt[15:32]),
            NextValue(generator.ctrl, 0),
            NextValue(generator.osets, 0),
            NextState("MSB"),
        )

        fsm.act("MSB",
            NextValue(symbol_cnt, symbol_cnt + 1),
            NextValue(free_cnt, free_cnt + 1),
            NextValue(generator.data, free_cnt[0:16]),
            NextValue(generator.ctrl, 0),
            NextState("LSB"),
            If(symbol_cnt > SKIP_INTERVAL,
                NextState("SKIP_LSB"),
            ).Else(
                NextState("LSB"),
            ),
            If(_insert & ~done,
                self.rdport.adr.eq(0),
                NextValue(memory_cnt, 0),
                NextState("SEND_FRAME"),
            ),
            If(~_insert,
                NextValue(done, 0),
            )
        )

        fsm.act("SKIP_LSB",
            NextValue(generator.data, 0xbc1c),
            NextValue(generator.ctrl, 0b11),
            NextValue(generator.osets, 0b11),
            NextState("SKIP_MSB"),
        )

        fsm.act("SKIP_MSB",
            NextValue(symbol_cnt, 0),
            NextValue(generator.data, 0x1c1c),
            NextValue(generator.ctrl, 0b11),
            NextValue(generator.osets, 0b11),
            NextState("LSB"),
        )

        fsm.act("SEND_FRAME",
            NextValue(memory_cnt, memory_cnt + 1),
            self.rdport.adr.eq(memory_cnt),
            NextValue(generator.data, self.rdport.dat_r[0:16]),
            NextValue(generator.ctrl, self.rdport.dat_r[16:18]),
            NextValue(generator.osets, self.rdport.dat_r[18:20]),
            If(memory_cnt == (_size - 1),
                NextValue(done, 1),
                NextState("LSB"),
            ),
        )
