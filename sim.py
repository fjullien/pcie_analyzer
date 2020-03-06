#!/usr/bin/env python3

# This file is Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import argparse

from migen import *
from migen.genlib.cdc import *

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig

from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *
from litex.soc.cores import uart
from litex.soc.interconnect import stream

from litedram import modules as litedram_modules
from litedram.common import PhySettings
from litedram.modules import MT48LC16M16
from litedram.phy.model import SDRAMPHYModel
from litedram.frontend.dma import LiteDRAMDMAWriter

from liteeth.phy.model import LiteEthPHYModel
from liteeth.core import LiteEthUDPIPCore
from liteeth.frontend.etherbone import LiteEthEtherbone

import sys
sys.path.append("./pcie_analyzer")
sys.path.append("./pcie_analyzer/descrambler")
sys.path.append("./pcie_analyzer/trigger")
sys.path.append("./pcie_analyzer/recorder")

from descrambler import Descrambler, DetectOrderedSets
from trigger import Trigger
from recorder import RingRecorder
from common import *

# *********************************************************
# *                                                       *
# *                      IOs                              *
# *                                                       *
# ********************************************************

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("eth_clocks", 0,
        Subsignal("tx", Pins(1)),
        Subsignal("rx", Pins(1)),
    ),
    ("eth", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    ),
]

# *********************************************************
# *                                                       *
# *                      Platform                         *
# *                                                       *
# *********************************************************

class Platform(SimPlatform):
    def __init__(self):
        SimPlatform.__init__(self, "SIM", _io)

# *********************************************************
# *                                                       *
# *                      Analyzer                         *
# *                                                       *
# *********************************************************

class PCIeAnalyzer(SoCSDRAM):
    def __init__(self, sdram_module, sdram_data_width, **kwargs):
        platform     = Platform()
        sys_clk_freq = int(1e6)

        # *********************************************************
        # *                      SoC SDRAM                        *
        # *********************************************************
        SoCSDRAM.__init__(self, platform, sys_clk_freq,
            integrated_rom_size  = 0x8000,
            integrated_sram_size = 0x1000,
            uart_name            = "crossover",
            l2_size              = 0,
            csr_data_width       = 32,
            **kwargs
        )

        # *********************************************************
        # *                      CRG                              *
        # *********************************************************
        self.submodules.crg = CRG(platform.request("sys_clk"))

        # *********************************************************
        # *                   SDR SDRAM                           *
        # *********************************************************
        from litex.tools.litex_sim import sdram_module_nphases, get_sdram_phy_settings
        sdram_clk_freq   = int(100e6) # FIXME: use 100MHz timings
        sdram_module_cls = getattr(litedram_modules, sdram_module)
        sdram_rate       = "1:{}".format(sdram_module_nphases[sdram_module_cls.memtype])
        sdram_module     = sdram_module_cls(sdram_clk_freq, sdram_rate)
        phy_settings     = get_sdram_phy_settings(
            memtype    = sdram_module.memtype,
            data_width = sdram_data_width,
            clk_freq   = sdram_clk_freq)
        self.submodules.sdrphy = SDRAMPHYModel(
            module    = sdram_module,
            settings  = phy_settings,
            clk_freq  = sdram_clk_freq)
        self.register_sdram(
            self.sdrphy,
            sdram_module.geom_settings,
            sdram_module.timing_settings)
        # Disable Memtest for simulation speedup
        self.add_constant("MEMTEST_BUS_SIZE",  0)
        self.add_constant("MEMTEST_ADDR_SIZE", 0)
        self.add_constant("MEMTEST_DATA_SIZE", 0)

        # *********************************************************
        # *                  Ethernet PHY                         *
        # *********************************************************
        self.submodules.ethphy = LiteEthPHYModel(self.platform.request("eth"))
        self.add_csr("ethphy")

        # *********************************************************
        # *                  Ethernet Core                        *
        # *********************************************************
        ethcore = LiteEthUDPIPCore(self.ethphy,
            mac_address = 0x10e2d5000000,
            ip_address  = "172.30.28.201",
            clk_freq    = sys_clk_freq)
        self.submodules.ethcore = ethcore

        # *********************************************************
        # *                 Etherbone bridge                      *
        # *********************************************************
        self.submodules.etherbone = LiteEthEtherbone(self.ethcore.udp, 1234, mode="master")
        self.add_wb_master(self.etherbone.wishbone.bus)

        # *********************************************************
        # *        Ordered Sets Detector / Descrambler RX         *
        # *********************************************************
        self.submodules.rx_detector    = DetectOrderedSets()
        self.submodules.rx_descrambler = Descrambler("sys")
        self.add_csr("rx_descrambler")

        self.comb += [
            #self.gtp0.source.connect(self.rx_detector.sink, omit={"valid"}),
            self.rx_detector.sink.valid.eq(1),
            self.rx_detector.source.connect(self.rx_descrambler.sink),
        ]

        # *********************************************************
        # *        Ordered Sets Detector / Descrambler TX         *
        # *********************************************************
        self.submodules.tx_detector    = DetectOrderedSets()
        self.submodules.tx_descrambler = Descrambler("sys")
        self.add_csr("tx_descrambler")

        self.comb += [
            #self.gtp1.source.connect(self.tx_detector.sink, omit={"valid"}),
            self.tx_detector.sink.valid.eq(1),
            self.tx_detector.source.connect(self.tx_descrambler.sink),
        ]

        # *********************************************************
        # *                     Trigger RX                        *
        # *********************************************************
        self.submodules.rx_trigger = Trigger("sys")
        self.comb += [
            self.rx_descrambler.source.connect(self.rx_trigger.sink),
        ]
        self.add_csr("rx_trigger_mem")
        self.add_csr("rx_trigger")

        # *********************************************************
        # *                     Trigger TX                        *
        # *********************************************************
        self.submodules.tx_trigger = Trigger("sys")
        self.comb += [
            self.tx_descrambler.source.connect(self.tx_trigger.sink),
        ]
        self.add_csr("tx_trigger_mem")
        self.add_csr("tx_trigger")

        # *********************************************************
        # *                    Recorder RX                        *
        # *********************************************************
        rx_port = self.sdram.crossbar.get_port("write", 256)

        STRIDE_MULTIPLIER = 12

        rx_recorder = RingRecorder("sys", rx_port, 0, 0x100000, STRIDE_MULTIPLIER)
        self.submodules.rx_recorder = rx_recorder
        self.add_csr("rx_recorder")

        rx_cdc = stream.AsyncFIFO([("address", rx_port.address_width), ("data", rx_port.data_width)],
                                  1024, buffered=True)
        rx_cdc = ClockDomainsRenamer({"write": "sys", "read": "sys"})(rx_cdc)
        self.submodules.rx_cdc = rx_cdc

        self.submodules.rx_dma = LiteDRAMDMAWriter(rx_port)

        self.comb += [
            self.rx_trigger.source.connect(self.rx_recorder.sink),
            self.rx_trigger.enable.eq(self.rx_recorder.enable),

            self.rx_recorder.source.connect(self.rx_cdc.sink),

            self.rx_cdc.source.connect(self.rx_dma.sink),
        ]

        # *********************************************************
        # *                    Recorder TX                        *
        # *********************************************************
        tx_port = self.sdram.crossbar.get_port("write", 256)

        tx_recorder = RingRecorder("sys", tx_port, 0x100000, 0x100000, STRIDE_MULTIPLIER)
        self.submodules.tx_recorder = tx_recorder
        self.add_csr("tx_recorder")

        tx_cdc = stream.AsyncFIFO([("address", tx_port.address_width), ("data", tx_port.data_width)],
                                  1024, buffered=True)
        tx_cdc = ClockDomainsRenamer({"write": "sys", "read": "sys"})(tx_cdc)
        self.submodules.tx_cdc = tx_cdc

        self.submodules.tx_dma = LiteDRAMDMAWriter(tx_port)

        self.comb += [
            self.tx_trigger.source.connect(self.tx_recorder.sink),
            self.tx_trigger.enable.eq(self.tx_recorder.enable),

            self.tx_recorder.source.connect(self.tx_cdc.sink),

            self.tx_cdc.source.connect(self.tx_dma.sink),
        ]

        # *********************************************************
        # *                 Recorder RX/TX                        *
        # *********************************************************
        self.comb += [
            self.tx_recorder.force.eq(self.rx_recorder.enable),
            self.rx_recorder.force.eq(self.tx_recorder.enable),
        ]

