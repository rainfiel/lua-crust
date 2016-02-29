#-*- coding:utf-8 -*-
"""Interpreter executes Python commands."""

__author__ = "Patrick K. O'Brien <pobrien@orbtech.com> / "
__author__ += "David N. Mashburn <david.n.mashburn@gmail.com>"
__cvsid__ = "$Id$"
__revision__ = "$Revision$"[11:-2]

import os
import re
import sys
import json
from code import InteractiveInterpreter, compile_command
from wx.py import dispatcher
from wx.py import introspect
import wx
import socket

end_pattern = re.compile(r".*'end' expected .*near \<eof\>$")

class Interpreter(InteractiveInterpreter):
    """Interpreter based on code.InteractiveInterpreter."""
    
    revision = __revision__
    
    def __init__(self, locals=None, rawin=None, 
                 stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
                 showInterpIntro=True):
        """Create an interactive interpreter object."""
        if not locals:
            locals = {}
        locals['connect'] = self.connect
        InteractiveInterpreter.__init__(self, locals=locals)
        self.lua_locals = {}
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        if rawin:
            import __builtin__
            __builtin__.raw_input = rawin
            del __builtin__
        if showInterpIntro:
            self.introText = 'Inspect the ejoy2dx client'
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = '>>> '
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = '... '
        self.more = 0
        # List of lists to support recursive push().
        self.commandBuffer = []
        self.startupScript = None

        self.socket = None

    def log(self, txt):
        self.locals['pp'](txt)

    def connect(self, ip, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(3)
        self.socket.connect((ip, port))
        self.socket.settimeout(0.3)
        print("--> connection established, find available api in \'Namespace\'")
        self.push("help()")
        self.push("env()")

    def disconnect(self):
        self.socket.close()
        self.socket = None
        print("--> disconnected")

    def push(self, command, astMod=None):
        """Send command to the interpreter to be executed.
        
        Because this may be called recursively, we append a new list
        onto the commandBuffer list and then append commands into
        that.  If the passed in command is part of a multi-line
        command we keep appending the pieces to the last list in
        commandBuffer until we have a complete command. If not, we
        delete that last list."""
        
        # In case the command is unicode try encoding it
        if type(command) == unicode:
            try:
                command = command.encode(wx.GetDefaultPyEncoding())
            except UnicodeEncodeError:
                pass # otherwise leave it alone

        if not self.more:
            try: del self.commandBuffer[-1]
            except IndexError: pass
        if not self.more: self.commandBuffer.append([])
        self.commandBuffer[-1].append(command)
        source = '\n'.join(self.commandBuffer[-1])
        
        # If an ast code module is passed, pass it to runModule instead
        more = self.more = self.runsource(source)
        dispatcher.send(signal='Interpreter.push', sender=self,
                        command=command, more=more, source=source)
        return more

    def rmt_run(self, txt):
        try:
            self.socket.send(txt)
        except Exception, e:
            if e != socket.timeout:
                self.disconnect()
            else:
                print("run failed, pls retry")
            return
        
        ret = ""
        while True:
            try:
                ret += self.socket.recv(256)
            except Exception, e:
                # print(str(e)+str(len(ret)))
                if e == socket.error:
                    self.disconnect()
                if len(ret) > 0:
                    break
        if ret == "":
            return False

        self.log(ret)
        data = json.loads(ret)
        if data['type'] == "result" or data['type'] == "error":
            msg = data.get('msg')
            if msg:
                if end_pattern.match(msg):  #need more input to complete function
                    return True
                else:
                    print(msg)
        elif data['type'] == "env":
            self.lua_locals.clear()
            data = json.loads(data['msg'])
            for k, v in data.iteritems():
                self.lua_locals[k] = v
        elif data['type'] == "disconnect":
            self.disconnect()
        elif data['type'] == "help":
            self.locals['filling'].help_doc = json.loads(data['msg'])
        return False

    def addsource(self, source):
        stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
        sys.stdin, sys.stdout, sys.stderr = \
                   self.stdin, self.stdout, self.stderr
        # more = InteractiveInterpreter.runsource(self, source)
        # this was a cute idea, but didn't work...
        #more = self.runcode(compile(source,'',
        #               ('exec' if self.useExecMode else 'single')))
        
        print(source)

        # If sys.std* is still what we set it to, then restore it.
        # But, if the executed source changed sys.std*, assume it was
        # meant to be changed and leave it. Power to the people.
        if sys.stdin == self.stdin:
            sys.stdin = stdin
        else:
            self.stdin = sys.stdin
        if sys.stdout == self.stdout:
            sys.stdout = stdout
        else:
            self.stdout = sys.stdout
        if sys.stderr == self.stderr:
            sys.stderr = stderr
        else:
            self.stderr = sys.stderr
        
    def runsource(self, source):
        """Compile and run source code in the interpreter."""
        stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
        sys.stdin, sys.stdout, sys.stderr = \
                   self.stdin, self.stdout, self.stderr
        # more = InteractiveInterpreter.runsource(self, source)
        # this was a cute idea, but didn't work...
        #more = self.runcode(compile(source,'',
        #               ('exec' if self.useExecMode else 'single')))
        
        more = False
        if not self.socket:
            if not source.startswith("connect"):
                print("Type \"connect(ip, port)\" to connect the game client")
            else:
                more = InteractiveInterpreter.runsource(self, source)
        else:
            more = self.rmt_run(source)

        # If sys.std* is still what we set it to, then restore it.
        # But, if the executed source changed sys.std*, assume it was
        # meant to be changed and leave it. Power to the people.
        if sys.stdin == self.stdin:
            sys.stdin = stdin
        else:
            self.stdin = sys.stdin
        if sys.stdout == self.stdout:
            sys.stdout = stdout
        else:
            self.stdout = sys.stdout
        if sys.stderr == self.stderr:
            sys.stderr = stderr
        else:
            self.stderr = sys.stderr
        return more
        
    def getAutoCompleteKeys(self):
        """Return list of auto-completion keycodes."""
        return [ord('.')]

    def getAutoCompleteList(self, command='', *args, **kwds):
        """Return list of auto-completion options for a command.
        
        The list of options will be based on the locals namespace."""
        stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
        sys.stdin, sys.stdout, sys.stderr = \
                   self.stdin, self.stdout, self.stderr
        l = introspect.getAutoCompleteList(command, self.locals,
                                           *args, **kwds)
        sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr
        return l

    def getCallTip(self, command='', *args, **kwds):
        """Return call tip text for a command.
        
        Call tip information will be based on the locals namespace."""
        return introspect.getCallTip(command, self.locals, *args, **kwds)


class InterpreterAlaCarte(Interpreter):
    """Demo Interpreter."""
    
    def __init__(self, locals, rawin, stdin, stdout, stderr, 
                 ps1='main prompt', ps2='continuation prompt'):
        """Create an interactive interpreter object."""
        Interpreter.__init__(self, locals=locals, rawin=rawin, 
                             stdin=stdin, stdout=stdout, stderr=stderr)
        sys.ps1 = ps1
        sys.ps2 = ps2

   
