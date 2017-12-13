# Define custom utilities
# Test for OSX with [ -n "$IS_OSX" ]

if [ -n "$IS_OSX"]; then
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
        which libtool
        libtool --version
        which ragel
        ragel --version
        which flex
        flex --version
        which bison
        bison --version
    else
        build_simple libtool 2.4.6 http://ftpmirror.gnu.org/libtool
        build_simple ragel 6.10 http://www.colm.net/files/ragel
        build_simple flex 2.6.4 https://github.com/westes/flex/releases/download/v2.6.4
        build_simple bison 3.0.4 http://ftp.gnu.org/gnu/bison
    fi
}

function run_tests {
    # The function is called from an empty temporary directory.
    python -c "import ttfautohint"
}
