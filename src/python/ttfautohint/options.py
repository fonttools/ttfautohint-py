import sys
from ttfautohint._compat import ensure_binary


USER_OPTIONS = dict(
    in_file=None,
    in_buffer=None,
    out_file=None,
    control_file=None,
    control_buffer=None,
    reference_file=None,
    reference_buffer=None,
    reference_index=0,
    reference_name=None,
    hinting_range_min=8,
    hinting_range_max=50,
    hinting_limit=200,
    hint_composites=False,
    adjust_subglyphs=False,
    gray_strong_stem_width=False,
    gdi_cleartype_strong_stem_width=True,
    dw_cleartype_strong_stem_width=False,
    increase_x_height=14,
    x_height_snapping_exceptions="",
    windows_compatibility=False,
    default_script="latn",
    fallback_script="none",
    fallback_scaling=False,
    symbol=False,
    fallback_stem_width=0,
    ignore_restrictions=False,
    detailed_info=False,
    no_info=False,
    TTFA_info=False,
    dehint=False,
    epoch=None,
    debug=False,
)

PRIVATE_OPTIONS = frozenset([
    "in_buffer_len",
    "control_buffer_len",
    "reference_buffer_len",
    "out_buffer",
    "out_buffer_len",
    "error_string",
    "alloc_func",
    "free_func",
    "info_callback",
    "info_post_callback",
    "info_callback_data",
])

ALL_OPTIONS = frozenset(USER_OPTIONS) | PRIVATE_OPTIONS


def validate_options(kwargs):
    opts = {k: kwargs.pop(k, USER_OPTIONS[k]) for k in USER_OPTIONS}
    if kwargs:
        raise TypeError(
            "unknown keyword argument%s: %s" % (
                "s" if len(kwargs) > 1 else "",
                ", ".join(repr(k) for k in kwargs)))

    if opts["no_info"] and opts["detailed_info"]:
        raise ValueError("no_info and detailed_info are mutually exclusive")

    in_file, in_buffer = opts.pop("in_file"), opts.pop("in_buffer")
    if in_file is None and in_buffer is None:
        raise ValueError("No input file or buffer provided")
    elif in_file is not None and in_buffer is not None:
        raise ValueError("in_file and in_buffer are mutually exclusive")
    if in_file is not None:
        try:
            in_buffer = in_file.read()
        except AttributeError:
            with open(in_file, "rb") as f:
                in_buffer = f.read()
    if not isinstance(in_buffer, bytes):
        raise TypeError("in_buffer type must be bytes, not %s"
                        % type(in_buffer).__name__)
    opts['in_buffer'] = in_buffer
    opts['in_buffer_len'] = len(in_buffer)

    control_file = opts.pop('control_file')
    control_buffer = opts.pop('control_buffer')
    if control_file is not None:
        if control_buffer is not None:
            raise ValueError(
                "control_file and control_buffer are mutually exclusive")
        try:
            control_buffer = control_file.read()
        except AttributeError:
            with open(control_file, "rb") as f:
                control_buffer = f.read()
            opts["control_name"] = ensure_binary(
                control_file, encoding=sys.getfilesystemencoding())
        else:
            try:
                opts["control_name"] = ensure_binary(
                    control_file.name, encoding=sys.getfilesystemencoding())
            except AttributeError:
                pass
    if control_buffer is not None:
        if not isinstance(control_buffer, bytes):
            raise TypeError("control_buffer type must be bytes, not %s"
                            % type(control_buffer).__name__)
        opts['control_buffer'] = control_buffer
        opts['control_buffer_len'] = len(control_buffer)

    reference_file = opts.pop('reference_file')
    reference_buffer = opts.pop('reference_buffer')
    if reference_file is not None:
        if reference_buffer is not None:
            raise ValueError(
                "reference_file and reference_buffer are mutually exclusive")
        try:
            reference_buffer = reference_file.read()
        except AttributeError:
            with open(reference_file, "rb") as f:
                reference_buffer = f.read()
            if opts["reference_name"] is not None:
                opts["reference_name"] = reference_file
        else:
            if opts["reference_name"] is not None:
                try:
                    opts["reference_name"] = reference_file.name
                except AttributeError:
                    pass
    if reference_buffer is not None:
        if not isinstance(reference_buffer, bytes):
            raise TypeError("reference_buffer type must be bytes, not %s"
                            % type(reference_buffer).__name__)
        opts['reference_buffer'] = reference_buffer
        opts['reference_buffer_len'] = len(reference_buffer)
    if opts["reference_name"] is not None:
        opts["reference_name"] = ensure_binary(
            opts["reference_name"], encoding=sys.getfilesystemencoding())

    for key in ('default_script', 'fallback_script',
                'x_height_snapping_exceptions'):
        if opts[key] is not None:
            opts[key] = ensure_binary(opts[key])

    if opts['epoch'] is not None:
        from ctypes import c_ulonglong
        opts['epoch'] = c_ulonglong(opts['epoch'])

    return opts


def format_varargs(**options):
    items = sorted((k, v) for k, v in options.items()
                   if k in ALL_OPTIONS and v is not None)
    format_string = b", ".join(ensure_binary(k.replace("_", "-"))
                               for k, v in items)
    values = tuple(v for k, v in items)
    return format_string, values
