# Define custom utilities
# Test for OSX with [ -n "$IS_OSX" ]

function pre_build {
    # Any stuff that you need to do before you start building the wheels
    # Runs in the root directory of this repository.
    if [ -n "$IS_OSX" ]; then
        brew install autoconf
        brew install automake
        brew install libtool
        brew install bison
        brew install flex
        brew install ragel
    else
        yum -y install autoconf
        yum -y install automake
        yum -y install libtool
        yum -y install bison
        yum -y install flex
        yum -y install ragel
    fi
}

function run_tests {
    # The function is called from an empty temporary directory.
    python -c "import ttfautohint"
}
