from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
# from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
# from PyQt5.QtCore import QAbstractListModel, QFile, QIODevice, QModelIndex, Qt
from PyQt5.uic import loadUi


from copy import deepcopy

import sys
# import datetime
import pickle
import os
import re
import threading
import json

from util import Window_ui
# util will have to be changed eventually


from qlistmodel import SequenceListModel
from qlistmodel import ScanListModel


dropstring = re.compile(r'([a-zA-Z0-9])')
searchf_number = re.compile(r'([0-9]+[.]*[0-9]*)')
searchf_string = re.compile(r'''["']{2}(.*?)["']{2}''')


class EOSException(Exception):
    """Exception to raise if an EOS was encountered"""
    pass


def parse_binary(number):
    """parse an integer number which represents a sum of bits
        returns a list with True and False, from back to front
    """
    # print(number)
    number = int(number)
    nums = list(reversed('{:b}'.format(number)))
    # print(nums)
    for ct, num in enumerate(nums):
        nums[ct] = True if int(num) else False
    return nums


class Window_ChangeDataFile(QtWidgets.QDialog):
    """docstring for Window_waiting"""

    sig_accept = pyqtSignal(dict)
    sig_reject = pyqtSignal()

    def __init__(self, ui_file='.\\configurations\\Sequence_change_datafile.ui'):
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

    def __init__(self, ui_file='.\\configurations\\sequence_waiting.ui'):
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

    def __init__(self, ui_file='.\\configurations\\sequence_scan_temperature.ui', **kwargs):
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
            QTimer.singleShot(0, self.update_lcds)

    def acc(self):
        """if not rejected, emit signal with configuration and accept"""

        self.conf['sequence_temperature'] = self.model.pass_data()

        self.sig_accept.emit(deepcopy(self.conf))
        self.accept()


