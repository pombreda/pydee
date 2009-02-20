# -*- coding: utf-8 -*-
"""
Text encoding utilities, text file I/O

Functions 'get_coding', 'decode', 'encode' and 'to_unicode' come from Eric4
source code (Utilities/__init___.py) Copyright © 2003-2009 Detlev Offenbach
"""

import re, os, locale
from codecs import BOM_UTF8, BOM_UTF16, BOM_UTF32
from PyQt4.QtCore import QString

def transcode(text, input_encoding=None, output_encoding='utf-8'):
    """Transcode a text string"""
    if input_encoding is None:
        input_encoding = locale.getpreferredencoding()
    return unicode(text.decode(input_encoding).encode(output_encoding))

CODING_RE = re.compile(r"coding[:=]\s*([-\w_.]+)")
CODECS = ['utf-8', 'iso8859-1',  'iso8859-15', 'koi8-r', 'koi8-u',
          'iso8859-2', 'iso8859-3', 'iso8859-4', 'iso8859-5', 
          'iso8859-6', 'iso8859-7', 'iso8859-8', 'iso8859-9', 
          'iso8859-10', 'iso8859-13', 'iso8859-14', 'latin-1', 
          'utf-16']
    
def get_coding(text):
    """
    Function to get the coding of a text.
    @param text text to inspect (string)
    @return coding string
    """
    for line in text.splitlines()[:2]:
        result = CODING_RE.search(line)
        if result:
            return result.group(1)
    return None

def decode(text):
    """
    Function to decode a text.
    @param text text to decode (string)
    @return decoded text and encoding
    """
    try:
        if text.startswith(BOM_UTF8):
            # UTF-8 with BOM
            return unicode(text[len(BOM_UTF8):], 'utf-8'), 'utf-8-bom'
        elif text.startswith(BOM_UTF16):
            # UTF-16 with BOM
            return unicode(text[len(BOM_UTF16):], 'utf-16'), 'utf-16'
        elif text.startswith(BOM_UTF32):
            # UTF-32 with BOM
            return unicode(text[len(BOM_UTF32):], 'utf-32'), 'utf-32'
        coding = get_coding(text)
        if coding:
            return unicode(text, coding), coding
    except (UnicodeError, LookupError):
        pass
    # Assume UTF-8
    try:
        return unicode(text, 'utf-8'), 'utf-8-guessed'
    except (UnicodeError, LookupError):
        pass
    # Assume Latin-1 (behaviour before 3.7.1)
    return unicode(text, "latin-1"), 'latin-1-guessed'

def encode(text, orig_coding):
    """
    Function to encode a text.
    @param text text to encode (string)
    @param orig_coding type of the original coding (string)
    @return encoded text and encoding
    """
    if orig_coding == 'utf-8-bom':
        return BOM_UTF8 + text.encode("utf-8"), 'utf-8-bom'
    
    # Try declared coding spec
    coding = get_coding(text)
    if coding:
        try:
            return text.encode(coding), coding
        except (UnicodeError, LookupError):
            raise RuntimeError("Incorrect encoding (%s)" % coding)
    if orig_coding and orig_coding.endswith('-default'):
        coding = orig_coding.replace("-default", "")
        try:
            return text.encode(coding), coding
        except (UnicodeError, LookupError):
            pass
    if orig_coding == 'utf-8-guessed':
        return text.encode('utf-8'), 'utf-8'
    
    # Try saving as ASCII
    try:
        return text.encode('ascii'), 'ascii'
    except UnicodeError:
        pass
    
    # Save as UTF-8 without BOM
    return text.encode('utf-8'), 'utf-8'
    
def to_unicode(string):
    """
    Public method to convert a string to unicode.
    
    If the passed in string is of type QString, it is
    simply returned unaltered, assuming, that it is already
    a unicode string. For all other strings, various codes
    are tried until one converts the string without an error.
    If all codecs fail, the string is returned unaltered.
    
    @param s string to be converted (string or QString)
    @return converted string (unicode or QString)
    """
    if isinstance(string, QString):
        return string
    
    if type(string) is type(u""):
        return string
    
    for codec in CODECS:
        try:
            unic = unicode(string, codec)
        except UnicodeError:
            pass
        except TypeError:
            break
        else:
            return unic
    
    # we didn't succeed
    return string
    

def write(text, filename, encoding='utf-8'):
    """
    Write 'text' to file ('filename') assuming 'encoding'
    Return (eventually new) encoding
    """
    text, encoding = encode(text, encoding)
    file(filename, 'wb').write(text)
    return encoding

def writelines(lines, filename, encoding='utf-8'):
    """
    Write 'lines' to file ('filename') assuming 'encoding'
    Return (eventually new) encoding
    """
    return write(os.linesep.join(lines), filename, encoding)

def read(filename, encoding='utf-8'):
    """
    Read text from file ('filename')
    Return text and encoding
    """
    text, encoding = decode( file(filename, 'rb').read() )
    return text, encoding

def readlines(filename, encoding='utf-8'):
    """
    Read lines from file ('filename')
    Return lines and encoding
    """
    text, encoding = read(filename, encoding)
    return text.split(os.linesep), encoding