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


class Download(Command):
    user_options = [
        ("ttfautohint-version=", None, "ttfautohint source version number to download"),
        (
            "ttfautohint-sha256=",
            None,
            "expected SHA-256 hash of the ttfautohint source archive",
        ),
        ("freetype-version=", None, "freetype version to download"),
        ("freetype-sha256=", None, "expected SHA-256 hash of the freetype archive"),
        ("harfbuzz-version=", None, "harfbuzz version to download"),
        ("harfbuzz-sha256=", None, "expected SHA-256 hash of the harfbuzz archive"),
        (
            "download-dir=",
            "d",
            "where to unpack the 'ttfautohint' dir (default: src/c)",
        ),
        ("clean", None, "remove existing directory before downloading"),
    ]
    boolean_options = ["clean"]

    TTFAUTOHINT_URL_TEMPLATE = (
        "https://download.savannah.gnu.org/releases/freetype/"
        "ttfautohint-{ttfautohint_version}.tar.gz"
    )
    FREETYPE_URL_TEMPLATE = (
        "https://download.savannah.gnu.org/releases/freetype/"
        "freetype-{freetype_version}.tar.xz"
    )
    HARFBUZZ_URL_TEMPLATE = (
        "https://github.com/harfbuzz/harfbuzz/releases/download/{harfbuzz_version}/"
        "harfbuzz-{harfbuzz_version}.tar.xz"
    )

    def initialize_options(self):
        self.ttfautohint_version = None
        self.ttfautohint_sha256 = None
        self.freetype_version = None
        self.freetype_sha256 = None
        self.harfbuzz_version = None
        self.harfbuzz_sha256 = None
        self.download_dir = None
        self.clean = False

    def finalize_options(self):
        if self.ttfautohint_version is None:
            raise DistutilsSetupError("must specify --ttfautohint-version to download")
        if self.freetype_version is None:
            raise DistutilsSetupError("must specify --freetype-version to download")
        if self.harfbuzz_version is None:
            raise DistutilsSetupError("must specify --harfbuzz-version to download")

        if self.ttfautohint_sha256 is None:
            raise DistutilsSetupError(
                "must specify --ttfautohint-sha256 of downloaded file"
            )
        if self.freetype_sha256 is None:
            raise DistutilsSetupError(
                "must specify --freetype-sha256 of downloaded file"
            )
        if self.harfbuzz_sha256 is None:
            raise DistutilsSetupError(
                "must specify --harfbuzz-sha256 of downloaded file"
            )

        if self.download_dir is None:
            self.download_dir = os.path.join("src", "c")

        self.to_download = {
            "ttfautohint": self.TTFAUTOHINT_URL_TEMPLATE.format(**vars(self)),
            "freetype": self.FREETYPE_URL_TEMPLATE.format(**vars(self)),
            "harfbuzz": self.HARFBUZZ_URL_TEMPLATE.format(**vars(self)),
        }

    def run(self):
        from urllib.request import urlopen
        from io import BytesIO
        import tarfile
        import gzip
        import lzma
        import hashlib

        for download_name, url in self.to_download.items():
            output_dir = os.path.join(self.download_dir, download_name)
            if self.clean and os.path.isdir(output_dir):
                remove_tree(output_dir, verbose=self.verbose, dry_run=self.dry_run)

            if os.path.isdir(output_dir):
                log.info("{} was already downloaded".format(output_dir))
            else:
                archive_name = url.rsplit("/", 1)[-1]

                mkpath(self.download_dir, verbose=self.verbose, dry_run=self.dry_run)

                log.info("downloading {}".format(url))
                if not self.dry_run:
                    # response is not seekable so we first download *.tar.gz to an
                    # in-memory file, and then extract all files to the output_dir
                    f = BytesIO()
                    with urlopen(url) as response:
                        f.write(response.read())
                    f.seek(0)

                actual_sha256 = hashlib.sha256(f.getvalue()).hexdigest()
                expected_sha256 = getattr(self, download_name + "_sha256")
                if actual_sha256 != expected_sha256:
                    from distutils.errors import DistutilsSetupError

                    raise DistutilsSetupError(
                        "invalid SHA-256 checksum:\n"
                        "actual:   {}\n"
                        "expected: {}".format(actual_sha256, expected_sha256)
                    )

                log.info("unarchiving {} to {}".format(archive_name, output_dir))
                if not self.dry_run:
                    ext = os.path.splitext(archive_name)[-1]
                    if ext == ".xz":
                        compression_module = lzma
                    elif ext == ".gz":
                        compression_module = gzip
                    else:
                        raise NotImplementedError(
                            f"Don't know how to decompress archive with {ext} extension"
                        )
                    with compression_module.open(f) as archive:
                        with tarfile.open(fileobj=archive) as tar:
                            filelist = tar.getmembers()
                            first = filelist[0]
                            if not (
                                first.isdir() and first.name.startswith(download_name)
                            ):
                                from distutils.errors import DistutilsSetupError

                                raise DistutilsSetupError(
                                    "The downloaded archive is not recognized as "
                                    "a valid ttfautohint source tarball"
                                )
                            # strip the root directory before extracting
                            rootdir = first.name + "/"
                            to_extract = []
                            for member in filelist[1:]:
                                if member.name.startswith(rootdir):
                                    member.name = member.name[len(rootdir) :]
                                    to_extract.append(member)
                            tar.extractall(output_dir, members=to_extract)


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
        self.run_command("download")
        self.run_command("apply_patches")

        if self.compiler == "msvc":
            self.call_vcvarsall_bat()

        build_ext.run(self)

    def call_vcvarsall_bat(self):
        import struct
        from distutils._msvccompiler import _get_vc_env

        arch = "x64" if struct.calcsize("P") * 8 == 64 else "x86"
        vc_env = _get_vc_env(arch)
        self._compiler_env.update(vc_env)

    def build_extension(self, ext):
        if not isinstance(ext, Executable):
            build_ext.build_extension(self, ext)
            return

        cmd = ["make"] + [ext.target]
        log.debug("running '{}'".format(" ".join(cmd)))
        if not self.dry_run:
            env = self._compiler_env.copy()
            if ext.env:
                env.update(ext.env)
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
        # make sure the ttfautohint source is downloaded before creating sdist manifest
        self.run_command("download")
        self.run_command("apply_patches")
        egg_info.run(self)


class CustomClean(clean):
    def run(self):
        clean.run(self)
        # also remove downloaded sources and all build byproducts
        for path in ["src/c/ttfautohint", "src/c/freetype", "src/c/harfbuzz"]:
            if os.path.isdir(path):
                remove_tree(path, self.verbose, self.dry_run)
            else:
                log.info("'{}' does not exist -- can't clean it".format(path))
        if not self.dry_run:
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
        cmdclass["download"] = Download
        cmdclass["apply_patches"] = ApplyPatches
        cmdclass["build_ext"] = ExecutableBuildExt
        cmdclass["egg_info"] = CustomEggInfo
        cmdclass["clean"] = CustomClean
        ext_modules = [ttfautohint_exe]

with open("README.md", "r", encoding="utf-8") as readme:
    long_description = readme.read()

setup(
    name="ttfautohint",
    use_scm_version={"write_to": "src/python/ttfautohint/_version.py"},
    description=("Python wrapper for ttfautohint"),
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
    python_requires=">=3.8",
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