class Sequence_parser(object):
    """Abstract Sequence parser, without GUI"""

    def __init__(self, sequence_file=None, textnesting='   ', **kwargs):
        """initialise important attributes"""
        super(Sequence_parser, self).__init__(**kwargs)

        self.sequence_file = sequence_file
        self.textnesting = textnesting
        self.initialize_sequence(self.sequence_file)

    def saving(self):
        """save serialised versions of a sequence"""
        with open(self.sequence_file_p, 'wb') as output:
            pickle.dump(self.data, output, pickle.HIGHEST_PROTOCOL)
        with open(self.sequence_file_json, 'w') as output:
            output.write(json.dumps(self.data))

    def change_file_location(self, fname):
        self.sequence_file = os.path.splitext(fname)[0] + '.seq'
        self.sequence_file_p = os.path.splitext(self.sequence_file)[0] + '.pkl'
        self.sequence_file_json = os.path.splitext(
            self.sequence_file)[0] + '.json'

    @staticmethod
    def construct_pattern(expressions):
        pat = ''
        for e in expressions:
            pat = pat + r'|' + e
        return pat[1:]

    def initialize_sequence(self, sequence_file):
        """parse a complete file of instructions"""
        if sequence_file:
            self.change_file_location(sequence_file)

            exp = [r'TMP TEMP(.*?)$', r'FLD FIELD(.*?)$', r'SCAN(.*?)$',
                   r'WAITFOR(.*?)$', r'CHN(.*?)$', r'CDF(.*?)$', r'DFC(.*?)$',
                   r'LPI(.*?)$', r'SHT(.*?)DOWN', r'EN(.*?)EOS$', r'RES(.*?)$',
                   r'BEP BEEP(.*?)$', r'CMB CHAMBER(.*?)$', r'REM(.*?)$']
            self.p = re.compile(self.construct_pattern(
                exp), re.DOTALL | re.M)  # '(.*?)[^\S]* EOS'

            self.data, self.textsequence = self.read_sequence(sequence_file)
            # print(
            # 'done -----------------------------------------------------------------')

        else:
            self.textsequence = []
            self.data = []
            self.sequence_file = ''

    def read_sequence(self, file):
        """read the whole sequence from a file"""
        with open(file, 'r') as f:
            data = f.readlines()  # .replace('\n', '')

        # preparing variables
        self.jumping_count = [0, 0]
        self.nesting_level = 0
        # parse sequence
        commands, textsequence = self.parse_nesting(data, -1)
        return commands, textsequence

    def parse_nesting(self, lines_file, lines_index):
        """parse a nested command structure"""
        commands = []
        if lines_index == -1:
            textsequence = []
        else:
            textsequence = None
        for ct, line_further in enumerate(lines_file[lines_index + 1:]):
            if self.jumping_count[self.nesting_level + 1] > 0:
                self.jumping_count[self.nesting_level + 1] -= 1
                continue
            for count, jump in enumerate(self.jumping_count[:-1]):
                self.jumping_count[count] += 1
            try:

                dic_loop = self.parse_line(
                    lines_file, line_further, lines_index + 1 + ct)
            except EOSException:
                self.nesting_level -= 1
                dic_loop = dict(
                    typ="EOS", DisplayText=self.textnesting * (self.nesting_level) + 'EOS')
                commands.append(dic_loop)
                break
            if dic_loop is not None:
                commands.append(dic_loop)
                if lines_index == -1:
                    textsequence.append(dic_loop)
                    self.add_text(textsequence, dic_loop)
        del self.jumping_count[-1]
        return commands, textsequence

    def add_text(self, text_list, dic):
        """build the un-nested list of displayed commands"""
        if 'commands' in dic:
            for c in dic['commands']:

                try:
                    text_list.append(dict(DisplayText=c['DisplayText']))
                except KeyError:
                    print(c)
                self.add_text(text_list, c)

    def parse_line(self, lines_file, line, line_index):
        """parse one line of a sequence file, possibly more if it is a scan"""
        line_found = self.p.findall(line)

        try:
            line_found = line_found[0]
        except IndexError:
            return None

        # print(line_found)
        if line_found[0]:
            # set temperature
            # print('I found set_temp')
            dic = self.parse_set_temp(line)
        elif line_found[1]:
            # set field
            # print('I found set_field')
            dic = self.parse_set_field(line)
        elif line_found[2]:
            # scan something
            # print('I found a scan ')
            self.jumping_count.append(0)
            dic = self.parse_scan_arb(lines_file, line, line_index)
        elif line_found[3]:
            # waitfor
            # print('I found waiting')
            dic = self.parse_waiting(line)
        elif line_found[4]:
            # chain sequence
            # print('I found chain_sequence')
            dic = self.parse_chain_sequence(line)
        elif line_found[5]:
            # resistivity change datafile
            # print('I found res_change_datafile')
            dic = self.parse_res_change_datafile(line)
        elif line_found[6]:
            # resistivity datafile comment
            # print('I found res_datafilecomment')
            dic = self.parse_res_datafilecomment(line)
        elif line_found[7]:
            # resistivity scan excitation
            # print('I found res_scan_excitation')
            dic = self.parse_res_scan_excitation(line)
        elif line_found[8]:
            # Shutdown to a standby configuration
            # print('I found Shutdown')
            dic = dict(typ='Shutdown')
        elif line_found[9]:
            # end of a scan
            # print('I found EOS')
            raise EOSException()
        elif line_found[10]:
            # resistivity - measure
            # print('I found res meausrement')
            dic = self.parse_res(line)
        elif line_found[11]:
            # beep of certain length and frequency
            dic = self.parse_beep(line)
        elif line_found[12]:
            # chamber operations
            dic = self.parse_chamber(line)

        elif line_found[13]:
            # remark
            dic = dict(typ='remark', DisplayText=line_found[13])

        # try:
        #     print(dic)
        # except NameError:
        #     print(line_found)
        # if dic['typ'] is None:
        #     print(line_found)

        return dic

    def parse_scan_arb(self, lines_file, line, lines_index):
        """parse a line in which a scan was defined"""
        # parse this scan instructions
        line_found = self.p.findall(line)[0]

        dic = dict(typ=None)
        if line_found[2][0] == 'H':
            # Field
            dic = self.parse_scan_H(line)

        if line_found[2][0] == 'T':
            # temperature
            dic = self.parse_scan_T(line)

        if line_found[2][0] == 'P':
            # position
            dic = self.parse_scan_P(line)

        if line_found[2][0] == 'C':
            # time
            dic = self.parse_scan_time(line)

        self.nesting_level += 1

        commands, _ = self.parse_nesting(lines_file, lines_index)

        dic.update(dict(commands=commands))
        return dic

    @staticmethod
    def read_nums(comm):
        """convert a string of numbers into a list of floats"""
        return [float(x) for x in searchf_number.findall(comm)]

    @staticmethod
    def parse_binary_dataflags(number):
        """parse flags what to store"""
        nums = parse_binary(number)
        names = ['General Status', 'Temperature',
                 'Magnetic Field', 'Sample Position',
                 'Chan 1 Resistivity', 'Chan 1 Excitation',
                 'Chan 2 Resistivity', 'Chan 2 Excitation',
                 'Chan 3 Resistivity', 'Chan 3 Excitation',
                 'Chan 4 Resistivity', 'Chan 4 Excitation']
        empty = [False for x in names]
        bare = dict(zip(names, empty))
        bare.update(dict(zip(names, nums)))
        return bare

    @staticmethod
    def displaytext_waiting(data):
        """generate the displaytext for the wait function"""
        string = 'Wait for '
        separator = ', ' if data['Temp'] and data['Field'] else ''
        sep_taken = False

        if data['Temp']:
            string += 'Temperature' + separator
            sep_taken = True
        if data['Field']:
            string = string + 'Field' if sep_taken else string + 'Field' + separator
            sep_taken = True
        string += ' & {} seconds more'.format(data['Delay'])
        return string

    @staticmethod
    def displaytext_scan_T(data):
        """generate the displaytext for the temperature scan"""
        return 'Scan Temperature from {start} to {end} in {Nsteps} steps, {SweepRate}K/min, {ApproachMode}, {SpacingCode}'.format(**data)

    @staticmethod
    def displaytext_scan_H(data):
        """generate the displaytext for the field scan"""
        return 'Scan Field from {start} to {end} in {Nsteps} steps, {SweepRate}K/min, {ApproachMode}, {SpacingCode}, {EndMode}'.format(**data)

    @staticmethod
    def displaytext_set_temp(data):
        """generate the displaytext for a set temperature"""
        return 'Set Temperature to {Temp} at {SweepRate}K/min, {ApproachMode}'.format(**data)

    @staticmethod
    def displatext_res_scan_exc(data):
        """generate the displaytext for an excitation scan"""
        # TODO - finish this up
        return 'Scanning RES Excitation'

    @staticmethod
    def displaytext_res(data):
        """generate the displaytext for the resistivity measurement"""
        # TODO - finish this up
        text = 'Resistivity '
        chans = []
        chans.append('Ch1 ')
        chans.append('Ch2 ')
        chans.append('Ch3 ')
        chans.append('Ch4 ')

        for ct, chan_conf in enumerate(data['bridge_conf']):
            if chan_conf['on_off'] is False:
                chans[ct] += 'Off, '
                continue
            chans[ct] += '{limit_current_uA}uA, '.format(**chan_conf)
        chans[-1].strip(',')
        for c in chans:
            text += c
        return text

    @staticmethod
    def displaytext_set_field(data):
        """generate the displaytext for a set field"""
        return 'Set Field to {Field} at {SweepRate}T/min, {ApproachMode}, {EndMode} '.format(**data)

    def parse_chamber(self, comm):
        '''parse a command for a chamber operation'''
        nums = self.read_nums(comm)
        dic = dict(typ='chamber_operation')
        if nums[0] == 0:
            dic['operation'] = 'seal immediate'
        if nums[0] == 1:
            dic['operation'] = 'purge then seal'
        if nums[0] == 2:
            dic['operation'] = 'vent then seal'
        if nums[0] == 3:
            dic['operation'] = 'pump continuous'
        if nums[0] == 4:
            dic['operation'] = 'vent continuous'
        if nums[0] == 5:
            dic['operation'] = 'high vacuum'

        dic['DisplayText'] = self.textnesting * self.nesting_level + \
            'Chamber Op: {operation}'.format(**dic)
        return dic

    def parse_set_temp(self, comm):
        """parse a command to set a single temperature"""
        # TODO: Fast settle
        nums = self.read_nums(comm)
        dic = dict(typ='set_T', Temp=nums[0], SweepRate=nums[1])

        if int(nums[2]) == 0:
            dic['ApproachMode'] = 'Fast'
        if int(nums[2]) == 1:
            dic['ApproachMode'] = 'No O\'Shoot'

        dic['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displaytext_set_temp(dic)
        return dic

    def parse_set_field(self, comm):
        """parse a command to set a single field"""
        nums = self.read_nums(comm)
        dic = dict(typ='set_Field', Field=nums[0], SweepRate=nums[1])
        if int(nums[2]) == 0:
            dic['ApproachMode'] = 'Linear'
        if int(nums[2]) == 1:
            dic['ApproachMode'] = 'No O\'Shoot'
        if int(nums[2]) == 2:
            dic['ApproachMode'] = 'Oscillate'

        if int(nums[3]) == 0:
            dic['EndMode'] = 'persistent'
        if int(nums[3]) == 1:
            dic['EndMode'] = 'driven'

        dic['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displaytext_set_field(dic)
        return dic

    def parse_waiting(self, comm):
        """parse a command to wait for certain values"""
        nums = self.read_nums(comm)
        dic = dict(typ='Wait',
                   Temp=bool(int(nums[1])),
                   Field=bool(int(nums[2])),
                   Position=bool(int(nums[3])),
                   Chamber=bool(int(nums[4])),
                   Delay=nums[0])
        dic['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displaytext_waiting(dic)
        return dic
        # dic.update(local_dic.update(dict(DisplayText=self.parse_waiting(local_dic))))

    def parse_chain_sequence(self, comm):
        """parse a command to chain a sequence file"""
        file = comm[4:]
        return dict(typ='chain sequence', new_file_seq=file,
                    DisplayText=self.textnesting * self.nesting_level + 'Chain sequence: {}'.format(comm))
        # print('CHN', comm, dic)
        # return dic

    def parse_scan_T(self, comm):
        """parse a command to do a temperature scan"""
        temps = self.read_nums(comm)
        # temps are floats!
        if len(temps) < 6:
            raise AssertionError(
                'not enough specifying numbers for T-scan!')

        dic = dict(typ='scan_T', start=temps[0],
                   end=temps[1],
                   SweepRate=temps[2],
                   Nsteps=temps[3],
                   SpacingCode=temps[4],
                   ApproachMode=temps[5])
        if int(temps[4]) == 0:
            dic['SpacingCode'] = 'uniform'
        elif int(temps[4]) == 1:
            dic['SpacingCode'] = '1/T'
        elif int(temps[4]) == 2:
            dic['SpacingCode'] = 'logT'

        if int(temps[5]) == 0:
            dic['ApproachMode'] = 'Fast'
        elif int(temps[5]) == 1:
            dic['ApproachMode'] = 'No O\'Shoot'
        elif int(temps[5]) == 2:
            dic['ApproachMode'] = 'Sweep'
        dic['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displaytext_scan_T(dic)
        return dic

    def parse_scan_H(self, comm):
        '''parse a command to do a field scan'''
        numbers = self.read_nums(comm)
        if len(numbers) < 7:
            raise AssertionError('not enough specifying numbers for H-scan!')

        dic = dict(typ='scan_H',
                   start=numbers[0],
                   end=numbers[1],
                   SweepRate=numbers[2],
                   Nsteps=numbers[3])

        if int(numbers[4]) == 0:
            dic['SpacingCode'] = 'uniform'
        elif int(numbers[4]) == 1:
            dic['SpacingCode'] = 'H*H'
        elif int(numbers[4]) == 2:
            dic['SpacingCode'] = 'H^1/2'
        elif int(numbers[4]) == 3:
            dic['SpacingCode'] = '1/H'
        elif int(numbers[4]) == 4:
            dic['SpacingCode'] = 'logH'

        if int(numbers[5]) == 0:
            dic['ApproachMode'] = 'Linear'
        if int(numbers[5]) == 1:
            dic['ApproachMode'] = 'No O\'Shoot'
        if int(numbers[5]) == 2:
            dic['ApproachMode'] = 'Oscillate'
        if int(numbers[5]) == 3:
            dic['ApproachMode'] = 'Sweep'

        if int(numbers[6]) == 0:
            dic['EndMode'] = 'persistent'
        if int(numbers[6]) == 1:
            dic['EndMode'] = 'driven'

        dic['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displaytext_scan_H(dic)
        return dic

    def parse_scan_time(self, comm):
        nums = self.read_nums(comm)
        if len(nums) < 3:
            raise AssertionError(
                'not enough specifying numbers for time-scan!')

        dic = dict(typ='scan_time', time=nums[0], Nsteps=nums[1])

        if int(nums[2]) == 0:
            dic['SpacingCode'] = 'uniform'
        if int(nums[2]) == 1:
            dic['SpacingCode'] = 'ln(t)'

        dic['DisplayText'] = self.textnesting * self.nesting_level + \
            'Scan Time {time}secs in {Nsteps} steps, {SpacingCode}'
        return dic

    def parse_scan_P(self, comm):
        nums = self.read_nums(comm)
        if len(nums) < 4:
            raise AssertionError(
                'not enough specifying numbers for position-scan!')

        dic = dict(typ='scan_position',
                   start=nums[0],
                   end=nums[1],
                   speedindex=nums[2],
                   Nsteps=nums[3])

        if len(nums) > 4:
            if int(nums[4]) == 1:
                dic['ApproachMode'] = 'Sweep'
            else:
                dic['ApproachMode'] = 'Pause'
        else:
            dic['ApproachMode'] = 'Pause'

        # dic['ApproachMode'] = 'Sweep' if len(nums) > 4 else 'Pause'
        dic['DisplayText'] = self.textnesting * self.nesting_level + \
            'Scan Position from {start} to {end} in {Nsteps} steps, {speedindex}, {ApproachMode} '.format(
                **dic)
        return dic

    def parse_beep(self, comm):
        '''parse a command to beep for a certain time at a certain frequency'''
        nums = self.read_nums(comm)
        if len(nums) < 2:
            raise AssertionError('not enough specifying numbers for beep!')

        dic = dict(typ='beep', length=nums[0], frequency=nums[1])
        dic['DisplayText'] = self.textnesting * self.nesting_level + \
            'Beep for {length}secs at {frequency}Hz'.format(**dic)
        return dic

    def parse_res_change_datafile(self, comm):
        """parse a command to change the datafile"""
        file = searchf_string.findall(comm)
        return dict(typ='res_change_datafile', new_file_data=file,
                    mode='a' if comm[-1] == '1' else 'w',
                    # a - appending, w - writing, can be inserted
                    # directly into opening statement
                    DisplayText=self.textnesting * self.nesting_level + 'Change data file: {}'.format(file))
        # print('CDF', comm, dic)
        # return dic

    def parse_res_datafilecomment(self, comm):
        """parse a command to write a comment to the datafile"""
        comment = searchf_string.findall(comm)[0]
        dic = dict(typ='res_datafilecomment',
                   comment=comment,
                   DisplayText=self.textnesting * self.nesting_level +
                   'Datafile Comment: {}'.format(comment))
        return dic

    @staticmethod
    def parse_res_bridge_setup(nums):
        """parse the res bridge setup for an excitation scan"""
        bridge_setup = []
        bridge_setup.append(nums[:5])
        bridge_setup.append(nums[5:10])
        bridge_setup.append(nums[10:15])
        bridge_setup.append(nums[15:20])
        for ct, channel in enumerate(bridge_setup):
            bridge_setup[ct] = dict(limit_power_uW=channel[1],
                                    limit_voltage_mV=channel[4])
            bridge_setup[ct]['ac_dc'] = 'AC' if channel[2] == 0 else 'DC'
            bridge_setup[ct]['on_off'] = True if channel[0] == 2 else False
            bridge_setup[ct]['calibration_mode'] = 'Standard' if channel[
                3] == 0 else 'Fast'
        return bridge_setup

    def parse_res(self, comm):
        """parse a command to measure resistivity"""
        nums = self.read_nums(comm)
        dataflags = self.parse_binary_dataflags(int(nums[0]))
        reading_count = nums[1]
        nums = nums[2:]
        bridge_conf = []
        bridge_conf.append(nums[:6])
        bridge_conf.append(nums[6:12])
        bridge_conf.append(nums[12:18])
        bridge_conf.append(nums[18:24])
        for ct, channel in enumerate(bridge_conf):
            bridge_conf[ct] = dict(limit_power_uW=channel[2],
                                   limit_current_uA=channel[1],
                                   limit_voltage_mV=channel[5])
            bridge_conf[ct]['on_off'] = True if channel[0] == 2 else False
            bridge_conf[ct]['ac_dc'] = 'AC' if channel[3] == 0 else 'DC'
            bridge_conf[ct]['calibration_mode'] = 'Standard' if channel[
                4] == 0 else 'Fast'
        data = dict(typ='res_measure',
                    dataflags=dataflags,
                    reading_count=reading_count,
                    bridge_conf=bridge_conf)
        data['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displaytext_res(data)
        return data

    def parse_res_scan_excitation(self, comm):
        """parse a command to do an excitation scan"""
        nums = self.read_nums(comm)
        scan_setup = []
        scan_setup.append(nums[:3])  # 1
        scan_setup.append(nums[3:6])  # 2
        scan_setup.append(nums[6:9])  # 3
        scan_setup.append(nums[9:12])  # 4
        for ct, channel in enumerate(scan_setup):
            scan_setup[ct] = dict(start=channel[0], end=[channel[1]])
            if channel[-1] == 0:
                scan_setup[ct]['Spacing'] = 'linear'
            if channel[-1] == 1:
                scan_setup[ct]['Spacing'] = 'log'
            if channel[-1] == 2:
                scan_setup[ct]['Spacing'] = 'power'

        dataflags = self.parse_binary_dataflags(nums[14])
        n_steps = nums[12]
        reading_count = nums[13]
        bridge_setup = self.parse_res_bridge_setup(nums[15:35])
        data = dict(typ='res_scan_excitation',
                    scan_setup=scan_setup,
                    bridge_setup=bridge_setup,
                    dataflags=dataflags,
                    n_steps=n_steps,
                    reading_count=reading_count)
        data['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displatext_res_scan_exc(data)
        return data


class Sequence_builder(Window_ui, Sequence_parser):
    """docstring for sequence_builder"""

    sig_runSequence = pyqtSignal(list)
    sig_abortSequence = pyqtSignal()

    def __init__(self, parent=None, **kwargs):
        super().__init__(
            ui_file='.\\configurations\\sequence.ui', **kwargs)

        # self.listSequence.sig_dropped.connect(lambda value: self.dropreact(value))

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
        self.pushClear.clicked.connect(lambda: self.model.clear_all())
        self.pushClear.clicked.connect(self.init_data)

        # self.Button_RunSequence.clicked.connect(self.running_sequence)
        self.Button_AbortSequence.clicked.connect(
            lambda: self.sig_abortSequence.emit())
        # self.model.sig_send.connect(lambda value: self.printing(value))
        # self.model.sig_send.connect(self.saving)
        # self.treeOptions.itemDoubleClicked['QTreeWidgetItem*', 'int'].connect(lambda value: self.listSequence.repaint())
        self.show()

    def init_data(self):
        self.data = []

    def running_sequence(self):
        self.data = self.model.pass_data()
        self.sig_runSequence.emit(deepcopy(self.data))

    def addItem_toSequence(self, text):
        """
            depending on the Item clicked, add the correct Item to the model,
            which may involve executing a certain window
        """
        if text.text(0) == 'Wait':
            # self.window_waiting.show()
            self.window_waiting.exec_()  # if self.window_waiting.exec_():
            # print('success')

        if text.text(0) == 'Resistivity vs Temperature':
            # here the Tscan comes
            self.window_Tscan.exec_()

        if text.text(0) == 'Chain Sequence':
            new_file_seq, __ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Sequence',
                                                                     'c:\\', "Sequence files (*.seq)")
            data = dict(typ='chain sequence', new_file_seq=new_file_seq,
                            DisplayText='Chain sequence: {}'.format(new_file_seq))
            self.model.addItem(data)
            QTimer.singleShot(1, lambda: self.listSequence.repaint())

        if text.text(0) == 'Change Data File':
            raise NotImplementedError
        if text.text(0) == 'Set Temperature':
            raise NotImplementedError
        if text.text(0) == 'Set Field':
            raise NotImplementedError
        if text.text(0) == 'Resistivity vs Field':
            raise NotImplementedError
        if text.text(0) == 'Shutdown Temperature Control':
            raise NotImplementedError

    def addWaiting(self, data):
        string = self.displaytext_waiting(data)
        data.update(dict(DisplayText=string))
        # self.listSequence.addItem(string)
        self.model.addItem(data)
        QTimer.singleShot(1, lambda: self.listSequence.repaint())
        # QTimer.singleShot(10, self.model.)

    def addTscan(self, data):
        string = self.displaytext_scan_T(data)
        data.update(dict(DisplayText=string))
        self.model.addItem(data)
        QTimer.singleShot(1, lambda: self.listSequence.repaint())

    def addChangeDataFile(self, data):
        pass

    @staticmethod
    def printing(self, data):
        print(data)

    # def saving(self):
    #     with open(self.sequence_file_p, 'wb') as output:
    #         pickle.dump(self.data, output, pickle.HIGHEST_PROTOCOL)
    #     with open(self.sequence_file_json, 'w') as output:
    #         output.write(json.dumps(self.data))

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

    def window_FileDialogSave(self):
        self.sequence_file_json, __ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save As',
                                                                            'c:\\', "Serialised (*.json)")
        # last option is a file specifier, like 'Sequence Files (*.seq)'
        self.lineFileLocation_serialised.setText(self.sequence_file_json)
        self.sequence_file_p = self.sequence_file_json[:-4] + 'pkl'
        # self.sequence_file_json = self.sequence_file[:-3] + 'json'

    def window_FileDialogOpen(self):
        self.sequence_file, __ = QtWidgets.QFileDialog.getOpenFileName(self, 'Save As',
                                                                       'c:\\', "Sequence files (*.seq)")
        self.lineFileLocation.setText(self.sequence_file)
        self.initialize_sequence(self.sequence_file)

    def initialize_sequence(self, sequence_file):
        """build & run the sequence parsing, add items to the display model"""
        super().initialize_sequence(sequence_file)
        for command in self.textsequence:
            self.model.addItem(command)


if __name__ == '__main__':

    file = 'SEQ_20180914_Tscans.seq'
    file = 'Tempscan.seq'
    file = None
    # file = 't.seq'

    app = QtWidgets.QApplication(sys.argv)
    form = Sequence_builder(file)
    form.show()
    sys.exit(app.exec_())
