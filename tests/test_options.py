import sys
from io import StringIO, BytesIO
import argparse
import os
import logging
import pytest

from ctypes import c_ulonglong

from ttfautohint._compat import ensure_binary, text_type
from ttfautohint.options import (
    validate_options, format_varargs, strong_stem_width,
    stdin_or_input_path_type, stdout_or_output_path_type, parse_args,
    stem_width_mode, StemWidthMode, _windows_cmdline2list
)


class TestValidateOptions(object):

    def test_no_input(self):
        with pytest.raises(ValueError, match="No input file"):
            validate_options({})

    def test_unknown_keyword(self):
        kwargs = dict(foo="bar")
        with pytest.raises(TypeError, match="unknown keyword argument: 'foo'"):
            validate_options(kwargs)

        # 's' for plural
        kwargs = dict(foo="bar", baz=False)
        with pytest.raises(TypeError,
                           match="unknown keyword arguments: 'foo', 'baz'"):
            validate_options(kwargs)

    def test_no_info_or_detailed_info(self, tmpdir):
        msg = "no_info and detailed_info are mutually exclusive"
        kwargs = dict(no_info=True, detailed_info=True)
        with pytest.raises(ValueError, match=msg):
            validate_options(kwargs)

    def test_in_file_or_in_buffer(self, tmpdir):
        msg = "in_file and in_buffer are mutually exclusive"
        in_file = (tmpdir / "file1.ttf").ensure()
        kwargs = dict(in_file=str(in_file), in_buffer=b"\x00\x01\x00\x00")
        with pytest.raises(ValueError, match=msg):
            validate_options(kwargs)

    def test_control_file_or_control_buffer(self, tmpdir):
        msg = "control_file and control_buffer are mutually exclusive"
        control_file = (tmpdir / "ta_ctrl.txt").ensure()
        kwargs = dict(in_buffer=b"\0\1\0\0",
                      control_file=control_file,
                      control_buffer=b"abcd")
        with pytest.raises(ValueError, match=msg):
            validate_options(kwargs)

    def test_reference_file_or_reference_buffer(self, tmpdir):
        msg = "reference_file and reference_buffer are mutually exclusive"
        reference_file = (tmpdir / "ref.ttf").ensure()
        kwargs = dict(in_buffer=b"\0\1\0\0",
                      reference_file=reference_file,
                      reference_buffer=b"\x00\x01\x00\x00")
        with pytest.raises(ValueError, match=msg):
            validate_options(kwargs)

    def test_in_file_to_in_buffer(self, tmpdir):
        in_file = tmpdir / "file1.ttf"
        data = b"\0\1\0\0"
        in_file.write_binary(data)

        # 'in_file' is a file-like object
        options = validate_options({'in_file': in_file.open(mode="rb")})
        assert options["in_buffer"] == data
        assert "in_file" not in options
        assert options["in_buffer_len"] == len(data)

        # 'in_file' is a path string
        options = validate_options({"in_file": str(in_file)})
        assert options["in_buffer"] == data
        assert "in_file" not in options
        assert options["in_buffer_len"] == len(data)

    def test_in_buffer_is_bytes(self, tmpdir):
        with pytest.raises(TypeError, match="in_buffer type must be bytes"):
            validate_options({"in_buffer": u"abcd"})

    def test_control_file_to_control_buffer(self, tmpdir):
        control_file = tmpdir / "ta_ctrl.txt"
        data = u"abcd"
        control_file.write_text(data, encoding="utf-8")

        # 'control_file' is a file object opened in text mode
        with control_file.open(mode="rt", encoding="utf-8") as f:
            kwargs = {'in_buffer': b"\0", 'control_file': f}
            options = validate_options(kwargs)
        assert options["control_buffer"] == data.encode("utf-8")
        assert "control_file" not in options
        assert options["control_buffer_len"] == len(data)
        assert options["control_name"] == str(control_file)

        # 'control_file' is a path string
        kwargs = {'in_buffer': b"\0", 'control_file': str(control_file)}
        options = validate_options(kwargs)
        assert options["control_buffer"] == data.encode("utf-8")
        assert "control_file" not in options
        assert options["control_buffer_len"] == len(data)
        assert options["control_name"] == str(control_file)

        # 'control_file' is a file-like stream
        kwargs = {'in_buffer': b"\0", 'control_file': StringIO(data)}
        options = validate_options(kwargs)
        assert options["control_buffer"] == data.encode("utf-8")
        assert "control_file" not in options
        assert options["control_buffer_len"] == len(data)
        # the stream doesn't have a 'name' attribute; using fallback
        assert options["control_name"] == u"<control-instructions>"

    def test_control_buffer_name(self, tmpdir):
        kwargs = {"in_buffer": b"\0", "control_buffer": b"abcd"}
        options = validate_options(kwargs)
        assert options["control_name"] == u"<control-instructions>"

    def test_reference_file_to_reference_buffer(self, tmpdir):
        reference_file = tmpdir / "font.ttf"
        data = b"\0\1\0\0"
        reference_file.write_binary(data)
        encoded_filename = ensure_binary(
            str(reference_file), encoding=sys.getfilesystemencoding())

        # 'reference_file' is a file object opened in binary mode
        with reference_file.open(mode="rb") as f:
            kwargs = {'in_buffer': b"\0", 'reference_file': f}
            options = validate_options(kwargs)
        assert options["reference_buffer"] == data
        assert "reference_file" not in options
        assert options["reference_buffer_len"] == len(data)
        assert options["reference_name"] == encoded_filename

        # 'reference_file' is a path string
        kwargs = {'in_buffer': b"\0", 'reference_file': str(reference_file)}
        options = validate_options(kwargs)
        assert options["reference_buffer"] == data
        assert "reference_file" not in options
        assert options["reference_buffer_len"] == len(data)
        assert options["reference_name"] == encoded_filename

        # 'reference_file' is a file-like stream
        kwargs = {'in_buffer': b"\0", 'reference_file': BytesIO(data)}
        options = validate_options(kwargs)
        assert options["reference_buffer"] == data
        assert "reference_file" not in options
        assert options["reference_buffer_len"] == len(data)
        # the stream doesn't have a 'name' attribute, no reference_name
        assert options["reference_name"] is None

    def test_custom_reference_name(self, tmpdir):
        reference_file = tmpdir / "font.ttf"
        data = b"\0\1\0\0"
        reference_file.write_binary(data)
        expected = u"Some Font".encode(sys.getfilesystemencoding())

        with reference_file.open(mode="rb") as f:
            kwargs = {'in_buffer': b"\0",
                      'reference_file': f,
                      'reference_name': u"Some Font"}
            options = validate_options(kwargs)

        assert options["reference_name"] == expected

        kwargs = {'in_buffer': b"\0",
                  'reference_file': str(reference_file),
                  'reference_name': u"Some Font"}
        options = validate_options(kwargs)

        assert options["reference_name"] == expected

    def test_reference_buffer_is_bytes(self, tmpdir):
        with pytest.raises(TypeError,
                           match="reference_buffer type must be bytes"):
            validate_options({"in_buffer": b"\0", "reference_buffer": u""})

    def test_epoch(self):
        options = validate_options({"in_buffer": b"\0", "epoch": 0})
        assert isinstance(options["epoch"], c_ulonglong)
        assert options["epoch"].value == 0

    def test_family_suffix(self):
        options = validate_options({"in_buffer": b"\0",
                                    "family_suffix": b"-TA"})
        assert isinstance(options["family_suffix"], text_type)
        assert options["family_suffix"] == u"-TA"


