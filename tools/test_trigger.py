#!/usr/bin/env python3

import sys

from litex import RemoteClient

wb = RemoteClient()
wb.open()

# # #

# *********************************************************
# *                                                       *
# *                      Helpers                          *
# *                                                       *
# *********************************************************

def make_mem_data(dc, ctrl, data):
    return (dc << 18) + (ctrl << 16) + data

# *********************************************************
# *                                                       *
# *                Trigger memory data                    *
# *                                                       *
# *********************************************************

#  data       ------------------------------+
#  ctrl       -----------------------+      |
#  don't care -------------------+   |      |
#  address    --+                |   |      |
#               |                |   |      |
#               v                v   v      v
mem_data =    [(0, make_mem_data(0, 0b11, 0xbcf7)),
               (1, make_mem_data(1, 0b00, 0x0000)),
               (2, make_mem_data(1, 0b00, 0x0000)),
               (3, make_mem_data(0, 0b00, 0x4a4a)),
]

# *********************************************************
# *                                                       *
# *                  Trigger control                      *
# *                                                       *
# *********************************************************

class Trigger:
    def __init__(self, name):
        self._armed   = getattr(wb.regs, name + "_armed")
        self._trigged = getattr(wb.regs, name + "_trigged")
        self._size    = getattr(wb.regs, name + "_size")
        self._mem     = getattr(wb.bases, name + "_mem")

    def configure(self, data):
        print("Configure trigger memory")
        offset = 0
        for addr, val in mem_data:
                print("{:x} -> {:b} {:04x}".format(addr, val >> 16, val & 0xffff))
                wb.write(wb.bases.rx_trigger_mem + (addr * 4), val)
        self._size.write(len(mem_data))
        print("Done...")

    def armed(self, value):
        self._armed.write(value)

# *********************************************************
# *                                                       *
# *                      Run tests                        *
# *                                                       *
# *********************************************************

trigger = Trigger("rx_trigger")

# Load trigger memory
trigger.configure(mem_data)

# Arm trigger
trigger.armed(1)

# Wait trigger
print("Wait for trigger...")
while trigger._trigged.read() != 1:
    pass
print("Done !")

# Arm trigger
trigger.armed(0)

# # #

wb.close()
