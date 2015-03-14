# Introduction #

Pydee currently provides two kinds of GUI-integrated Python shell:
  * the **InteractiveShell**: it inherits InteractiveConsole (from the Python standard module [code](http://docs.python.org/library/code.html)) and runs a Python interpreter (not a real one actually, just an "emulation") in the same thread as the main application, allowing to implement easily interesting and powerful introspection features such as the _Workspace_ plugin but blocking the whole software during the execution of a slow script
  * the **ExternalShell**: it runs a Python interpreter in a separate process (QProcess instance) and may interact with it almost like with the InteractiveShell (however, the _Workspace_ plugin is not supported with this shell, and the _DocViewer_ plugin is supported only for standard modules or so)

# IPython #

In the _InteractiveShell_, it could be interesting to replace _code.InteractiveConsole_ by IPython.
## Pros ##
  * [IPython](http://ipython.scipy.org) is a powerful interactive shell adding enhanced introspection, additional shell syntax, code highlighting, tab completion and matplotlib integration (handling GUI event loops) to the standard Python interpreter
## Cons ##
  * Is it really necessary? IPython is a powerful interactive tool if you're using it from a classic text-based terminal. But, from a GUI-based console which already supports code instropection, code highlighting, code completion and of course matplotlib integration (which is easier to handle in a GUI-based environment: no more GUI event loops to handle), is it really necessary? To be completely honest, there are some features missing in Pydee:
    1. the %who and %whos commands: useless in Pydee thanks to the _Workspace_ plugin
    1. IPython debugger: in Pydee, only the Python debugger (pdb) is supported indeed
    1. the %cd magic command: useless in Pydee thanks to _File explorer_ and _Working directory_ plugins
    1. of course, there are certainly other features missing in Pydee that I don't know about
  * debugging will be more complicated with this additionnal layer
  * as soon as IPython is embedded in your application, you may kiss all your IDEs goodbye -- IPython has to tweak standard I/O so that every IDE I know will raise an error in IPython at execution (of course, if you run your program from a terminal, it will work but Eclipse/Pydev or WingIDE debuggers won't)
  * integrating IPython in Pydee adds a dependency upon _IPython.frontend_, a module which API is still evolving rapidly from a version to another -- meaning that it will add another dependency version constraint to Pydee which is not a good thing at all

## IPython integration plans ##

### May 2009 ###

Pydee v0.5.0 will integrate an IPython shell:

  * phase #1: Gaël Varoquaux wrote "wx\_frontend.py" (http://bazaar.launchpad.net/~ipython-dev/ipython/trunk/files/head%3A/IPython/frontend/wx/), let's implement its PyQt4?'s counterpart (https://code.launchpad.net/~pierre-raybaut/ipython/qt_frontend)
  * phase #2: merge this code ("qt\_frontend.py") to PyQtShell?'s code

Currently phase #1 is started and related code is expected to be mature at the end of May.<br>
Phase #2 will follow and hopefully Pydee 0.5.0 will be released before the end of June.<br>
<br>
<h3>June 2009</h3>

The previous paragraph is still correct but there won't be a v0.5.0 release ;-)<br>
So basically IPython integration has become optional for the forthcoming v1.0.0 (see <a href='Roadmap.md'>Roadmap</a>).