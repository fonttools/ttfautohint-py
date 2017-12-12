from __future__ import print_function, division, absolute_import

from ctypes import (
    cdll, POINTER, c_void_p, c_char, c_char_p, c_size_t, c_ulonglong,
    byref)

from io import BytesIO, open
import sys
import os


__all__ = ["ttfautohint", "TAError"]


try:  # PY2
    text_type = unicode
except NameError:  # PY3
    text_type = str


def tobytes(s, encoding="ascii", errors="strict"):
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    elif isinstance(s, bytes):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))


if sys.platform == "win32":
    libttfautohint_name = "libttfautohint.dll"
    libc = cdll.msvcrt
else:
    from ctypes.util import find_library
    libc_path = find_library("c")
    if libc_path is None:
        raise OSError("Could not find the libc shared library")
    libc = cdll.LoadLibrary(libc_path)
    if sys.platform == "darwin":
        libttfautohint_name = "libttfautohint.dylib"
    else:
        libttfautohint_name = "libttfautohint.so"

libttfautohint_path = os.path.join(os.path.dirname(__file__),
                                   libttfautohint_name)
libttfautohint = cdll.LoadLibrary(libttfautohint_path)

libc.free.argtypes = [c_void_p]
libc.free.restype = None

OPTIONS = dict(
    in_file=None,
    in_buffer=None,
    out_file=None,
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


def _validate_options(kwargs):
    opts = {k: kwargs.pop(k, OPTIONS[k]) for k in OPTIONS}
    if kwargs:
        raise TypeError(
            "unknown keyword argument%s: %s" % (
                "s" if len(kwargs) > 1 else "",
                ", ".join(repr(k) for k in kwargs)))

    in_file, in_buffer = opts.pop("in_file"), opts.pop("in_buffer")
    if in_file is None and in_buffer is None:
        raise ValueError("No input file or buffer provided")
    elif in_file is not None and in_buffer is not None:
        raise ValueError("in_file and in_buffer are mutually exclusive")
    if in_file is not None:
        try:
            in_buffer = in_file.read()
        except AttributeError:
            with open(in_file, "rb") as f:
                in_buffer = f.read()
    if not isinstance(in_buffer, bytes):
        raise TypeError("in_buffer type must be bytes, not %s"
                        % type(in_buffer).__name__)
    opts['in_buffer'] = in_buffer
    opts['in_buffer_len'] = len(in_buffer)

    control_file = opts.pop('control_file')
    control_buffer = opts.pop('control_buffer')
    if control_file is not None:
        if control_buffer is not None:
            raise ValueError(
                "control_file and control_buffer are mutually exclusive")
        try:
            control_buffer = control_file.read()
        except AttributeError:
            with open(control_file, "rb") as f:
                control_buffer = f.read()
    if control_buffer is not None:
        if not isinstance(control_buffer, bytes):
            raise TypeError("control_buffer type must be bytes, not %s"
                            % type(control_buffer).__name__)
        opts['control_buffer'] = control_buffer
        opts['control_buffer_len'] = len(control_buffer)

    reference_file = opts.pop('reference_file')
    reference_buffer = opts.pop('reference_buffer')
    if reference_file is not None:
        if reference_buffer is not None:
            raise ValueError(
                "reference_file and reference_buffer are mutually exclusive")
        try:
            reference_buffer = reference_file.read()
        except AttributeError:
            with open(reference_file, "rb") as f:
                reference_buffer = f.read()
    if reference_buffer is not None:
        if not isinstance(reference_buffer, bytes):
            raise TypeError("reference_buffer type must be bytes, not %s"
                            % type(reference_buffer).__name__)
        opts['reference_buffer'] = reference_buffer
        opts['reference_buffer_len'] = len(reference_buffer)

    for key in ('reference_name', 'default_script', 'fallback_script',
                'x_height_snapping_exceptions'):
        if opts[key] is not None:
            opts[key] = tobytes(opts[key])

    if opts['epoch'] is not None:
        opts['epoch'] = c_ulonglong(epoc)

    return opts


def _format_varargs(**kwargs):
    items = sorted((k, v) for k, v in kwargs.items() if v is not None)
    format_string = b", ".join(tobytes(k.replace("_", "-"))
                               for k, v in items)
    values = tuple(v for k, v in items)
    return format_string, values


def ttfautohint(**kwargs):
    options = _validate_options(kwargs)

    # pop 'out_file' from options dict since we use 'out_buffer'
    out_file = options.pop('out_file')

    out_buffer_p = POINTER(c_char)()
    out_buffer_len = c_size_t(0)
    error_string = c_char_p()

    option_keys, option_values = _format_varargs(
        out_buffer=byref(out_buffer_p),
        out_buffer_len=byref(out_buffer_len),
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
        try:
            return out_file.write(data)
        except AttributeError:
            with open(out_file, 'wb') as f:
                return f.write(data)
    else:
        return data