@pytest.mark.parametrize(
    "options, expected",
    [
        (
            {},
            (b"", ())
        ),
        (
            {
                "in_buffer": b"\0\1\0\0",
                "in_buffer_len": 4,
                "out_buffer": None,
                "out_buffer_len": None,
                "error_string": None,
                "alloc_func": None,
                "free_func": None,
                "info_callback": None,
                "info_post_callback": None,
                "progress_callback": None,
                "progress_callback_data": None,
                "error_callback": None,
                "error_callback_data": None,
                "control_buffer": b"abcd",
                "control_buffer_len": 4,
                "reference_buffer": b"\0\1\0\0",
                "reference_buffer_len": 4,
                "reference_index": 1,
                "reference_name": b"/path/to/font.ttf",
                "hinting_range_min": 8,
                "hinting_range_max": 50,
                "hinting_limit": 200,
                "hint_composites": False,
                "adjust_subglyphs": False,
                "increase_x_height": 14,
                "x_height_snapping_exceptions": b"6,15-18",
                "windows_compatibility": True,
                "default_script": b"grek",
                "fallback_script": b"latn",
                "fallback_scaling": False,
                "symbol": True,
                "fallback_stem_width": 100,
                "ignore_restrictions": True,
                "family_suffix": b"-Hinted",
                "detailed_info": True,
                "no_info": False,
                "TTFA_info": True,
                "dehint": False,
                "epoch": 1513955869,
                "debug": False,
                "verbose": True,
            },
            ((b"TTFA-info, adjust-subglyphs, control-buffer, "
              b"control-buffer-len, debug, default-script, dehint, "
              b"detailed-info, epoch, fallback-scaling, fallback-script, "
              b"fallback-stem-width, family-suffix, hint-composites, "
              b"hinting-limit, hinting-range-max, hinting-range-min, "
              b"ignore-restrictions, in-buffer, in-buffer-len, "
              b"increase-x-height, no-info, reference-buffer, "
              b"reference-buffer-len, reference-index, reference-name, "
              b"symbol, verbose, windows-compatibility, "
              b"x-height-snapping-exceptions"),
             (True, False, b'abcd',
              4, False, b'grek', False,
              True, 1513955869, False, b'latn',
              100, b'-Hinted', False,
              200, 50, 8,
              True, b'\x00\x01\x00\x00', 4,
              14, False, b'\x00\x01\x00\x00',
              4, 1, b'/path/to/font.ttf',
              True, True, True,
              b'6,15-18'))
        ),
        (
            {"unkown_option": 1},
            (b"", ())
        )
    ],
    ids=[
        "empty",
        "full-options",
        "unknown-option",
    ]
)
def test_format_varargs(options, expected):
    assert format_varargs(**options) == expected


