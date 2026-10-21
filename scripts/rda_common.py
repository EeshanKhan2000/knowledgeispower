import rdata
def deref(o):
    while o is not None and o.info.type.name == "REF":
        o = o.referenced_object
    return o
def sym(o):
    o = deref(o)
    if o is None: return None
    if o.info.type.name == "SYM":
        c = deref(o.value)
        return c.value.decode() if isinstance(c.value, bytes) else str(c.value)
    if o.info.type.name == "CHAR":
        return o.value.decode()
    return f"<{o.info.type.name}>"
def pairlist(o):
    out = []
    o = deref(o)
    while o is not None and o.info.type.name in ("LIST", "ATTRLIST", "LISTSXP") :
        out.append((sym(o.tag) if o.tag is not None else None, o.value[0]))
        o = deref(o.value[1])
    return out
def attrs(o):
    o = deref(o)
    return dict(pairlist(o.attributes)) if o is not None and o.attributes is not None else {}
def strvec(o):
    o = deref(o)
    return [None if x is None or x.value is None else x.value.decode() for x in o.value]
def cls(o):
    c = attrs(o).get("class")
    return strvec(c) if c is not None and deref(c).info.type.name == "STR" else []
