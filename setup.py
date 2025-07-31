from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.bdist_wheel import bdist_wheel
from distutils.command.clean import clean
from distutils.file_util import copy_file
from distutils.dir_util import mkpath
from distutils import log
import os
import platform
import subprocess


class UniversalBdistWheel(bdist_wheel):
    def get_tag(self):
        return ("py3", "none") + bdist_wheel.get_tag(self)[2:]


class Executable(Extension):
    if os.name == "nt":
        suffix = ".exe"
    else:
        suffix = ""

    def __init__(self, name, output_dir=".", cwd=None, env=None):
        Extension.__init__(self, name, sources=[])
        self.target = self.name.split(".")[-1] + self.suffix
        self.output_dir = output_dir
        self.cwd = cwd
        self.env = env


class ExecutableBuildExt(build_ext):
    def get_ext_filename(self, ext_name):
        for ext in self.extensions:
            if isinstance(ext, Executable):
                return os.path.join(*ext_name.split(".")) + ext.suffix
        return build_ext.get_ext_filename(self, ext_name)

    def build_extension(self, ext):
        if not isinstance(ext, Executable):
            build_ext.build_extension(self, ext)
            return

        if platform.system() == "Windows":
            # we need to run make from a bash shell.
            cmd = ["bash", "-c", "make all"]
        else:
            cmd = ["make", "all"]

        log.debug("running '{}'".format(" ".join(cmd)))
        if not self.dry_run:
            env = dict(os.environ)
            if ext.env:
                env.update(ext.env)
            if platform.system() == "Windows":
                import struct

                msys2_root = os.path.abspath(env.get("MSYS2ROOT", "C:\\msys64"))
                msys2_bin = os.path.join(msys2_root, "usr", "bin")
                # select mingw32 or mingw64 toolchain depending on python architecture
                bits = struct.calcsize("P") * 8
                toolchain = "mingw%d" % bits

                # We require the standalone MinGW with win32 threads (MSYS2 only comes with
                # posix threads and unnecessarily pulls in libwinpthread-1.dll)
                standalone_mingw = f"C:\\mingw-win32\\mingw{bits}\\bin"
                if not os.path.isdir(standalone_mingw):
                    from distutils.errors import DistutilsPlatformError

                    raise DistutilsPlatformError(f"Could not find {standalone_mingw}")

                PATH = os.pathsep.join([standalone_mingw, msys2_bin, env["PATH"]])
                env.update(
                    PATH=PATH,
                    MSYSTEM=toolchain.upper(),
                    # this tells bash to keep the current working directory
                    CHERE_INVOKING="1",
                )

            if self.force:
                subprocess.call(["make", "clean"], cwd=ext.cwd, env=env)
            p = subprocess.run(cmd, cwd=ext.cwd, env=env, shell=True)
            if p.returncode != 0:
                from distutils.errors import DistutilsExecError

                raise DistutilsExecError("running 'make' failed")

        exe_fullpath = os.path.join(ext.output_dir, ext.target)

        dest_path = self.get_ext_fullpath(ext.name)
        mkpath(os.path.dirname(dest_path), verbose=self.verbose, dry_run=self.dry_run)

        copy_file(exe_fullpath, dest_path, verbose=self.verbose, dry_run=self.dry_run)


class CustomClean(clean):
    def run(self):
        clean.run(self)
        if not self.dry_run:
            # if -a, also git clean submodules to remove all the build byproducts
            if self.all:
                subprocess.call(
                    [
                        "git",
                        "submodule",
                        "foreach",
                        "--recursive",
                        "git",
                        "clean",
                        "-fdx",
                    ]
                )
            subprocess.call(["make", "clean"], cwd=os.path.join("src", "c"))


ttfautohint_exe = Executable(
    "ttfautohint.ttfautohint",
    cwd=os.path.join("src", "c"),
    output_dir=os.path.join("build", "local", "bin"),
)

cmdclass = {}
ext_modules = []
for env_var in ("TTFAUTOHINTPY_BUNDLE_DLL", "TTFAUTOHINTPY_BUNDLE_EXE"):
    if os.environ.get(env_var, "0") in {"1", "yes", "true"}:
        cmdclass["bdist_wheel"] = UniversalBdistWheel
        cmdclass["build_ext"] = ExecutableBuildExt
        cmdclass["clean"] = CustomClean
        ext_modules = [ttfautohint_exe]

with open("README.md", "r", encoding="utf-8") as readme:
    long_description = readme.read()

setup(
    name="ttfautohint-py",
    use_scm_version={"write_to": "src/python/ttfautohint/_version.py"},
    description=(
        "Python wrapper for ttfautohint, a free auto-hinter for TrueType fonts"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Cosimo Lupo",
    author_email="cosimo@anthrotype.com",
    url="https://github.com/fonttools/ttfautohint-py",
    license="MIT",
    platforms=["posix", "nt"],
    package_dir={"": "src/python"},
    packages=find_packages("src/python"),
    ext_modules=ext_modules,
    zip_safe=True,
    cmdclass=cmdclass,
    setup_requires=["setuptools_scm"],
    extras_require={"testing": ["pytest", "coverage", "fontTools"]},
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Text Processing :: Fonts",
        "Topic :: Multimedia :: Graphics",
    ],
)
