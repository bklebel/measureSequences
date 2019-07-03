"""
Utility module


Classes:

    Window_ui: a window class, which loads the UI definitions from a spcified .ui file,
        emits a signal upon closing
    Author(s):
        bklebel (Benjamin Klebel)
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets
from PyQt5.uic import loadUi


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
