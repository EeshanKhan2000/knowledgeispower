"""Low-memory streaming reader for R .rda/.RData files (XDR serialization v2/v3), no R needed.

`rdata` builds a Python object per CHARSXP and runs out of memory on large scpdata objects (hundreds of
PSM-level assays). This reader keeps numeric vectors as numpy arrays and drops the contents of string
vectors longer than `max_str` (replaced by None), which is enough to pull out protein-level assays,
their row names and the colData. Used by the scripts/corpus_ext builders.

    from rda_stream import load_rda, RObj
    top = load_rda(path, max_str=300_000)   # list of (name, RObj)
"""
import bz2
import gzip
import io
import lzma
import struct

import numpy as np

NILVALUE, GLOBALENV, UNBOUND, MISSINGARG, BASENS, NAMESPACE, PACKAGE, PERSIST = 254, 253, 252, 251, 250, 249, 248, 247
EMPTYENV, BASEENV, ATTRLANG, ATTRLIST, ALTREP, REF = 242, 241, 240, 239, 238, 255
PAIRLIKE = {2, 3, 5, 6, 17, ATTRLANG, ATTRLIST}


class RObj:
    __slots__ = ("type", "value", "attr", "tag")

    def __init__(self, type, value=None, attr=None, tag=None):
        self.type, self.value, self.attr, self.tag = type, value, attr or {}, tag

    def __repr__(self):
        v = self.value
        n = len(v) if hasattr(v, "__len__") else ""
        return f"RObj(type={self.type}, len={n}, attrs={list(self.attr)})"


def _open(path):
    with open(path, "rb") as f:
        mg = f.read(6)
    if mg.startswith(b"\xfd7zXZ"):
        raw = lzma.open(path)
    elif mg.startswith(b"\x1f\x8b"):
        raw = gzip.open(path)
    elif mg.startswith(b"BZh"):
        raw = bz2.open(path)
    else:
        raw = open(path, "rb")
    return io.BufferedReader(raw, buffer_size=1 << 22)


class _Reader:
    def __init__(self, f, max_str):
        self.f, self.max_str, self.refs = f, max_str, []

    def read(self, n):
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError
        return b

    def i(self):
        return struct.unpack(">i", self.read(4))[0]

    def length(self):
        n = self.i()
        if n == -1:
            hi, lo = self.i(), self.i()
            n = (hi << 32) + lo
        return n

    def charsxp_body(self):
        n = self.i()
        return None if n == -1 else self.read(n).decode("utf-8", "replace")

    def item(self):
        flags = self.i()
        t = flags & 0xFF
        has_attr, has_tag = bool(flags & (1 << 9)), bool(flags & (1 << 10))
        if t == NILVALUE:
            return None
        if t in (GLOBALENV, UNBOUND, MISSINGARG, BASENS, EMPTYENV, BASEENV):
            return RObj(t)
        if t == REF:
            idx = flags >> 8
            if idx == 0:
                idx = self.i()
            return self.refs[idx - 1]
        if t in (PERSIST, NAMESPACE, PACKAGE):
            self.i()
            n = self.i()
            o = RObj(t, [self.item().value for _ in range(n)])
            self.refs.append(o)
            return o
        if t == 1:  # SYMSXP
            o = RObj(1, self.item().value)
            self.refs.append(o)
            return o
        if t == 4:  # ENVSXP
            self.i()
            o = RObj(4)
            self.refs.append(o)
            enclos, frame, hashtab, attr = self.item(), self.item(), self.item(), self.item()
            o.value = (frame, hashtab)
            return o
        if t in PAIRLIKE:
            # iterative pairlist -> RObj(type, [(tag, value), ...])
            out, first_attr = [], None
            while True:
                attr = self.item() if has_attr else None
                if first_attr is None and attr is not None:
                    first_attr = attr
                tag = self.item() if has_tag else None
                car = self.item()
                out.append((tag.value if isinstance(tag, RObj) and tag.type == 1 else tag, car))
                flags = self.i()
                nt = flags & 0xFF
                if nt == NILVALUE:
                    break
                if nt not in PAIRLIKE:
                    # cdr is not a pairlist cell: push back by reading as single item from these flags
                    out.append((None, self._item_from_flags(flags)))
                    break
                has_attr, has_tag = bool(flags & (1 << 9)), bool(flags & (1 << 10))
            return RObj(t, out, _attrs(first_attr))
        return self._item_from_flags(flags)

    def _item_from_flags(self, flags):
        t = flags & 0xFF
        has_attr = bool(flags & (1 << 9))
        if t in PAIRLIKE or t in (NILVALUE, REF, 1, 4, PERSIST, NAMESPACE, PACKAGE, GLOBALENV, EMPTYENV, BASEENV):
            # re-dispatch through item() by faking: only reached for odd dotted pairs; not expected
            raise ValueError(f"unexpected dotted cdr type {t}")
        if t == 9:
            return RObj(9, self.charsxp_body())
        if t in (10, 13):
            n = self.length()
            v = np.frombuffer(self.read(4 * n), ">i4").astype(np.int32)
        elif t == 14:
            n = self.length()
            v = np.frombuffer(self.read(8 * n), ">f8").astype(np.float64)
        elif t == 15:
            n = self.length()
            v = np.frombuffer(self.read(16 * n), ">f8").astype(np.float64)
        elif t == 24:
            n = self.length()
            v = self.read(n)
        elif t == 16:
            n = self.length()
            keep = n <= self.max_str
            v = [] if keep else None
            for _ in range(n):
                self.i()
                s = self.charsxp_body()
                if keep:
                    v.append(s)
        elif t in (19, 20):
            n = self.length()
            v = [self.item() for _ in range(n)]
        elif t == 25:  # S4SXP
            v = None
        elif t in (7, 8):
            v = self.read(self.i()).decode()
        elif t == 22:  # EXTPTR
            o = RObj(22)
            self.refs.append(o)
            self.item(); self.item()
            v = None
            if has_attr:
                o.attr = _attrs(self.item())
            return o
        elif t == 23:
            o = RObj(23)
            self.refs.append(o)
            if has_attr:
                o.attr = _attrs(self.item())
            return o
        elif t == ALTREP:
            info, state, attr = self.item(), self.item(), self.item()
            o = _altrep(info, state)
            o.attr = _attrs(attr)
            return o
        else:
            raise ValueError(f"unsupported SEXP type {t}")
        o = RObj(t, v)
        if has_attr:
            o.attr = _attrs(self.item())
        return o


