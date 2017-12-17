from __future__ import print_function, division, absolute_import

from ctypes import (
    cdll, POINTER, c_char, c_char_p, c_size_t, c_int, byref,
)
from ctypes.util import find_library

from io import open
import sys
import os

from ttfautohint import memory
from ttfautohint.info import InfoData, info_callback
from ttfautohint.options import validate_options, format_varargs


__version__ = "0.1.0.dev0"

__all__ = ["ttfautohint", "TAError"]


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

    def ttfautohint(self, **kwargs):
        options = validate_options(kwargs)

        no_info = options.pop("no_info")
        detailed_info = options.pop("detailed_info")
        if no_info:
            info_data = InfoData()
        else:
            info_data = InfoData(self.version_string, detailed_info, **options)

        # pop 'out_file' from options dict since we use 'out_buffer'
        out_file = options.pop('out_file')

        out_buffer_p = POINTER(c_char)()
        out_buffer_len = c_size_t(0)
        error_string = c_char_p()

        option_keys, option_values = format_varargs(
            out_buffer=byref(out_buffer_p),
            out_buffer_len=byref(out_buffer_len),
            error_string=byref(error_string),
            alloc_func=memory.alloc_callback,
            free_func=memory.free_callback,
            info_callback=info_callback,
            info_callback_data=byref(info_data),
            **options
        )

        rv = self.lib.TTF_autohint(option_keys, *option_values)
        if rv:
            raise TAError(rv, error_string)

        assert out_buffer_len.value

        data = out_buffer_p[:out_buffer_len.value]
        assert len(data) == out_buffer_len.value

        if out_buffer_p:
            memory.free(out_buffer_p)
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


class TAError(Exception):

    def __init__(self, rv, error_string):
        self.rv = rv
        self.error_string = error_string.value or b""

    def __str__(self):
        return "%d: %s" % (self.rv, self.error_string.decode('utf-8'))


ttfautohint = libttfautohint.ttfautohint
