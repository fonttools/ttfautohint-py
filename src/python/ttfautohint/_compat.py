import sys


PY3 = sys.version_info[0] >= 3
if PY3:
    text_type = str
    iterbytes = iter
else: # PY2
    text_type = unicode
    import itertools
    import functools
    iterbytes = functools.partial(itertools.imap, ord)


def ensure_binary(s, encoding="ascii", errors="strict"):
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    elif isinstance(s, bytes):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))


def ensure_text(s, encoding="ascii", errors="strict"):
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    elif isinstance(s, bytes):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))
