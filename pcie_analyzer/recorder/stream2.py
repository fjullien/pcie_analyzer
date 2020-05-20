# This file is Copyright (c) 2015 Sebastien Bourdeauducq <sb@m-labs.hk>
# This file is Copyright (c) 2015-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# This file is Copyright (c) 2018 Tim 'mithro' Ansell <me@mith.ro>
# License: BSD

from migen import *
from litex.soc.interconnect.stream import Endpoint, _DownConverter

def _get_converter_ratio(nbits_from, nbits_to):
    converter_cls = _UpConverter
    if nbits_to % nbits_from:
        raise ValueError("Ratio must be an int")
    ratio = nbits_to//nbits_from

    return converter_cls, ratio

class _UpConverter(Module):
    def __init__(self, nbits_from, nbits_to, ratio, reverse):
        self.sink   = sink   = Endpoint([("data", nbits_from)])
        self.source = source = Endpoint([("data", nbits_to), ("valid_token_count", bits_for(ratio))])
        self.latency = 1
        self.flush = Signal()

        # # #

        # Control path
        demux      = Signal(max=ratio)
        load_part  = Signal()
        strobe_all = Signal()
        self.comb += [
            sink.ready.eq(~strobe_all | source.ready),
            source.valid.eq(strobe_all),
            load_part.eq(sink.valid & sink.ready)
        ]

        demux_last = ((demux == (ratio - 1)) | sink.last)

        self.sync += [
            If(source.ready, strobe_all.eq(0)),
            If(self.flush,
                demux.eq(0),
                strobe_all.eq(1)
            ),
            If(load_part,
                If(demux_last,
                    demux.eq(0),
                    strobe_all.eq(1)
                ).Else(
                    demux.eq(demux + 1)
                )
            ),
            If(source.valid & source.ready,
                If(sink.valid & sink.ready,
                    source.first.eq(sink.first),
                    source.last.eq(sink.last)
                ).Else(
                    source.first.eq(0),
                    source.last.eq(0)
                )
            ).Elif(sink.valid & sink.ready,
                source.first.eq(sink.first | source.first),
                source.last.eq(sink.last | source.last)
            )
        ]

        # Data path
        cases = {}
        for i in range(ratio):
            n = ratio-i-1 if reverse else i
            cases[i] = source.data[n*nbits_from:(n+1)*nbits_from].eq(sink.data)
        self.sync += If(load_part, Case(demux, cases))

        # Valid token count
        self.sync += If(load_part, source.valid_token_count.eq(demux + 1))

class Converter(Module):
    def __init__(self, nbits_from, nbits_to,
        reverse                  = False,
        report_valid_token_count = False):
        self.cls, self.ratio = _get_converter_ratio(nbits_from, nbits_to)
        self.flush = Signal()

        # # #

        converter = self.cls(nbits_from, nbits_to, self.ratio, reverse)
        self.submodules += converter
        self.latency = converter.latency

        self.comb += converter.flush.eq(self.flush)

        self.sink = converter.sink
        if report_valid_token_count:
            self.source = converter.source
        else:
            self.source = Endpoint([("data", nbits_to)])
            self.comb += converter.source.connect(self.source, omit=set(["valid_token_count"]))

class StrideConverter2(Module):
    def __init__(self, description_from, description_to, reverse=False, report_valid_token_count=False):
        self.sink   = sink   = Endpoint(description_from)
        self.source = source = Endpoint(description_to)
        self.flush  = Signal()

        # # #

        nbits_from = len(sink.payload.raw_bits())
        nbits_to   = len(source.payload.raw_bits())

        converter = Converter(nbits_from, nbits_to, reverse, report_valid_token_count)
        self.submodules += converter

        # Cast sink to converter.sink (user fields --> raw bits)
        self.comb += [
            converter.sink.valid.eq(sink.valid),
            converter.sink.first.eq(sink.first),
            converter.sink.last.eq(sink.last),
            converter.flush.eq(self.flush),
            sink.ready.eq(converter.sink.ready)
        ]

        if report_valid_token_count == True:
            self.valid_token_count = Signal(8)
            self.comb += self.valid_token_count.eq(converter.source.valid_token_count)

        if converter.cls == _DownConverter:
            ratio = converter.ratio
            for i in range(ratio):
                j = 0
                for name, width in source.description.payload_layout:
                    src = getattr(sink, name)[i*width:(i+1)*width]
                    dst = converter.sink.data[i*nbits_to+j:i*nbits_to+j+width]
                    self.comb += dst.eq(src)
                    j += width
        else:
            self.comb += converter.sink.data.eq(sink.payload.raw_bits())


        # Cast converter.source to source (raw bits --> user fields)
        self.comb += [
            source.valid.eq(converter.source.valid),
            source.first.eq(converter.source.first),
            source.last.eq(converter.source.last),
            converter.source.ready.eq(source.ready)
        ]
        if converter.cls == _UpConverter:
            ratio = converter.ratio
            for i in range(ratio):
                j = 0
                for name, width in sink.description.payload_layout:
                    src = converter.source.data[i*nbits_from+j:i*nbits_from+j+width]
                    dst = getattr(source, name)[i*width:(i+1)*width]
                    self.comb += dst.eq(src)
                    j += width
        else:
            self.comb += source.payload.raw_bits().eq(converter.source.data)

        # Connect params
        if converter.latency == 0:
            self.comb += source.param.eq(sink.param)
        elif converter.latency == 1:
            self.sync += source.param.eq(sink.param)
        else:
            raise ValueError
