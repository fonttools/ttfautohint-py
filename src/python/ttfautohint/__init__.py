from ctypes import (
    cdll, POINTER, c_void_p, c_char, c_char_p, c_size_t, c_ulonglong,
    byref)

from io import BytesIO
import sys


# TODO: load embedded libttfautohint DLL using relative path
if sys.platform == "win32":
    libttfautohint = cdll.LoadLibrary("ttfautohint.dll")
    libc = cdll.msvcrt
elif sys.platform == "darwin":
    libttfautohint = cdll.LoadLibrary("libttfautohint.dylib")
    libc = cdll.LoadLibrary("libc.dylib")
else:
    libttfautohint = cdll.LoadLibrary("libttfautohint.so")
    libc = cdll.LoadLibrary("libc.so.6")

libc.free.argtypes = [c_void_p]
libc.free.restype = None

OPTIONS = dict(
    in_file=None,
    in_buffer=None,
    out_file=None,
    out_buffer=None,
    control_file=None,
    control_buffer=None,
    reference_file=None,
    reference_buffer=None,
    reference_index=0,
    reference_name=None,
    hinting_range_min=8,
    hinting_range_max=50,
    hinting_limit=200,
    hint_composites=False,
    adjust_subglyphs=False,
    gray_strong_stem_width=False,
    gdi_cleartype_strong_stem_width=True,
    dw_cleartype_strong_stem_width=False,
    increase_x_height=14,
    x_height_snapping_exceptions="",
    windows_compatibility=False,
    default_script="latn",
    fallback_script="none",
    fallback_scaling=False,
    symbol=False,
    fallback_stem_width=0,
    ignore_restrictions=False,
    TTFA_info=False,
    dehint=False,
    epoch=None,
    debug=False,
)


class TAError(Exception):

    def __init__(self, rv, error_string):
        self.rv = rv
        self.error_string = error_string

    def __str__(self):
        return "%d: %s" % (self.rv, self.error_string.value.decode('ascii'))


def tobytes(s, encoding='ascii', errors='strict'):
    if not isinstance(s, bytes):
        return s.encode(encoding, errors)
    else:
        return s


def _validate_options(kwargs):
    opts = {k: kwargs.pop(k, OPTIONS[k]) for k in OPTIONS}
    if kwargs:
        raise TypeError(
            "unknown keyword argument%s: %s" % (
                "s" if len(kwargs) > 1 else "",
                ", ".join(repr(k) for k in kwargs)))

    in_file, in_buffer = opts["in_file"], opts["in_buffer"]
    if in_file is None and in_buffer is None:
        raise ValueError("No input file or buffer provided")
    elif in_file is not None and in_buffer is not None:
        raise ValueError("in_file and in_buffer are mutually exclusive")

    out_file, out_buffer = opts["out_file"], opts["out_buffer"]
    if out_file is None and out_buffer is None:
        raise ValueError("No output file or buffer provided")
    elif out_file is not None and out_buffer is not None:
        raise ValueError("out_file and out_buffer are mutually exclusive")

    if (opts["control_file"] is not None
            and opts["control_buffer"] is not None):
        raise ValueError(
            "control_file and control_buffer are mutually exclusive")

    if (opts["reference_file"] is not None
            and opts["reference_buffer"] is not None):
        raise ValueError(
            "reference_file and reference_buffer are mutually exclusive")

    return opts


def _format_varargs(**kwargs):
    items = sorted((k, v) for k, v in kwargs.items() if v is not None)
    format_string = b", ".join(tobytes(k.replace("_", "-"))
                               for k, v in items)
    values = tuple(v for k, v in items)
    return format_string, values


def ttfautohint(**kwargs):
    options = _validate_options(kwargs)

    in_file, in_buffer = options.pop('in_file'), options.pop('in_buffer')
    if in_file is not None:
        if hasattr(in_file, 'read'):
            in_buffer = bytes(in_file.read())
        else:
            with open(in_file, "rb") as f:
                in_buffer = f.read()
    else:
        in_buffer = bytes(in_buffer)
    in_buffer_len = len(in_buffer)

    out_file, out_buffer = options.pop('out_file'), options.pop('out_buffer')

    control_file = options.pop('control_file')
    control_buffer = options.pop('control_buffer')
    if control_file is not None:
        control_buffer = control_file.read()
    elif control_buffer is not None:
        control_buffer = bytes(control_buffer)

    reference_file = options.pop('reference_file')
    reference_buffer = options.pop('reference_buffer')
    if reference_file is not None:
        reference_buffer = reference_file.read()
    elif reference_buffer is not None:
        reference_buffer = bytes(reference_buffer)

    out_buffer_p = POINTER(c_char)()
    out_buffer_len = c_size_t(0)
    error_string = c_char_p()

    default_script = tobytes(options.pop('default_script'))
    fallback_script = tobytes(options.pop('fallback_script'))

    reference_name = options.pop('reference_name')
    if reference_name is not None:
        reference_name = tobytes(reference_name)

    epoch = options.pop('epoch')
    if epoch is not None:
        epoch = c_ulonglong(epoch)

    option_keys, option_values = _format_varargs(
        in_buffer=in_buffer,
        in_buffer_len=in_buffer_len,
        out_buffer=byref(out_buffer_p),
        out_buffer_len=byref(out_buffer_len),
        control_buffer=control_buffer,
        reference_buffer=reference_buffer,
        reference_name=reference_name,
        epoch=epoch,
        error_string=byref(error_string),
        **options
    )

    rv = libttfautohint.TTF_autohint(option_keys, *option_values)
    if rv:
        raise TAError(rv, error_string)

    assert out_buffer_len.value

    data = out_buffer_p[:out_buffer_len.value]
    assert len(data) == out_buffer_len.value

    libc.free(out_buffer_p)

    if out_file is not None:
        if hasattr(out_file, 'write'):
            out_file.write(data)
        else:
            with open(out_file, 'wb') as f:
                f.write(data)
    else:
        out_buffer.extend(data)