def _attrs(pl):
    if pl is None:
        return {}
    return {k: v for k, v in pl.value}


def _altrep(info, state):
    cls = info.value[0][1].value
    if cls == "compact_intseq":
        n, start, step = state.value
        return RObj(13, (start + step * np.arange(int(n))).astype(np.int32))
    if cls == "compact_realseq":
        n, start, step = state.value
        return RObj(14, start + step * np.arange(int(n), dtype=float))
    if cls == "deferred_string":
        arg = state.value[0][1]
        v = arg.value
        if v is None:
            return RObj(16, None)
        if arg.type == 14:
            return RObj(16, [repr(float(x)) for x in v])
        return RObj(16, [str(int(x)) for x in v])
    if cls.startswith("wrap_"):
        return state.value[0]
    raise ValueError(f"unsupported ALTREP class {cls}")


def load_rda(path, max_str=300_000):
    f = _open(path)
    head = f.read(5)
    assert head in (b"RDX2\n", b"RDX3\n"), head
    r = _Reader(f, max_str)
    assert r.read(2) == b"X\n"
    ver = r.i(); r.i(); r.i()
    if ver == 3:
        r.read(r.i())
    top = r.item()
    return [(k, v) for k, v in top.value]


# --- QFeatures helpers -------------------------------------------------------------------------
def strs(o):
    return o.value if o is not None else None


def qf_assays(qf):
    ld = qf.attr["ExperimentList"].attr["listData"]
    return dict(zip(ld.attr["names"].value, ld.value))


def sce_matrix(sce):
    lst = sce.attr["assays"].attr["data"].attr["listData"]
    m = lst.value[0]
    dim = [int(x) for x in m.attr["dim"].value]
    return m, dim


def dataframe(df):
    """S4 DataFrame -> (rownames, {col: values}) (factors decoded, None for dropped long strings)."""
    lst = df.attr["listData"]
    names = lst.attr["names"].value if "names" in lst.attr else []
    out = {}
    for n, v in zip(names, lst.value or []):
        if v is None:
            continue
        if v.type == 13 and "levels" in v.attr:
            lv = v.attr["levels"].value
            out[n] = [lv[i - 1] if i > 0 else None for i in v.value]
        else:
            out[n] = v.value
    rn = df.attr.get("rownames")
    return (rn.value if rn is not None else None), out
