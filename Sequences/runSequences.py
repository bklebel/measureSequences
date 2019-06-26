"""Module containing the class and possible helperfunctions to run a measuring sequence

Author: bklebel (Benjamin Klebel)

"""


# import sys
# import datetime
# import pickle
# import re
import time
import threading
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


def mapping_tofunc(func, start: float, end: float, Nsteps: int) -> type(np.array()):
    """Map a function behaviour to an arbitrary Sequence

    Nsteps must be >= 2!

    applied logic:
        f(t) = c + ((d-c)/(b-a)) * (t-a)
    for going between intervals:
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

    def __init__(self, lock, sequence: list, thresholds_waiting: dict = dict(Temp = 0.1, Field = 0.1, Position = 0.1), **kwargs):
        super().__init__(**kwargs)
        self._isRunning = True
        self.sequence = sequence
        self.lock = lock
        # self.mainthread = mainthread

        # self.threshold_Temp = 0.1
        # self.threshold_Field = 0.1
        self.thresholds_waiting = thresholds_waiting

        # self.temp_VTI_offset = 5

        self.sensor_control = None  # needs to be set!
        self.sensor_sample = None   # needs to be set!

        self.scan_time_force = False

    def running(self):
        # self.temp_setpoint = 0
        with self.lock:
            try:
                self.executing_commands(self.sequence)
            except BreakCondition:
                return 'Aborted!'

    def executing_commands(self, commands):
        for entry in commands:
            try:
                self.execute_sequence_entry(entry)
            except NotImplementedError as e:
                self.message_to_user(f'An error occured: {e}. Did you maybe' +
                                     ' try to call a function/method which' +
                                     ' needs to be manually overriden?')
            except AttributeError as e:
                self.message_to_user(f'An error occured: {e}. Did you maybe' +
                                     ' try to call a function/method which' +
                                     ' needs to be manually injected?')

    def check_running(self):
        if not self._isRunning:
            raise BreakCondition

    def stop(self):
        """stop the sequence execution by setting self._isRunning to False"""
        self._isRunning = False

    def execute_sequence_entry(self, entry):
        self.check_running()

        if entry['typ'] == 'Shutdown':
            self.Shutdown()
        if entry['typ'] == 'Wait':
            self.execute_waiting(**entry)
        if entry['typ'] == 'chamber_operation':
            self.execute_chamber(**entry)
        if entry['typ'] == 'beep':
            self.execute_beep(**entry)
        if entry['typ'] == 'scan_T':
            self.execute_scan_T(**entry)
        if entry['typ'] == 'scan_H':
            self.execute_scan_H(**entry)
        if entry['typ'] == 'scan_time':
            self.execute_scan_time(**entry)

        if entry['typ'] == 'scan_position':
            # has yet to be implemented!
            pass

        if entry['typ'] == 'set_T':
            self.execute_set_Temperature(**entry)

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
            self.execute_remark(entry['DisplayText'])

    def execute_scan_time(self, time: float, Nsteps: int, SpacingCode: str, commands: list, **kwargs) -> None:
        """execute a Time scan
        The intervals t between starting to invoke all commands in the list
        are:
        if self.scan_time_force is False:
            t = max(set interval time, duration of all actions in command list),
            where 'set interval time' is the time given
                by the scan_time functionality

            and 'duration of all actions in command list' refers to
                the time it takes to conduct everything which is defined
                in the list of commands given
        else:
            exactly the set interval times
            However, in this case, all commands are executed in a
                different thread, to ensure all are correctly started
                TODO: test whether this actually works
        """

        if SpacingCode == 'uniform':
            times = mapping_tofunc(lambda x: x, 0, time, Nsteps)

        elif SpacingCode == 'ln(t)':
            times = mapping_tofunc(lambda x: np.ln(x), 0, time, Nsteps)

        if self.scan_time_force is False:
            for time in times[1:]:
                # start timer thread
                timer = threading.Timer(time, lambda: 0)
                timer.start()

                # execute command
                self.executing_commands(commands)

                # join timer thread
                timer.join()
        else:
            # Experimental!
            # commands and stuff needs to be threadsafe!

            timerlist = []
            for time in times:
                timerlist.append(threading.Timer(
                    time, self.executing_commands, commands=commands))
                timerlist[-1].start()

            while any([x.isAlive() for x in timerlist]):
                time.sleep(0.5)
                try:
                    self.check_running()
                except BreakCondition:
                    for x in timerlist:
                        x.cancel()
                        x.join()
                    raise BreakCondition

    def execute_scan_H(self, start, end, Nsteps, SweepRate, SpacingCode, ApproachMode, commands, EndMode, **kwargs):
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
            for field in fields:
                self._setpoint_field = field
                self.setField(field=field, EndMode=EndMode)
                self.executing_commands(commands)

        if ApproachMode == 'No O\'Shoot':
            for ct, field in enumerate(fields):
                first = fields[0] if ct == 0 else fields[ct - 1]
                approachFields = mapping_tofunc(lambda x: np.log(
                    x), start=first, end=field, Nsteps=10)
                for t in approachFields:
                    self.setField(field=field, EndMode='driven')
                    self._setpoint_field = field
                    # self.checkStable_Temp(Temp=t,
                    #                       direction=np.sign(temp - first),
                    #                       ApproachMode='Fast')

                    self.execute_waiting(Field=True, Delay=10)
                # self.checkStable_Temp(
                    # Temp=temp, direction=0, ApproachMode=ApproachMode)
                # self.setFieldEndMode(EndMode=EndMode)
                self.executing_commands(commands)

        if ApproachMode == 'Oscillate':
            raise NotImplementedError('oscillating field ApproachMode')

        if ApproachMode == 'Sweep':
            self.scan_H_programSweep(
                start=start, end=end, Nsteps=Nsteps, SweepRate=SweepRate, SpacingCode=SpacingCode)
            for field in fields:
                first = fields[0] if ct == 0 else fields[ct - 1]
                self.checkField(Field=field,
                                direction=np.sign(field - first),
                                ApproachMode='Sweep')
                self.executing_commands(commands)

        self.setFieldEndMode(EndMode=EndMode)

    def execute_scan_T(self, start, end, Nsteps, SweepRate, SpacingCode, ApproachMode, commands, **kwargs):
        """perform a temperature scan with given parameters"""

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
        if ApproachMode == "No O\'Shoot":
            for ct, temp in enumerate(temperatures):
                first = temperatures[0] if ct == 0 else temperatures[ct - 1]
                approachTemps = mapping_tofunc(lambda x: np.log(
                    x), start=first, end=temp, Nsteps=10)
                for t in approachTemps:
                    self.setTemperature(t)
                    self._setpoint_temp = t
                    self.checkStable_Temp(temp=t,
                                          direction=np.sign(temp - first),
                                          ApproachMode='Fast')

                    self.execute_waiting(Temp=True, Delay=10)
                self.checkStable_Temp(
                    Temp=temp, direction=0, ApproachMode=ApproachMode)

                self.executing_commands(commands)

        # approaching rather fast:
        if ApproachMode == 'Fast':
            for ct, temp in enumerate(temperatures):
                first = temperatures[0] if ct == 0 else temperatures[ct - 1]

                self.setTemperature(temp)
                self.checkStable_Temp(temp=temp,
                                      direction=np.sign(temp - first),
                                      ApproachMode=ApproachMode)

                self.executing_commands(commands)

        # sweeping through the values:
        if ApproachMode == 'Sweep':
            self.scan_T_programSweep(start=start, end=end, Nsteps=Nsteps,
                                     temperatures=temperatures, SweepRate=SweepRate, SpacingCode=SpacingCode)

            for ct, temp in enumerate(temperatures):

                first = temperatures[0] if ct == 0 else temperatures[ct - 1]
                self.checkStable_Temp(temp=temp,
                                      direction=np.sign(temp - first),
                                      ApproachMode='Sweep')

                self.executing_commands(commands)

    def execute_scan_P(self, start, end, Nsteps, speedindex, ApproachMode, commands, **kwargs) -> None:
        """perform a position scan with the given parameters"""

        positions = mapping_tofunc(lambda x: x, start, end, Nsteps)

        if ApproachMode == 'Pause':
            for pos in positions:
                self.setPosition(position=pos, speedindex=speedindex)
                self.wait_for(target=self._setpoint_pos,
                              getfunc=self.getPosition,
                              threshold=self.thresholds_waiting['Position'])
                self.executing_commands(commands)

        if ApproachMode == 'Sweep':
            pass

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
                          threshold=self.thresholds_waiting['Temp'])
        if Field:
            self.wait_for(target=self._setpoint_field,
                          getfunc=self.getField,
                          threshold=self.thresholds_waiting['Field'])
        if Position:
            self.wait_for(target=self._setpoint_pos,
                          getfunc=self.getPosition,
                          threshold=self.thresholds_waiting['Position'])
        if Chamber:
            self.wait_for(target=self._setpoint_chamber,
                          getfunc=self.getChamber,
                          threshold=0)

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

    def wait_for(self, getfunc, target, threshold=0.1, additional_condition=True, **kwargs):
        """repeatedly check whether the respective value was reached,
            given the respective threshold, return once it has
            produce a possibility to abort the sequence, through
            repeated check for value, for breaking condition, and sleeping
        """
        value_now = getfunc()

        while (abs(value_now - target) > threshold) & additional_condition:
            # check for break condition
            self.check_running()
            # check for value
            value_now = getfunc()
            # sleep
            time.sleep(0.1)

    def execute_set_Temperature(self, Temp: float, SweepRate: float = None) -> None:
        """execute the set temperature command

        in case a SweepRate is supplied, use it in a scan_T fashion
        else just hard-set the temperature

        Nsteps in the SweepRate mode is set to 2, implying
            the current temperature to be step 1 of 2
        """
        if SweepRate:
            self.scan_T_programSweep(start=self.getTemperature(
            ), end=Temp, Nsteps=2, temperatures=None, SweepRate=SweepRate)
        else:
            self.setTemperature(temperature=Temp)

    def execute_remark(self, remark: str) -> None:
        """use the given remark

        shoud be overriden in case the remark means anything"""
        self.message_to_user(f'there is a remark: {remark}')

    @staticmethod
    def message_to_user(message: str) -> None:
        """deliver a message to a user in some way

        default is printing to the command line
        may be overriden!
        """
        super().message_to_user(message)
        print(message)

    def scan_T_programSweep(self, start: float, end: float, Nsteps: float, temperatures: list, SweepRate: float, SpacingCode='uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep temperatures
        """
        raise NotImplementedError

    def scan_H_programSweep(self, start: float, end: float, Nsteps: float, fields: list, SweepRate: float, SpacingCode='uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep for field values
        """
        raise NotImplementedError

    def setField(self, field: float, EndMode: str) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a certain field directly
            needs to be implemented.
            TODO: override method
        """
        self._setpoint_field = field
        super().setField(field=field, EndMode=EndMode)
        # raise NotImplementedError

    def setFieldEndMode(self, EndMode: str) -> bool:
        """Method to be overridden/injected by a child class
        return bool stating success or failure (optional)
        """
        raise NotImplementedError

    def setTemperature(self, temperature: float) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a
            certain temperature directly
            needs to be implemented.
            TODO: override method
        """
        self._setpoint_temp = temperature
        super().setTemperature(temperature=temperature)
        # raise NotImplementedError

    def getTemperature(self) -> float:
        """Read the temperature

        Method to be overriden by child class
        implement measuring the temperature used for control
        returns: temperature as a float
        """
        raise NotImplementedError

    def setPosition(self, position: float, speedindex: float) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a
            certain position directly
            needs to be implemented.
            TODO: override method
        """
        self._setpoint_pos = position
        super().setPosition(position=position, speedindex=speedindex)
        # raise NotImplementedError

    def getPosition(self) -> float:
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

    def checkStable_Temp(self, temp, direction=0, ApproachMode='Sweep'):
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

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called
        """
        raise NotImplementedError

    def checkField(self, Field: float, direction: int = 0, ApproachMode: str = 'Sweep'):
        """check whether the Field has passed a certain value"""
        pass

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
