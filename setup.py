from __future__ import print_function, absolute_import
from setuptools import setup, find_packages, Extension, Command
from setuptools.command.build_ext import build_ext
from distutils.file_util import copy_file
from distutils.dir_util import mkpath
from distutils import log
import os
import sys
import subprocess


NAME = "ttfautohint"
LIB_NAME = "lib" + NAME
if sys.platform == "darwin":
    LIB_SUFFIX = ".dylib"
elif sys.platform == "win32":
    LIB_SUFFIX = ".dll"
else:
    LIB_SUFFIX = ".so"
LIB_FILENAME = LIB_NAME + LIB_SUFFIX
HERE = os.path.dirname(__file__)
LIB_DIR = os.path.join(HERE, "build", "local", "lib")
EMPTY_C = os.path.join(HERE, "src", "c", "empty.c")


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


class BuildShlib(Command):

    def initialize_options(self):
        self.build_lib = None

    def finalize_options(self):
        self.set_undefined_options('build',
                                   ('build_lib', 'build_lib'))

    def run(self):
        log.info("running 'make'")
        if not self.dry_run:
            rv = subprocess.Popen(["make"], env=dict(os.environ)).wait()
            if rv != 0:
                sys.exit(rv)

        for filename in os.listdir(LIB_DIR):
            if filename == LIB_FILENAME:
                shlib = os.path.join(LIB_DIR, filename)
                break
        else:
            raise LookupError('%r not found' % LIB_FILENAME)

        dest_dir = os.path.join(self.build_lib, NAME)
        mkpath(dest_dir, verbose=self.verbose, dry_run=self.dry_run)

        dest_path = os.path.join(dest_dir, LIB_FILENAME)
        copy_file(shlib, dest_path, preserve_times=False,
                  verbose=self.verbose, dry_run=self.dry_run)


class DummyBuildExt(build_ext):

    def finalize_options(self):
        build_ext.finalize_options(self)
        self.force = False

    def get_ext_fullpath(self, ext_name):
        lib_filename = self._get_lib_filename(ext_name)
        if lib_filename is None:
            return build_ext.get_ext_fullpath(self, ext_name)

        if not self.inplace:
            return os.path.join(self.build_lib, NAME, lib_filename)

        build_py = self.get_finalized_command('build_py')
        package_dir = os.path.abspath(build_py.get_package_dir(NAME))
        return os.path.join(package_dir, lib_filename)

    def get_ext_filename(self, ext_name):
        lib_filename = self._get_lib_filename(ext_name)
        if lib_filename is None:
            return build_ext.get_ext_filename(self, ext_name)
        return os.path.join(NAME, lib_filename)

    def _get_lib_filename(self, ext_name):
        for ext in self.distribution.ext_modules:
            if ext.name == ext_name:
                return getattr(ext, '_lib_filename', None)

    def run(self):
        self.run_command("build_shlib")
        build_ext.run(self)


cmdclass['build_shlib'] = BuildShlib
cmdclass['build_ext'] = DummyBuildExt

dummy_ext = Extension("%s.%s" % (NAME, LIB_NAME), sources=[EMPTY_C])
dummy_ext._lib_filename = LIB_FILENAME


setup(
    name=NAME,
    version='0.1.0.dev0',
    package_dir={'': 'src/python'},
    packages=find_packages('src/python'),
    ext_modules=[dummy_ext],
    zip_safe=False,
    cmdclass=cmdclass,
)
