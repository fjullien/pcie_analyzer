# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *
from migen.genlib.cdc import *

from litex.soc.interconnect import stream

from pcie_analyzer.common import *

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************

# *********************************************************
# *                                                       *
# *                      Aligner                          *
# *                                                       *
# *********************************************************

class Aligner(Module):
    def __init__(self, check_ctrl_only=False):

        # *********************************************************
        # *                    Interface                          *
        # *********************************************************
        self.enable = Signal(reset=1)
        self.source = source = stream.Endpoint(descrambler_layout)
        self.sink   = sink   = stream.Endpoint(descrambler_layout)

        # *********************************************************
        # *                      Signals                          *
        # *********************************************************
        data0     = Signal(16)
        data1     = Signal(16)
        ctrl0     = Signal(2)
        ctrl1     = Signal(2)
        osets0    = Signal(2)
        osets1    = Signal(2)
        type0     = Signal(4)
        type1     = Signal(4)

        unaligned   = Signal()
        unaligned_d = Signal()

        # *********************************************************
        # *                      Constants                        *
        # *********************************************************

        # *********************************************************
        # *                     Submodules                        *
        # *********************************************************

        # *********************************************************
        # *                    Combinatorial                      *
        # *********************************************************
        self.comb += [
            self.sink.ready.eq(1),
            If(ctrl0 == 0b01 & (check_ctrl_only | data0[0:8] == COM.value),
                unaligned.eq(1)
            )
        ]

        # *********************************************************
        # *                    Synchronous                        *
        # *********************************************************
        self.sync += [
            data0.eq(self.sink.data),
            data1.eq(data0),
            ctrl0.eq(self.sink.ctrl),
            ctrl1.eq(ctrl0),
            osets0.eq(self.sink.osets),
            osets1.eq(osets0),
            type0.eq(self.sink.type),
            type1.eq(type0),

            If(self.enable,
                If((ctrl0 != 0) & (ctrl1 == 0),
                    unaligned_d.eq(unaligned)
                ),
            ),

            If(unaligned_d,
                self.source.data.eq(Cat(data0[8:16],data1[0:8])),
                self.source.ctrl.eq(Cat(ctrl0[1],ctrl1[0])),
                self.source.osets.eq(Cat(osets0[1],osets1[0])),
                self.source.type.eq(type1),
            ).Else(
                self.source.data.eq(data1),
                self.source.ctrl.eq(ctrl1),
                self.source.osets.eq(osets1),
                self.source.type.eq(type1),
            )
        ]
