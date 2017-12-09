# use different build dirs for different python platforms
PYTHON := python
PLATFORM := $(shell $(PYTHON) -c \
    "import sysconfig; print(sysconfig.get_platform())")

ROOT := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SRC := $(ROOT)/src/c
BUILD := $(ROOT)/build/$(PLATFORM)
TMP := $(BUILD)/temp
PREFIX := $(BUILD)/local

CPPFLAGS := -I$(PREFIX)/include
CFLAGS := -g -O2 -fPIC
CXXFLAGS := -g -O2 -fPIC
LDFLAGS := -fPIC -L$(PREFIX)/lib -L$(PREFIX)/lib64

# on Windows, libtool cannot be used to build the ttfautohint.dll, we run
# dllwrap ourselves on the static libraries, so we --disable-shared
# https://lists.gnu.org/archive/html/freetype-devel/2017-12/msg00013.html
# http://lists.gnu.org/archive/html/libtool/2017-12/msg00003.html
LIBTTFAUTOHINT_OPTIONS := --enable-static
ifeq ($(OS), Windows_NT)
  LIBTTFAUTOHINT_OPTIONS += --disable-shared
  LIBTTFAUTOHINT := "ttfautohint.dll"
else
  LIBTTFAUTOHINT_OPTIONS += --enable-shared
  ifeq ($(shell uname -s), Darwin)
    LIBTTFAUTOHINT := "libttfautohint.dylib"
  else ifeq ($(shell uname -s), Linux)
    LIBTTFAUTOHINT := "libttfautohint.so"
  endif
endif

all: dll

dll: $(BUILD)/$(LIBTTFAUTOHINT)

freetype: $(TMP)/.freetype

harfbuzz: $(TMP)/.harfbuzz

ttfautohint: $(TMP)/.ttfautohint

$(TMP)/.freetype:
	cd $(SRC)/freetype2; ./autogen.sh
	@rm -rf $(TMP)/freetype
	@mkdir -p $(TMP)/freetype
	cd $(TMP)/freetype; $(SRC)/freetype2/configure \
        --without-bzip2 \
        --without-png \
        --without-zlib \
        --without-harfbuzz \
        --prefix="$(PREFIX)" \
        --enable-static \
        --disable-shared \
        PKG_CONFIG=" " \
        CFLAGS="$(CPPFLAGS) $(CFLAGS)" \
        CXXFLAGS="$(CPPFLAGS) $(CXXFLAGS)" \
        LDFLAGS="$(LDFLAGS)"
	cd $(TMP)/freetype; make
	cd $(TMP)/freetype; make install
	touch $(TMP)/.freetype

$(TMP)/.harfbuzz: $(TMP)/.freetype
	cd $(SRC)/harfbuzz; ./autogen.sh
	cd $(SRC)/harfbuzz; make distclean
	@rm -rf $(TMP)/harfbuzz
	@mkdir -p $(TMP)/harfbuzz
	cd $(TMP)/harfbuzz; $(SRC)/harfbuzz/configure \
        --disable-dependency-tracking \
        --disable-gtk-doc-html \
        --with-glib=no \
        --with-cairo=no \
        --with-fontconfig=no \
        --with-icu=no \
        --prefix=$(PREFIX) \
        --enable-static \
        --disable-shared \
        CFLAGS="$(CPPFLAGS) $(CFLAGS)" \
        CXXFLAGS="$(CPPFLAGS) $(CXXFLAGS)" \
        LDFLAGS="$(LDFLAGS)" \
        PKG_CONFIG=true \
        FREETYPE_CFLAGS="$(CPPFLAGS)/freetype2" \
        FREETYPE_LIBS="$(LDFLAGS) -lfreetype"
	cd $(TMP)/harfbuzz; make
	cd $(TMP)/harfbuzz; make install
	touch $(TMP)/.harfbuzz

$(TMP)/.ttfautohint: $(TMP)/.harfbuzz
	cd $(SRC)/ttfautohint; ./bootstrap
	@rm -rf $(TMP)/ttfautohint
	@mkdir -p $(TMP)/ttfautohint
	cd $(TMP)/ttfautohint; $(SRC)/ttfautohint/configure \
        --disable-dependency-tracking \
        --without-qt \
        --without-doc \
        --prefix="$(PREFIX)" \
        $(LIBTTFAUTOHINT_OPTIONS) \
        --with-freetype-config="$(PREFIX)/bin/freetype-config" \
        CFLAGS="$(CPPFLAGS) $(CFLAGS)" \
        CXXFLAGS="$(CPPFLAGS) $(CXXFLAGS)" \
        LDFLAGS="$(LDFLAGS)" \
        PKG_CONFIG=true \
        HARFBUZZ_CFLAGS="$(CPPFLAGS)/harfbuzz" \
        HARFBUZZ_LIBS="$(LDFLAGS) -lharfbuzz"
	cd $(TMP)/ttfautohint; make
	cd $(TMP)/ttfautohint; make install
	touch $(TMP)/.ttfautohint

$(BUILD)/$(LIBTTFAUTOHINT): $(TMP)/.ttfautohint
ifeq ($(OS), Windows_NT)
	dllwrap -v --def $(SRC)/ttfautohint.def -o $@ \
        $(TMP)/ttfautohint/lib/.libs/libttfautohint.a \
        $(TMP)/ttfautohint/lib/.libs/libsds.a \
        $(TMP)/ttfautohint/lib/.libs/libnumberset.a \
        $(TMP)/ttfautohint/gnulib/src/.libs/libgnu.a \
        $(PREFIX)/lib/libharfbuzz.a \
        $(PREFIX)/lib/libfreetype.a
else
	@cp $(PREFIX)/lib/$(LIBTTFAUTOHINT) $@
endif

clean:
	@git submodule foreach git clean -fdx .
	@rm -rf build

.PHONY: clean all dll freetype harfbuzz ttfautohint
