# measureSequences

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ba794e9427f0457696a2861f39e04786)](https://app.codacy.com/app/bklebel/measureSequences?utm_source=github.com&utm_medium=referral&utm_content=bklebel/measureSequences&utm_campaign=Badge_Grade_Dashboard)

Tools for an abstract sequence editor, parser and runner

It can read PPMS (resistivity option) sequence files - an abstract class to run those sequences is being built currently.

Most of the generic commands are now implemented (in reading). It is possible to read arbitrarily nested scanning commands. Empty lines are ignored.  

Commands implemented include:
-   setting a temperature
-   setting a field
-   scanning temperature
-   scanning field
-   scanning position
-   scanning time
-   Shutdown
-   producing sound (Beep)
-   waiting
-   chain another sequence
-   chamber operations

-   change the resistivity datafile
-   print a res datafile comment
-   measure resistivity
-   scanning res excitations

Saving a serialised version will write a pickled object and a json file, containing a list with all commands (dictionaries). No reasonable sequences can be written so far, using the PPMS Sequence editor is recommended.
Currently the sequence editor lives outside of the general application (Sequence_editor.py). 
