# -*- coding: utf-8 -*-
"""Widgets used only if QScintilla is not installed"""

from PyQt4.QtGui import QTextEdit, QTextCursor, qApp, QColor, QBrush
from PyQt4.QtCore import Qt, QString, SIGNAL

# Local import
from shell import Interpreter, create_banner
from config import get_font


def is_python_string(text):
    """ Return True if text is enclosed by a string mark """
    return (
         (text.startswith("'''") and text.endswith("'''")) or
         (text.startswith('"""') and text.endswith('"""')) or
         (text.startswith("'") and text.endswith("'")) or
         (text.startswith('"') and text.endswith('"')) 
         )

KEYWORDS = set(["and", "del", "from", "not", "while",
            "as", "elif", "global", "or", "with",
            "assert", "else", "if", "pass", "yield",
            "break", "except", "import", "print",
            "class", "exec", "in", "raise",              
            "continue", "finally", "is", "return",
            "def", "for", "lambda", "try"])

def get_color(word):
    """Return a color depending of the string word"""
    stripped = word.strip()
    if(stripped in KEYWORDS):
        return Qt.blue
    elif(is_python_string(stripped)):
        return Qt.darkGreen
    else:
        return Qt.black


class QtEditor(QTextEdit):
    """
    Qt-based Editor Widget
    """
    def __init__(self, parent=None):
        super(QtEditor, self).__init__(parent)
        self.is_modified = False
        
    def isModified(self):
        return self.is_modified
    
    def setModified(self, state):
        self.is_modified = state
        
    def setCursorPosition(self, arg1, arg2):
        pass
    
    def lines(self):
        return 0
    
    def setup_api(self):
        pass

    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        if enable:
            self.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.setLineWrapMode(QTextEdit.NoWrap)

    def set_font(self, font):
        pass
    
    def setup_margin(self, font, width=None):
        """Set margin font and width"""
        pass
           
    def go_to_line(self, linenb):
        """Go to line number"""
        pass
        
    def set_text(self, str):
        """Set the text of the editor"""
        self.setPlainText(str)

    def get_text(self):
        """Return editor text"""
        return self.toPlainText()


