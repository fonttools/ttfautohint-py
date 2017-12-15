from __future__ import print_function, division, absolute_import

from ctypes import (
    cdll, POINTER, c_void_p, c_char, c_char_p, c_size_t, c_ulonglong,
    c_int, c_ushort, c_ubyte, byref, CFUNCTYPE, Structure, cast, memmove)
from ctypes.util import find_library

from io import BytesIO, open
import sys
import os


__version__ = "0.1.0.dev0"

__all__ = ["ttfautohint", "TAError"]


PY3 = sys.version_info[0] >= 3
if PY3:
    text_type = str
    iterbytes = iter
else: # PY2
    text_type = unicode
    import itertools
    import functools
    iterbytes = functools.partial(itertools.imap, ord)


def tobytes(s, encoding="ascii", errors="strict"):
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    elif isinstance(s, bytes):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))


# we load the libc to get the standard malloc and free functions.
# They will be used anyway by libttfautohint if we didn't provide the
# 'alloc-func' and 'free-func' callbacks. However, by explicitly passing
# them, we ensure that both libttfautohint and cytpes will use the same
# memory allocation functions. E.g. on Windows, a DLL may be linked
# with a different version of the C runtime library than the application
# which loads the DLL.
if sys.platform == "win32":
    libc = cdll.msvcrt
else:
    libc_path = find_library("c")
    if libc_path is None:
        raise OSError("Could not find the libc shared library")
    libc = cdll.LoadLibrary(libc_path)

libc.malloc.argtypes = [c_size_t]
libc.malloc.restype = c_void_p

libc.free.argtypes = [c_void_p]
libc.free.restype = None

libc.realloc.argtypes = [c_void_p, c_size_t]
libc.realloc.restype = c_void_p

TA_Alloc_Func_Proto = CFUNCTYPE(c_void_p, c_size_t)
alloc_func = TA_Alloc_Func_Proto(lambda size: libc.malloc(size))

TA_Free_Func_Proto = CFUNCTYPE(None, c_void_p)
free_func = TA_Free_Func_Proto(lambda p: libc.free(p))


TA_Info_Func_Proto = CFUNCTYPE(
    c_int,                      # (return value)
    c_ushort,                   # platform_id
    c_ushort,                   # encoding_id
    c_ushort,                   # language_id
    c_ushort,                   # name_id
    POINTER(c_ushort),          # str_len
    POINTER(POINTER(c_ubyte)),  # str
    c_void_p                    # info_data
)


class InfoData(Structure):

    _fields_ = [
        ("info_string", POINTER(c_ubyte)),
        ("info_string_wide", POINTER(c_ubyte)),
        ("info_string_len", c_ushort),
        ("info_string_wide_len", c_ushort),
    ]


INFO_STRING = u"; ttfautohint"


def _info_callback(platform_id, encoding_id, language_id, name_id, str_len_p,
                   string_p, info_data_p):
    # for now we only modify the version string
    if name_id != 5:
        return 0

    # cast void pointer to a pointer to InfoData struct
    info_data_p = cast(info_data_p, POINTER(InfoData))
    d = info_data_p[0]

    str_len = str_len_p[0]
    string = bytes(bytearray(string_p[0][:str_len]))

    if (platform_id == 1 or
            (platform_id == 3 and not (
                encoding_id == 1 or encoding_id == 10))):
        # one-byte or multi-byte encodings
        v_len = d.info_string_len
        v = bytes(bytearray(d.info_string[:v_len]))
        info_encoding = "ascii"
        offset = 1
    else:
        # (two-byte) UTF-16BE for everything else
        v_len = d.info_string_wide_len
        v = bytes(bytearray(d.info_string_wide[:v_len]))
        info_encoding = "utf-16be"
        offset = 2

    info_bytes = INFO_STRING.encode(info_encoding)
    semicolon = u";".encode(info_encoding)
    # if we already have an ttfautohint info string, remove it up to a
    # following `;' character (or end of string)
    start = string.find(info_bytes)
    if start != -1:
        new_string = string[:start] + v
        string_end = string[start+offset:]
        last_semicolon_index = string_end.rfind(semicolon)
        if last_semicolon_index != -1:
            new_string += string_end[last_semicolon_index:]
    else:
        new_string = string + v

    # do nothing if the string would become too long
    len_new = len(new_string)
    if len_new > 0xFFFF:
        return 0

    new_string_array = (c_ubyte * len_new)(*iterbytes(new_string))

    new_string_p = libc.realloc(string_p[0], len_new)
    if not new_string_p:
        # hm, realloc failed... nevermind
        return 1

    string_p[0] = cast(new_string_p, POINTER(c_ubyte))

    memmove(string_p[0], new_string_array, len_new)
    str_len_p[0] = len_new

    return 0


info_callback = TA_Info_Func_Proto(_info_callback)


class TALibrary(object):

    def __init__(self, path=None, **kwargs):
        """ Initialize a new handle to the libttfautohint shared library.
        If no path is provided, by default the embedded shared library that
        comes with the binary wheel is loaded first. If this is not found,
        then `ctypes.util.find_library` function is used to search in the
        system's default search paths.
        """
        if path is None:
            if sys.platform == "win32":
                name = "libttfautohint.dll"
            elif sys.platform == "darwin":
                name = "libttfautohint.dylib"
            else:
                name = "libttfautohint.so"
            path = os.path.join(os.path.dirname(__file__), name)
            if not os.path.isfile(path):
                path = find_library("ttfautohint")
                if not path:
                    raise OSError("cannot find '%s'" % name)
        self.lib = lib = cdll.LoadLibrary(path, **kwargs)
        self.path = path

        lib.TTF_autohint_version.argtypes = [POINTER(c_int)] * 3
        lib.TTF_autohint_version.restype = None
        _major, _minor, _revision = c_int(), c_int(), c_int()
        lib.TTF_autohint_version(_major, _minor, _revision)
        self.major = _major.value
        self.minor = _minor.value
        self.revision = _revision.value

        lib.TTF_autohint_version_string.restype = c_char_p
        version_string = lib.TTF_autohint_version_string().decode('ascii')
        self.version_string = version_string

        info_string = INFO_STRING + u" (v%s)" % version_string
        s = info_string.encode('ascii')
        s_len = len(s)
        ws = info_string.encode('utf-16be')
        ws_len = len(ws)
        s_array = (c_ubyte * s_len)(*(iterbytes(s)))
        ws_array = (c_ubyte * ws_len)(*(iterbytes(ws)))
        self.info_data = InfoData(s_array, ws_array, s_len, ws_len)

    def ttfautohint(self, **kwargs):
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
            alloc_func=alloc_func,
            free_func=free_func,
            info_callback=info_callback,
            info_callback_data=byref(self.info_data),
            **options
        )

        rv = self.lib.TTF_autohint(option_keys, *option_values)
        if rv:
            raise TAError(rv, error_string)

        assert out_buffer_len.value

        data = out_buffer_p[:out_buffer_len.value]
        assert len(data) == out_buffer_len.value

        if out_buffer_p:
            free_func(out_buffer_p)
            out_buffer_p = None

        if out_file is not None:
            try:
                return out_file.write(data)
            except AttributeError:
                with open(out_file, 'wb') as f:
                    return f.write(data)
        else:
            return data


libttfautohint = TALibrary()


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


ttfautohint = libttfautohint.ttfautohint
