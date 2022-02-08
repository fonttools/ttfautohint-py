LIB_NAME := "libttfautohint"

SRC := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
ROOT := $(shell dirname $(shell dirname $(SRC)))
BUILD := $(ROOT)/build
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
  LIBTTFAUTOHINT := "$(LIB_NAME).dll"
else
  LIBTTFAUTOHINT_OPTIONS += --enable-shared
  ifeq ($(shell uname -s), Darwin)
    LIBTTFAUTOHINT := "$(LIB_NAME).dylib"
    # on macOS, we want a 64-bit only lib targeting >= 10.9, since harfbuzz >= 2.4
    # requires c++11
    MACOSX_DEPLOYMENT_TARGET ?= 10.9
    CFLAGS   += -m64 -arch x86_64 -arch arm64 -mmacosx-version-min=$(MACOSX_DEPLOYMENT_TARGET)
    CXXFLAGS += -m64 -arch x86_64 -arch arm64 -mmacosx-version-min=$(MACOSX_DEPLOYMENT_TARGET)
    LDFLAGS  += -m64 -arch x86_64 -arch arm64 -mmacosx-version-min=$(MACOSX_DEPLOYMENT_TARGET)
  else ifeq ($(shell uname -s), Linux)
    LIBTTFAUTOHINT := "$(LIB_NAME).so"
  endif
endif

all: libttfautohint

libttfautohint: $(PREFIX)/lib/$(LIBTTFAUTOHINT)

freetype: $(TMP)/.freetype-stamp

harfbuzz: $(TMP)/.harfbuzz-stamp

ttfautohint: $(TMP)/.ttfautohint-stamp

$(TMP)/.freetype-stamp:
	@mkdir -p $(TMP)
	cd $(SRC)/freetype2; ./autogen.sh
	cd $(SRC)/freetype2; ./configure \
	  --without-bzip2 \
	  --without-png \
	  --without-zlib \
	  --without-harfbuzz \
	  --without-brotli \
	  --prefix="$(PREFIX)" \
	  --enable-static \
	  --disable-shared \
	  --enable-freetype-config \
	  PKG_CONFIG=" " \
	  CFLAGS="$(CPPFLAGS) $(CFLAGS)" \
	  CXXFLAGS="$(CPPFLAGS) $(CXXFLAGS)" \
	  LDFLAGS="$(LDFLAGS)"
	cd $(SRC)/freetype2; make
	cd $(SRC)/freetype2; make install
	@touch $(TMP)/.freetype-stamp

$(TMP)/.harfbuzz-stamp: $(TMP)/.freetype-stamp
	@mkdir -p $(TMP)
	cd $(SRC)/harfbuzz; NOCONFIGURE=1 ./autogen.sh
	cd $(SRC)/harfbuzz; ./configure \
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
	cd $(SRC)/harfbuzz; make
	cd $(SRC)/harfbuzz; make install
	@touch $(TMP)/.harfbuzz-stamp

$(TMP)/.ttfautohint-stamp: $(TMP)/.harfbuzz-stamp
	@mkdir -p $(TMP)
	cd $(SRC)/ttfautohint; ./bootstrap
	cd $(SRC)/ttfautohint; ./configure \
          --disable-dependency-tracking \
          --without-qt \
          --without-doc \
          --prefix="$(PREFIX)" \
          $(LIBTTFAUTOHINT_OPTIONS) \
          CFLAGS="$(CPPFLAGS) -I$(TMP)/ttfautohint/lib $(CFLAGS)" \
          CXXFLAGS="$(CPPFLAGS) -I$(TMP)/ttfautohint/lib $(CXXFLAGS)" \
          LDFLAGS="$(LDFLAGS)" \
          PKG_CONFIG=true \
	  FREETYPE_CFLAGS="$(CPPFLAGS)/freetype2" \
	  FREETYPE_LIBS="$(LDFLAGS) -lfreetype" \
          HARFBUZZ_CFLAGS="$(CPPFLAGS)/harfbuzz" \
          HARFBUZZ_LIBS="$(LDFLAGS) -lharfbuzz -lfreetype"
	cd $(SRC)/ttfautohint; make
	cd $(SRC)/ttfautohint; make install
	@touch $(TMP)/.ttfautohint-stamp

$(PREFIX)/lib/$(LIBTTFAUTOHINT): $(TMP)/.ttfautohint-stamp
ifeq ($(OS), Windows_NT)
	dllwrap -v --def $(SRC)/ttfautohint.def -o $@ \
        $(PREFIX)/lib/libttfautohint.a \
        $(PREFIX)/lib/libharfbuzz.a \
        $(PREFIX)/lib/libfreetype.a
endif

clean:
	@git submodule foreach git clean -fdx .
	@rm -rf $(TMP) $(PREFIX)

.PHONY: clean all libttfautohint freetype harfbuzz ttfautohint
