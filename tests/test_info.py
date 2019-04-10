import os
from contextlib import contextmanager

from ctypes import (
    c_ushort, c_ubyte, POINTER, cast,
)

from ttfautohint._compat import iterbytes
from ttfautohint import memory, StemWidthMode
from ttfautohint.info import (
    MutableByteString, InfoData, info_name_id_5, build_info_string,
    name_string_is_wide, INFO_PREFIX, insert_suffix
)

import pytest


@contextmanager
def create_ubyte_buffer(init):
    size = c_ushort(len(init))

    void_p = memory.malloc(size.value)
    if not void_p:  # pragma: no cover
        raise MemoryError()
    p = cast(void_p, POINTER(c_ubyte))

    for i, b in enumerate(iterbytes(init)):
        p[i] = b

    string_p = POINTER(POINTER(c_ubyte))(p)
    size_p = POINTER(c_ushort)(size)

    yield MutableByteString(string_p, size_p)

    memory.free(p)


@pytest.mark.parametrize(
    "input_string",
    [b"hello world", b""],
    ids=["non-empty", "empty"]
)
class TestMutableByteString(object):

    def test_tobytes(self, input_string):
        with create_ubyte_buffer(input_string) as buf:
            string = buf.tobytes()
            assert isinstance(string, bytes)
            assert string == input_string
            assert len(string) == len(buf)

    def test_frombytes(self, input_string):
        with create_ubyte_buffer(input_string) as buf:
            string = buf.tobytes()
            suffix = b" abc"
            new_string = string + suffix

            buf.frombytes(string + suffix)

            assert buf.tobytes().endswith(suffix)
            assert len(buf) == (len(new_string))


TEST_VERSION = u"1.7"
TEST_INFO = INFO_PREFIX + u" (v%s)" % TEST_VERSION
TEST_INFO_DETAILED = TEST_INFO + (
    u' -l 8 -r 50 -G 200 -x 14 -D latn -f none -w G -X ""')


@pytest.mark.parametrize(
    "detailed_info",
    [True, False],
    ids=["detailed", "no_detailed"]
)
@pytest.mark.parametrize(
    "font_version, previous_info, appendix",
    [
        ("Version 1.000", "", ""),
        ("Version 1.000", "; ttfautohint (v1.5)", ""),
        ("Version 1.000", "; ttfautohint (v1.5)", "; foo bar"),
    ],
    ids=[
        "no-previous-info",
        "previous-info-last",
        "previous-info-not-last",
    ]
)
@pytest.mark.parametrize(
    "plat_id, enc_id",
    [(1, 0), (3, 1), (3, 10)],
)
def test_info_name_id_5(plat_id, enc_id, detailed_info, font_version,
                        previous_info, appendix):
    info_string = TEST_INFO_DETAILED if detailed_info else TEST_INFO
    info_data = InfoData(info_string)
    initial_string = font_version + previous_info + appendix
    encoding = "utf-16be" if name_string_is_wide(plat_id, enc_id) else "ascii"

    with create_ubyte_buffer(initial_string.encode(encoding)) as buf:
        info_name_id_5(plat_id, enc_id, buf, info_data)
        new_string = buf.tobytes().decode(encoding)

    assert new_string == (font_version + info_string + appendix)


def test_info_name_id_5_overflow():
    # we don't modify the string if it would overflow max length
    size = MutableByteString.max_length - len(TEST_INFO) + 1
    string = b"\0" * size
    with create_ubyte_buffer(string) as buf:
        info_name_id_5(1, 0, buf, InfoData(TEST_INFO))

        assert buf.tobytes() == string


def test_build_info_string_no_detail():
    s = build_info_string(TEST_VERSION, detailed_info=False)
    assert s == TEST_INFO


@pytest.mark.parametrize(
    "options, expected",
    [
        ({}, ' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -X ""'),
        ({"dehint": True}, " -d"),
        ({"fallback_stem_width": 200}, (
            ' -l 8 -r 50 -G 200 -x 14 -H 200 -D latn -f none -a qsq -X ""')),
        ({"control_name": os.path.join("src", "my_control_file.txt")},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none'
          ' -m "my_control_file.txt" -a qsq -X ""')),
        ({"reference_name": os.path.join("build", "MyFont-Regular.ttf"),
          "reference_index": 1},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none'
          ' -R "MyFont-Regular.ttf" -Z 1 -a qsq -X ""')),
        ({"gray_stem_width_mode": StemWidthMode.NATURAL},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a nsq -X ""')),
        ({"gray_stem_width_mode": StemWidthMode.STRONG},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a ssq -X ""')),
        ({"gdi_cleartype_stem_width_mode": StemWidthMode.NATURAL},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qnq -X ""')),
        ({"gdi_cleartype_stem_width_mode": StemWidthMode.QUANTIZED},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qqq -X ""')),
        ({"dw_cleartype_stem_width_mode": StemWidthMode.NATURAL},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsn -X ""')),
        ({"dw_cleartype_stem_width_mode": StemWidthMode.STRONG},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qss -X ""')),
        ({"windows_compatibility": True},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -W -X ""')),
        ({"adjust_subglyphs": True},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -p -X ""')),
        ({"hint_composites": True},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -c -X ""')),
        ({"symbol": True},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -s -X ""')),
        ({"fallback_scaling": True},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -S -X ""')),
        ({"TTFA_info": True},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -t -X ""')),
        ({"x_height_snapping_exceptions": "6,13-17"},
         (' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -X "6,13-17"')),
    ],
    ids=[
        "default",
        "dehint",
        "fallback_stem_width",
        "control_name",
        "reference_name_and_index",
        "gray_stem_width_mode_NATURAL",
        "gray_stem_width_mode_STRONG",
        "gdi_cleartype_stem_width_mode_NATURAL",
        "gdi_cleartype_stem_width_mode_QUANTIZED",
        "dw_cleartype_stem_width_mode_NATURAL",
        "dw_cleartype_stem_width_mode_STRONG",
        "windows_compatibility",
        "adjust_subglyphs",
        "hint_composites",
        "symbol",
        "fallback_scaling",
        "TTFA_info",
        "x_height_snapping_exceptions",
    ]
)
def test_build_info_string_detailed(options, expected):
    s = build_info_string(TEST_VERSION, detailed_info=True, **options)
    assert s == TEST_INFO + expected


@pytest.mark.parametrize(
    "suffix, family_name, string, expected",
    [
        (b" Hinted", b"New Font", b"New Font", b"New Font Hinted"),
        (b" Hinted", b"New Font", b"New Font Condensed",
         b"New Font Hinted Condensed"),
        (b" Hinted", b"New Font", b"FooBar",
         b"FooBar Hinted"),
    ],
    ids=[
        "is-substring",
        "insert-after-substring",
        "no-substring",
    ]
)
def test_insert_suffix(suffix, family_name, string, expected):
    with create_ubyte_buffer(string) as buf:
        insert_suffix(suffix, family_name, buf)
        new_string = buf.tobytes()

    assert suffix in new_string
    assert new_string == expected


def test_insert_suffix_overflows():
    s = b"\0" * 0xFFFE
    with create_ubyte_buffer(s) as buf:
        insert_suffix(b"-H", b"Foo Bar", buf)
        new_string = buf.tobytes()

    assert new_string == s
