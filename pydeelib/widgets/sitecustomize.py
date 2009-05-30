# -*- coding: utf-8 -*-

# Set standard outputs encoding:
# (otherwise, for example, print u"é" will fail)

import locale, sys
sys.setdefaultencoding( locale.getdefaultlocale()[1] )