@pytest.mark.parametrize(
    "string, expected",
    [
        (
            "",
            {
                "gray_stem_width_mode": StemWidthMode.QUANTIZED,
                "gdi_cleartype_stem_width_mode": StemWidthMode.QUANTIZED,
                "dw_cleartype_stem_width_mode": StemWidthMode.QUANTIZED
            }
        ),
        (
            "g",
            {
                "gray_stem_width_mode": StemWidthMode.STRONG,
                "gdi_cleartype_stem_width_mode": StemWidthMode.QUANTIZED,
                "dw_cleartype_stem_width_mode": StemWidthMode.QUANTIZED
            }
        ),
        (
            "G",
            {
                "gray_stem_width_mode": StemWidthMode.QUANTIZED,
                "gdi_cleartype_stem_width_mode": StemWidthMode.STRONG,
                "dw_cleartype_stem_width_mode": StemWidthMode.QUANTIZED
            }
        ),
        (
            "D",
            {
                "gray_stem_width_mode": StemWidthMode.QUANTIZED,
                "gdi_cleartype_stem_width_mode": StemWidthMode.QUANTIZED,
                "dw_cleartype_stem_width_mode": StemWidthMode.STRONG
            }
        ),
        (
            "DGg",
            {
                "gray_stem_width_mode": StemWidthMode.STRONG,
                "gdi_cleartype_stem_width_mode": StemWidthMode.STRONG,
                "dw_cleartype_stem_width_mode": StemWidthMode.STRONG
            }
        ),
    ],
    ids=[
        "empty-string",
        "only-gray",
        "only-gdi",
        "only-dw",
        "all"
    ]
)
def test_strong_stem_width(string, expected):
    assert strong_stem_width(string) == expected


def test_strong_stem_width_invalid():
    with pytest.raises(argparse.ArgumentTypeError,
                       match="string can only contain up to 3 letters"):
        strong_stem_width("GGGG")

    with pytest.raises(argparse.ArgumentTypeError,
                       match="invalid value: 'a'"):
        strong_stem_width("a")


@pytest.mark.parametrize(
    "string, expected",
    [
        (
            "nnn",
            {
                "gray_stem_width_mode": StemWidthMode.NATURAL,
                "gdi_cleartype_stem_width_mode": StemWidthMode.NATURAL,
                "dw_cleartype_stem_width_mode": StemWidthMode.NATURAL
            }
        ),
        (
            "qqq",
            {
                "gray_stem_width_mode": StemWidthMode.QUANTIZED,
                "gdi_cleartype_stem_width_mode": StemWidthMode.QUANTIZED,
                "dw_cleartype_stem_width_mode": StemWidthMode.QUANTIZED
            }
        ),
        (
            "sss",
            {
                "gray_stem_width_mode": StemWidthMode.STRONG,
                "gdi_cleartype_stem_width_mode": StemWidthMode.STRONG,
                "dw_cleartype_stem_width_mode": StemWidthMode.STRONG
            }
        ),
        (
            "nqs",
            {
                "gray_stem_width_mode": StemWidthMode.NATURAL,
                "gdi_cleartype_stem_width_mode": StemWidthMode.QUANTIZED,
                "dw_cleartype_stem_width_mode": StemWidthMode.STRONG
            }
        ),
    ],
    ids=["nnn", "qqq", "sss", "nqs"]
)
def test_stem_width_mode(string, expected):
    assert stem_width_mode(string) == expected


def test_stem_width_mode_invalid():
    with pytest.raises(argparse.ArgumentTypeError,
                       match="must consist of exactly three letters"):
        stem_width_mode("nnnn")

    with pytest.raises(argparse.ArgumentTypeError,
                       match="Stem width mode letter for .* must be"):
        stem_width_mode("zzz")


@pytest.fixture(
    params=[True, False],
    ids=['tty', 'pipe'],
)
def isatty(request):
    return request.param


