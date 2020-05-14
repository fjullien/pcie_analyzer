#!/usr/bin/env python3

# This file is Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import sys

from migen import *
from migen.genlib.cdc import *

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform

from litex.soc.cores.clock import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *
from litex.soc.interconnect import stream

from litedram.modules import MT8JTF12864
from litedram.phy import s7ddrphy
from litedram.frontend.dma import LiteDRAMDMAWriter

from liteeth.phy.s7rgmii import LiteEthPHYRGMII
from liteeth.core import LiteEthUDPIPCore
from liteeth.frontend.etherbone import LiteEthEtherbone

from pcie_analyzer.liteiclink.gtp_7series import GTPQuadPLL, GTP

from pcie_analyzer.capture_pipeline.capture_pipeline import *
from pcie_analyzer.common import *

# *********************************************************
# *                                                       *
# *                      IOs                              *
# *                                                       *
# *********************************************************

_io = [
    ("clk200", 0,
        Subsignal("p", Pins("R3"), IOStandard("DIFF_SSTL15")),
        Subsignal("n", Pins("P3"), IOStandard("DIFF_SSTL15"))
    ),

    ("cpu_reset", 0, Pins("U4"), IOStandard("SSTL15")),

    ("user_led", 0, Pins("M26"), IOStandard("LVCMOS33")),
    ("user_led", 1, Pins("T24"), IOStandard("LVCMOS33")),
    ("user_led", 2, Pins("T25"), IOStandard("LVCMOS33")),
    ("user_led", 3, Pins("R26"), IOStandard("LVCMOS33")),

    ("pcie_refclk", 0,
        Subsignal("p", Pins("F11")),
        Subsignal("n", Pins("E11"))
    ),

    ("pcie_tx", 0,
        Subsignal("p", Pins("D10")),
        Subsignal("n", Pins("C10"))
    ),
    ("pcie_rx", 0,
        Subsignal("p", Pins("D12")),
        Subsignal("n", Pins("C12"))
    ),

    ("pcie_tx", 1,
        Subsignal("p", Pins("B9")),
        Subsignal("n", Pins("A9"))
    ),
    ("pcie_rx", 1,
        Subsignal("p", Pins("B13")),
        Subsignal("n", Pins("AA3"))
    ),

    ("eth_clocks", 0,
        Subsignal("tx", Pins("U22")),
        Subsignal("rx", Pins("U21")),
        IOStandard("LVCMOS18")
    ),
    ("eth", 0,
        Subsignal("rx_ctl", Pins("U14")),
        Subsignal("rx_data", Pins("U17 V17 V16 V14")),
        Subsignal("tx_ctl", Pins("T15")),
        Subsignal("tx_data", Pins("U16 U15 T18 T17")),
        Subsignal("rst_n", Pins("V18")),
        Subsignal("mdc", Pins("W18")),
        Subsignal("mdio", Pins("T14")),
        IOStandard("LVCMOS18"), Misc("SLEW=FAST"), Drive(16)
    ),

    ("serial", 0,
        Subsignal("cts", Pins("V19")),
        Subsignal("rts", Pins("W19")),
        Subsignal("tx", Pins("U19")),
        Subsignal("rx", Pins("T19")),
        IOStandard("LVCMOS18")
    ),

    ("ddram", 0,
        Subsignal("a", Pins(
            "M4 J3 J1 L4 K5 M7 K1 M6",
            "H1 K3 N7 L5 L7 N6 L3 K2"),
            IOStandard("SSTL15")),
        Subsignal("ba", Pins("N1 M1 H2"), IOStandard("SSTL15")),
        Subsignal("ras_n", Pins("P1"), IOStandard("SSTL15")),
        Subsignal("cas_n", Pins("T4"), IOStandard("SSTL15")),
        Subsignal("we_n", Pins("R1"), IOStandard("SSTL15")),
        Subsignal("cs_n", Pins("T3"), IOStandard("SSTL15")),
        Subsignal("dm", Pins("AC6 AC4 AA3 U7"),
            IOStandard("SSTL15")),
        Subsignal("dq", Pins(
            "AB6 AA8 Y8 AB5 AA5 Y5 Y6 Y7",
            "AF4 AF5 AF3 AE3 AD3 AC3 AB4 AA4",
            "AC2 AB2 AF2 AE2 Y1 Y2 AC1 AB1",
            "Y3 W3 W6 V6 W4 W5 W1 V1"),
            IOStandard("SSTL15"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("dqs_p", Pins("V8 AD5 AD1 V3"),
            IOStandard("DIFF_SSTL15")),
        Subsignal("dqs_n", Pins("W8 AE5 AE1 V2"),
            IOStandard("DIFF_SSTL15")),
        Subsignal("clk_p", Pins("M2"), IOStandard("DIFF_SSTL15")),
        Subsignal("clk_n", Pins("L2"), IOStandard("DIFF_SSTL15")),
        Subsignal("cke", Pins("P4"), IOStandard("SSTL15")),
        Subsignal("odt", Pins("R2"), IOStandard("SSTL15")),
        Subsignal("reset_n", Pins("N8"), IOStandard("LVCMOS15")),
        Misc("SLEW=FAST"),
    ),
]

# *********************************************************
# *                                                       *
# *                      Platform                         *
# *                                                       *
# *********************************************************

class Platform(XilinxPlatform):
    def __init__(self):
        XilinxPlatform.__init__(self, "xc7a200t-fbg676-2", _io, toolchain="vivado")
        self.toolchain.bitstream_commands = ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]"]
        self.toolchain.additional_commands = ["write_cfgmem -force -format MCS -size 32 -interface SPIx4 -loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.mcs"]

# *********************************************************
# *                                                       *
# *                      CRG                              *
# *                                                       *
# *********************************************************

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys       = ClockDomain()
        self.clock_domains.cd_sys4x     = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys4x_dqs = ClockDomain(reset_less=True)
        self.clock_domains.cd_clk200    = ClockDomain()
        self.clock_domains.cd_clk125    = ClockDomain()

        # # #

        clk200 = platform.request("clk200")
        rst    = platform.request("cpu_reset")
        platform.add_period_constraint(clk200.p, 1e9/200e6)

        self.submodules.pll = pll = S7MMCM(speedgrade=-2)
        self.comb += pll.reset.eq(rst)
        pll.register_clkin(clk200, 200e6)
        pll.create_clkout(self.cd_sys,       sys_clk_freq)
        pll.create_clkout(self.cd_sys4x,     4*sys_clk_freq)
        pll.create_clkout(self.cd_sys4x_dqs, 4*sys_clk_freq, phase=90)
        pll.create_clkout(self.cd_clk200,    200e6)
        pll.create_clkout(self.cd_clk125,    125e6)

        self.submodules.idelayctrl = S7IDELAYCTRL(self.cd_clk200)

# *********************************************************
# *                                                       *
# *                      Analyzer                         *
# *                                                       *
# *********************************************************

class PCIeAnalyzer(SoCSDRAM):
    def __init__(self, platform, connector="pcie", linerate=2.5e9):
        assert connector in ["pcie"]
        sys_clk_freq = int(50e6)

        # *********************************************************
        # *                      SoC SDRAM                        *
        # *********************************************************
        SoCSDRAM.__init__(self, platform, sys_clk_freq,
            integrated_rom_size  = 0x8000,
            integrated_sram_size = 0x1000,
            uart_name            = "serial",
            l2_size              = 0,
            csr_data_width       = 32,
        )

        # *********************************************************
        # *                      CRG                              *
        # *********************************************************
        self.submodules.crg = _CRG(platform, sys_clk_freq)
        platform.add_period_constraint(self.crg.cd_sys.clk, 1e9/sys_clk_freq)

        # *********************************************************
        # *                      DDR3                             *
        # *********************************************************

        self.submodules.ddrphy = s7ddrphy.A7DDRPHY(platform.request("ddram"),
            memtype      = "DDR3",
            nphases      = 4,
            sys_clk_freq = sys_clk_freq)
        self.add_csr("ddrphy")
        sdram_module = MT8JTF12864(sys_clk_freq, "1:4")
        self.register_sdram(self.ddrphy,
            geom_settings   = sdram_module.geom_settings,
            timing_settings = sdram_module.timing_settings)

        # *********************************************************
        # *                  Ethernet PHY                         *
        # *********************************************************
        eth_phy = LiteEthPHYRGMII(
            clock_pads         = platform.request("eth_clocks"),
            pads               = platform.request("eth"),
            with_hw_init_reset = False,
            tx_delay           = 0e-9,
            rx_delay           = 0e-9)
        self.submodules.eth_phy = ClockDomainsRenamer("eth_tx")(eth_phy)
        self.add_csr("eth_phy")

        # *********************************************************
        # *                  Ethernet Core                        *
        # *********************************************************
        eth_core = LiteEthUDPIPCore(
            phy         = self.eth_phy,
            mac_address = 0x10e2d5000000,
            ip_address  = "192.168.1.201",
            clk_freq    = 125000000)
        self.submodules.eth_core = ClockDomainsRenamer("eth_tx")(eth_core)

        # *********************************************************
        # *                 Etherbone bridge                      *
        # *********************************************************
        etherbone_cd = ClockDomain("etherbone") # similar to sys but need for correct
        self.clock_domains += etherbone_cd      # clock domain renaming
        self.comb += [
            etherbone_cd.clk.eq(ClockSignal("sys")),
            etherbone_cd.rst.eq(ResetSignal("sys"))
        ]
        self.submodules.etherbone = LiteEthEtherbone(self.eth_core.udp, 1234, cd="etherbone")
        self.add_wb_master(self.etherbone.wishbone.bus)

        # *********************************************************
        # *          Timing constraints for Ethernet              *
        # *********************************************************
        self.platform.add_period_constraint(self.eth_phy.crg.cd_eth_rx.clk, 1e9/125e6)
        self.platform.add_period_constraint(self.eth_phy.crg.cd_eth_tx.clk, 1e9/125e6)
        self.platform.add_false_path_constraints(
            self.crg.cd_sys.clk,
            self.eth_phy.crg.cd_eth_rx.clk,
            self.eth_phy.crg.cd_eth_tx.clk)

        # *********************************************************
        # *                     GTP Refclk                        *
        # *********************************************************
        refclk      = Signal()
        refclk_freq = 100e6
        refclk_pads = platform.request("pcie_refclk")
        self.specials += Instance("IBUFDS_GTE2",
            i_CEB   = 0,
            i_I     = refclk_pads.p,
            i_IB    = refclk_pads.n,
            o_O     = refclk)

        # *********************************************************
        # *                     GTP PLL                           *
        # *********************************************************
        qpll = GTPQuadPLL(refclk, refclk_freq, linerate)
        print(qpll)
        self.submodules += qpll

        # *********************************************************
        # *                       GTPs                            *
        # *********************************************************
        for i in range(2):
            tx_pads = platform.request(connector + "_tx", i)
            rx_pads = platform.request(connector + "_rx", i)
            gtp = GTP(qpll, tx_pads, rx_pads, sys_clk_freq,
                data_width       = 20,
                clock_aligner    = False,
                tx_buffer_enable = True,
                rx_buffer_enable = True)
            gtp.add_stream_endpoints()
            gtp.tx_enable = 0
            setattr(self.submodules, "gtp"+str(i), gtp)
            platform.add_period_constraint(gtp.cd_tx.clk, 1e9/gtp.tx_clk_freq)
            platform.add_period_constraint(gtp.cd_rx.clk, 1e9/gtp.rx_clk_freq)
            self.platform.add_false_path_constraints(
                self.crg.cd_sys.clk,
                gtp.cd_tx.clk,
                gtp.cd_rx.clk)

        # *********************************************************
        # *         Capture pipeline clock selection              *
        # *********************************************************
        rx_sim = Signal()
        tx_sim = Signal()

        self.comb += [
            self.gtp0.simuclk.eq(self.crg.cd_clk125.clk),
            self.gtp0.clksel.eq(rx_sim),

            self.gtp1.simuclk.eq(self.crg.cd_clk125.clk),
            self.gtp1.clksel.eq(tx_sim),
        ]

        # *********************************************************
        # *                      Time base                        *
        # *********************************************************
        time    = Signal(32)
        time_rx = Signal(32)
        time_tx = Signal(32)

        self.sync.clk125 += time.eq(time + 1)
        self.specials += MultiReg(time, time_rx, "gtp0_rx")
        self.specials += MultiReg(time, time_tx, "gtp1_rx")

        # *********************************************************
        # *                RX Capture Pipeline                    *
        # *********************************************************

        RX_RING_BUFFER_BASE_ADDRESS = 0
        RX_RING_BUFFER_SIZE         = 0x100000

        # Elaborate gtp0_ready
        gtp0_ready = Signal()
        self.specials += MultiReg(qpll.lock & self.gtp0.rx_ready, gtp0_ready, "gtp0_rx")
        
        # Request RX DDR3 port
        rx_port = self.sdram.crossbar.get_port("write", 256)


        self.submodules.rx_capture = CapturePipeline("gtp0_rx",
                                                     rx_port,
                                                     RX_RING_BUFFER_BASE_ADDRESS,
                                                     RX_RING_BUFFER_SIZE)
        self.add_csr("rx_capture")
        self.add_csr("rx_capture_exerciser_mem")
        self.add_csr("rx_capture_trigger_mem")

        pipeline_ready = Signal()

        self.comb += [
            self.gtp0.source.connect(self.rx_capture.sink, omit={"valid"}),
            pipeline_ready.eq(gtp0_ready | self.rx_capture.simmode),
            self.rx_capture.sink.valid.eq(pipeline_ready),
            self.rx_capture.time.eq(time_rx),
            rx_sim.eq(self.rx_capture.simu.storage),
        ]

        # *********************************************************
        # *                TX Capture Pipeline                    *
        # *********************************************************

        TX_RING_BUFFER_BASE_ADDRESS = 0x100000
        TX_RING_BUFFER_SIZE         = 0x100000

        # Elaborate gtp1_ready
        gtp1_ready = Signal()
        self.specials += MultiReg(qpll.lock & self.gtp1.rx_ready, gtp1_ready, "gtp1_rx")
        
        # Request TX DDR3 port
        tx_port = self.sdram.crossbar.get_port("write", 256)


        self.submodules.tx_capture = CapturePipeline("gtp1_rx",
                                                     tx_port,
                                                     TX_RING_BUFFER_BASE_ADDRESS,
                                                     TX_RING_BUFFER_SIZE)
        self.add_csr("tx_capture")
        self.add_csr("tx_capture_exerciser_mem")
        self.add_csr("tx_capture_trigger_mem")

        self.comb += [
            self.gtp1.source.connect(self.tx_capture.sink, omit={"valid"}),
            self.tx_capture.sink.valid.eq(gtp1_ready),
            self.tx_capture.time.eq(time_tx),
            tx_sim.eq(self.tx_capture.simu.storage),
        ]

        # *********************************************************
        # *                 Recorder RX/TX                        *
        # *********************************************************
        self.comb += [
            self.tx_capture.forced.eq(self.rx_capture.record),
            self.rx_capture.forced.eq(self.tx_capture.record),
            self.tx_capture.trigExt.eq(self.rx_capture.trigOut),
            self.rx_capture.trigExt.eq(self.tx_capture.trigOut),
        ]

        # *********************************************************
        # *                           LEDs                        *
        # *********************************************************

        led_counter = Signal(32)
        self.sync.gtp0_rx += led_counter.eq(led_counter + 1)
        self.comb += platform.request("user_led", 0).eq(led_counter[24])

        self.comb += platform.request("user_led", 1).eq(self.gtp0.rx_cdr_lock)
        self.comb += platform.request("user_led", 2).eq(self.gtp1.rx_cdr_lock)
        self.comb += platform.request("user_led", 3).eq(0)

        # *********************************************************
        # *                          ILA                          *
        # *********************************************************
        # ~ from litescope import LiteScopeAnalyzer
        # ~ analyzer_signals = [
            # ~ self.rx_recorder.sink.data,
            # ~ self.rx_recorder.enable,
            # ~ self.rx_recorder.trigAddr.status,
            # ~ self.rx_recorder.start.re,
            # ~ self.rx_recorder.fsm,
            # ~ self.rx_recorder.fifo.source.data,
            # ~ self.rx_recorder.fifo.source.trig,
            # ~ self.rx_recorder.fifo.level,
            # ~ self.rx_recorder.source.address,
            # ~ self.rx_recorder.source.data,
            # ~ self.rx_recorder.source.ready,
            # ~ self.rx_recorder.source.valid,
            # ~ self.rx_descrambler.source.data,
            # ~ self.rx_trigger.fsm
        # ~ ]

        # ~ self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals, 4096, clock_domain="gtp0_rx", csr_csv="tools/analyzer.csv")
        # ~ self.add_csr("analyzer")

        #from litescope import LiteScopeAnalyzer
        #analyzer_signals = [
        #    self.rx_cdc.source.data,
        #    self.rx_cdc.source.ready,
        #    self.rx_cdc.source.valid,
        #    self.rx_dma_recorder.fsm,
        #]
        #
        #self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals, 4096, csr_csv="tools/analyzer.csv")
        #self.add_csr("analyzer")

# Load ---------------------------------------------------------------------------------------------

def load():
    from litex.build.xilinx import VivadoProgrammer
    prog = VivadoProgrammer()
    prog.load_bitstream("build/gateware/ac701.bit")
    exit()


def flash():
    from litex.build.xilinx import VivadoProgrammer
    prog = VivadoProgrammer(flash_part="mt25ql256-spi-x1_x2_x4")
    prog.flash(0, "build/gateware/ac701.mcs")
    exit()

# Build --------------------------------------------------------------------------------------------

def main():
    if "load" in sys.argv[1:]:
        load()
    if "flash" in sys.argv[1:]:
        flash()
    platform = Platform()
    soc     = PCIeAnalyzer(platform)
    builder = Builder(soc, output_dir="build", csr_csv="tools/csr.csv")
    builder.build(build_name="ac701")

if __name__ == "__main__":
    main()
