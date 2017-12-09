# use different build dirs for different python platforms
PYTHON := python
PLATFORM := $(shell $(PYTHON) -c \
    "import sysconfig; print(sysconfig.get_platform())")

ROOT := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SRC := $(ROOT)/src/c
BUILD := $(ROOT)/build/$(PLATFORM)/temp
PREFIX := $(ROOT)/build/$(PLATFORM)/local

CPPFLAGS := -I$(PREFIX)/include
CFLAGS := -g -O2 -fPIC
CXXFLAGS := -g -O2 -fPIC
LDFLAGS := -fPIC -L$(PREFIX)/lib -L$(PREFIX)/lib64

# on Windows, libtool cannot be used to build the ttfautohint.dll, we run
# dllwrap ourselves on the static libraries, so we --disable-shared
# https://lists.gnu.org/archive/html/freetype-devel/2017-12/msg00013.html
# http://lists.gnu.org/archive/html/libtool/2017-12/msg00003.html
LIBTA_OPTIONS := --enable-static
ifeq ($(OS), Windows_NT)
  LIBTA_OPTIONS += --disable-shared
else
  LIBTA_OPTIONS += --enable-shared
endif

all: ttfautohint

freetype: $(BUILD)/.freetype

harfbuzz: $(BUILD)/.harfbuzz

ttfautohint: $(BUILD)/.ttfautohint

$(BUILD)/.freetype:
	cd $(SRC)/freetype2; ./autogen.sh
	@rm -rf $(BUILD)/freetype
	@mkdir -p $(BUILD)/freetype
	cd $(BUILD)/freetype; $(SRC)/freetype2/configure \
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
	cd $(BUILD)/freetype; make
	cd $(BUILD)/freetype; make install
	touch $(BUILD)/.freetype

$(BUILD)/.harfbuzz: $(BUILD)/.freetype
	cd $(SRC)/harfbuzz; ./autogen.sh
	cd $(SRC)/harfbuzz; make distclean
	@rm -rf $(BUILD)/harfbuzz
	@mkdir -p $(BUILD)/harfbuzz
	cd $(BUILD)/harfbuzz; $(SRC)/harfbuzz/configure \
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
	cd $(BUILD)/harfbuzz; make
	cd $(BUILD)/harfbuzz; make install
	touch $(BUILD)/.harfbuzz

$(BUILD)/.ttfautohint: $(BUILD)/.harfbuzz
	cd $(SRC)/ttfautohint; ./bootstrap
	@rm -rf $(BUILD)/ttfautohint
	@mkdir -p $(BUILD)/ttfautohint
	cd $(BUILD)/ttfautohint; $(SRC)/ttfautohint/configure \
        --disable-dependency-tracking \
        --without-qt \
        --without-doc \
        --prefix="$(PREFIX)" \
        $(LIBTA_OPTIONS) \
        --with-freetype-config="$(PREFIX)/bin/freetype-config" \
        CFLAGS="$(CPPFLAGS) $(CFLAGS)" \
        CXXFLAGS="$(CPPFLAGS) $(CXXFLAGS)" \
        LDFLAGS="$(LDFLAGS)" \
        PKG_CONFIG=true \
        HARFBUZZ_CFLAGS="$(CPPFLAGS)/harfbuzz" \
        HARFBUZZ_LIBS="$(LDFLAGS) -lharfbuzz"
	cd $(BUILD)/ttfautohint; make
	cd $(BUILD)/ttfautohint; make install
	touch $(BUILD)/.ttfautohint

clean:
	@git submodule foreach git clean -fdx .
	@rm -rf build

.PHONY: clean all freetype harfbuzz ttfautohint
