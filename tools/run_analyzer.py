#!/usr/bin/env python3

from litex.tools.litex_client import RemoteClient
from litescope.software.driver.analyzer import LiteScopeAnalyzerDriver

wb = RemoteClient()
wb.open()

analyzer = LiteScopeAnalyzerDriver(wb.regs, "analyzer", debug=True)

analyzer.configure_subsampler(1)  ## increase this to "skip" cycles, e.g. subsample
analyzer.configure_group(0)

#analyzer.add_falling_edge_trigger("soc_videooverlaysoc_hdmi_in0_timing_payload_vsync")
#analyzer.add_rising_edge_trigger("soc_videooverlaysoc_hdmi_in0_timing_payload_de")
#analyzer.add_trigger(cond={"soc_videooverlaysoc_hdmi_in0_timing_payload_hsync" : 1})
#analyzer.add_rising_edge_trigger("descrambler0_source_ready")


# trigger conditions will depend upon each other in sequence
#analyzer.add_trigger(cond = {"gtp0_source_payload_data" : 0x1cbc,
#                             "gtp0_source_payload_ctrl" : 3}) 
#analyzer.add_trigger(cond = {"detectorderedsets1_source_payload_type" : 1}) 

#analyzer.add_falling_edge_trigger("trig")

analyzer.run(offset=128, length=1024)  ### CHANGE THIS TO MATCH DEPTH
analyzer.wait_done()
analyzer.upload()
analyzer.save("dump.vcd")

wb.close()
