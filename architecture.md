    +-----+                    +----------------------+         +---------------+
    |     +------------------->+                      |         |               |
    | GTP |                    |   DetectOrderedSets  +-------->+  Descrambler  +----+
    |     |      valid +------>+                      |         |               |    |
    +-----+            |       +----------------------+         +---------------+    |
                       |                                                             |
                       |                                                             |
                       |                                                             |
                       +                                                             |
             qpll.lock & gtp.rx_ready          +---------+                           |
                                               |         +<--------------------------+
    +------------------------------------------+ Trigger |
    |                                          |         +<-----------------------+
    |                                          +---------+                        |
    |                                                                             |
    |          +------------------------------------------------------------+     | enable
    |          |                                                            |     |
    |          |  +-----------------+    +--------------+    +-----------+  +-----+
    |          |  |                 |    |              |    |           |  |
    +------------>+ StrideConverter +--->+ RingRecorder +--->+ AsyncFIFO +-----------+
               |  |                 |    |              |    |           |  |        |
               |  +-----------------+    +--------------+    +-----------+  |        |
               |                                                            |        |
               +------------------------------------------------------------+        |
                                                                                     |
    +--------------------------------------------------------------------------------+
    |
    |                        +----------------------+         +----------------------+
    |                        |                      |         |                      |
    +----------------------->+ LiteDRAMDMAWriter    +-------->+ DDR Memory controller|
                             |                      |         |                      |
                             +----------------------+         +----------------------+


## GTP
This module provides PCIe sniffed datas.
Source Record format is:

    [("data", 16), ("ctrl", 2)]
If *ctrl* is '1' for a nibble, it means it's a special symbol.

## DetectOrderedSets

Sink: 

     [("data", 16), ("ctrl", 2)]
Source:

    descrambler_layout = [
        ("data" , 16),
        ("ctrl" , 2),
        ("osets", 2),
        ("type" , 4)
    ]
    
Detect PCIe Ordered Sets. Descrambler needs this information to disable descrambling during TS1 and TS2 ordered sets.
Moreover, *osets* and *type* can be used as a trigger source.
If *osets* is '1' for a nibble, it means it's part of an ordered set *type*.

This is the definition for *type*:

    class osetsType(IntEnum):
        DATA = 0
        SKIP = 1
        IDLE = 2
        FTS  = 3
        TS1  = 4
        TS2  = 5
        COMPLIANCE = 6
        MODIFIED_COMPLIANCE = 7

## Descrambler

Sink: 

    descrambler_layout = [
        ("data" , 16),
        ("ctrl" , 2),
        ("osets", 2),
        ("type" , 4)
    ]
Source:

    descrambler_layout = [
        ("data" , 16),
        ("ctrl" , 2),
        ("osets", 2),
        ("type" , 4)
    ]

Descramble data as per PCIe polynomial  *X^16^+X^5^+X^4^+X^3^+1*

## Trigger
Sink: 

    descrambler_layout = [
        ("data" , 16),
        ("ctrl" , 2),
        ("osets", 2),
        ("type" , 4)
    ]
Source:

    trigger_layout = [
        ("data" , 16),
        ("ctrl" , 2),
        ("trig" , 1)
    ]

Trigger compares incoming datas to a trigger memory value. Each time there is a match, trigger memory presents the next data to be compared. If the comparaison fails, trigger memory pointer is reset to 0.
When incoming datas match trigger memory, trig bit is set in source stream. It'll be on the last data of trigger memory match. Software is then responsible to find the first byte of matching sequence.

## StrideConverter
Sink: 

    trigger_layout = [
        ("data" , 16),
        ("ctrl" , 2),
        ("osets", 2),
        ("type" , 4)
    ]
Source:

    recorder_layout= [
        ("data" , 192),
        ("ctrl" , 24),
        ("trig" , 12)
    ]
Convert source stream size to native memory size (here it is 256 bits).

## AsyncFIFO
This FIFO is here to do the clock domain crossing between *cd_gtp0_rx* and *cd_sys*.

Data layout:

    recorder_layout= [
        ("data" , 192),
        ("ctrl" , 24),
        ("trig" , 12)
    ]

## Recorder

This module starts and stops LiteDRAMDMAWriter depending on storage parameters and trigger conditions.
When software want to capture something then:
1. Trigger is configured and enabled,
2. DMA is started. DMA will act as a ring buffer of configured depth. It continuously stores data until it is stopped,
3. Once a number of pre-trigger data have been captured, Recorder waits for a trigger condition (DMA still runs),
4. When trigger condition is detected, the current DMA address is saved,
5. Recorder waits for post-trigger datas,
6. DMA is stopped, trigger is disabled,
7. Sotfware can now get datas from address [@trigger - pre_samples_size] to [@trigger + post_samples_size]

