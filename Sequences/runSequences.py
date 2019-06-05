"""Module containing the class and possible helperfunctions to run a measuring sequence

Author: bklebel (Benjamin Klebel)

"""


# import sys
# import datetime
# import pickle
# import re
import time
# from copy import deepcopy
import numpy as np
# from numpy.polynomial.polynomial import polyfit
# from itertools import combinations_with_replacement as comb

# for sequence commands
import platform
import os
try:
    import winsound
except ImportError:
    pass

# from util import ScanningN


class BreakCondition(Exception):
    """docstring for BreakCondition"""
    pass


def mapping_tofunc(func, start, end, Nsteps):
    """Map a function behaviour to an arbitrary Sequence

    Nsteps must be >= 2!
    applied logic:
        f(t) = c + ((d-c)/(b-a)) * (t-a)
    going between intervals:
        [a, b] --> [c, d]
    nbase == new base sequence
    nbase[0] + ((nbase[-1]-nbase[0])/(cbase[-1]-cbase[0]))*(cbase - cbase[0])

    returns numpy array with the corresponding functional behaviour
    """
    if Nsteps == 1:
        raise AssertionError('mapping_tofunc: Nsteps must be >= 2!')
    # make base 'grid'
    base = np.linspace(1, 100, Nsteps)
    # make calculated base, which represents the respective function
    cbase = func(base)
    # apply the correct mapping to the intended interval
    mapped = start + ((end - start) /
                      (cbase[-1] - cbase[0])) * (cbase - cbase[0])
    return mapped


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

    def execute_chamber(self, operation, **kwargs):
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

    def execute_waiting(self, Temp=False, Field=False, Position=False, Chamber=False, Delay=0, threshold=0.1, **kwargs):
        """wait for specified variables, including a Delay

        target variables are 'self._setpoint_VARIABLE'
            VARIABLE: temp, field, position, chamber
        getfunc functions are 'self.getVARIABLE'
            VARIABLE: Temperature, Field, Position, Chamber

        returns: None
        """
        if Temp:
            self.wait_for(target=self._setpoint_temp,
                          getfunc=self.getTemperature,
                          threshold=threshold)
        if Field:
            self.wait_for(target=self._setpoint_field,
                          getfunc=self.getField,
                          threshold=threshold)
        if Position:
            self.wait_for(target=self._setpoint_position,
                          getfunc=self.getPosition,
                          threshold=threshold)
        if Chamber:
            self.wait_for(target=self._setpoint_chamber,
                          getfunc=self.getChamber, threshold=0)

        delay_start = 0
        delay_step = 0.01
        while delay_start < Delay & self._isRunning:
            time.sleep(delay_step)
            delay_start += delay_step

    def execute_beep(self, length, frequency, **kwargs):
        """beep for a certain time at a certain frequency

        controlelled beep available on windows and linux, not on mac

        length in seconds
        frequency in Hertz
        """
        if platform.system() == 'Windows':
            winsound.Beep(int(frequency), int(length * 1e3))
        if platform.system() == 'Linux':
            answer = os.system(f'beep -f {frequency} -l {length}')
            if answer:
                print('\a')  # ring the command lin bell
                self.message_to_user(
                    'The program "beep" had a problem. Maybe it is not installed?')
        if platform.system() == 'Darwin':
            print('\a')
            self.message_to_user(
                'no easily controllable beep function on mac available')

    def scan_H_execute(self, start, end, Nsteps, SweepRate, SpacingCode, ApproachMode, commands, **kwargs):
        '''execute a Field scan

        '''
        if SpacingCode == 'uniform':
            fields = mapping_tofunc(lambda x: x, start, end, Nsteps)

        elif SpacingCode == 'H*H':
            fields = mapping_tofunc(lambda x: np.square(x), start, end, Nsteps)

        elif SpacingCode == 'logH':
            fields = mapping_tofunc(lambda x: np.log(x), start, end, Nsteps)

        elif SpacingCode == '1/H':
            fields = mapping_tofunc(lambda x: 1 / x, start, end, Nsteps)

        elif SpacingCode == 'H^1/2':
            fields = mapping_tofunc(lambda x: x**0.5, start, end, Nsteps)

        if ApproachMode == 'Linear':
            raise NotImplementedError
            if EndMode == 'persistent':
                raise NotImplementedError
            if EndMode == 'driven':
                raise NotImplementedError
        if ApproachMode == 'No O\'Shoot':
            raise NotImplementedError
            if EndMode == 'persistent':
                raise NotImplementedError
            if EndMode == 'driven':
                raise NotImplementedError
        if ApproachMode == 'Oscillate':
            raise NotImplementedError
            if EndMode == 'persistent':
                raise NotImplementedError
            if EndMode == 'driven':
                raise NotImplementedError
        if ApproachMode == 'Sweep':
            raise NotImplementedError

            if EndMode == 'persistent':
                raise NotImplementedError
            if EndMode == 'driven':
                raise NotImplementedError

    def scan_T_execute(self, start, end, Nsteps, SweepRate, SpacingCode, ApproachMode, commands, **kwargs):

        # building the individual temperatures to scan through
        if SpacingCode == 'uniform':
            temperatures = mapping_tofunc(lambda x: x, start, end, Nsteps)

        elif SpacingCode == '1/T':
            temperatures = mapping_tofunc(lambda x: 1 / x, start, end, Nsteps)

        elif SpacingCode == 'logT':
            temperatures = mapping_tofunc(
                lambda x: np.log(x), start, end, Nsteps)

        # scanning through the temperatures:

        # approaching very slowly:
        if ApproachMode == "No O'Shoot":
            for ct, temp in enumerate(temperatures):
                first = temperatures[0] if ct == 0 else temperatures[ct - 1]
                scantemps = mapping_tofunc(lambda x: np.log(
                    x), start=first, end=temp, Nsteps=10)
                for t in scantemps:
                    self.setTemperature(t)
                    self._setpoint_temp = t
                    self.checkStable_Temp(Temp=t,
                                          direction=np.sign(temp - first),
                                          ApproachMode=ApproachMode)

                    self.execute_waiting(Temp=True, Delay=10)
                self.checkStable_Temp(temp, direction=0)

                for entry in commands:
                    self.execute_sequence_entry(entry)

        # approaching rather fast:
        if ApproachMode == 'Fast':
            for ct, temp in enumerate(temperatures):
                first = temperatures[0] if ct == 0 else temperatures[ct - 1]

                self.setTemperature(temp)
                self.checkStable_Temp(Temp=temp,
                                      direction=np.sign(temp - first),
                                      ApproachMode=ApproachMode)

                for entry in commands:
                    self.execute_sequence_entry(entry)

        # sweeping through the values:
        if ApproachMode == 'Sweep':
            self.scan_T_programSweep(temperatures, SweepRate, SpacingCode)

            for ct, temp in enumerate(temperatures):

                first = temperatures[0] if ct == 0 else temperatures[ct - 1]
                self.checkStable_Temp(Temp=temp,
                                      direction=np.sign(temp - first),
                                      ApproachMode=ApproachMode)

                for entry in commands:
                    self.execute_sequence_entry(entry)

    def wait_for(self, getfunc, target, threshold=0.1, additional_condition=True):
        """repeatedly check whether the temperature was reached,
            given the respective threshold, return once it has
            produce a possibility to abort the sequence, through
            repeated check for value, for breaking condition, and sleeping
        """
        value_now = getfunc()

        while (abs(value_now - target) > threshold) & additional_condition:
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

    @staticmethod
    def message_to_user(message):
        """deliver a message to a user in some way

        default is printing to the command line
        may be overriden!
        """
        print(message)

    def scan_T_programSweep(self, temperatures, SweepRate, SpacingCode='uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep temperatures
        """
        raise NotImplementedError

    def setTemperature(self, temperature):
        """
            Method to be overridden by a child class
            here, all logic which is needed to go to a certain temperature
            needs to be implemented.
            TODO: override method
        """
        self._setpoint_temp = temperature
        super().setTemperature(temperature=temperature)
        # raise NotImplementedError

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
