SRC := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
ROOT := $(shell dirname $(shell dirname $(SRC)))
BUILD := $(ROOT)/build
TMP := $(BUILD)/temp
PREFIX := $(BUILD)/local

CPPFLAGS := -I$(PREFIX)/include
CFLAGS := -g -O2 -fPIC
CXXFLAGS := -g -O2 -fPIC
LDFLAGS := -fPIC -L$(PREFIX)/lib -L$(PREFIX)/lib64

LIBTTFAUTOHINT_OPTIONS := --enable-static --disable-shared
ifeq ($(shell uname -s), Darwin)
	# on macOS, we want a 64-bit only lib targeting >= 10.9, since harfbuzz >= 2.4
	# requires c++11
	MACOSX_DEPLOYMENT_TARGET ?= 10.9
	CFLAGS   += -m64 -arch x86_64 -arch arm64 -mmacosx-version-min=$(MACOSX_DEPLOYMENT_TARGET)
	CXXFLAGS += -m64 -arch x86_64 -arch arm64 -mmacosx-version-min=$(MACOSX_DEPLOYMENT_TARGET)
	LDFLAGS  += -m64 -arch x86_64 -arch arm64 -mmacosx-version-min=$(MACOSX_DEPLOYMENT_TARGET)
endif

# On Windows/MINGW, statically link GCC runtime libraries to avoid DLL dependencies
ifneq (,$(findstring MINGW,$(shell uname -s)))
	LDFLAGS += -static-libgcc -static-libstdc++
endif

all: ttfautohint

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

# We pass --disable-threads on MinGW to avoid depending on libwinpthread-1.dll
$(TMP)/.ttfautohint-stamp: $(TMP)/.harfbuzz-stamp
	@mkdir -p $(TMP)
	cd $(SRC)/ttfautohint; ./bootstrap
	cd $(SRC)/ttfautohint; ./configure \
          --disable-dependency-tracking \
          --without-qt \
          --without-doc \
          --prefix="$(PREFIX)" \
          $(LIBTTFAUTOHINT_OPTIONS) \
          $(if $(findstring MINGW,$(shell uname -s)),--disable-threads) \
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

clean:
	@rm -rf $(TMP) $(PREFIX)

.PHONY: clean all freetype harfbuzz ttfautohint
