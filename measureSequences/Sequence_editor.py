"""Module containing an implementation of the Sequence editor
this is only to display the parsed sequence, though there are elements which could be used in a full sequence editor

Classes:
    Window_ChangeDataFile
    Window_waiting
    Window_Tscan
    Sequence_builder: sequence editor class
        currently it just displays the parsed sequence
        could be enhanced to enable writing sequences

Author: bklebel (Benjamin Klebel)

"""

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.uic import loadUi

from copy import deepcopy
import sys
import threading

from .util import Window_ui
from .util import ExceptionHandling
from .Sequence_parsing import Sequence_parser

from .qlistmodel import SequenceListModel
from .qlistmodel import ScanListModel

import pkg_resources


class Window_ChangeDataFile(QtWidgets.QDialog):
    """docstring for Window_waiting"""

    sig_accept = pyqtSignal(dict)
    sig_reject = pyqtSignal()

    def __init__(self, ui_file=pkg_resources.resource_filename(__name__, '.\\configurations\\Sequence_change_datafile.ui')):
        """build ui, build dict, connect to signals"""
        super().__init__()
        loadUi(ui_file, self)

        self.conf = dict(typ='change datafile', new_file_data='',
                         mode='',
                         DisplayText='')
        self.lineFileLocation.setText(self.conf['new_file_data'])
        self.lineFileLocation.textChanged.connect(
            lambda value: self.setValue('new_file_data', value))
        self.pushBrowse.clicked.connect(self.Browse)
        self.comboMode.activated['int'].connect(self.setMode)

        self.buttonDialog.accepted.connect(self.acc)
        self.buttonDialog.rejected.connect(self.close)

    def acc(self):
        """if not rejected, emit signal with configuration and accept"""
        # if not self.conf['Temp'] and not self.conf['Field']:
        #     self.reject()
        #     return
        self.sig_accept.emit(deepcopy(self.conf))
        self.accept()

    def setValue(self, parameter, value):
        """set any kind of value in the conf dict"""
        self.conf[parameter] = value

    def Browse(self):
        """open File Saving Dialog, to choose the datafile, set datafile in conf dict"""
        new_file_data, __ = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose Datafile',
                                                                  'c:\\', "Datafiles (*.dat)")
        self.setValue('new_file_data', new_file_data)
        self.lineFileLocation.setText(self.conf['new_file_data'])

    def setMode(self, modeint):
        pass


class Window_waiting(QtWidgets.QDialog):
    """docstring for Window_waiting"""

    sig_accept = pyqtSignal(dict)
    sig_reject = pyqtSignal()

    def __init__(self, ui_file=pkg_resources.resource_filename(__name__, '.\\configurations\\sequence_waiting.ui')):
        """build ui, build dict, connect to signals"""
        super().__init__()
        loadUi(ui_file, self)

        self.conf = dict(typ='Wait', Temp=False, Field=False, Delay=0)
        self.check_Temp.toggled.connect(
            lambda value: self.setValue('Temp', value))
        self.check_Field.toggled.connect(
            lambda value: self.setValue('Field', value))
        self.spin_delayseconds.valueChanged.connect(
            lambda value: self.setValue('Delay', value))
        self.buttonDialog.accepted.connect(self.acc)
        self.buttonDialog.rejected.connect(self.close)

    def acc(self):
        """if not rejected, emit signal with configuration and accept"""
        # if not self.conf['Temp'] and not self.conf['Field']:
        #     self.reject()
        #     return
        self.sig_accept.emit(deepcopy(self.conf))
        self.accept()

    def setValue(self, parameter, value):
        """set any kind of value in the conf dict"""
        self.conf[parameter] = value

    # def accepted(self):
    #     self.sig_accept.emit(self.conf)


