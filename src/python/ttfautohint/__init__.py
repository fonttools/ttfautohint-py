import io
import os
import subprocess
import sys
from importlib.resources import as_file, files, is_resource

from ttfautohint._version import __version__
from ttfautohint.errors import TAError
from ttfautohint.options import validate_options, format_kwargs, StemWidthMode


__all__ = ["__version__", "ttfautohint", "TAError", "StemWidthMode", "run"]


EXECUTABLE = "ttfautohint"
if sys.platform == "win32":
    EXECUTABLE += ".exe"

HAS_BUNDLED_EXE = None


def _has_bundled_exe():
    global HAS_BUNDLED_EXE

    if HAS_BUNDLED_EXE is None:
        HAS_BUNDLED_EXE = is_resource(__name__, EXECUTABLE)

    return HAS_BUNDLED_EXE


def run(args, **kwargs):
    """Run the 'ttfautohint' executable with the list of positional arguments.

    All keyword arguments are forwarded to subprocess.run function.

    The bundled copy of the 'ttfautohint' executable is tried first; if this
    was not included at installation, the version which is on $PATH is used.

    Return:
        subprocess.CompletedProcess object with the following attributes:
        args, returncode, stdout, stderr.
    """
    if _has_bundled_exe():
        with as_file(files(__name__).joinpath(EXECUTABLE)) as bundled_exe:
            return subprocess.run([str(bundled_exe)] + list(args), **kwargs)
    else:
        return subprocess.run([EXECUTABLE] + list(args), **kwargs)


# TODO: add docstring
def ttfautohint(**kwargs):
    options = validate_options(kwargs)

    in_buffer = options.pop("in_buffer")
    out_file = options.pop("out_file")

    capture_output = True
    stdout = None
    should_close_stdout = False
    if out_file is not None:
        if isinstance(out_file, (str, bytes, os.PathLike)):
            stdout, out_file = open(out_file, "w"), None
            should_close_stdout = True
            capture_output = False
        else:
            try:
                out_file.fileno()
            except io.UnsupportedOperation:
                if not out_file.writable():
                    raise TypeError(f"{out_file} is not writable")
            else:
                stdout, out_file = out_file, None
                capture_output = False

    args = format_kwargs(**options)

    result = run(
        args,
        input=in_buffer,
        capture_output=capture_output,
        stdout=stdout,
    )
    if result.returncode != 0:
        raise TAError(result.returncode, result.stderr)

    output_data = result.stdout

    if output_data and out_file is not None:
        out_file.write(output_data)

    if stdout is not None and should_close_stdout:
        stdout.close()

    return output_data