class MockFile(object):

    def __init__(self, f, isatty):
        self._file = f
        self._isatty = isatty

    def isatty(self):
        return self._isatty

    def __getattr__(self, attr):
        return getattr(self._file, attr)


def test_stdin_input_type(monkeypatch, tmpdir, isatty):
    tmp = (tmpdir / "stdin").ensure().open("r")
    monkeypatch.setattr(sys, "stdin", MockFile(tmp, isatty))

    f = stdin_or_input_path_type("-")

    if isatty:
        assert f is None
    else:
        assert hasattr(f, "read")
        assert f.mode == "rb"
        assert f.closed is False


def test_path_input_type(tmpdir):
    tmp = tmpdir / "font.ttf"
    s = str(tmp)
    path = stdin_or_input_path_type(s)
    assert path == s


def test_stdout_output_type(monkeypatch, tmpdir, isatty):
    tmp = (tmpdir / "stdout").open("w")
    monkeypatch.setattr(sys, "stdout", MockFile(tmp, isatty))

    f = stdout_or_output_path_type("-")

    if isatty:
        assert f is None
    else:
        assert hasattr(f, "write")
        assert f.mode == "wb"
        assert f.closed is False


def test_path_output_type(tmpdir):
    tmp = tmpdir / "font.ttf"
    s = str(tmp)
    path = stdout_or_output_path_type(s)
    assert path == s


class TestParseArgs(object):

    argv0 = "python -m ttfautohint"

    def test_unrecognized_arguments(self, monkeypatch, capsys):
        monkeypatch.setattr(argparse._sys, "argv", [self.argv0, "--foo"])

        with pytest.raises(SystemExit) as exc_info:
            parse_args()

        assert str(exc_info.value) == "2"
        assert "unrecognized arguments: --foo" in capsys.readouterr()[1]

        monkeypatch.undo()

        assert parse_args("--bar") is None
        assert "unrecognized arguments: --bar" in capsys.readouterr()[1]

        assert parse_args(["--baz"]) is None
        assert "unrecognized arguments: --baz" in capsys.readouterr()[1]

    def test_no_in_file(self, monkeypatch, capsys):
        monkeypatch.setattr(argparse._sys, "argv", [self.argv0])

        with pytest.raises(SystemExit) as exc_info:
            parse_args()

        assert str(exc_info.value) == "1"

        out, err = capsys.readouterr()
        assert "usage: ttfautohint" in out
        assert not err

    def test_no_out_file(self, monkeypatch, capsys):
        monkeypatch.setattr(argparse._sys, "argv", [self.argv0, "font.ttf"])

        with pytest.raises(SystemExit) as exc_info:
            parse_args()

        assert str(exc_info.value) == "1"

        out, err = capsys.readouterr()
        assert "usage: ttfautohint" in out
        assert not err

    def test_source_date_epoch(self, monkeypatch):
        epoch = "1513966552"
        env = dict(os.environ)
        env["SOURCE_DATE_EPOCH"] = epoch
        monkeypatch.setattr(os, "environ", env)

        options = parse_args([])

        assert options["epoch"] == int(epoch)

    def test_source_date_epoch_invalid(self, monkeypatch):
        invalid_epoch = "foobar"
        env = dict(os.environ)
        env["SOURCE_DATE_EPOCH"] = invalid_epoch
        monkeypatch.setattr(os, "environ", env)

        with pytest.warns(UserWarning,
                          match="invalid SOURCE_DATE_EPOCH: 'foobar'"):
            options = parse_args([])

        assert "epoch" not in options

    def test_show_ttfa_info_unsupported(self):
        with pytest.raises(NotImplementedError):
            parse_args("-T")

    def test_parse_args_custom_splitfunc(self):
        # https://github.com/fonttools/ttfautohint-py/issues/2
        s = '"build folder\\unhinted\\Test_Lt.ttf" "output folder\\hinted\\Test_Lt.ttf"'
        args = parse_args(s, splitfunc=_windows_cmdline2list)
        assert args["in_file"] == "build folder\\unhinted\\Test_Lt.ttf"
        assert args["out_file"] == "output folder\\hinted\\Test_Lt.ttf"

    @pytest.mark.skipif(sys.platform != "win32", reason="only for windows")
    def test_parse_args_windows_paths(self):
        # https://github.com/fonttools/ttfautohint-py/issues/2
        s = '"build folder\\unhinted\\Test_Lt.ttf" "output folder\\hinted\\Test_Lt.ttf"'
        args = parse_args(s)
        assert args["in_file"] == "build folder\\unhinted\\Test_Lt.ttf"
        assert args["out_file"] == "output folder\\hinted\\Test_Lt.ttf"