class Window_Tscan(QtWidgets.QDialog):
    """docstring for Window_Tscan"""

    sig_accept = pyqtSignal(dict)
    sig_reject = pyqtSignal()
    sig_updateScanListModel = pyqtSignal(dict)

    def __init__(self, ui_file=pkg_resources.resource_filename(__name__, "configurations\\sequence_scan_temperature.ui"), **kwargs):
        super().__init__(**kwargs)
        loadUi(ui_file, self)

        QTimer.singleShot(0, self.initialisations)
        self.dictlock = threading.Lock()

    def initialisations(self):

        # BUGS BUGS BUGS

        self.conf = dict(typ='scan_T', measuretype='RES')
        self.__scanconf = dict(
            start=0,
            end=0,
            Nsteps=None,
            SizeSteps=None)
        self.putin_start = False
        self.putin_end = False
        self.putin_N = False
        self.putin_Size = False
        self.model = ScanListModel(self, 0, 0, 0, 0)
        self.listTemperatures.setModel(self.model)

        self._LCD_stepsize = 0
        self._LCD_Nsteps = 0
        self.update_lcds()

        self.buttonOK.clicked.connect(self.acc)
        self.buttonCANCEL.clicked.connect(self.close)

        self.comboSetTempramp.activated['int'].connect(self.setRampCondition)
        self.spinSetRate.valueChanged.connect(self.setSweepRate)

        self.spinSetTstart.valueChanged.connect(self.setTstart)
        self.spinSetTstart.editingFinished.connect(
            lambda: self.update_list(None, None))

        self.spinSetTend.valueChanged.connect(self.setTend)
        self.spinSetTend.editingFinished.connect(
            lambda: self.update_list(None, None))

        # self.spinSetNsteps.valueChanged.connect(lambda value: self.printing('spinSetNsteps: valueChanged: {}'.format(value)))
        # self.spinSetNsteps.editingFinished.connect(lambda: self.printing('spinSetNsteps: editingFinished'))
        # self.model.sig_Nsteps.connect(lambda value: self.printing('model: sig_Nsteps: {}'.format(value)))

        self.spinSetNsteps.valueChanged.connect(self.setN)
        self.spinSetNsteps.editingFinished.connect(
            lambda: self.setLCDNsteps(self.__scanconf['Nsteps']))
        self.spinSetNsteps.editingFinished.connect(
            lambda: self.update_list(1, 0))
        self.model.sig_Nsteps.connect(lambda value: self.setLCDNsteps(value))
        # self.model.sig_Nsteps.connect(self.spinSetNsteps.setValue)

        # self.spinSetSizeSteps.valueChanged.connect(lambda value: self.printing('spinSetSizeSteps: valueChanged: {}'.format(value)))
        # self.model.sig_stepsize.connect(lambda value: self.printing('model: sig_stepsize: {}'.format(value)))
        # self.spinSetSizeSteps.editingFinished.connect(lambda: self.printing('spinSetSizeSteps: editingFinished'))

        self.spinSetSizeSteps.valueChanged.connect(self.setSizeSteps)
        self.spinSetSizeSteps.editingFinished.connect(
            lambda: self.setLCDstepsize(self.__scanconf['SizeSteps']))
        self.spinSetSizeSteps.editingFinished.connect(
            lambda: self.update_list(0, 1))
        self.model.sig_stepsize.connect(
            lambda value: self.setLCDstepsize(value))
        # self.model.sig_stepsize.connect(self.spinSetSizeSteps.setValue)

    def update_list(self, Nsteps, SizeSteps):
        if not (self.putin_start and self.putin_end):
            return
        # if not (self.putin_Size or self.putin_N):
        #     return
        if Nsteps:
            # self.__scanconf['Nsteps'] = Nsteps
            with self.dictlock:
                self.__scanconf['SizeSteps'] = None

        if SizeSteps:
            with self.dictlock:
                self.__scanconf['Nsteps'] = None
            # self.__scanconf['SizeSteps'] = None
        # print(self.__scanconf)
        self.sig_updateScanListModel.emit(deepcopy(self.__scanconf))

    def setTstart(self, Tstart):
        with self.dictlock:
            self.__scanconf['start'] = Tstart
        self.putin_start = True
        self.conf.update(self.__scanconf)

    def setTend(self, Tend):
        with self.dictlock:
            self.__scanconf['end'] = Tend
        self.putin_end = True
        self.conf.update(self.__scanconf)

    def setN(self, N):
        with self.dictlock:
            self.__scanconf['Nsteps'] = N
        # self.putin_N = True
        self.conf.update(self.__scanconf)

    def setSizeSteps(self, stepsize):
        with self.dictlock:
            self.__scanconf['SizeSteps'] = stepsize
        # self.putin_Size = True
        self.conf.update(self.__scanconf)

    def setLCDstepsize(self, value):
        self._LCD_stepsize = value
        self.__scanconf['SizeSteps'] = value

    def setLCDNsteps(self, value):
        self._LCD_Nsteps = value
        self.__scanconf['Nsteps'] = value

    @staticmethod
    def printing(message):
        print(message)

    def setRampCondition(self, value):
        with self.dictlock:
            self.conf['RampCondition'] = value
            # 0 == Stabilize
            # 1 == Sweep
            # CHECK THIS

            # if value == 0:
            #     self.conf['RampCondition'] = 'Stabilize'
            # elif value == 1:
            #     self.conf['RampCondition'] = 'Sweep'

    def setSweepRate(self, value):
        with self.dictlock:
            self.conf['SweepRate'] = value

    def update_lcds(self):
        try:
            self.lcdStepsize.display(self._LCD_stepsize)
            self.lcdNsteps.display(self._LCD_Nsteps)
            # self.listTemperatures.repaint()
        finally:
            QTimer.singleShot(1e2, self.update_lcds)

    def acc(self):
        """if not rejected, emit signal with configuration and accept"""

        self.conf['sequence_temperature'] = self.model.pass_data()

        self.sig_accept.emit(deepcopy(self.conf))
        self.accept()


