# measureSequences

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ba794e9427f0457696a2861f39e04786)](https://app.codacy.com/app/bklebel/measureSequences?utm_source=github.com&utm_medium=referral&utm_content=bklebel/measureSequences&utm_campaign=Badge_Grade_Dashboard)

Tools for an abstract sequence editor, parser and runner

### Main Functions
-   The `Sequence_parser` in `Sequence_parsing.py` can read PPMS (measurements: resistivity only) sequence files. 
-   The `Sequence_runner` in `runSequences.py` contains all logic to run those sequences - however, this must be inherited: There are many functions which need to be overridden or injected in order to - function properly. 
    -   A demonstration printing-dummy class can be found in `Dummy.py`. 
-   The `Sequence_builder` in `Sequence_editor.py` can display the parsed sequences. There exists a start of classes and functions tfor actually editing and building sequences, they are however woefully incomplete, feel free to contribute here!

### Features/Behaviour
-   Most of the generic commands are implemented. 
-   It is possible to read arbitrarily nested scanning commands. 
-   Empty lines are ignored. 
-   In contrast to the logic in the PPMS, when chaining an additional sequence, after the completion of the chained sequence, the mother-sequence continues after the `chain_sequence` command (multiple nesting allowed too). 
-   Saving a serialised version of the parsed sequence will write a pickled object and a json file, containing a list with all commands (dictionaries). No reasonable sequences can be written so far, using MultiVu is recommended.

Most of the running functionality has not yet been tested -- **use at your own risk!** 

Missing functionality in running Sequences is partially documented in issues on [GitHub](https://github.com/bklebel/measureSequences). 



### Installing

Install with pip: 
update to newest version:
`pip install --upgrade git+https://github.com/bklebel/measureSequences@master`

latest stable release: 
`pip install https://github.com/bklebel/measureSequences/archive/0.1.9.tar.gz`
