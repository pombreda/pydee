# Supported platforms #

Pydee has been successfully tested on Microsoft Windows XP/Vista, GNU/Linux and MacOS X.


# Installation instructions #

## Requirements ##

Pydee requires:
  * Python 2.x (x>=5)
  * PyQt4 4.x (x>=3 ; recommended x>=4) with !QScintilla2
  * optional modules for Pydee: numpy (N-dimensional arrays), scipy (signal/image processing), matplotlib (2D plotting)

## Installing Pydee on Linux ##

Installing on Ubuntu:
  * Requirements: sudo apt-get install python-qscintilla2

Using setuptools:
  * Installing (.egg file): sudo easy\_install pydee
  * Updating: sudo easy\_install -U pydee

Using distutils:
  * Download and extract files from the source package (pydee-[version](version.md).tar.gz)
  * Install: sudo python setup.py install

## Installing Pydee on Windows XP/Vista ##

The easy way (thanks to Python(x,y)):
  * Requirements and optional modules: download/install Python(x,y)
  * Pydee is already included in Python(x,y)

Updating Pydee in Python(x,y):
  * Updating Python(x,y) will update Pydee if necessary (Python(x,y) is updated ~monthly)
  * Updating Pydee manually - option 1 (the easiest): from here
  * Updating Pydee manually - option 2: if the Python(x,y) plugin is outdated, either be patient (it certainly won't be outdated for long...) or uninstall the Pydee plugin and install the .msi installer available from this page

The "hard" way:
  * Requirements: Python language, PyQt4 with QScintilla2
  * Optional modules: numpy, scipy, matplotlib
  * Installing Pydee itself: download/install the .msi file available from this page
  * Updating Pydee: please do not forget to uninstall any previous .msi Pydee package before installing a new one (note: you may mix .msi installers and Python(x,y) plugins if you uninstall any previous version before installing a new one)