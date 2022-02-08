|GitHub CI Status| |PyPI| |Codecov|

ttfautohint-py
~~~~~~~~~~~~~~

``ttfautohint-py`` is a Python wrapper for `ttfautohint
<https://www.freetype.org/ttfautohint>`__, a free auto-hinter for TrueType fonts
created by Werner Lemberg (`@lemzwerg <https://github.com/lemzwerg>`__).

It uses `ctypes <https://docs.python.org/3/library/ctypes.html>`__ to load the
``libttfautohint`` shared library and call the ``TTF_autohint`` function.

Binary "wheel" packages are available for Linux (``manylinux1``), macOS and
Windows, for both Python 2.7 and Python 3.x, with 32 and 64 bit architecture.
They can be installed from the Python Package Index
(`PyPI <https://pypi.python.org/pypi/ttfautohint-py>`__) using the
`pip <https://pip.pypa.io/en/stable/>`__ installer.

.. code:: sh

    $ pip install ttfautohint-py

The wheels include a precompiled ``libttfautohint.so`` (``*.dylib`` on
macOS, or ``*.dll`` on Windows) shared library which has no other dependency
apart from system libraries. The `FreeType <https://www.freetype.org>`__ and
the `HarfBuzz <https://github.com/harfbuzz/harfbuzz>`__ libraries are compiled
from source as static libraries and embedded in ``libttfautohint``.

To compile the ``libttfautohint.dll`` from source on Windows, you need to
install `MSYS2 <http://www.msys2.org/>`__ and the latest MinGW-w64 toolchain.
This is because the ``ttfautohint`` build system is based on autotools and
thus requires a Unix-like environment.

A ``Makefile`` is used to build the library and its static dependencies, thus
the GNU `make <https://www.gnu.org/software/make/>`__ executable must be on the
``$PATH``, as this is called upon by the ``setup.py`` script.

Because we build ``freetype``, ``harfbuzz`` and ``ttfautohint`` from their git
source (checked in as git submodules), some relatively recent versions of the
following development tools are also required: ``autoconf``, ``automake``,
``libtool``, ``flex``, ``bison`` and ``ragel``. Please check the respective
documentation of these libraries for more information.

.. |Github CI Status| image:: https://img.shields.io/github/workflow/status/fonttools/ttfautohint-py/CI
   :target: https://github.com/fonttools/ttfautohint-py/actions/workflows/ci.yml
.. |PyPI| image:: https://img.shields.io/pypi/v/ttfautohint-py.svg
   :target: https://pypi.python.org/pypi/ttfautohint-py
.. |Codecov| image:: https://codecov.io/gh/fonttools/ttfautohint-py/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/fonttools/ttfautohint-py
