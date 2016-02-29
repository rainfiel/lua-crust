"""Crust combines the shell and filling into one control."""

__author__ = "Patrick K. O'Brien <pobrien@orbtech.com>"
__cvsid__ = "$Id$"
__revision__ = "$Revision$"[11:-2]

import wx
import wx.py

import os
import pprint
import re
import sys

from wx.py import dispatcher
import lua_edit as editwindow
from filling import Filling
from wx.py import frame
from shell import Shell
from wx.py.version import VERSION


class Crust(wx.SplitterWindow):
    """Crust based on SplitterWindow."""

    name = 'Crust'
    revision = __revision__
    sashoffset = 200

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.SP_3D|wx.SP_LIVE_UPDATE,
                 name='Crust Window', rootObject=None, rootLabel=None,
                 rootIsNamespace=True, intro='', locals=None,
                 InterpClass=None,
                 startupScript=None, execStartupScript=True,
                 *args, **kwds):
        """Create Crust instance."""
        wx.SplitterWindow.__init__(self, parent, id, pos, size, style, name)

        # Turn off the tab-traversal style that is automatically
        # turned on by wx.SplitterWindow.  We do this because on
        # Windows the event for Ctrl-Enter is stolen and used as a
        # navigation key, but the Shell window uses it to insert lines.
        style = self.GetWindowStyle()
        self.SetWindowStyle(style & ~wx.TAB_TRAVERSAL)
        
        self.shell = Shell(parent=self, introText=intro,
                           locals=locals, InterpClass=InterpClass,
                           startupScript=startupScript,
                           execStartupScript=execStartupScript,
                           *args, **kwds)
        
        self.editor = self.shell
        if rootObject is None:
            rootObject = self.shell.interp.lua_locals
        self.notebook = wx.Notebook(parent=self, id=-1)
        self.shell.interp.locals['notebook'] = self.notebook
        self.filling = Filling(parent=self.notebook,
                               rootObject=rootObject,
                               rootLabel="env",
                               rootIsNamespace=rootIsNamespace)
        # Add 'filling' to the interpreter's locals.
        self.shell.interp.locals['filling'] = self.filling
        self.notebook.AddPage(page=self.filling, text='Namespace', select=True)
        
        self.display = Display(parent=self.notebook)
        self.notebook.AddPage(page=self.display, text='Log')
        # Add 'pp' (pretty print) to the interpreter's locals.
        self.shell.interp.locals['pp'] = self.display.setItem
        self.display.nbTab = self.notebook.GetPageCount()-1
        
        self.helptip = Helptip(parent=self.notebook)
        self.notebook.AddPage(page=self.helptip, text='Help')
        
        self.sessionlisting = SessionListing(parent=self.notebook)
        self.notebook.AddPage(page=self.sessionlisting, text='History')
        
        # Initialize in an unsplit mode, and check later after loading
        # settings if we should split or not.
        self.shell.Hide()
        self.notebook.Hide()
        self.Initialize(self.shell)
        self._shouldsplit = True
        wx.CallAfter(self._CheckShouldSplit)
        self.SetMinimumPaneSize(100)

        self.Bind(wx.EVT_SIZE, self.SplitterOnSize)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnChanged)
        self.Bind(wx.EVT_SPLITTER_DCLICK, self.OnSashDClick)

    def _CheckShouldSplit(self):
        if self._shouldsplit:
            self.SplitHorizontally(self.shell, self.notebook, -self.sashoffset)
            self.lastsashpos = self.GetSashPosition()
        else:
            self.lastsashpos = -1
        self.issplit = self.IsSplit()       

    def ToggleTools(self):
        """Toggle the display of the filling and other tools"""
        if self.issplit:
            self.Unsplit()
        else:
            self.SplitHorizontally(self.shell, self.notebook, -self.sashoffset)
            self.lastsashpos = self.GetSashPosition()
        self.issplit = self.IsSplit()

    def ToolsShown(self):
        return self.issplit

    def OnChanged(self, event):
        """update sash offset from the bottom of the window"""
        self.sashoffset = self.GetSize().height - event.GetSashPosition()
        self.lastsashpos = event.GetSashPosition()
        event.Skip()

    def OnSashDClick(self, event):
        self.Unsplit()
        self.issplit = False

    # Make the splitter expand the top window when resized
    def SplitterOnSize(self, event):
        splitter = event.GetEventObject()
        sz = splitter.GetSize()
        splitter.SetSashPosition(sz.height - self.sashoffset, True)
        event.Skip()


    def LoadSettings(self, config):
        self.shell.LoadSettings(config)
        self.filling.LoadSettings(config)

        pos = config.ReadInt('Sash/CrustPos', 400)
        wx.CallAfter(self.SetSashPosition, pos)
        def _updateSashPosValue():
            sz = self.GetSize()
            self.sashoffset = sz.height - self.GetSashPosition()
        wx.CallAfter(_updateSashPosValue)
        zoom = config.ReadInt('View/Zoom/Display', -99)
        if zoom != -99:
            self.display.SetZoom(zoom)
        self.issplit = config.ReadInt('Sash/IsSplit', True)
        if not self.issplit:
            self._shouldsplit = False

    def SaveSettings(self, config):
        self.shell.SaveSettings(config)
        self.filling.SaveSettings(config)

        if self.lastsashpos != -1:
            config.WriteInt('Sash/CrustPos', self.lastsashpos)
        config.WriteInt('Sash/IsSplit', self.issplit)
        config.WriteInt('View/Zoom/Display', self.display.GetZoom())
        
