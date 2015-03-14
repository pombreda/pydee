This page is not updated as often as it should be: [Mercurial history logs](http://code.google.com/p/pydee/source/list) may be interesting to look at to have an up-to-date overview of Pydee features.

## Pydee features ##
_(not exhaustive)_
  * **Pydee options** (type pydee --help to see all available options):
    1. 'light' option (i.e. -l or --light) to disable all widgets except the shell and the working directory changer
> > 2. 'modules' option, i.e. -m or --modules followed by a comma separated (without spaces) list of module names to be imported at startup
> > 3. 's' (or --startup): specify a startup script (overrides _PYTHONSTARTUP_ script)
  * **Shell**:
    1. Scintilla's code completion
> > 2. filename/dirname completion (press Tab after a " or ' character)
> > 3. Calltips: object's documentation or arguments (if callable)
> > 4. PYTHONSTARTUP script is executed at startup
> > 5. IPython-like 'run', 'edit', 'cls' and system commands (using prefix '!', e.g. !ls or !dir)
> > 6. IPython's deep reload function as builtin reload replacement
> > 7. 'xedit' command to edit script in an external editor
> > 8. 'oedit' function to edit object in a GUI-based editor (dictionaries, lists, tuples, arrays, strings, ...)
> > 9. Find/replace with a Firefox-like widget (not a pop-up window)
  * **DocViewer**:
    1. Automatic documentation on every callable object written in console
> > 2. History
> > 3. Find/replace with a Firefox-like widget (not a pop-up window)
  * **Editor**:
    1. Multiple file support
> > 2. Find/replace with a Firefox-like widget (not a pop-up window)
> > 3. ...

See below for a short descript of available widgets.

## Pydee's PyQt4 widgets ##
Here are examples of available PyQt4 widgets:

  * **Shell**, a Python shell with useful options (like a '-os' switch for importing os and os.path as osp, a '-pylab' switch for importing matplotlib in interactive mode, ...) and advanced features like code completion (requires !QScintilla, i.e. module PyQt4.Qsci)

  * **WorkingDirectory**: shows the current directory and allows to change it

  * **Editor**: multiline Python code editor with syntax coloration and code-completion

  * **HistoryLog**: read-only colorated editor containing history

  * **DocViewer**: a widget to show documentation on an object (docstring) either by entering its reference manually or automatically when you type the reference in the console

  * **ArrayEditor**: NumPy arrays editor with optional background coloring

  * **DictEditor**: dict/list editor (and tuple read-only 'editor')

  * **Workspace**: shows globals() list with some properties for each global (e.g. value for int or float, min and max values for arrays, ...) and allows to open an appropriate GUI editor

**Pydee** stores its settings in _.pydee.ini_, a configuration file in your home directory (on Windows: C:\Documents and Settings\%username%). Thanks to this .ini file, a lot of features of Pydee may be enabled, disabled or tweaked.