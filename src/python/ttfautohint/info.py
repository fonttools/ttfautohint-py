from ctypes import (
    c_int, c_ushort, c_ubyte, c_void_p, c_wchar_p, POINTER, CFUNCTYPE, cast,
    Structure, memmove, py_object,
)
import sys
import os

from ._compat import ensure_text, iterbytes
from . import memory


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


INFO_PREFIX = u"; ttfautohint"


def build_info_string(version, detailed_info=True, **options):
    s = INFO_PREFIX + " (v%s)" % version

    if not detailed_info:
        return s

    if options["dehint"]:
        s += " -d"
        return s

    s += " -l %d" % options["hinting_range_min"]
    s += " -r %d" % options["hinting_range_max"]
    s += " -G %d" % options["hinting_limit"]
    s += " -x %d" % options["increase_x_height"]
    if options["fallback_stem_width"]:
        s += " -H %d" % options["fallback_stem_width"]
    s += " -D %s" % ensure_text(options["default_script"])
    s += " -f %s" % ensure_text(options["fallback_script"])

    control_name = options.pop("control_name", None)
    if control_name:
        s += ' -m "%s"' % os.path.basename(
            ensure_text(control_name, sys.getfilesystemencoding()))

    reference_name = options.get("reference_name")
    if reference_name:
        s += ' -R "%s"' % os.path.basename(
            ensure_text(reference_name, sys.getfilesystemencoding()))

    if options["reference_index"]:
        s += " -Z %d" % options["reference_index"]

    strong_stem_width = ""
    if options["gray_strong_stem_width"]:
        strong_stem_width += "g"
    if options["gdi_cleartype_strong_stem_width"]:
        strong_stem_width += "G"
    if options["dw_cleartype_strong_stem_width"]:
        strong_stem_width += "D"
    s += " -w %s" % strong_stem_width or '""'

    if options["windows_compatibility"]:
        s += " -W"
    if options["adjust_subglyphs"]:
        s += " -p"
    if options["hint_composites"]:
        s += " -c"
    if options["symbol"]:
        s += " -s"
    if options["fallback_scaling"]:
        s += " -S"
    if options["TTFA_info"]:
        s += " -t"
    x_excepts = ensure_text(options["x_height_snapping_exceptions"])
    s += ' -X "%s"' % x_excepts

    return s


class InfoData(Structure):

    _fields_ = [
        ("info_string", c_wchar_p),
        ("family_suffix", c_wchar_p),
        ("family_data", py_object),
    ]

    def __init__(self, info_string=None, family_suffix=None, family_data=None):
        if family_data is None:
            family_data = {}
        super(InfoData, self).__init__(info_string, family_suffix, family_data)


class Family(Structure):

    _fields_ = [
        ("platform_id", c_ushort),
        ("encoding_id", c_ushort),
        ("language_id", c_ushort),
        ("name_id_1_len", POINTER(c_ushort)),
        ("name_id_1_str", POINTER(POINTER(c_ubyte))),
        ("name_id_4_len", POINTER(c_ushort)),
        ("name_id_4_str", POINTER(POINTER(c_ubyte))),
        ("name_id_6_len", POINTER(c_ushort)),
        ("name_id_6_str", POINTER(POINTER(c_ubyte))),
        ("name_id_16_len", POINTER(c_ushort)),
        ("name_id_16_str", POINTER(POINTER(c_ubyte))),
        ("name_id_21_len", POINTER(c_ushort)),
        ("name_id_21_str", POINTER(POINTER(c_ubyte))),
        ("family_name", c_wchar_p)
    ]


def info_name_id_5(platform_id, encoding_id, str_len_p, string_p, data):
    str_len = str_len_p[0]
    string = bytes(bytearray(string_p[0][:str_len]))

    if (platform_id == 1 or
            (platform_id == 3 and not (
                encoding_id == 1 or encoding_id == 10))):
        # one-byte or multi-byte encodings
        encoding = "ascii"
        offset = 1
    else:
        # (two-byte) UTF-16BE for everything else
        encoding = "utf-16be"
        offset = 2

    info_string = data.info_string.encode(encoding)
    info_prefix = INFO_PREFIX.encode(encoding)
    semicolon = u";".encode(encoding)
    # if we already have an ttfautohint info string, remove it up to a
    # following `;' character (or end of string)
    start = string.find(info_prefix)
    if start != -1:
        new_string = string[:start] + info_string
        string_end = string[start+offset:]
        last_semicolon_index = string_end.rfind(semicolon)
        if last_semicolon_index != -1:
            new_string += string_end[last_semicolon_index:]
    else:
        new_string = string + info_string

    # do nothing if the string would become too long
    len_new = len(new_string)
    if len_new > 0xFFFF:
        return 0

    new_string_array = (c_ubyte * len_new)(*iterbytes(new_string))

    new_string_p = memory.realloc(string_p[0], len_new)
    if not new_string_p:
        # hm, realloc failed... nevermind
        return 1

    string_p[0] = cast(new_string_p, POINTER(c_ubyte))

    memmove(string_p[0], new_string_array, len_new)
    str_len_p[0] = len_new

    return 0


def _info_callback(platform_id, encoding_id, language_id, name_id, str_len_p,
                   string_p, info_data_p):
    # cast void pointer to a pointer to InfoData struct
    info_data_p = cast(info_data_p, POINTER(InfoData))
    data = info_data_p[0]

    # if ID is a version string, append our data
    if data.info_string and name_id == 5:
        return info_name_id_5(platform_id, encoding_id, str_len_p, string_p,
                              data)

    # if ID is related to a family name, collect the data
    # TODO
    return 0


info_callback = TA_Info_Func_Proto(_info_callback)
