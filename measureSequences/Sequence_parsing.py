"""Module containing the Sequence parser
    for PPMS Sequence files (resistivity option measurement commands only)

Functions:
    parse_binary

Classes:
    EOSException: End of Scan Exception,
        to be used in the Sequence parser

    Sequence_parser: Sequence parsing object

Author: bklebel (Benjamin Klebel)

"""

import pickle
import os
import re
import json
import logging
logger = logging.getLogger(
    'measureSequences.Sequence_parser')
logger.addHandler(logging.NullHandler())


dropstring = re.compile(r'([a-zA-Z0-9])')
searchf_number = re.compile(r'([0-9]+[.]*[0-9]*)')
searchf_string = re.compile(
    r'''["]{1}(.*?)["]{1}|[']{2}(.*?)[']{2}|[']{1}(.*?)[']{1}''')


# PPMS = 'PPMS'
# MPMSold = 'MPMSold'


class EOSException(Exception):
    """Exception to raise if an EOS was encountered"""
    pass


def parse_binary(number: int) -> list:
    """parse an integer number which represents a sum of bits
        returns a list with True and False, from back to front
    """
    # print(number)
    number = int(number)
    nums = list(reversed('{:b}'.format(number)))
    # print(nums)
    for ct, num in enumerate(nums):
        nums[ct] = bool(int(num))
    return nums


def parse_strings(string):
    """parse all strings in one line"""
    a = [[y for y in x if y] for x in searchf_string.findall(string)]
    # second comprehension is to filter for those elements which were found
    # groups which did not match anything appear as empty strings, which are
    # not taken into account - only one type of string definition will be used
    # within one possible match (using | as exclusive OR in the regex pattern)
    for ct, _ in enumerate(a):
        try:
            a[ct] = a[ct][0]
        except IndexError:
            a[ct] = ''
    return a


