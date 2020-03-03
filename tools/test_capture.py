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
# *                  Trigger control                      *
# *                                                       *
# *********************************************************

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
                print("{:x} -> {:1b} {:02b} {:04x}".format(addr, (val >> 18) & 3, (val >> 16) & 3, val & 0xffff))
                wb.write(wb.bases.rx_trigger_mem + (addr * 4), val)
        self._size.write(len(mem_data))
        print("Done...")

    def armed(self, value):
        self._armed.write(value)


# *********************************************************
# *                                                       *
# *                  Recorder control                      *
# *                                                       *
# *********************************************************

class Recorder:
    def __init__(self, name):
        self._start    = getattr(wb.regs, name + "_start")
        self._stop     = getattr(wb.regs, name + "_stop")
        self._finished = getattr(wb.regs, name + "_finished")
        self._size     = getattr(wb.regs, name + "_size")
        self._offset   = getattr(wb.regs, name + "_offset")
        self._trigAddr = getattr(wb.regs, name + "_trigAddr")

        self.addr   = 0;
        self.offset = 0;
        self.size   = 0;

    def configure(self, size, offset):
        print("Capture size {} bytes, trigger offset {}".format(size, offset))
        self._size.write(size - offset)
        self._offset.write(offset)
        self.offset = offset
        self.size = size

    def start(self):
        self._start.write(1)

    def stop(self):
        self._stop.write(1)

    def wait(self):
        while self._finished.read() != 1:
            pass
        print("Done !")
        self.addr = self._trigAddr.read()
        print("Trigger at 0x{:08x}".format(self.addr))

    def upload(self):
        base = wb.mems.main_ram.base
        base += self.addr - self.offset
        size = self.size
        print("Upload of {} bytes from 0x{:08x}...".format(size, base))
        datas = []
        for i in range(size//4):
            datas.append(wb.read(base + 4*i))
        return datas

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
mem_data =    [(0, make_mem_data(0, 0b00, 0x8000)),
               (1, make_mem_data(1, 0b00, 0x0000)),
               (2, make_mem_data(1, 0b00, 0x0000)),
               (3, make_mem_data(1, 0b00, 0x0000)),
]

# *********************************************************
# *                                                       *
# *                      Run tests                        *
# *                                                       *
# *********************************************************

#wb.write(wb.mems.main_ram.base, 0x11223344)
#wb.write(wb.mems.main_ram.base + 4, 0x55667788)
#val = wb.read(wb.mems.main_ram.base)
#print("{:08x}".format(val))
#val = wb.read(wb.mems.main_ram.base + 4)
#print("{:08x}".format(val))

trigger  = Trigger("rx_trigger")
recorder = Recorder("rx_recorder")

# Load trigger memory
trigger.configure(mem_data)

# Arm trigger
trigger.armed(1)

recorder.configure(0x1000, 0x400)
recorder.start()
recorder.wait()
recorder.stop()

datas = recorder.upload()
for data in datas:
    print("{:08x}".format(data))



# # #

wb.close()