class Display(editwindow.EditWindow):
    """STC used to display an object using Pretty Print."""

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize,
                 style=wx.CLIP_CHILDREN | wx.SUNKEN_BORDER,
                 static=False):
        """Create Display instance."""
        editwindow.EditWindow.__init__(self, parent, id, pos, size, style)
        # Configure various defaults and user preferences.
        self.SetReadOnly(True)
        self.SetWrapMode(False)
        if not static:
            dispatcher.connect(receiver=self.push, signal='Interpreter.push')

    def push(self, command, more):
        """Receiver for Interpreter.push signal."""
        self.Refresh()

    def Refresh(self):
        if not hasattr(self, "item"):
            return
        self.SetReadOnly(False)
        text = pprint.pformat(self.item)
        self.SetText(text)
        self.SetReadOnly(True)

    def setItem(self, item):
        """Set item to pretty print in the notebook Display tab."""
        self.item = item
        self.Refresh()
        # if self.GetParent().GetSelection() != self.nbTab:
        #     focus = wx.Window.FindFocus()
        #     self.GetParent().SetSelection(self.nbTab)
        #     wx.CallAfter(focus.SetFocus)
            

HELP_TEXT = """\
* Key bindings:
Home              Go to the beginning of the command or line.
Shift+Home        Select to the beginning of the command or line.
Shift+End         Select to the end of the line.
End               Go to the end of the line.
Ctrl+C            Copy selected text, removing prompts.
Ctrl+Shift+C      Copy selected text, retaining prompts.
Alt+C             Copy to the clipboard, including prefixed prompts.
Ctrl+X            Cut selected text.
Ctrl+V            Paste from clipboard.
Ctrl+Shift+V      Paste and run multiple commands from clipboard.
Ctrl+Up Arrow     Retrieve Previous History item.
Alt+P             Retrieve Previous History item.
Ctrl+Down Arrow   Retrieve Next History item.
Alt+N             Retrieve Next History item.
Shift+Up Arrow    Insert Previous History item.
Shift+Down Arrow  Insert Next History item.
F8                Command-completion of History item.
                  (Type a few characters of a previous command and press F8.)
Ctrl+Enter        Insert new line into multiline command.
Ctrl+]            Increase font size.
Ctrl+[            Decrease font size.
Ctrl+=            Default font size.
Ctrl-Space        Show Auto Completion.
Ctrl-Alt-Space    Show Call Tip.
Shift+Enter       Complete Text from History.
Ctrl+H            "hide" lines containing selection / "unhide"
F12               on/off "free-edit" mode

F4                Load lua file
F5                refresh env
"""