class Sequence_builder(Window_ui, Sequence_parser):
    """docstring for sequence_builder"""

    sig_runSequence = pyqtSignal(list)
    sig_abortSequence = pyqtSignal()
    sig_assertion = pyqtSignal(str)
    sig_readSequence = pyqtSignal()
    sig_clearedSequence = pyqtSignal()

    def __init__(self, parent=None, **kwargs):
        super().__init__(
            ui_file=pkg_resources.resource_filename(__name__, "configurations\\sequence.ui"), **kwargs)

        # self.listSequence.sig_dropped.connect(lambda value: self.dropreact(value))
        self.__name__ = 'Sequence_builder'

        QTimer.singleShot(0, self.initialize_all_windows)
        # QTimer.singleShot(
        # 0, lambda: self.initialize_sequence(self.sequence_file))

        # self.sequence_file = sequence_file
        # self.textnesting = textnesting
        self.model = SequenceListModel()
        self.listSequence.setModel(self.model)

        self.treeOptions.itemDoubleClicked[
            'QTreeWidgetItem*', 'int'].connect(lambda value: self.addItem_toSequence(value))
        self.pushSaving.clicked.connect(self.saving)
        self.pushBrowse.clicked.connect(self.window_FileDialogSave)
        self.pushOpen.clicked.connect(self.window_FileDialogOpen)
        self.lineFileLocation.setText(self.sequence_file)
        self.lineFileLocation.textChanged.connect(
            lambda value: self.change_file_location(value))
        self.pushClear.clicked.connect(self.init_data)

        self.Button_RunSequence.clicked.connect(self.running_sequence)
        self.Button_AbortSequence.clicked.connect(self.aborting_sequence)

    def init_data(self):
        self.model.clear_all()
        self.initialize_sequence('')
        self.sig_clearedSequence.emit()

    @ExceptionHandling
    def running_sequence(self):
        self.sig_runSequence.emit(deepcopy(self.data))
        self.Button_AbortSequence.setEnabled(True)

    @ExceptionHandling
    def aborting_sequence(self):
        self.sig_abortSequence.emit()
        self.Button_AbortSequence.setEnabled(False)

    # @ExceptionHandling
    # def addItem_toSequence(self, text):
    #     """
    #         depending on the Item clicked, add the correct Item to the model,
    #         which may involve executing a certain window
    #     """
    #     if text.text(0) == 'Wait':
    #         # self.window_waiting.show()
    #         self.window_waiting.exec_()  # if self.window_waiting.exec_():
    #         # print('success')

    #     if text.text(0) == 'Resistivity vs Temperature':
    #         # here the Tscan comes
    #         self.window_Tscan.exec_()

    #     if text.text(0) == 'Chain Sequence':
    #         new_file_seq, __ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Sequence',
    #                                                                  'c:\\', "Sequence files (*.seq)")
    #         data = dict(typ='chain sequence', new_file_seq=new_file_seq,
    #                         DisplayText='Chain sequence: {}'.format(new_file_seq))
    #         self.model.addItem(data)
    #         QTimer.singleShot(1, lambda: self.listSequence.repaint())

    #     if text.text(0) == 'Change Data File':
    #         raise NotImplementedError
    #     if text.text(0) == 'Set Temperature':
    #         raise NotImplementedError
    #     if text.text(0) == 'Set Field':
    #         raise NotImplementedError
    #     if text.text(0) == 'Resistivity vs Field':
    #         raise NotImplementedError
    #     if text.text(0) == 'Shutdown Temperature Control':
    #         raise NotImplementedError

    # @ExceptionHandling
    # def addWaiting(self, data):
    #     string = self.displaytext_waiting(data)
    #     data.update(dict(DisplayText=string))
    #     # self.listSequence.addItem(string)
    #     self.model.addItem(data)
    #     QTimer.singleShot(1, lambda: self.listSequence.repaint())
    #     # QTimer.singleShot(10, self.model.)

    # @ExceptionHandling
    # def addTscan(self, data):
    #     string = self.displaytext_scan_T(data)
    #     data.update(dict(DisplayText=string))
    #     self.model.addItem(data)
    #     QTimer.singleShot(1, lambda: self.listSequence.repaint())

    # def addChangeDataFile(self, data):
    #     pass

    # @staticmethod
    # def printing(self, data):
    #     print(data)

    # def saving(self):
    #     with open(self.sequence_file_p, 'wb') as output:
    #         pickle.dump(self.data, output, pickle.HIGHEST_PROTOCOL)
    #     with open(self.sequence_file_json, 'w') as output:
    #         output.write(json.dumps(self.data))

    @ExceptionHandling
    def initialize_all_windows(self):
        self.initialise_window_waiting()
        self.initialise_window_Tscan()
        self.initialise_window_ChangeDataFile()

    def initialise_window_waiting(self):
        self.window_waiting = Window_waiting()
        self.window_waiting.sig_accept.connect(
            lambda value: self.addWaiting(value))

    def initialise_window_Tscan(self):
        self.window_Tscan = Window_Tscan()
        self.window_Tscan.sig_accept.connect(
            lambda value: self.addTscan(value))

    def initialise_window_ChangeDataFile(self):
        self.Window_ChangeDataFile = Window_ChangeDataFile()
        self.Window_ChangeDataFile.sig_accept.connect(
            lambda value: self.addChangeDataFile(value))

    # @ExceptionHandling
    def window_FileDialogSave(self):
        self.sequence_file_json, __ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save As',
                                                                            'c:\\', "Serialised (*.json)")
        # last option is a file specifier, like 'Sequence Files (*.seq)'
        self.lineFileLocation_serialised.setText(self.sequence_file_json)
        self.sequence_file_p = self.sequence_file_json[:-4] + 'pkl'

    # @ExceptionHandling
    def window_FileDialogOpen(self):
        sequence_file, __ = QtWidgets.QFileDialog.getOpenFileName(self, 'Save As',
                                                                       'c:\\', "Sequence files (*.seq)")
        if sequence_file:
            # print(sequence_file)
            self.init_data()
            self.sequence_file = sequence_file
            self.lineFileLocation.setText(self.sequence_file)
            self.initialize_sequence(self.sequence_file)

    @ExceptionHandling
    def initialize_sequence(self, sequence_file):
        """build & run the sequence parsing, add items to the display model"""
        super().initialize_sequence(sequence_file)
        for command in self.textsequence:
            self.model.addItem(command)
        if sequence_file:
            self.sig_readSequence.emit()


if __name__ == '__main__':

    file = 'SEQ_20180914_Tscans.seq'
    file = 'Tempscan.seq'
    file = None
    # file = 't.seq'

    app = QtWidgets.QApplication(sys.argv)
    form = Sequence_builder(file)
    form.show()
    sys.exit(app.exec_())
