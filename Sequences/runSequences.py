"""Module containing the class and possible helperfunctions to run a measuring sequence



    Author: bklebel (Benjamin Klebel)

"""


# import sys
# import datetime
# import pickle
# import re
import time
from copy import deepcopy
import numpy as np
from numpy.polynomial.polynomial import polyfit
# from itertools import combinations_with_replacement as comb

# for sequence commands
import platform
import os
try:
    import winsound
except ImportError:
    pass


def ScanningN(start, end, N):
    N += 1
    stepsize = abs(end - start) / (N - 1)
    stepsize = abs(stepsize) if start < end else -abs(stepsize)
    seq = []
    for __ in range(int(N)):
        seq.append(start)
        start += stepsize
    return seq, stepsize


def ScanningSize(start, end, parameter):
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


class BreakCondition(Exception):
    """docstring for BreakCondition"""
    pass


class Sequence_runner(object):
    """docstring for Sequence_Thread"""

    def __init__(self, lock, sequence, **kwargs):
        super().__init__(**kwargs)
        self._isRunning = True
        self.sequence = sequence
        self.lock = lock
        # self.mainthread = mainthread

        # self.threshold_Temp = 0.1
        # self.threshold_Field = 0.1

        # self.temp_VTI_offset = 5

        self.sensor_control = None  # needs to be set!
        self.sensor_sample = None   # needs to be set!

    def running(self):
        # self.temp_setpoint = 0
        with self.lock:
            try:
                for entry in self.sequence:
                    self.execute_sequence_entry(entry)
            except BreakCondition:
                return 'Aborted!'

    def execute_sequence_entry(self, entry):
        if self._isRunning:

            if entry['typ'] == 'Shutdown':
                self.Shutdown()
            if entry['typ'] == 'Wait':
                self.execute_waiting(**entry)
            if entry['typ'] == 'chamber_operation':
                self.execute_chamber(**entry)
            if entry['typ'] == 'beep':
                self.execute_beep(**entry)
            if entry['typ'] == 'scan_T':
                self.scan_T_execute(**entry)

            if entry['typ'] == 'scan_H':
                # has yet to be implemented!
                pass
            if entry['typ'] == 'scan_time':
                # has yet to be implemented!
                pass
            if entry['typ'] == 'scan_position':
                # has yet to be implemented!
                pass

            if entry['typ'] == 'set_T':
                # has yet to be implemented!
                pass
            if entry['typ'] == 'set_Field':
                # has yet to be implemented!
                pass
            if entry['typ'] == 'chain sequence':
                # has yet to be implemented!
                pass
            if entry['typ'] == 'res_change_datafile':
                # has yet to be implemented!
                pass
            if entry['typ'] == 'res_datafilecomment':
                # has yet to be implemented!
                pass
            if entry['typ'] == 'res_measure':
                # has yet to be implemented!
                pass
            if entry['typ'] == 'res_scan_excitation':
                # has yet to be implemented!
                pass

            if entry['typ'] == 'remark':
                # true pass statement
                pass
        else:
            raise BreakCondition

    def execute_chamber(self, operation):
        """execute the specified chamber operation"""
        if operation == 'seal immediate':
            self.execute_chamber_seal()

        if operation == 'purge then seal':
            self.execute_chamber_purge()
            self.execute_chamber_seal()

        if operation == 'vent then seal':
            self.execute_chamber_vent()
            self.execute_chamber_seal()

        if operation == 'pump continuous':
            self.execute_chamber_continuous('pumping')

        if operation == 'vent continuous':
            self.execute_chamber_continuous('venting')

        if operation == 'high vacuum':
            self.execute_chamber_high_vacuum()

    def execute_waiting(self, Temp, Field, Position, Chamber, Delay, **kwargs):
        if Temp:
            self.wait_for(target=self.setpoint_temp,
                          getfunc=self.getTemperature)
        if Field:
            self.wait_for(target=self.setpoint_field,
                          getfunc=self.getField)
        if Position:
            self.wait_for(target=self.setpoint_position,
                          getfunc=self.getPosition)
        if Chamber:
            self.wait_for(target=self.setpoint_chamber,
                          getfunc=self.getChamber, threshold=0)
        time.sleep(Delay)

    def execute_beep(self, length, frequency):
        """beep for a certain time at a certain frequency

        controlelled beep available on windows and linux, not on mac

        length in seconds
        frequency in Hertz
        """
        if platform.system() == 'Windows':
            winsound.Beep(frequency, length * 1e3)
        if platform.system() == 'Linux':
            answer = os.system('beep -f 165.4064 -l 1000')
            if answer:
                print('\a')  # ring the command lin bell
                self.message_to_user(
                    'The program "beep" had a problem. Maybe it is not installed?')
        if platform.system() == 'Darwin':
            print('\a')
            self.message_to_user(
                'no easily controllable beep function on mac available')

    @staticmethod
    def message_to_user(message):
        """deliver a message to a user in some way

        default is printing to the command line
        """
        print(message)

    def scan_T_execute(self, start, end, Nsteps, SweepRate, SpacingCode, ApproachMode, commands, **kwargs):

        temperatures, stepsize = ScanningN(start=start,
                                           end=end,
                                           N=Nsteps)

        if ApproachMode == "No O'Shoot":
            raise NotImplementedError

        if ApproachMode == 'Fast':
            for temp_setpoint_sample in temperatures:
                self.temp_setpoint = temp_setpoint_sample
                temp_setpoint_VTI = temp_setpoint_sample - self.temp_VTI_offset
                temp_setpoint_VTI = 4.3 if temp_setpoint_VTI < 4.3 else temp_setpoint_VTI

                self.setTemperatures_hard(VTI=temp_setpoint_VTI,
                                          Sample=temp_setpoint_sample)

                self.check_Temp_in_Scan(temp_setpoint_sample)

                for entry in commands:
                    self.execute_sequence_entry(entry)

        if ApproachMode == 'Sweep':
            pass
            # program VTI sweep, in accordance to the VTI Offset
            self.scan_T_programSweep(temperatures, SweepRate)
            # set temp and RampRate for Lakeshore
            # if T_sweepentry is arrived: do stuff
            for temp in temperatures:
                # do checking and so on
                for entry in commands:
                    self.execute_sequence_entry(entry)

    def wait_for(self, getfunc, target, threshold=0.1):
        """repeatedly check whether the temperature was reached,
            given the respective threshold, return once it has
            produce a possibility to abort the sequence, through
            repeated check for value, for breaking condition, and sleeping
        """
        value_now = getfunc()

        while abs(value_now - target) > threshold:
            # check for break condition
            if not self._isRunning:
                raise BreakCondition
            # check for value
            value_now = getfunc()
            # sleep
            time.sleep(0.1)

    def stop(self):
        """stop the sequence execution by setting self._isRunning to False"""
        self._isRunning = False

    def scan_T_programSweep(self, temperatures, SweepRate):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep
            temperatures
        """
        raise NotImplementedError

    def setTemperature(self, temperature):
        """
            Method to be overridden by a child class
            here, all logic which is needed to go to a certain temperature
            needs to be implemented.
            TODO: override method
        """
        raise NotImplementedError

    def getTemperature(self):
        """Read the temperature

        Method to be overriden by child class
        implement measuring the temperature used for control
        returns: temperature as a float
        """
        raise NotImplementedError

    def getPosition(self):
        """
            Method to be overriden by child class
            implement checking the position

            returns: position as a float
        """
        raise NotImplementedError

    def getField(self):
        """Read the Field

        Method to be overriden by child class
        implement measuring the field
        returns: Field as a float
        """
        raise NotImplementedError

    def getChamber(self):
        """Read the Chamber status

        Method to be overriden by child class
        implement measuring whether the chamber is ready
        returns: chamber status
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

    def Shutdown(self):
        """Shut down instruments to a standby-configuration"""
        raise NotImplementedError

    def execute_chamber_purge(self):
        """purge the chamber

        must block until the chamber is purged
        """
        raise NotImplementedError

    def execute_chamber_vent(self):
        """vent the chamber

        must block until the chamber is vented
        """
        raise NotImplementedError

    def execute_chamber_seal(self):
        """seal the chamber

        must block until the chamber is sealed
        """
        raise NotImplementedError

    def execute_chamber_continuous(self, action):
        """pump or vent the chamber continuously"""
        if action == 'pumping':
            raise NotImplementedError
        if action == 'venting':
            raise NotImplementedError

    def execute_chamber_high_vacuum(self):
        """pump the chamber to high vacuum

        must block until the chamber is  at high vacuum
        """
        raise NotImplementedError