class QtShell(QTextEdit, Interpreter):
    """
    Python shell based on Qt only
    Derived from:
        PyCute (pycute.py): http://gerard.vermeulen.free.fr (GPL)
    """    
    def __init__(self, namespace=None, commands=None,
                 message="", parent=None, debug=False, exitfunc=None):
        """
        namespace : locals send to InteractiveInterpreter object
        commands: list of commands executed at startup
        message : welcome message string
        parent : specifies the parent widget
        If no parent widget has been specified, it is possible to
        exit the interpreter by Ctrl-D
        """
        Interpreter.__init__(self, namespace, commands, debug, exitfunc)       
        QTextEdit.__init__(self, parent)
                        
        self.set_font( get_font('shell') )
        
        # to exit the main interpreter by a Ctrl-D if PyCute has no parent
        if parent is None:
            self.eofKey = Qt.Key_D
        else:
            self.eofKey = None
        
        # last line + last incomplete lines
        self.line    = QString()
        self.lines   = []
        # the cursor position in the last line
        self.point   = 0
        # flag: the interpreter needs more input to run the last lines. 
        self.more    = 0
        self.pointer = 0
        self.cursor_pos   = 0

        # user interface setup
        #self.setLineWrapMode(QTextEdit.NoWrap)

        # interpreter banner
        moreinfo, _ = self.get_banner()
        self.write( create_banner(moreinfo, message) )
        self.write(self.tr('Please install QScintilla to enable auto-completion and calltips')+':'+
                   '\n'+'http://www.riverbankcomputing.co.uk/qscintilla\n\n')
        self.write(self.prompt)
        self.emit(SIGNAL("status(QString)"), QString())
        
    
    def set_docviewer(self, arg):
        pass
    
    def get_banner(self):
        """Return interpreter banner and a one-line message"""
        return (self.tr('Type "copyright", "credits" or "license" for more information.'), )      

    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        if enable:
            self.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.setLineWrapMode(QTextEdit.NoWrap)
                
    def set_font(self, font):
        """Set shell font"""
        self.font = font    

    def readline(self):
        """
        Simulate stdin, stdout, and stderr.
        """
        self.reading = 1
        self.__clear_line()
        self.moveCursor(QTextCursor.End)
        while self.reading:
            qApp.processOneEvent()
        if self.line.length() == 0:
            return '\n'
        else:
            return str(self.line) 

    
    def write(self, text):
        """
        Simulate stdin, stdout, and stderr.
        """
        # The output of self.append(text) contains to many newline characters,
        # so work around QTextEdit's policy for handling newline characters.

        cursor = self.textCursor()

        cursor.movePosition(QTextCursor.End)

        pos1 = cursor.position()
        cursor.insertText(text)

        self.cursor_pos = cursor.position()
        self.setTextCursor(cursor)
        self.ensureCursorVisible ()

        # Set the format
        cursor.setPosition(pos1, QTextCursor.KeepAnchor)
        format = cursor.charFormat()
        format.setForeground(QBrush(Qt.black))
        format.setFont(self.font)
        cursor.setCharFormat(format)


    def writelines(self, text):
        """
        Simulate stdin, stdout, and stderr.
        """
        map(self.write, text)


    def __run(self):
        """
        Append the last line to the history list, let the interpreter execute
        the last line(s), and clean up accounting for the interpreter results:
        (1) the interpreter succeeds
        (2) the interpreter fails, finds no errors and wants more line(s)
        (3) the interpreter fails, finds errors and writes them to sys.stderr
        """
        self.add_to_history(self.line)
        self.pointer = 0
        try:
            self.lines.append(str(self.line))
        except Exception,e:
            print e

        self.emit(SIGNAL("status(QString)"), self.tr('Busy...'))
        
        source = '\n'.join(self.lines)
        self.more = self.runsource(source)

        if self.more:
            self.write(self.prompt_more)
        else:
            self.write(self.prompt)
            self.lines = []
        self.__clear_line()
        
        self.emit(SIGNAL("status(QString)"), QString())
        self.emit(SIGNAL("refresh()"))
        
    def __clear_line(self):
        """
        Clear input line buffer
        """
        self.line.truncate(0)
        self.point = 0

        
    def __insert_text(self, text):
        """
        Insert text at the current cursor position.
        """

        self.line.insert(self.point, text)
        self.point += text.length()

        cursor = self.textCursor()
        cursor.insertText(text)
        self.color_line()


    def keyPressEvent(self, e):
        """
        Handle user input a key at a time.
        """
        text  = e.text()
        key   = e.key()

        if key == Qt.Key_Backspace:
            if self.point:
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.PreviousCharacter,
                                    QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                self.color_line()
            
                self.point -= 1 
                self.line.remove(self.point, 1)

        elif key == Qt.Key_Delete:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.NextCharacter,
                                QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.color_line()
                        
            self.line.remove(self.point, 1)
            
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            self.write('\n')
            if self.reading:
                self.reading = 0
            else:
                self.__run()
                
        elif key == Qt.Key_Tab:
            self.__insert_text(text)
        elif key == Qt.Key_Left:
            if self.point : 
                self.moveCursor(QTextCursor.Left)
                self.point -= 1 
        elif key == Qt.Key_Right:
            if self.point < self.line.length():
                self.moveCursor(QTextCursor.Right)
                self.point += 1 

        elif key == Qt.Key_Home:
            cursor = self.textCursor ()
            cursor.setPosition(self.cursor_pos)
            self.setTextCursor (cursor)
            self.point = 0 

        elif key == Qt.Key_End:
            self.moveCursor(QTextCursor.EndOfLine)
            self.point = self.line.length() 

        elif key == Qt.Key_Up:
            if len(self.history):
                if self.pointer == 0:
                    self.pointer = len(self.history)
                self.pointer -= 1
                self.__recall()
                
        elif key == Qt.Key_Down:
            if len(self.history):
                self.pointer += 1
                if self.pointer == len(self.history):
                    self.pointer = 0
                self.__recall()

        elif text.length():
            self.__insert_text(text)
            return

        else:
            e.ignore()


    def __recall(self):
        """
        Display the current item from the command history.
        """
        cursor = self.textCursor ()
        cursor.select( QTextCursor.LineUnderCursor )
        cursor.removeSelectedText()

        if self.more:
            self.write(self.prompt_more)
        else:
            self.write(self.prompt)
            
        self.__clear_line()
        self.__insert_text( QString(self.history[self.pointer]) )


    def mousePressEvent(self, e):
        """Keep the cursor after the last prompt"""
        if e.button() == Qt.LeftButton:
            self.moveCursor(QTextCursor.End)
            

    def contentsContextMenuEvent(self,ev):
        """Suppress the right button context menu"""
        pass
    
    
    def color_line(self):
        """Color the current line"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine)

        newpos = cursor.position()
        pos = -1
        
        while(newpos != pos):
            cursor.movePosition(QTextCursor.NextWord)

            pos = newpos
            newpos = cursor.position()

            cursor.select(QTextCursor.WordUnderCursor)
            word = str(cursor.selectedText ().toAscii())

            if not word:
                continue
                        
            format = cursor.charFormat()
            format.setForeground( QBrush(QColor( get_color(word) )))
            cursor.setCharFormat(format)