# TODO: Switch this to a editwindow.EditWindow
class Helptip(wx.TextCtrl):
    """Text control containing the most recent shell Helptip."""

    def __init__(self, parent=None, id=-1,ShellClassName='Shell'):
        style = (wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        wx.TextCtrl.__init__(self, parent, id, style=style)
        self.SetBackgroundColour(wx.Colour(255, 255, 208))
        self.ShellClassName=ShellClassName

        df = self.GetFont()
        font = wx.Font(df.GetPointSize(), wx.TELETYPE, wx.NORMAL, wx.NORMAL)
        self.SetFont(font)

        self.Clear()
        self.AppendText(HELP_TEXT)
        self.SetInsertionPoint(0)

# TODO: Switch this to a editwindow.EditWindow
class SessionListing(wx.TextCtrl):
    """Text control containing all commands for session."""

    def __init__(self, parent=None, id=-1,ShellClassName='Shell'):
        style = (wx.TE_MULTILINE | wx.TE_READONLY |
                 wx.TE_RICH2 | wx.TE_DONTWRAP)
        wx.TextCtrl.__init__(self, parent, id, style=style)
        dispatcher.connect(receiver=self.addHistory,
                           signal=ShellClassName+".addHistory")
        dispatcher.connect(receiver=self.clearHistory,
                           signal=ShellClassName+".clearHistory")
        dispatcher.connect(receiver=self.loadHistory,
                           signal=ShellClassName+".loadHistory")

        df = self.GetFont()
        font = wx.Font(df.GetPointSize(), wx.TELETYPE, wx.NORMAL, wx.NORMAL)
        self.SetFont(font)

    def loadHistory(self, history):
        # preload the existing history, if any
        hist = history[:]
        hist.reverse()
        self.SetValue('\n'.join(hist) + '\n')
        self.SetInsertionPointEnd()

    def addHistory(self, command):
        if command:
            self.SetInsertionPointEnd()
            self.AppendText(command + '\n')

    def clearHistory(self):
        self.SetValue("")


class DispatcherListing(wx.TextCtrl):
    """Text control containing all dispatches for session."""

    def __init__(self, parent=None, id=-1):
        style = (wx.TE_MULTILINE | wx.TE_READONLY |
                 wx.TE_RICH2 | wx.TE_DONTWRAP)
        wx.TextCtrl.__init__(self, parent, id, style=style)
        dispatcher.connect(receiver=self.spy)

        df = self.GetFont()
        font = wx.Font(df.GetPointSize(), wx.TELETYPE, wx.NORMAL, wx.NORMAL)
        self.SetFont(font)

    def spy(self, signal, sender):
        """Receiver for Any signal from Any sender."""
        text = '%r from %s' % (signal, sender)
        self.SetInsertionPointEnd()
        start, end = self.GetSelection()
        if start != end:
            self.SetSelection(0, 0)
        self.AppendText(text + '\n')



class CrustFrame(frame.Frame, frame.ShellFrameMixin):
    """Frame containing all the PyCrust components."""

    name = 'CrustFrame'
    revision = __revision__


    def __init__(self, parent=None, id=-1, title='lua-crust',
                 pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=wx.DEFAULT_FRAME_STYLE,
                 rootObject=None, rootLabel=None, rootIsNamespace=True,
                 locals=None, InterpClass=None,
                 config=None, dataDir=None,
                 *args, **kwds):
        """Create CrustFrame instance."""
        frame.Frame.__init__(self, parent, id, title, pos, size, style,
                             shellName='lua-crust')
        frame.ShellFrameMixin.__init__(self, config, dataDir)

        if size == wx.DefaultSize:
            self.SetSize((800, 600))
        
        intro = 'lua-crust'
        
        self.SetStatusText(intro.replace('\n', ', '))
        self.crust = Crust(parent=self, intro=intro,
                           rootObject=rootObject,
                           rootLabel=rootLabel,
                           rootIsNamespace=rootIsNamespace,
                           locals=locals,
                           InterpClass=InterpClass,
                           startupScript=self.startupScript,
                           execStartupScript=self.execStartupScript,
                           *args, **kwds)
        self.shell = self.crust.shell

        # Override the filling so that status messages go to the status bar.
        self.crust.filling.tree.setStatusText = self.SetStatusText
        
        # Override the shell so that status messages go to the status bar.
        self.shell.setStatusText = self.SetStatusText
        
        self.shell.SetFocus()
        self.LoadSettings()


    def OnClose(self, event):
        """Event handler for closing."""
        self.SaveSettings()
        self.crust.shell.destroy()
        self.Destroy()


    def OnAbout(self, event):
        pass

    def ToggleTools(self):
        """Toggle the display of the filling and other tools"""
        return self.crust.ToggleTools()

    def ToolsShown(self):
        return self.crust.ToolsShown()

    def OnHelp(self, event):
        """Show a help dialog."""
        frame.ShellFrameMixin.OnHelp(self, event)

    def LoadSettings(self):
        if self.config is not None:
            frame.ShellFrameMixin.LoadSettings(self)
            frame.Frame.LoadSettings(self, self.config)
            self.crust.LoadSettings(self.config)


    def SaveSettings(self, force=False):
        if self.config is not None:
            frame.ShellFrameMixin.SaveSettings(self,force)
            if self.autoSaveSettings or force:
                frame.Frame.SaveSettings(self, self.config)
                self.crust.SaveSettings(self.config)


    def DoSaveSettings(self):
        if self.config is not None:
            self.SaveSettings(force=True)
            self.config.Flush()
    
