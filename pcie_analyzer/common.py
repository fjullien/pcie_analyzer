# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from enum import IntEnum

class osetsType(IntEnum):
    DATA = 0
    SKIP = 1
    IDLE = 2
    FTS  = 3
    TS1  = 4
    TS2  = 5
    COMPLIANCE = 6
    MODIFIED_COMPLIANCE = 7

descrambler_layout = [
    ("data" , 16),
    ("ctrl" , 2),
    ("osets", 2),
    ("type" , 4)
]

trigger_layout = [
    ("data"   , 16), # 2 bytes
    ("ctrl"   , 2),  # 2 K symbols flag
    ("trig"   , 1)   # 1 Trigger position indicator
#   ("spare"  , 1)   # 
]

recorder_layout = [
    ("data"   , 192), # 24 bytes
    ("ctrl"   , 24),  # 24 K symbols flag
    ("trig"   , 12)   # Trigger position indicator
#   ("spare"  , 12)   # 
]

RECORD_DATA = slice(0,192)
RECORD_CTRL = slice(192,216)
RECORD_TRIG = slice(216,228)