class Sequence_parser():
    """Abstract Sequence parser, without GUI"""

    def __init__(self, sequence_file: str = None, textnesting: str = '   ', **kwargs):
        """initialise important attributes"""
        super(Sequence_parser, self).__init__(**kwargs)
        self._logger = logging.getLogger(
            __name__ + "." + self.__class__.__name__
        )

        self.sequence_file = sequence_file
        self.textnesting = textnesting
        self.initialize_sequence(self.sequence_file)

    def saving(self) -> None:
        """save serialised versions of a sequence"""
        with open(self.sequence_file_p, 'wb') as output:
            pickle.dump(self.data, output, pickle.HIGHEST_PROTOCOL)
        with open(self.sequence_file_json, 'w') as output:
            output.write(json.dumps(self.data))

    def change_file_location(self, fname: str) -> None:
        self.sequence_file = os.path.splitext(fname)[0] + '.seq'
        self.sequence_file_p = os.path.splitext(self.sequence_file)[0] + '.pkl'
        self.sequence_file_json = os.path.splitext(
            self.sequence_file)[0] + '.json'

    @staticmethod
    def construct_pattern(expressions: list) -> str:
        pat = ''
        for e in expressions:
            pat = pat + r'|' + e
        return pat[1:]

    def initialize_sequence(self, sequence_file: str) -> None:
        """parse a complete file of instructions"""
        if sequence_file:
            self.change_file_location(sequence_file)

            exp = [r'TMP TEMP(.*?)$', r'FLD FIELD(.*?)$', r'SCAN(.*?)$',
                   r'WAITFOR(.*?)$', r'CHN(.*?)$', r'CDF(.*?)$', r'DFC(.*?)$',
                   r'LPI(.*?)$', r'SHT(.*?)DOWN', r'EN(.*?)EOS$', r'RES(.*?)$',
                   r'BEP BEEP(.*?)$', r'CMB CHAMBER(.*?)$', r'REM(.*?)$',
                   r'MVP MOVE(.*?)$', r'MES(.*?)$',
                   ]
            self.p = re.compile(self.construct_pattern(
                exp), re.DOTALL | re.M)  # '(.*?)[^\S]* EOS'

            self.data, self.textsequence = self.read_sequence(sequence_file)

        else:
            self.textsequence = []
            self.data = []
            self.sequence_file = ''

    def read_sequence(self, file: str) -> (list, list):
        """read the whole sequence from a file"""
        with open(file, 'r') as f:
            data = f.readlines()  # .replace('\n', '')

        # preparing variables
        self.jumping_count = [0, 0]
        self.nesting_level = 0
        # parse sequence
        commands, textsequence = self.parse_nesting(data, -1)
        return commands, textsequence

    def parse_nesting(self, lines_file: int, lines_index: int) -> (list, list):
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
            for count, _unused_jump in enumerate(self.jumping_count[:-1]):
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

    def add_text(self, text_list: list, dic: dict) -> None:
        """build the un-nested list of displayed commands"""
        if 'commands' in dic:
            for c in dic['commands']:

                try:
                    text_list.append(dict(DisplayText=c['DisplayText']))
                except KeyError:
                    logger.warning(f'Building Text list: missing DisplayText parameter in {dic}!')
                self.add_text(text_list, c)

    def parse_line(self, lines_file: int, line: str, line_index: int) -> dict:
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
            dic = self.parse_remark(line_found[13])

        elif line_found[14]:
            # set position
            dic = self.parse_set_position(line)

        elif line_found[15]:
            # sequence message
            dic = self.parse_sequence_message(line)

        elif line_found[16]:
            # python exec file
            dic = self.parse_python_exec(line)

        # try:
        #     print(dic)
        # except NameError:
        #     print(line_found)
        # if dic['typ'] is None:
        #     print(line_found)

        return dic

    def parse_scan_arb(self, lines_file: int, line: str, lines_index: int) -> dict:
        """parse a line in which a scan was defined"""
        # parse this scan instructions
        line_found = self.p.findall(line)[0]

        dic = dict(typ=None)
        # if self.device == 'PPMS':
        #     Hidentifier = 'H'
        # elif self.device == 'MPMSold':
        #     Hidentifier = 'B'
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
    def read_nums(comm: str) -> list:
        """convert a string of numbers into a list of floats"""
        return [float(x) for x in searchf_number.findall(comm)]

    @staticmethod
    def parse_binary_dataflags(number: int) -> dict:
        """parse flags what to store"""
        nums = parse_binary(number)
        names = ['General Status', 'Temperature',
                 'Magnetic Field', 'Sample Position',
                 'Chan 1 Resistivity', 'Chan 1 Excitation',
                 'Chan 2 Resistivity', 'Chan 2 Excitation',
                 'Chan 3 Resistivity', 'Chan 3 Excitation',
                 'Chan 4 Resistivity', 'Chan 4 Excitation',

                 'Sig Ch-1 Input Voltage', 'Sig Ch-1 Input Voltage',
                 'Digital Inputs',
                 'Dr Ch-1 Current', 'Dr Ch-1 Power',
                 'Dr Ch-2 Current', 'Dr Ch-2 Power',
                 'Sample Pressure',
                 'Map 20', 'Map 21', 'Map 22', 'Map 23', 'Map 24',
                 'Map 25', 'Map 26', 'Map 27', 'Map 28', 'Map 29',
                 ]
        empty = [False for x in names]
        bare = dict(zip(names, empty))
        bare.update(dict(zip(names, nums)))
        return bare

    @staticmethod
    def displaytext_waiting(data: dict) -> str:
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
    def displaytext_scan_T(data: dict) -> str:
        """generate the displaytext for the temperature scan"""
        return 'Scan Temperature from {start} to {end} in {Nsteps} steps, {SweepRate}K/min, {ApproachMode}, {SpacingCode}'.format(**data)

    @staticmethod
    def displaytext_scan_H(data: dict) -> str:
        """generate the displaytext for the field scan"""
        return 'Scan Field from {start} to {end} in {Nsteps} steps, {SweepRate}K/min, {ApproachMode}, {SpacingCode}, {EndMode}'.format(**data)

    @staticmethod
    def displaytext_set_temp(data: dict) -> str:
        """generate the displaytext for a set temperature"""
        return 'Set Temperature to {Temp} at {SweepRate}K/min, {ApproachMode}'.format(**data)

    @staticmethod
    def displaytext_set_position(data: dict) -> str:
        """generate the displaytext for a set temperature"""
        return 'Move Sample Position to {position} with SpeedIndex {speedindex} ({speedtext}), Mode: {Mode}'.format(**data)

    @staticmethod
    def displaytext_res_scan_exc(data: dict) -> str:
        """generate the displaytext for an excitation scan"""
        # TODO - finish this up
        return 'Scanning RES Excitation'

    @staticmethod
    def displaytext_res(data: dict) -> str:
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
    def displaytext_set_field(data: dict) -> str:
        """generate the displaytext for a set field"""
        return 'Set Field to {Field} at {SweepRate}T/min, {ApproachMode}, {EndMode} '.format(**data)

    @staticmethod
    def displaytext_sequence_message(data: dict) -> str:
        """generate the displaytext for the sequence message"""
        return 'SeqMes {timeout_waiting_min}min, {message_type}, {message_direct}, Email To {email_receiver}, {email_cc}, {email_subject}, {email_message}, attachements: {email_attachement_path}'.format(**data)

    def parse_python_exec(self, file: str) -> dict:
        """parse command to execute python script file -- EXTERNAL !"""
        return dict(typ='exec python', file=file,
                    DisplayText=self.textnesting * (self.nesting_level + 1) +
                    'Exec: {}'.format(file))

    def parse_remark(self, comm: str) -> dict:
        """parse a remark

        This could be overwritten in case the remarks have a special structure
        which could be designed for a certain instrument/measurement"""
        text = comm.strip()
        if text.startswith('python'):
            files = parse_strings(comm)
            return dict(typ='exec python multiple',
                        DisplayText=self.textnesting * self.nesting_level +
                        'Execute python scripts:',
                        commands=[self.parse_python_exec(f) for f in files])

        return dict(typ='remark',
                    text=comm.strip(),
                    DisplayText=self.textnesting * self.nesting_level + comm)

    def parse_chamber(self, comm: str) -> dict:
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

    def parse_set_temp(self, comm: str) -> dict:
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

    def parse_set_field(self, comm: str) -> dict:
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

    def parse_set_position(self, comm: str) -> dict:
        """parse a command to set a single temperature"""
        # TODO: Fast settle
        nums = self.read_nums(comm)
        dic = dict(typ='set_P',
                   position=nums[0],
                   speedindex=int(nums[2]),  # 'Reduction Factor'
                   speedtext=parse_strings(comm)[0])

        if int(nums[1]) == 0:
            dic['Mode'] = 'move to position'
        if int(nums[1]) == 1:
            dic['Mode'] = 'move to index and define'
        if int(nums[1]) == 2:
            dic['Mode'] = 'redefine present position'

        dic['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displaytext_set_position(dic)
        return dic

    def parse_waiting(self, comm: str) -> dict:
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

    def parse_chain_sequence(self, comm: str) -> dict:
        """parse a command to chain a sequence file"""
        file = comm[4:]
        return dict(typ='chain sequence', new_file_seq=file,
                    DisplayText=self.textnesting * self.nesting_level + 'Chain sequence: {}'.format(comm))

    def parse_scan_T(self, comm: str) -> dict:
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

    def parse_scan_H(self, comm: str) -> dict:
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

    def parse_scan_time(self, comm: str) -> dict:
        '''parse command to do a time scan
        (execute commands in scan in certain time intervals)'''
        nums = self.read_nums(comm)
        if len(nums) < 3:
            raise AssertionError(
                'not enough specifying numbers for time-scan!')

        dic = dict(typ='scan_time', time_total=nums[0], Nsteps=nums[1])

        if int(nums[2]) == 0:
            dic['SpacingCode'] = 'uniform'
        if int(nums[2]) == 1:
            dic['SpacingCode'] = 'ln(t)'

        dic['DisplayText'] = self.textnesting * self.nesting_level + \
            'Scan Time {time_total}secs in {Nsteps} steps, {SpacingCode}'.format(
                **dic)
        return dic

    def parse_scan_P(self, comm: str) -> dict:
        '''parse command to scan through positions'''
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

    def parse_beep(self, comm: str) -> dict:
        '''parse a command to beep for a certain time at a certain frequency'''
        nums = self.read_nums(comm)
        if len(nums) < 2:
            raise AssertionError('not enough specifying numbers for beep!')

        dic = dict(typ='beep', length=nums[0], frequency=nums[1])
        dic['DisplayText'] = self.textnesting * self.nesting_level + \
            'Beep for {length}secs at {frequency}Hz'.format(**dic)
        return dic

    def parse_res_change_datafile(self, comm: str) -> dict:
        """parse a command to change the datafile"""
        file = parse_strings(comm)[0]
        return dict(typ='res_change_datafile', new_file_data=file,
                    mode='a' if comm[-1] == '1' else 'w',
                    # a - appending, w - writing, can be inserted
                    # directly into opening statement
                    DisplayText=self.textnesting * self.nesting_level + 'Change data file: {}'.format(file))

    def parse_res_datafilecomment(self, comm: str) -> dict:
        """parse a command to write a comment to the datafile"""
        comment = parse_strings(comm)[0]
        dic = dict(typ='res_datafilecomment',
                   comment=comment,
                   DisplayText=self.textnesting * self.nesting_level +
                   'Datafile Comment: {}'.format(comment))
        return dic

    def parse_res(self, comm: str) -> dict:
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
            bridge_conf[ct]['on_off'] = bool(channel[0] == 2)
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

    def parse_res_scan_excitation(self, comm: str) -> dict:
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
            self.nesting_level + self.displaytext_res_scan_exc(data)
        return data

    def parse_sequence_message(self, comm: str) -> dict:
        """parse a command for a message to the user
        this should block the sequence execution at least
        timeout_waiting_min minutes"""
        nums = self.read_nums(comm)
        strings = parse_strings(comm)
        if nums[1] == 0:
            message_type = 'Information'
        if nums[1] == 1:
            message_type = 'Warning'
        if nums[1] == 2:
            message_type = 'Error'
        try:
            attachement_path = strings[5:]
        except IndexError:
            attachement_path = None

        dic = dict(typ='sequence_message',
                   timeout_waiting_min=nums[0],
                   message_direct=strings[0],
                   email_receiver=strings[1],
                   email_subject=strings[2],
                   email_cc=strings[3],
                   email_message=strings[4],
                   email_attachement_path=attachement_path,
                   message_type=message_type,)
        dic['DisplayText'] = self.textnesting * \
            self.nesting_level + self.displaytext_sequence_message(dic)
        return dic

    @staticmethod
    def parse_res_bridge_setup(nums: list) -> dict:
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
            bridge_setup[ct]['on_off'] = bool(channel[0] == 2)
            bridge_setup[ct]['calibration_mode'] = 'Standard' if channel[
                3] == 0 else 'Fast'
        return bridge_setup
