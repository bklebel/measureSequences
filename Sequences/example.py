
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
# from PyQt5.QtCore import QTimer


from runSequences import Sequence_runner
from CryostatGUI.util import AbstractEventhandlingThread


class Sequence_CryostatGUI(Sequence_runner, AbstractEventhandlingThread):
    """docstring for Sequence_CryostatGUI"""

    sig_aborted = pyqtSignal()

    def __init__(self, mainthread, **kwargs):
        super(Sequence_CryostatGUI, self).__init__(**kwargs)
        self.mainthread = mainthread
        self.dataLock = mainthread.dataLock

    def setTemperatures_hard(self, VTI, Sample):
        self.mainthread.threads['control_ITC'][0].gettoset_Temperature(VTI)
        self.mainthread.threads['control_ITC'][0].setTemperature()

        self.mainthread.threads['control_LakeShore350'][
            0].gettoset_Temp_K(Sample)
        self.mainthread.threads['control_LakeShore350'][0].setTemp_K()
        self.mainthread.threads['control_LakeShore350'][0].setStatusRamp(False)

    @pyqtSlot()
    def setTempVTIOffset(self, offset):
        self.temp_VTI_offset = offset

    def scan_T_programSweep(self, temperatures, SweepRate):
        """
            program sweep for VTI
            program sweep for LakeShore
        """
        raise NotImplementedError

    def getTemperature(self):
        """
            Method to be overriden by child class
            implement measuring the temperature used for control

            returns: temperature as a float
        """
        with self.dataLock:
            return self.mainthread.data['LakeShore350']['Sensor_1_K']

    def getField(self):
        """
            Method to be overriden by child class
            implement measuring the field

            returns: Field as a float
        """
        raise NotImplementedError

    def checkStable_Temp(self, Temp, direction=0):
        """
            wait for the temperature to stabilize
            must block until the temperature has arrived at the specified point!
            the optional parameter can be whether the corresponding value should
            currently be rising or falling
            direction = 0: default, no information
            direction =  1: temperature should be rising
            direction = -1: temperature should be falling
        """
        raise NotImplementedError
