# Define custom utilities
# Test for OSX with [ -n "$IS_OSX" ]

if [ -n "$IS_OSX" ]; then
    PATH="/usr/local/opt/libtool/bin:$PATH"
    PATH="/usr/local/opt/ragel/bin:$PATH"
    PATH="/usr/local/opt/bison/bin:$PATH"
    PATH="/usr/local/opt/flex/bin:$PATH"
    export PATH
fi

function pre_build {
    # Any stuff that you need to do before you start building the wheels
    # Runs in the root directory of this repository.
    if [ -n "$IS_OSX" ]; then
        echo $PATH
        brew install libtool ragel flex bison
        # the GNU libtool/libtoolize are prefixed with "g" to avoid clash
        # with /usr/bin/libtool
        which glibtool
        glibtool --version
    else
        build_libtool
        build_ragel
        build_flex
        build_bison

        which libtool
        libtool --version
    fi

    which ragel
    ragel --version

    which flex
    flex --version

    which bison
    bison --version
}

function run_tests {
    # The function is called from an empty temporary directory.
    python -c "import ttfautohint"
}
