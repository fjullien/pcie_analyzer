# This file is Copyright (c) 2020 Franck Jullien <franck.jullien@gmail.com>
# License: BSD

from enum import IntEnum

def K(x, y):
    """K code generator ex: K(28, 5) is COM Symbol"""
    return (y << 5) | x

def D(x, y):
    """D code generator"""
    return (y << 5) | x

# Symbols (6.3.5) ----------------------------------------------------------------------------------

class Symbol:
    """Symbol definition with name, 8-bit value and description"""
    def __init__(self, name, value, description=""):
        self.name        = name
        self.value       = value
        self.description = description

SKP =  Symbol("SKP", K(28, 0), "Skip")
COM =  Symbol("COM", K(28, 5), "Comma")
STP =  Symbol("STP", K(27, 7), "Start TLP")
SDP =  Symbol("SDP", K(28, 2), "Start DLLP")
END =  Symbol("END", K(29, 7), "End")
EDB =  Symbol("EDB", K(30, 7), "End Bad")
PAD =  Symbol("PAD", K(23, 7), "Padding")
FTS =  Symbol("FTS", K(28, 1), "Fast Train Sequence")
IDL =  Symbol("IDL", K(28, 3), "Electrical Idle")
EIE =  Symbol("EIE", K(28, 7), "Electrical Idle Exit")

symbols = [SKP, COM, STP, SDP, END, EDB, PAD, FTS, IDL, EIE]

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

gtp_layout = [
    ("data"   , 16), # 2 bytes
    ("ctrl"   , 2),  # 2 K symbols flag
]

filter_layout = [
    ("data"   , 16), # 2 bytes
    ("ctrl"   , 2),  # 2 K symbols flag
    ("time"   , 1)   # 1 Trigger position indicator
]

def recorder_layout(nb):
    payload = [
        ("data"   , 16 * nb),
        ("ctrl"   , 2 * nb),
        ("trig"   , nb)
    #   ("spare"  , xx)
    ]
    return payload

#RECORD_DATA = slice(0,192)
#RECORD_CTRL = slice(192,216)
#RECORD_TRIG = slice(216,228)
