
import numpy as np
from threading import Lock
import json

from runSequences import Sequence_runner
from Sequence_parsing import Sequence_parser


class Dummy_Functions(object):
    """docstring for Functions"""

    def __init__(self):
        super().__init__()

    def setTemperature(self, temperature: float) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a
            certain temperature directly
            needs to be implemented.
            TODO: override method
        """
        print('setTemperature :: temp = {}'.format(temperature))

    def setField(self, field: float, EndMode: str) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a certain field directly
            needs to be implemented.
            TODO: override method
        """
        print(f'setField :: field = {field}, EndMode = {EndMode}')

    def setPosition(self, position: float, speedindex: float) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a
            certain position directly
            needs to be implemented.
            TODO: override method
        """
        print(f'setPosition :: pos = {position}, speedindex = {speedindex}')

    def message_to_user(self, message: str) -> None:
        """deliver a message to a user in some way

        default is printing to the command line
        may be overriden!
        """
        # super().message_to_user(message)
        # print(message)
        print(f'message_to_user :: message = {message}')


class Dummy(Sequence_runner, Dummy_Functions):
    """docstring for Dummy"""

    def __init__(self, filename='', **kwargs):
        if filename:

            parser = Sequence_parser(sequence_file=filename)
            seq = parser.data

            # with open(filename) as f:
            #     seq = json.load(f)
            super().__init__(sequence=seq, **kwargs)
        else:
            super().__init__(**kwargs)
        # self.subrunner_class = Dummy

    def scan_T_programSweep(self, start: float, end: float, Nsteps: float, temperatures: list, SweepRate: float, SpacingCode: str = 'uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep of temperatures
        """
        print(f'scan_T_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, temps: {temperatures}, Rate: {SweepRate}, SpacingCode: {SpacingCode}')

    def scan_H_programSweep(self, start: float, end: float, Nsteps: float, fields: list, SweepRate: float, EndMode: str, SpacingCode: str = 'uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep for field values
        """
        print(f'scan_H_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, fields: {fields}, Rate: {SweepRate}, SpacingCode: {SpacingCode}, EndMode: {EndMode}')

    def scan_P_programSweep(self, start: float, end: float, Nsteps: float, positions: list, speedindex: float, SpacingCode: str = 'uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep of positions
        """
        print(f'scan_T_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, positions: {positions}, speedindex: {speedindex}, SpacingCode: {SpacingCode}')

    def setFieldEndMode(self, EndMode: str) -> bool:
        """Method to be overridden by a child class
        return bool stating success or failure (optional)
        """
        print(f'setFieldEndMode :: EndMode = {EndMode}')

    def getTemperature(self) -> float:
        """Read the temperature

        Method to be overriden by child class
        implement measuring the temperature used for control
        returns: temperature as a float
        """
        val = np.random.rand() * 300
        print(f'getTemperature :: returning random value: {val}')
        return val

    def getPosition(self) -> float:
        """
            Method to be overriden by child class
            implement checking the position

            returns: position as a float
        """
        val = np.random.rand() * 360
        print(f'getPosition :: returning random value: {val}')
        return val

    def getField(self) -> float:
        """Read the Field

        Method to be overriden by child class
        implement measuring the field
        returns: Field as a float
        """
        val = np.random.rand() * 9
        print(f'getField :: returning random value: {val}')
        return val

    def getChamber(self):
        """Read the Chamber status

        Method to be overriden by child class
        implement measuring whether the chamber is ready
        returns: chamber status
        """
        val = np.random.rand() * 4
        print(f'getChamber :: returning random value: {val}')
        return val

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
        print(f'checkstable_Temp :: Temp: {temp} is stable!, ApproachMode = {ApproachMode}, direction = {direction}')

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
        print(f'checkField :: Field: {Field} is stable!, ApproachMode = {ApproachMode}, direction = {direction}')

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
        print(f'checkPosition :: position: {position} is stable!, ApproachMode = {ApproachMode}, direction = {direction}')

    def Shutdown(self):
        """Shut down instruments to a safe standby-configuration"""
        print(f'Shutdown :: going into safe shutdown mode')

    def chamber_purge(self):
        """purge the chamber

        must block until the chamber is purged
        """
        print(f'chamber_purge :: purging chamber')

    def chamber_vent(self):
        """vent the chamber

        must block until the chamber is vented
        """
        print(f'chamber_vent :: venting chamber')

    def chamber_seal(self):
        """seal the chamber

        must block until the chamber is sealed
        """
        print(f'chamber_seal :: sealing chamber')

    def chamber_continuous(self, action):
        """pump or vent the chamber continuously"""
        if action == 'pumping':
            print(f'chamber_continuous :: pumping continuously')
        if action == 'venting':
            print(f'chamber_continuous :: venting continuously')

    def chamber_high_vacuum(self):
        """pump the chamber to high vacuum

        must block until the chamber is  at high vacuum
        """
        print(f'chamber_high_vacuum :: bringing the chamber to HV')


if __name__ == '__main__':
    dummy = Dummy(lock=Lock(), filename='seqfiles\\beepingsequence.seq')
    # QTimer.singleShot(3*1e3, lambda: dummy.stop())
    print(dummy.running())
