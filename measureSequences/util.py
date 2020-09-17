"""
Utility module
Functions:
    ScanninN:
        utility to build a linear spaced sequence based on
            a starting point
            an end point
            the number of steps
        returns the sequence and the stepsize
        could be shortened by use of np.linspace
    ScanninSize
        utility to build a linear spaced sequence based on
            a starting point
            an end point
            the stepsize
        returns the sequence and the number of steps
        could be shortened by use of np.linspace

Classes:

    Window_ui: a window class, which loads the UI definitions from a spcified .ui file,
        emits a signal upon closing
    Author(s):
        bklebel (Benjamin Klebel)
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets
from PyQt5.uic import loadUi

import functools
# import inspect
import logging

logger = logging.getLogger(
    'measureSequences.utility')
logger.addHandler(logging.NullHandler())


def ExceptionSignal(thread, func, e_type, err):
    """Emit assertion-signal with relevant information"""
    string = "{}: {}: {}: {}".format(
        thread.__class__.__name__, func.__name__, e_type, err.args[0]
    )
    return string


def ExceptionHandling(func):
    @functools.wraps(func)
    def wrapper_ExceptionHandling(*args, **kwargs):
        # if inspect.isclass(type(args[0])):
        # thread = args[0]
        try:
            return func(*args, **kwargs)
        except AssertionError as e:
            s = ExceptionSignal(args[0], func, "Assertion", e)
            # thread.logger.exception(s)
            args[0]._logger.error(s)
            args[0]._logger.exception(e)

        except TypeError as e:
            s = ExceptionSignal(args[0], func, "Type", e)
            # thread.logger.exception(s)
            args[0]._logger.error(s)
            args[0]._logger.exception(e)

        except KeyError as e:
            s = ExceptionSignal(args[0], func, "Key", e)
            # thread.logger.exception(s)
            args[0]._logger.error(s)
            args[0]._logger.exception(e)

        except IndexError as e:
            s = ExceptionSignal(args[0], func, "Index", e)
            # thread.logger.exception(s)
            args[0]._logger.error(s)
            args[0]._logger.exception(e)

        except ValueError as e:
            s = ExceptionSignal(args[0], func, "Value", e)
            # thread.logger.exception(s)
            args[0]._logger.error(s)
            args[0]._logger.exception(e)

        except AttributeError as e:
            s = ExceptionSignal(args[0], func, "Attribute", e)
            # thread.logger.exception(s)
            args[0]._logger.error(s)
            args[0]._logger.exception(e)

        except NotImplementedError as e:
            s = ExceptionSignal(args[0], func, "NotImplemented", e)
            # thread.logger.exception(s)
            args[0]._logger.error(s)
            args[0]._logger.exception(e)
            # e.args = [str(e)]

        except OSError as e:
            s = ExceptionSignal(args[0], func, "OSError", e)
            args[0]._logger.error(s)
            args[0]._logger.exception(e)
        # else:
        #     args[0]._logger.warning('There is a bug!! ' + func.__name__)

    return wrapper_ExceptionHandling


def ScanningN(start, end, N):
    """utility function for building linspaced number-sequences"""
    # N += 1
    stepsize = abs(end - start) / (N - 1)
    stepsize = abs(stepsize) if start < end else -abs(stepsize)
    seq = []
    for __ in range(int(N)):
        seq.append(start)
        start += stepsize
    return seq, stepsize


def ScanningSize(start, end, parameter):
    """utility function for building linspaced number-sequences"""
    stepsize = abs(parameter) if start < end else -abs(parameter)
    seq = []
    if start < end:
        while start < end:
            seq.append(start)
            start += stepsize
    else:
        while start > end:
            seq.append(start)
            start += stepsize
    N = len(seq)
    return seq, N


class Window_ui(QtWidgets.QWidget):
    """Class for a small window, the UI of which is loaded from the .ui file
        emits a signal when being closed
    """

    sig_closing = pyqtSignal()

    def __init__(self, ui_file=None, **kwargs):
        if 'lock' in kwargs:
            del kwargs['lock']
        super().__init__(**kwargs)
        if ui_file is not None:
            loadUi(ui_file, self)

    def closeEvent(self, event):
        # do stuff
        self.sig_closing.emit()
        event.accept()  # let the window close
