import os
from glob import glob
from io import BytesIO

from fontTools.ttLib import TTFont

from ttfautohint import ttfautohint

import pytest


DATA = os.path.join(os.path.dirname(__file__), "data")
UNHINTED_TTFS = glob(os.path.join(DATA, "*.ttf"))

GLOBAL_HINTING_TABLES = ["fpgm", "prep", "cvt ", "gasp"]


def autohint_font(ttfont, **options):
    buf = BytesIO()
    ttfont.save(buf)
    data = ttfautohint(in_buffer=buf.getvalue(), **options)
    return TTFont(BytesIO(data))


@pytest.fixture(
    params=UNHINTED_TTFS,
    ids=lambda p: os.path.basename(p)
)
def unhinted(request):
    return TTFont(request.param)


class TestTTFAutohint(object):

    def test_simple(self, unhinted):
        for tag in GLOBAL_HINTING_TABLES:
            assert tag not in unhinted
        assert not unhinted["glyf"]["a"].program
        nameID5 = unhinted["name"].getName(5, 3, 1).toUnicode()
        assert u"; ttfautohint" not in nameID5

        hinted = autohint_font(unhinted)

        for tag in GLOBAL_HINTING_TABLES:
            assert tag in hinted
        assert hinted["glyf"]["a"].program

        nameID5 = hinted["name"].getName(5, 3, 1).toUnicode()
        assert u"; ttfautohint" in nameID5

    def test_in_and_out_file_paths(self, tmpdir, unhinted):
        in_file = tmpdir / "unhinted.ttf"
        out_file = tmpdir / "hinted.ttf"

        with in_file.open("wb") as f:
            unhinted.save(f)

        n = ttfautohint(in_file=str(in_file), out_file=str(out_file))

        assert n > 0

    def test_no_info(self, unhinted):
        hinted = autohint_font(unhinted, no_info=True)

        nameID5 = hinted["name"].getName(5, 3, 1).toUnicode()
        assert u"; ttfautohint" not in nameID5

    def test_detailed_info(self, unhinted):
        hinted = autohint_font(unhinted, detailed_info=True)

        nameID5 = hinted["name"].getName(5, 3, 1).toUnicode()
        assert u"; ttfautohint" in nameID5

        assert (
            u' -l 8 -r 50 -G 200 -x 14 -D latn -f none -a qsq -X ""'
            in nameID5)

    def test_family_suffix(self, unhinted):
        suffix = " Hinted"
        hinted = autohint_font(unhinted, family_suffix=suffix)

        nametable = hinted["name"]
        nameID1 = nametable.getName(1, 3, 1).toUnicode()

        assert nameID1.endswith(suffix)
