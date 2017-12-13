from __future__ import print_function, absolute_import
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from distutils.file_util import copy_file
from distutils.dir_util import mkpath
from distutils import log
import os
import sys
import subprocess


cmdclass = {}
try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    print("warning: wheel package is not installed", file=sys.stderr)
else:
    class UniversalBdistWheel(bdist_wheel):

        def get_tag(self):
            return ('py2.py3', 'none',) + bdist_wheel.get_tag(self)[2:]

    cmdclass['bdist_wheel'] = UniversalBdistWheel


class SharedLibrary(Extension):

    if sys.platform == "darwin":
        suffix = ".dylib"
    elif sys.platform == "win32":
        suffix = ".dll"
    else:
        suffix = ".so"

    def __init__(self, name, cmd, cwd=".", output_dir=".", env=None):
        Extension.__init__(self, name, sources=[])
        self.cmd = cmd
        self.cwd = os.path.normpath(cwd)
        self.output_dir = os.path.normpath(output_dir)
        self.env = env or dict(os.environ)


class SharedLibBuildExt(build_ext):

    def get_ext_filename(self, ext_name):
        for ext in self.extensions:
            if isinstance(ext, SharedLibrary):
                return os.path.join(*ext_name.split('.')) + ext.suffix
        return build_ext.get_ext_filename(self, ext_name)

    def build_extension(self, ext):
        if not isinstance(ext, SharedLibrary):
            build_ext.build_extension(self, ext)
            return

        log.info("running '%s'" % " ".join(ext.cmd))
        if not self.dry_run:
            rv = subprocess.Popen(ext.cmd, cwd=ext.cwd, env=ext.env).wait()
            if rv != 0:
                sys.exit(rv)

        lib_name = ext.name.split(".")[-1] + ext.suffix
        lib_fullpath = os.path.join(ext.output_dir, lib_name)

        dest_path = self.get_ext_fullpath(ext.name)
        mkpath(os.path.dirname(dest_path),
               verbose=self.verbose, dry_run=self.dry_run)

        copy_file(lib_fullpath, dest_path,
                  verbose=self.verbose, dry_run=self.dry_run)


cmdclass['build_ext'] = SharedLibBuildExt

libttfautohint = SharedLibrary("ttfautohint.libttfautohint",
                               cmd=["make"],
                               cwd="src/c",
                               output_dir="build/local/lib")


setup(
    name="ttfautohint-py",
    version="0.1.0.dev0",
    description=("Python wrapper for ttfautohint, "
                 "a free auto-hinter for TrueType fonts"),
    author="Cosimo Lupo",
    author_email="cosimo@anthrotype.com",
    url="https://github.com/fonttools/ttfautohint-py",
    license="MIT",
    platforms=["posix", "nt"],
    package_dir={"": "src/python"},
    packages=find_packages("src/python"),
    ext_modules=[libttfautohint],
    zip_safe=False,
    cmdclass=cmdclass,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MTI License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Text Processing :: Fonts",
        "Topic :: Multimedia :: Graphics",
    ],
)
