import pytest

from ttfautohint.options import validate_options


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

        # 'control_file' is a file-like object opened in text mode
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

    def test_control_buffer_name(self, tmpdir):
        kwargs = {"in_buffer": b"\0", "control_buffer": b"abcd"}
        options = validate_options(kwargs)
        assert options["control_name"] == u"<control-instructions>"
