Overview
========

Pydee is a Python development environment with the following features:

:doc:`editor`:
    Multi-language editor with function/class browser, code
    analysis (pyflakes and pylint are currently supported), horizontal/vertical
    splitting, etc.
    
:doc:`docviewer`:
    Automatically show documentation (if available, or 
    source code otherwise) for any class instantiation or function call made
    in a Python shell (interactive/external console, see below)
    
:doc:`console`:
    Python shell with workspace support (variable explorer with GUI based 
    editors: dictionary editor, array editor, ...) and matplotlib figures 
    integration
    
:doc:`extconsole` (separate process):
    Run Python scripts (interactive, debugging or normal mode) or open a Python 
    interpreter with variable explorer and documentation viewer support (a basic
    terminal window may also be opened with the external console)
    
:doc:`explorer`:
    File/directory explorer
    
Find in files feature:
    Supporting regular expressions and mercurial repositories
    
:doc:`historylog`

Pydee may also be used as a PyQt4 extension library (module 'pydeelib').
For example, the Python interactive shell widget used in Pydee may be
embedded in your own PyQt4 application.            
