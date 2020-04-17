# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from migen import *
from migen.genlib.cdc import *

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import stream

from litedram.frontend.dma import LiteDRAMDMAWriter

from pcie_analyzer.common import *
from pcie_analyzer.descrambler.descrambler import *
from pcie_analyzer.aligner.aligner import *
from pcie_analyzer.filter.filters import *
from pcie_analyzer.trigger.trigger import *
from pcie_analyzer.recorder.recorder import *
from pcie_analyzer.exerciser.exerciser import *

# *********************************************************
# *                                                       *
# *                     Recorder                          *
# *                                                       *
# *********************************************************

class CapturePipeline(Module, AutoCSR):
    def __init__(self, clock_domain,
                       dram_port,
                       ring_buffer_base_address,
                       ring_buffer_size,
                       stride_multiplier=12,
                       filter_fifo_size=2048,
                       trigger_memory_size=128,
                       cdc_stream_fifo_size=1024):

        # *********************************************************
        # *                    Interface                          *
        # *********************************************************
        self.simu            = CSRStorage()    # GTP or Exerciser datas
  
        self.source = source = stream.Endpoint([("address", dram_port.address_width),
                                                ("data", dram_port.data_width)])
        self.sink   = sink   = stream.Endpoint(gtp_layout)

        self.forced    = Signal()          # Another CapturePipeline ask us to record datas
        self.record    = Signal()          # Ask another CapturePipeline to record datas
        self.enable    = Signal()          # Enable pipeline
        self.time      = Signal(32)        # Time source

        # *********************************************************
        # *                      Signals                          *
        # *********************************************************
        _simu   = Signal()

        # *********************************************************
        # *                         CDC                           *
        # *********************************************************
        self.specials += MultiReg(self.simu.storage, _simu, clock_domain)

        # *********************************************************
        # *                     Submodules                        *
        # *********************************************************

        self.submodules.exerciser   = Exerciser(clock_domain)
        self.submodules.multiplexer = stream.Multiplexer(gtp_layout, 2)
        self.submodules.descrambler = Descrambler(clock_domain)
        self.submodules.detect      = ClockDomainsRenamer(clock_domain)(DetectOrderedSets())
        self.submodules.aligner     = ClockDomainsRenamer(clock_domain)(Aligner())
        self.submodules.filter      = Filter(clock_domain, filter_fifo_size)
        self.submodules.trigger     = Trigger(clock_domain, trigger_memory_size)
        self.submodules.recorder    = RingRecorder(clock_domain, dram_port,
                                                   ring_buffer_base_address,
                                                   ring_buffer_size,
                                                   stride_multiplier)

        cdc = stream.AsyncFIFO([("address", dram_port.address_width),
                                ("data",    dram_port.data_width)],
                                cdc_stream_fifo_size, buffered=True)

        cdc                 = ClockDomainsRenamer({"write": clock_domain, "read": "sys"})(cdc)
        self.submodules.cdc = cdc
        self.submodules.dma = LiteDRAMDMAWriter(dram_port)

        # *********************************************************
        # *                    Combinatorial                      *
        # *********************************************************

        self.comb += [
            self.multiplexer.sel.eq(_simu),
            self.sink.connect(self.multiplexer.sink0),
            self.exerciser.source.connect(self.multiplexer.sink1),

            self.multiplexer.source.connect(self.detect.sink),

            self.detect.source.connect(self.descrambler.sink),
            self.descrambler.source.connect(self.aligner.sink),
            self.aligner.source.connect(self.filter.sink),

            self.filter.source.connect(self.trigger.sink),
            self.filter.ts.eq(self.time),

            self.trigger.source.connect(self.recorder.sink),
            self.trigger.enable.eq(self.recorder.enable),

            self.recorder.source.connect(self.cdc.sink),
            self.recorder.forced.eq(self.forced),
            self.record.eq(self.record),
            self.recorder.enable.eq(self.enable),

            self.trigger.enable.eq(self.recorder.enable),

            self.cdc.source.connect(self.dma.sink),
        ]
