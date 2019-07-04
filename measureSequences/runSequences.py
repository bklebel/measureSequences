"""Module containing the class and possible helperfunctions to run a measuring sequence

Classes:
    Sequence_runner

Author: bklebel (Benjamin Klebel)

"""
import time
import threading
import numpy as np

# for sequence commands
import platform
import os
try:
    import winsound
except ImportError:
    pass

from Sequence_parsing import Sequence_parser


class BreakCondition(Exception):
    """docstring for BreakCondition"""
    pass


def mapping_tofunc(func, start: float, end: float, Nsteps: int) -> 'type(np.array())':
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

    def __init__(self, sequence: list, lock=None, isRunning=None, thresholds_waiting: dict = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._isRunning = True if isRunning is None else isRunning
        self.sequence = sequence
        self.lock = threading.Lock() if lock is None else lock
        if thresholds_waiting is None:
            self.thresholds_waiting = dict(Temp=0.1, Field=0.1, Position=1)
        else:
            self.thresholds_waiting = thresholds_waiting

        # self.mainthread = mainthread

        # self.temp_VTI_offset = 5
        self.subrunner = None

        self.datafile = ''
        self.scan_time_force = False

    def running(self) -> str:
        """run the given sequence"""

        with self.lock:
            try:
                self.executing_commands(self.sequence)
            except BreakCondition:
                return 'Aborted!'
        return 'Sequence finished!'

    def executing_commands(self, commands: list) -> None:
        """execute all entries of the commands list"""
        for entry in commands:
            try:
                self.execute_sequence_entry(entry)
            except NotImplementedError as e:
                self.message_to_user(f'An error occured: {e}. Did you maybe' +
                                     ' try to call a function/method which' +
                                     ' needs to be manually overriden?')
            # except AttributeError as e:
            #     self.message_to_user(f'An error occured: {e}. Did you maybe' +
            #                          ' try to call a function/method which' +
            #                          ' needs to be manually injected?')
            # except TypeError as e:
            #     self.message_to_user(f'An error occured: {e}. Did you maybe' +
            #                          ' try to call a function/method which' +
            #                          ' needs to be manually injected?')

    def check_running(self) -> None:
        """check for the _isRunning flag, raise Exception if
        the Sequence_runner was stopped
        """
        if not self._isRunning:
            raise BreakCondition

    def stop(self) -> None:
        """stop the sequence execution by setting self._isRunning to False"""
        self._isRunning = False
        if self.subrunner:
            self.subrunner.stop()

    def execute_sequence_entry(self, entry: dict) -> None:
        """execute the one entry of a list of commands"""
        self.check_running()

        if entry['typ'] == 'Shutdown':
            self.Shutdown()
        if entry['typ'] == 'Wait':
            self.execute_waiting(**entry)
        if entry['typ'] == 'beep':
            self.execute_beep(**entry)
        if entry['typ'] == 'chain sequence':
            self.execute_chain_sequence(**entry)
        if entry['typ'] == 'remark':
            self.execute_remark(entry['DisplayText'])

        if entry['typ'] == 'scan_T':
            self.execute_scan_T(**entry)
        if entry['typ'] == 'scan_H':
            self.execute_scan_H(**entry)
        if entry['typ'] == 'scan_time':
            self.execute_scan_time(**entry)
        if entry['typ'] == 'scan_position':
            self.execute_scan_P(**entry)

        if entry['typ'] == 'chamber_operation':
            self.execute_chamber(**entry)
        if entry['typ'] == 'set_T':
            self.execute_set_Temperature(**entry)
        if entry['typ'] == 'set_Field':
            self.execute_set_Field(**entry)
        if entry['typ'] == 'set_Position':
            self.execute_set_Position(**entry)

        if entry['typ'] == 'res_change_datafile':
            self.execute_res_change_datafile(**entry)
        if entry['typ'] == 'res_datafilecomment':
            self.execute_res_datafilecomment(**entry)
        if entry['typ'] == 'res_measure':
            self.execute_res_measure(**entry)
        if entry['typ'] == 'res_scan_excitation':
            # has yet to be implemented!
            pass

    def execute_chamber(self, operation: str, **kwargs) -> None:
        """execute the specified chamber operation"""

        if operation == 'seal immediate':
            self.chamber_seal()

        if operation == 'purge then seal':
            self.chamber_purge()
            self.chamber_seal()

        if operation == 'vent then seal':
            self.chamber_vent()
            self.chamber_seal()

        if operation == 'pump continuous':
            self.chamber_continuous('pumping')

        if operation == 'vent continuous':
            self.chamber_continuous('venting')

        if operation == 'high vacuum':
            self.chamber_high_vacuum()

    def execute_waiting(self, Temp=False, Field=False, Position=False, Chamber=False, Delay=0, **kwargs):
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
        while (delay_start < Delay) & self._isRunning:
            time.sleep(delay_step)
            delay_start += delay_step

    def execute_beep(self, length: float, frequency: float, **kwargs) -> None:
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
                print('\a')  # ring the command line bell
                self.message_to_user(
                    'The program "beep" had a problem. Maybe it is not installed?')
        if platform.system() == 'Darwin':
            print('\a')
            self.message_to_user(
                'no easily controllable beep function on mac available')

    def wait_for(self, getfunc, target, threshold=0.1, additional_condition=True, **kwargs) -> None:
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

    def execute_chain_sequence(self, new_file_seq: str, **kwargs) -> None:
        """execute everything from a specified sequence"""

        print(new_file_seq[:-1])
        parser = Sequence_parser(sequence_file=new_file_seq[:-1])
        commands = parser.data

        self.subrunner = self.__class__(sequence=commands,
                                        isRunning=self._isRunning,
                                        thresholds_waiting=self.thresholds_waiting,
                                        lock=threading.Lock())

        done = self.subrunner.running()
        if done == 'Aborted':
            raise BreakCondition
        if done == 'Sequence finished!':
            self.subrunner = None

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

        if np.isclose(time, 0):
            while self._isRunning:
                self.executing_commands(commands)
            self.check_running()

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
            # seems especialy unsafe if there is a chained sequence
            # in one of the commands....

            timerlist = []
            for time in times:
                timerlist.append(threading.Timer(
                    time, self.executing_commands, kwargs=dict(commands=commands)))
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

    def execute_scan_H(self, start: float, end: float, Nsteps: int, SweepRate: float, SpacingCode: str, ApproachMode: str, commands: list, EndMode: str, **kwargs) -> None:
        '''execute a Field scan'''

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
                    self.setField(field=t, EndMode='driven')
                    # self._setpoint_field = t
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
                start=start, end=end, Nsteps=Nsteps, fields=fields, SweepRate=SweepRate, SpacingCode=SpacingCode, EndMode=EndMode)
            for ct, field in enumerate(fields):
                first = fields[0] if ct == 0 else fields[ct - 1]
                self.checkField(Field=field,
                                direction=np.sign(field - first),
                                ApproachMode='Sweep')
                self.executing_commands(commands)

        self.setFieldEndMode(EndMode=EndMode)

    def execute_scan_T(self, start: float, end: float, Nsteps: int, SweepRate: float, SpacingCode: str, ApproachMode: str, commands: list, **kwargs) -> None:
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
                    # self._setpoint_temp = t
                    self.checkStable_Temp(temp=t,
                                          direction=np.sign(temp - first),
                                          ApproachMode='Fast')

                    self.execute_waiting(Temp=True, Delay=10)
                self.checkStable_Temp(
                    temp=temp, direction=0, ApproachMode=ApproachMode)

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

    def execute_scan_P(self, start: float, end: float, Nsteps: int, speedindex: int, ApproachMode: str, commands: list, **kwargs) -> None:
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
            self.scan_P_programSweep(start=start, end=end, Nsteps=Nsteps,
                                     positions=positions, speedindex=speedindex)
            for ct, pos in enumerate(positions):
                first = positions[0] if ct == 0 else positions[ct - 1]
                self.checkPosition(position=pos,
                                   direction=np.sign(pos - first),
                                   ApproachMode='Sweep')
                self.executing_commands(commands)

    def execute_set_Temperature(self, Temp: float, ApproachMode: str, SweepRate: float = None, **kwargs) -> None:
        """execute the set temperature command

        in case a SweepRate is supplied, use it in a scan_T fashion
        else just hard-set the temperature

        Nsteps in the SweepRate mode is set to 2, implying
            the current temperature to be step 1 of 2

        TODO: include ApproachModes
        """
        if SweepRate:
            self.scan_T_programSweep(start=self.getTemperature(
            ), end=Temp, Nsteps=2, temperatures=None, SweepRate=SweepRate)
        else:
            self.setTemperature(temperature=Temp)

    def execute_set_Field(self, Field: float, EndMode: str, ApproachMode: str, SweepRate: float = None, **kwargs) -> None:
        """execute the set Field command

        in case a SweepRate is supplied, use it in a scan_H fashion
        else just hard-set the Field

        Nsteps in the SweepRate mode is set to 2, implying
            the current field to be step 1 of 2

        TODO: include ApproachModes
        """
        if SweepRate:
            self.scan_H_programSweep(start=self.getField(
            ), end=Field, Nsteps=2, fields=None, SweepRate=SweepRate, EndMode=EndMode)
        else:
            self.setField(field=Field, EndMode=EndMode)

    def execute_set_Position(self, position: float, speedindex: int, Mode: str, **kwargs) -> None:
        """execute the set Position command"""

        if Mode == 'move to position':
            self.setPosition(position=position, speedindex=speedindex)

        if Mode == 'move to index and define':
            raise NotImplementedError(
                'Mode "move to index and define" functionality not yet implemented')

        if Mode == 'redefine present position':
            raise NotImplementedError(
                'Mode "redefine present position" functionality not yet implemented')

    def execute_res_measure(self, dataflags: dict, reading_count: int, bridge_conf: dict, **kwargs) -> None:
        """execute the resistivity: measure command"""

        values_measured = []
        values_transposed = dict()
        values_merged = dict(non_numeric=dict(), mean=dict(),
                             median=dict(), stddev=dict())

        reading_count = int(reading_count)
        # print(reading_count)

        for ct in range(reading_count):
            values_measured.append(self.res_measure(
                dataflags=dataflags, bridge_conf=bridge_conf))

        keys_corrupted = []
        for key in values_measured[0]:
            try:
                values_transposed[key] = [values_measured[i][key]
                                          for i in range(reading_count)]
            except KeyError as e:
                keys_corrupted.append(key)
                self.message_to_user(f'An error occured: {e}. Something went wrong in the resistivity measuring procedure.')

        for key in values_transposed:
            if any([not isinstance(val, (int, float)) for val in values_transposed[key]]):
                values_merged['non_numeric'][key] = values_transposed[key]
                continue
            if key not in keys_corrupted:
                values_merged['mean'][key] = np.mean(values_transposed[key])
                values_merged['median'][key] = np.median(
                    values_transposed[key])
                values_merged['stddev'][key] = np.std(values_transposed[key])

        self.measuring_store_data(data=values_merged, datafile=self.datafile)

    def execute_res_datafilecomment(self, comment: str, **kwargs) -> None:
        """execute the resistivity: datafile-comment command"""
        self.res_datafilecomment(comment=comment, datafile=self.datafile)

    def execute_res_change_datafile(self, new_file_data: str, mode: str, **kwargs) -> None:
        """execute the resistivity: datafile-comment command"""
        self.datafile = new_file_data
        self.res_change_datafile(datafile=new_file_data, mode=mode)

    def execute_remark(self, remark: str, **kwargs) -> None:
        """use the given remark

        shoud be overriden in case the remark means anything"""
        self.message_to_user(f'remark: {remark}')

    def message_to_user(self, message: str) -> None:
        """deliver a message to a user in some way

        default is printing to the command line
        may be overriden!
        """
        super().message_to_user(message)
        # print(message)

    def scan_T_programSweep(self, start: float, end: float, Nsteps: float, temperatures: list, SweepRate: float, SpacingCode: str = 'uniform') -> None:
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep of temperatures
        """
        raise NotImplementedError

    def scan_H_programSweep(self, start: float, end: float, Nsteps: float, fields: list, SweepRate: float, EndMode: str, SpacingCode: str = 'uniform') -> None:
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep for field values
        """
        raise NotImplementedError

    def scan_P_programSweep(self, start: float, end: float, Nsteps: float, positions: list, speedindex: float, SpacingCode: str = 'uniform') -> None:
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep of positions
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
        """Method to be overridden by a child class
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

    def setPosition(self, position: float, speedindex: int) -> None:
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

    def getField(self) -> float:
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

    def checkStable_Temp(self, temp: float, direction: int = 0, ApproachMode: str = 'Sweep') -> bool:
        """wait for the temperature to stabilize

        param: Temp:
            the temperature which needs to be arrived to continue
            function must block until the temperature has reached this value!
            (apart from checking whether the sequence qas aborted)

        param: direction:
            indicates whether the 'Temp' should currently be
                rising or falling
                direction =  0: default, no information / non-sweeping
                direction =  1: temperature should be rising
                direction = -1: temperature should be falling

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called

        method should be overriden - possibly some convenience functionality
            will be added in the future
        """
        raise NotImplementedError

    def checkField(self, Field: float, direction: int = 0, ApproachMode: str = 'Sweep') -> bool:
        """check whether the Field has passed a certain value

        param: Field:
            the field which needs to be arrived to continue
            function must block until the field has reached this value!
            (apart from checking whether the sequence qas aborted)

        param: direction:
            indicates whether the 'Field' should currently be
                rising or falling
                direction =  0: default, no information / non-sweeping
                direction =  1: temperature should be rising
                direction = -1: temperature should be falling

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called

        method should be overriden - possibly some convenience functionality
            will be added in the future
        """
        raise NotImplementedError

    def checkPosition(self, position: float, direction: int = 0, ApproachMode: str = 'Sweep') -> bool:
        """check whether the Field has passed a certain value

        param: position:
            the field which needs to be arrived to continue
            function must block until the field has reached this value!
            (apart from checking whether the sequence qas aborted)

        param: direction:
            indicates whether the 'Field' should currently be
                rising or falling
                direction =  0: default, no information / non-sweeping
                direction =  1: temperature should be rising
                direction = -1: temperature should be falling

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called

        method should be overriden - possibly some convenience functionality
            will be added in the future
        """
        raise NotImplementedError

    def Shutdown(self) -> None:
        """Shut down instruments to a safe standby-configuration"""
        raise NotImplementedError

    def chamber_purge(self) -> bool:
        """purge the chamber

        must block until the chamber is purged
        """
        raise NotImplementedError

    def chamber_vent(self) -> bool:
        """vent the chamber

        must block until the chamber is vented
        """
        raise NotImplementedError

    def chamber_seal(self) -> bool:
        """seal the chamber

        must block until the chamber is sealed
        """
        raise NotImplementedError

    def chamber_continuous(self, action) -> bool:
        """pump or vent the chamber continuously"""
        if action == 'pumping':
            raise NotImplementedError
        if action == 'venting':
            raise NotImplementedError

    def chamber_high_vacuum(self) -> bool:
        """pump the chamber to high vacuum

        must block until the chamber is  at high vacuum
        """
        raise NotImplementedError

    def res_measure(self, dataflags: dict, bridge_conf: dict) -> dict:
        """Measure resistivity
            Must be overridden!
            return dict with all data according to the set dataflags
            this dict should be flat, just numbers, no nesting
        """
        raise NotImplementedError

    def measuring_store_data(self, data: dict, datafile: str) -> None:
        """Store measured data
            Must be overridden!
        """
        raise NotImplementedError

    def res_datafilecomment(self, comment: str, datafile: str) -> None:
        """write a comment to the datafile
            Must be overridden!
        """
        raise NotImplementedError

    def res_change_datafile(self, datafile: str, mode: str) -> None:
        """write a comment to the datafile
            Must be overridden!
            mode ('a' or 'w') determines whether data should be
                'a': appended
                'w': written over
            (to) the new datafile
        """
        raise NotImplementedError
