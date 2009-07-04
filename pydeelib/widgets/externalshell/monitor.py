# -*- coding: utf-8 -*-
"""External shell's monitor"""

import threading, socket, traceback, thread
import StringIO, pickle, struct
from PyQt4.QtCore import QThread, SIGNAL

from pydeelib.config import CONF, str2type
from pydeelib.dochelpers import getargtxt
from pydeelib.widgets.dicteditor import (get_type, get_size, get_color,
                                         value_to_display, globalsfilter)


FILTERS = tuple(str2type(CONF.get('external_shell', 'globalsexplorer/filters')))
ITERMAX = CONF.get('external_shell', 'globalsexplorer/itermax')
EXCLUDE_PRIVATE = CONF.get('external_shell', 'globalsexplorer/exclude_private')
EXCLUDE_UPPER = CONF.get('external_shell', 'globalsexplorer/exclude_upper')
EXCLUDE_UNSUPPORTED = CONF.get('external_shell',
                               'globalsexplorer/exclude_unsupported_datatypes')
EXCLUDED_NAMES = CONF.get('external_shell', 'globalsexplorer/excluded')

def glexp_make(data):
    """
    Make a remote view of dictionary *data*
    -> globals explorer
    """
    data = globalsfilter(data, itermax=ITERMAX, filters=FILTERS,
                         exclude_private=EXCLUDE_PRIVATE,
                         exclude_upper=EXCLUDE_UPPER,
                         exclude_unsupported=EXCLUDE_UNSUPPORTED,
                         excluded_names=EXCLUDED_NAMES)
    remote = {}
    for key, value in data.iteritems():
        remote[key] = {'type': get_type(value),
                       'size': get_size(value),
                       'color': get_color(value),
                       'view': value_to_display(value)}
    return remote
    

SZ = struct.calcsize("l")

def write_packet(sock, data):
    """Write *data* to socket *sock*"""
    sock.send(struct.pack("l", len(data)) + data)

def read_packet(sock):
    """Read data from socket *sock*"""
    datalen = sock.recv(SZ)
    dlen, = struct.unpack("l", datalen)
    data = ''
    while len(data) < dlen:
        data += sock.recv(dlen)
    return data

def communicate(sock, input, pickle_try=False):
    """Communicate with monitor"""
    write_packet(sock, input)
    output = read_packet(sock)
    if pickle_try:
        try:
            return pickle.loads(output)
        except EOFError:
            pass
    else:
        return output

def monitor_get_value(sock, name):
    """Get global variable *name* value"""
    return communicate(sock, name, pickle_try=True)

def monitor_set_value(sock, name, value):
    """Set global variable *name* value to *value*"""
    write_packet(sock, '__set_value__()')
    write_packet(sock, name)
    write_packet(sock, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
    read_packet(sock)


class Monitor(threading.Thread):
    """Monitor server"""
    def __init__(self, host, port, shell_id):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.request = socket.socket( socket.AF_INET )
        self.request.connect( (host, port) )
        write_packet(self.request, shell_id)
        self.locals = {"setlocal": self.setlocal,
                       "getargtxt": getargtxt,
                       "glexp_make": glexp_make,
                       "thread": thread,
                       "__set_value__": self.set_global_value,
                       "_" : None}
        
    def setlocal(self, name, value):
        """
        Set local reference value
        Not used right now - could be useful in the future
        """
        self.locals[name] = value
        
    def refresh(self):
        """
        Refresh Globals explorer in ExternalPythonShell
        """
        self.request.send("x", socket.MSG_OOB)
        
    def set_global_value(self):
        """
        Set global reference value
        """
        from __main__ import __dict__ as glbs
        name = read_packet(self.request)
        value = pickle.loads(read_packet(self.request))
        glbs[name] = value
        
    def run(self):
        from __main__ import __dict__ as glbs
        while True:
            try:
                command = read_packet(self.request)
                result = eval(command, glbs, self.locals)
                self.locals["_"] = result
                output = pickle.dumps(result, pickle.HIGHEST_PROTOCOL)
                write_packet(self.request, output)
            except StandardError:
                out = StringIO.StringIO()
                traceback.print_exc(file=out)
                data = out.getvalue()
                write_packet(self.request, data)


PYDEE_PORT = 20128

def select_port(port=20128):
    """Find and return a non used port"""
    while True:
        try:
            sock = socket.socket(socket.AF_INET,
                                 socket.SOCK_STREAM,
                                 socket.IPPROTO_TCP)
#            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind( ("127.0.0.1", port) )
        except socket.error, _msg:
            port += 1
        else:
            break
        finally:
            sock.close()
            sock = None
    return port


class Server(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.shells = {}
        global PYDEE_PORT
        PYDEE_PORT = select_port()
        
    def register(self, shell_id, shell):
        nt = NotificationThread(shell)
        self.shells[shell_id] = nt
        return nt
        
    def run(self):
        s = socket.socket(socket.AF_INET)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind( ("127.0.0.1", PYDEE_PORT) )
        
        while True:
            s.listen(2)
            s2, _addr = s.accept()
            shell_id = read_packet(s2)
            self.shells[shell_id].shell.monitor_socket = s2
            self.shells[shell_id].start()

SERVER = None

def start_server():
    """Start server only one time"""
    global SERVER
    if SERVER is None:
        SERVER = Server()
        SERVER.start()
    return SERVER, PYDEE_PORT


class NotificationThread(QThread):
    def __init__(self, shell):
        QThread.__init__(self, shell)
        self.shell = shell
        
    def run(self):
        while True:
            try:
                _d = self.shell.monitor_socket.recv(1, socket.MSG_OOB)
                self.emit(SIGNAL('refresh()'))
            except socket.error:
                # Connection closed
                break
