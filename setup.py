from setuptools import setup, find_packages, Extension, Command
from setuptools.command.build_ext import build_ext
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.egg_info import egg_info
from distutils.command.clean import clean
from distutils.errors import DistutilsSetupError
from distutils.file_util import copy_file
from distutils.dir_util import mkpath, remove_tree
from distutils import log
import os
import platform
import subprocess


class UniversalBdistWheel(bdist_wheel):
    def get_tag(self):
        return ("py3", "none") + bdist_wheel.get_tag(self)[2:]


class ApplyPatches(Command):
    user_options = []

    PATCHES = {
        "Windows": [
            ("freetype", "freetype2.patch"),
            ("harfbuzz", "harfbuzz.patch"),
        ],
    }

    def __init__(self, *args, **kwargs):
        Command.__init__(self, *args, **kwargs)
        self._applied = False

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if self._applied:
            return

        system = platform.system()
        if system in self.PATCHES:
            for src_dir, patch_file in self.PATCHES[system]:
                src_dir = os.path.join("src", "c", src_dir)
                patch = os.path.join("..", patch_file)
                subprocess.call(["git", "apply", patch], cwd=src_dir)

        self._applied = True


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
    def finalize_options(self):
        from distutils.ccompiler import get_default_compiler

        build_ext.finalize_options(self)

        if self.compiler is None:
            self.compiler = get_default_compiler(os.name)
        self._compiler_env = dict(os.environ)

    def get_ext_filename(self, ext_name):
        for ext in self.extensions:
            if isinstance(ext, Executable):
                return os.path.join(*ext_name.split(".")) + ext.suffix
        return build_ext.get_ext_filename(self, ext_name)

    def run(self):
        self.run_command("apply_patches")

        build_ext.run(self)

    def build_extension(self, ext):
        if not isinstance(ext, Executable):
            build_ext.build_extension(self, ext)
            return

        if platform.system() == "Windows":
            # we need to run make from an msys2 login shell.
            cmd = ["msys2", "-c", "make all"]
        else:
            cmd = ["make", "all"]

        log.debug("running '{}'".format(" ".join(cmd)))
        if not self.dry_run:
            env = self._compiler_env.copy()
            if ext.env:
                env.update(ext.env)
            if platform.system() == "Windows":
                import struct

                msys2_root = os.path.abspath(env.get("MSYS2ROOT", "C:\\msys64"))
                msys2_bin = os.path.join(msys2_root, "usr", "bin")
                # select mingw32 or mingw64 toolchain depending on python architecture
                bits = struct.calcsize("P") * 8
                toolchain = "mingw%d" % bits
                mingw_bin = os.path.join(msys2_root, toolchain, "bin")
                PATH = os.pathsep.join([mingw_bin, msys2_bin, env["PATH"]])
                env.update(
                    PATH=PATH,
                    MSYSTEM=toolchain.upper(),
                    # this tells bash to keep the current working directory
                    CHERE_INVOKING="1",
                )

            if self.force:
                subprocess.call(["make", "clean"], cwd=ext.cwd, env=env)
            p = subprocess.run(cmd, cwd=ext.cwd, env=env)
            if p.returncode != 0:
                from distutils.errors import DistutilsExecError

                raise DistutilsExecError("running 'make' failed")

        exe_fullpath = os.path.join(ext.output_dir, ext.target)

        dest_path = self.get_ext_fullpath(ext.name)
        mkpath(os.path.dirname(dest_path), verbose=self.verbose, dry_run=self.dry_run)

        copy_file(exe_fullpath, dest_path, verbose=self.verbose, dry_run=self.dry_run)


class CustomEggInfo(egg_info):
    def run(self):
        # make sure the ttfautohint source is patched before creating sdist manifest
        self.run_command("apply_patches")
        egg_info.run(self)


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
            subprocess.call(["make", "clean"], cwd="src/c")


ttfautohint_exe = Executable(
    "ttfautohint.ttfautohint",
    cwd="src/c",
    output_dir=os.path.join("build/local/bin"),
)

cmdclass = {}
ext_modules = []
for env_var in ("TTFAUTOHINTPY_BUNDLE_DLL", "TTFAUTOHINTPY_BUNDLE_EXE"):
    if os.environ.get(env_var, "0") in {"1", "yes", "true"}:
        cmdclass["bdist_wheel"] = UniversalBdistWheel
        cmdclass["apply_patches"] = ApplyPatches
        cmdclass["build_ext"] = ExecutableBuildExt
        cmdclass["egg_info"] = CustomEggInfo
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
    zip_safe=any(ext_modules),
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
