![CI Status](https://github.com/fonttools/ttfautohint-py/actions/workflows/ci.yml/badge.svg?branch=main)
# ttfautohint-py

`ttfautohint-py` is a Python wrapper for [ttfautohint](https://freetype.org/ttfautohint/), a free auto-hinter for TrueType fonts created by Werner Lemberg ([@lemzwerg](https://github.com/lemzwerg)).

As of v0.6, it runs the `ttfautohint` executable as a subprocess. Previous versions used [ctypes](https://docs.python.org/3/library/ctypes.html) to load the `libttfautohint` shared library, but that was hard to maintain and complicated to keep up to date with upstream `ttfautohint` hence we decided to switch to a simpler `subprocess` approach (cf. #15).

Binary "wheel" packages are available for Linux (`manylinux2014`), macOS and Windows, for Python 3.8+, with 32 and 64 bit architecture. They can be installed from the Python Package Index ([PyPI](https://pypi.python.org/pypi/ttfautohint-py)) using the pip installer.

    $ pip install ttfautohint-py

The wheels include a precompiled `ttfautohint` executable which has no other dependency apart from system libraries. The [FreeType](https://www.freetype.org/) and the [HarfBuzz](https://github.com/harfbuzz/harfbuzz) libraries are compiled from source as static libraries and embedded in `ttfautohint`.

To compile the `ttfautohint-py` package from source on Windows, you need to install [MSYS2](http://www.msys2.org/) and the latest MinGW-w64 toolchain. This is because the `ttfautohint` build system is based on autotools and thus requires a Unix-like environment.

A `Makefile` is used to build the library and its static dependencies, thus the GNU [make](https://www.gnu.org/software/make/) executable must be on the `$PATH`, as this is called upon by the `setup.py` script.