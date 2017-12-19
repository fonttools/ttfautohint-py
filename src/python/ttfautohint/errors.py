from ctypes import (
    CFUNCTYPE, Structure, c_int, c_char_p, c_uint, c_void_p, cast, POINTER,
    py_object, string_at, c_char, addressof,
)


class TAError(Exception):

    def __init__(self, rv, error_string=None, control_name=None, errlinenum=0,
                 errline=None, errpos=-1):
        self.rv = int(rv)

        if error_string is not None:
            error_string = error_string.decode("utf-8", errors="replace")
        self.error_string = error_string

        self.control_name = control_name
        self.errlinenum = int(errlinenum)

        if errline is not None:
            errline = errline.decode("utf-8", errors="replace")
        self.errline = errline
        self.errpos = int(errpos)

    def __str__(self):
        error = self.rv
        error_string = self.error_string
        errlinenum = self.errlinenum
        errline = self.errline
        errpos = self.errpos

        if error >= 0x100 and error < 0x200:
            s = ("An error with code 0x%03X occurred while parsing the "
                 "argument of option `-X'" % error)
            s += (":" if errline else ".")
            if errline:
                s += "\n  %s" % errline
                if errpos > -1:
                    s += "\n  %s^" % (" "*errpos)
        elif error >= 0x200 and error < 0x300:
            s = "%s:" % self.control_name
            if errlinenum > -1:
                s += "%d:" % errlinenum
            if errpos > -1 and errline:
                s += "%r:" % errpos
            if error_string:
                s += " %s" % error_string
            s += " (0x%02X)" % error
            if errline:
                s += "\n  %s" % errline
                if errpos > -1:
                    s += "\n  %s^" % (" "*errpos)
        elif error >= 0x300 and error < 0x400:
            error -= 0x300
            s = "error while loading the reference font"
            if error_string:
                s += ": %s" % error_string
            s += " (0x%02X)" % error
        else:
            s = "0x%02X" % error
            if error_string:
                s += ": %s" % error_string

        return s


class ErrorData(Structure):

    _fields_ = [
        ("kwargs", py_object),
    ]

    def __init__(self, control_name=None):
        kwargs = dict(control_name=control_name)
        super(ErrorData, self).__init__(kwargs)


@CFUNCTYPE(None, c_int, c_char_p, c_uint, POINTER(c_char), POINTER(c_char),
           c_void_p)
def error_callback(error, error_string, errlinenum, errline, errpos, user):
    e = cast(user, POINTER(ErrorData))[0]
    if not error:
        return
    e.kwargs["error_string"] = error_string
    e.kwargs["errlinenum"] = errlinenum
    if not errline:
        return
    e.kwargs["errline"] = string_at(errline)
    if errpos:
        e.kwargs["errpos"] = (addressof(errpos.contents) -
                              addressof(errline.contents) + 1)
