if [ "$(uname)" == "Darwin" ]; then
    export MACOSX_DEPLOYMENT_TARGET=10.9
elif [ "$(uname)" == "Linux" ]; then
    # The manylinux1 image's has pkg.m4 inside /usr/share/aclocal whereas the
    # default aclocal directory is /usr/local/share/aclocal. Without setting
    # this, compiling harfbuzz fails with syntax error in configure script:
    # https://askubuntu.com/a/468895
    export ACLOCAL_PATH=$(aclocal --print-ac-dir):/usr/share/aclocal
fi