# *********************************************************
# *                                                       *
# *                      Build                            *
# *                                                       *
# *********************************************************

def main():
    parser = argparse.ArgumentParser(description="PCIeAnalyzer LiteX SoC Simulation")
    builder_args(parser)
    soc_sdram_args(parser)
    parser.add_argument("--threads",          default=1,              help="Set number of threads (default=1)")
    parser.add_argument("--rom-init",         default=None,           help="rom_init file")
    parser.add_argument("--sdram-module",     default="MT8JTF12864",  help="Select SDRAM chip")
    parser.add_argument("--sdram-data-width", default=32,             help="Set SDRAM chip data width")
    parser.add_argument("--trace",            action="store_true",    help="Enable VCD tracing")
    parser.add_argument("--trace-start",      default=0,              help="Cycle to start VCD tracing")
    parser.add_argument("--trace-end",        default=-1,             help="Cycle to end VCD tracing")
    parser.add_argument("--opt-level",        default="O0",           help="Compilation optimization level")
    args = parser.parse_args()

    soc_kwargs     = {}
    builder_kwargs = builder_argdict(args)

    sim_config = SimConfig(default_clk="sys_clk")

    # *********************************************************
    # *                  Configuration                        *
    # *********************************************************
    if args.rom_init:
        soc_kwargs["integrated_rom_init"] = get_mem_data(args.rom_init, "little")
    sim_config.add_module("ethernet", "eth", args={"interface": "tap0", "ip": "172.30.28.50"})

    # *********************************************************
    # *                  Build                                *
    # *********************************************************
    soc     = PCIeAnalyzer(
        sdram_module     = args.sdram_module,
        sdram_data_width = args.sdram_data_width,
        **soc_kwargs)
    builder = Builder(soc, csr_csv="tools/csr.csv")
    vns = builder.build(threads=args.threads, sim_config=sim_config,
        opt_level   = args.opt_level,
        trace       = args.trace,
        trace_start = int(args.trace_start),
        trace_end   = int(args.trace_end)
    )

if __name__ == "__main__":
    main()
