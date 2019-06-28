# measureSequences

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ba794e9427f0457696a2861f39e04786)](https://app.codacy.com/app/bklebel/measureSequences?utm_source=github.com&utm_medium=referral&utm_content=bklebel/measureSequences&utm_campaign=Badge_Grade_Dashboard)

Tools for an abstract sequence editor, parser and runner

The `Sequence_parser` in `Sequence_parsing.py` can read PPMS (resistivity option) sequence files
The `Sequence_runner` in `runSequences.py` contains all logic to run those sequences - however, this is must be inherited: There are many functions which need to be overridden or injected in order to function properly. A demonstration printing-dummy class can be found in `Dummy.py`

Most of the generic commands are implemented. It is possible to read arbitrarily nested scanning commands. Empty lines are ignored. In contrast to the logic in the PPMS, when chaining an additional sequence, after the completion of the chained sequence, the mother-sequence continues after the `chain_sequence` command. 
Most of the running functionality has not yet been tested -- use at your own risk! 

Commands implemented include:
-   setting a temperature
-   setting a field
-   setting a position
-   scanning temperature
-   scanning field
-   scanning position
-   scanning time
-   Shutdown
-   producing sound (Beep)
-   waiting
-   chain another sequence
-   chamber operations
-   showing a sequence file remark

Commands only implemented in parsing:
-   change the resistivity datafile
-   print a res datafile comment
-   measure resistivity
-   scanning res excitations

Saving a serialised version will write a pickled object and a json file, containing a list with all commands (dictionaries). No reasonable sequences can be written so far, using the PPMS Sequence editor is recommended.
Currently the sequence editor lives outside of the general application (Sequence_editor.py). 
