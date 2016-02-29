
import wx
import wx.lib.inspection
import wx.lib.mixins.inspection
import sys, os

# stuff for debugging
print "Python", sys.version
print "wx.version:", wx.version()
print "pid:", os.getpid()
##print "executable:", sys.executable; raw_input("Press Enter...")

assertMode = wx.PYAPP_ASSERT_DIALOG
##assertMode = wx.PYAPP_ASSERT_EXCEPTION

intro = None #"inspect the ejoy2dx client"

#----------------------------------------------------------------------------

class Log:
    def WriteText(self, text):
        if text[-1:] == '\n':
            text = text[:-1]
        wx.LogMessage(text)
    write = WriteText

wildcard = "Lua source (*.lua)|*.lua"

class RunDemoApp(wx.App, wx.lib.mixins.inspection.InspectionMixin):
    def __init__(self, name, module, useShell):
        self.name = name
        self.demoModule = module
        self.useShell = useShell
        wx.App.__init__(self, redirect=False)


    def OnInit(self):
        wx.Log.SetActiveTarget(wx.LogStderr())

        self.SetAssertMode(assertMode)
        self.InitInspection()  # for the InspectionMixin base class

        frame = wx.Frame(None, -1, "lua-crust", pos=(50,50), size=(200,100),
                        style=wx.DEFAULT_FRAME_STYLE, name="run a sample")
        frame.CreateStatusBar()

        menuBar = wx.MenuBar()
        menu = wx.Menu()
        item = menu.Append(-1, "&Load lua file\tF4", "Load lua file and execute it remotely")
        self.Bind(wx.EVT_MENU, self.OnLoadLua, item)

        item = menu.Append(-1, "&Refresh env\tF5", "Refresh the env data of the current connection")
        self.Bind(wx.EVT_MENU, self.OnRefreshEnv, item)

        item = menu.Append(-1, "&Auto Discover\tF6", "Auto discover server during server launch", wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.OnDiscover, item)

        menu.AppendSeparator()
        item = menu.Append(-1, "&Widget Inspector\tF7", "Show the wxPython Widget Inspection Tool")
        self.Bind(wx.EVT_MENU, self.OnWidgetInspector, item)

        item = menu.Append(wx.ID_EXIT, "E&xit\tCtrl-Q", "Exit inspect")
        self.Bind(wx.EVT_MENU, self.OnExitApp, item)
        menuBar.Append(menu, "&File")

        ns = {}
        ns['wx'] = wx
        ns['app'] = self
        ns['module'] = self.demoModule
        ns['frame'] = frame
        
        frame.SetMenuBar(menuBar)
        frame.Show(True)
        frame.Bind(wx.EVT_CLOSE, self.OnCloseFrame)

        win = self.demoModule.Crust(frame, intro=intro)

        # a window will be returned if the demo does not create
        # its own top-level window
        if win:
            # so set the frame to a good size for showing stuff
            frame.SetSize((640, 480))
            win.SetFocus()
            self.window = win
            ns['win'] = win
            frect = frame.GetRect()

        else:
            # It was probably a dialog or something that is already
            # gone, so we're done.
            frame.Destroy()
            return True

        self.win = win
        self.SetTopWindow(frame)
        self.frame = frame
        #wx.Log_SetActiveTarget(wx.LogStderr())
        #wx.Log_SetTraceMask(wx.TraceMessages)

        if self.useShell:
            # Make a PyShell window, and position it below our test window
            from wx import py
            shell = py.shell.ShellFrame(None, locals=ns)
            frect.OffsetXY(0, frect.height)
            frect.height = 400
            shell.SetRect(frect)
            shell.Show()

            # Hook the close event of the test window so that we close
            # the shell at the same time
            def CloseShell(evt):
                if shell:
                    shell.Close()
                evt.Skip()
            frame.Bind(wx.EVT_CLOSE, CloseShell)
                    
        return True


    def OnExitApp(self, evt):
        self.frame.Close(True)

    def OnLoadLua(self, evt):
        interp = self.win.shell.interp
        if interp.socket:
            dlg = wx.FileDialog(
                self.frame, message="Choose a file",
                defaultDir=os.getcwd(),
                defaultFile="",
                wildcard=wildcard,
                style=wx.OPEN | wx.CHANGE_DIR
                )

            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                f = open(path, "r")
                lua = f.read()
                f.close()
                self.win.shell.alignDownPos()
                interp.addsource(lua)

            dlg.Destroy()
        else:
            dlg = wx.MessageDialog(self.frame, 'Pls make a connection at first',
                               'Notify',
                               wx.OK | wx.ICON_INFORMATION
                               #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                               )
            dlg.ShowModal()
            dlg.Destroy()

    def OnRefreshEnv(self, evt):
        interp = self.win.shell.interp
        if interp.socket:
            interp.push("env()")
        else:
            dlg = wx.MessageDialog(self.frame, 'Pls make a connection at first',
                               'Notify',
                               wx.OK | wx.ICON_INFORMATION
                               #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                               )
            dlg.ShowModal()
            dlg.Destroy()

    def OnDiscover(self, evt):
        self.win.setAutoDiscover(evt.IsChecked())

    def OnCloseFrame(self, evt):
        if hasattr(self, "window") and hasattr(self.window, "ShutdownDemo"):
            self.window.ShutdownDemo()
        evt.Skip()

    def OnWidgetInspector(self, evt):
        wx.lib.inspection.InspectionTool().Show()
    

#----------------------------------------------------------------------------


def main():
    useShell = False
    for x in range(len(sys.argv)):
        if sys.argv[x] in ['--shell', '-shell', '-s']:
            useShell = True
            del sys.argv[x]
            break
      
    name = "crust"
    module = __import__(name)

    app = RunDemoApp(name, module, useShell)
    app.MainLoop()


if __name__ == "__main__":
    main()


