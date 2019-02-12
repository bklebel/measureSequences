
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
# from PyQt5.QtCore import QTimer

import numpy as np
from threading import Lock
import json

from runSequences import Sequence_runner
# from CryostatGUI.util import AbstractEventhandlingThread


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

    def scan_T_programSweep(self, temperatures, SweepRate, SpacingCode):
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

    def setTemperature(self, temperature):
        """set Temperature"""
        temp_setpoint_sample = temperature
        temp_setpoint_VTI = temp_setpoint_sample - self.temp_VTI_offset
        temp_setpoint_VTI = 4.3 if temp_setpoint_VTI < 4.3 else temp_setpoint_VTI

        self.setTemperatures_hard(VTI=temp_setpoint_VTI,
                                  Sample=temp_setpoint_sample)


class Dummy_Functions(object):
    """docstring for Functions"""

    def __init__(self):
        super().__init__()

    def setTemperature(self, temperature):
        """
            Method to be overridden by a child class
            here, all logic which is needed to go to a certain temperature
            needs to be implemented.
            TODO: override method
        """
        print('setTemperature :: temp = {}'.format(temperature))


class Dummy(Sequence_runner, Dummy_Functions):
    """docstring for Dummy"""

    def __init__(self, filename='', **kwargs):
        if filename:
            with open(filename) as f:
                seq = json.load(f)
            super().__init__(sequence=seq, **kwargs)
        else:
            super().__init__(sequence=seq, **kwargs)

    def checkStable_Temp(self, Temp, direction=0, ApproachMode='Sweep'):
        """wait for the temperature to stabilize

        param: Temp:
            the temperature which needs to be arrived to continue
            function must block until the temperature has arrived at this temp!

        param: direction:
            indicates whether the 'Temp' should currently be
                rising or falling
                direction =  0: default, no information
                direction =  1: temperature should be rising
                direction = -1: temperature should be falling

        param: Approachmode:
            specifies the mode of approach in the scan this function is called
        """

        print('checkstableTemp :: Temp: {} is stable!, ApproachMode = {}, direction = {}'.format(
            Temp, ApproachMode, direction))

    def scan_T_programSweep(self, temperatures, SweepRate, SpacingCode='uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep temperatures
        """
        print('scan_T_programSweep :: temps: {}, Rate: {}, SpacingCode: {}'.format(
            temperatures, SweepRate, SpacingCode))

    def getTemperature(self):
        """Read the temperature

        Method to be overriden by child class
        implement measuring the temperature used for control
        returns: temperature as a float
        """
        print('getTemperature :: returning random value')
        return np.random.rand() * 300


if __name__ == '__main__':
    dummy = Dummy(lock=Lock(), filename='beep.json')
    # QTimer.singleShot(3*1e3, lambda: dummy.stop())
    dummy.running()
