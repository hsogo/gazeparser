import os
import wx

def DlgAskyesno(parent=None, caption='Ask Yes/No', message='Ask Yes/No'):
    dlg = wx.MessageDialog(parent, message=message, caption=caption, style=wx.YES_NO)
    response = dlg.ShowModal()
    dlg.Destroy()
    if response == wx.ID_YES:
        return True
    else:
        return False

def DlgShowinfo(parent=None, caption='Show Info', message='Show Info'):
    dlg = wx.MessageDialog(parent, message=message, caption=caption, style=wx.ICON_INFORMATION|wx.OK)
    dlg.ShowModal()
    dlg.Destroy()

def DlgShowerror(parent=None, caption='Show Error', message='Show Error'):
    dlg = wx.MessageDialog(parent, message=message, caption=caption, style=wx.ICON_ERROR|wx.OK)
    dlg.ShowModal()
    dlg.Destroy()

def DlgAskopenfilename(parent=None, filetypes='', initialdir=''):
    dlg = wx.FileDialog(parent, defaultDir=initialdir, wildcard=filetypes, style=wx.FD_OPEN)
    if dlg.ShowModal() == wx.ID_OK:
        d = dlg.GetDirectory()
        f = dlg.GetFilename()
        dlg.Destroy()
        return os.path.join(d, f)
    else:
        dlg.Destroy()
        return ''

def DlgAskopenfilenames(parent=None, filetypes='', initialdir=''):
    dlg = wx.FileDialog(parent, defaultDir=initialdir, wildcard=filetypes, style=wx.FD_OPEN|wx.FD_MULTIPLE)
    if dlg.ShowModal() == wx.ID_OK:
        d = dlg.GetDirectory()
        flist = dlg.GetFilenames()
        dlg.Destroy()
        return [os.path.join(d, f) for f in flist]
    else:
        dlg.Destroy()
        return []

def DlgAsksaveasfilename(parent=None, filetypes='', initialdir='', initialfile=''):
    dlg = wx.FileDialog(parent, defaultDir=initialdir, defaultFile=initialfile, wildcard=filetypes, style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
    if dlg.ShowModal() == wx.ID_OK:
        d = dlg.GetDirectory()
        f = dlg.GetFilename()
        dlg.Destroy()
        return os.path.join(d, f)
    else:
        dlg.Destroy()
        return ''

class DlgAsk3buttonDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY, message='message', buttons=['yes','no','cancel']):
        super(DlgAsk3buttonDialog, self).__init__(parent=parent, id=id)
        
        self.selectedButton = -1
        self.buttons = buttons
        
        buttonPanel = wx.Panel(self, wx.ID_ANY)
        button0 = wx.Button(buttonPanel, wx.ID_ANY, buttons[0])
        button1 = wx.Button(buttonPanel, wx.ID_ANY, buttons[1])
        button2 = wx.Button(buttonPanel, wx.ID_ANY, buttons[2])
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(button0)
        box.Add(button1)
        box.Add(button2)
        buttonPanel.SetSizer(box)
        
        button0.Bind(wx.EVT_BUTTON, self.onButton0)
        button1.Bind(wx.EVT_BUTTON, self.onButton1)
        button2.Bind(wx.EVT_BUTTON, self.onButton2)
        
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(self, wx.ID_ANY, message), flag=wx.EXPAND|wx.ALL, border=30)
        box.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        
        self.SetSizerAndFit(box)
    
    def onButton0(self, event=None):
        self.selectedButton = 0
        self.Close()
    
    def onButton1(self, event=None):
        self.selectedButton = 1
        self.Close()
    
    def onButton2(self, event=None):
        self.selectedButton = 2
        self.Close()
    
    def GetSelection(self, event=None):
        return self.selectedButton
    
    def GetStringSelection(self, event=None):
        if self.selectedButton == -1:
            return 'NOT SELECTED'
        else:
            return self.buttons[self.selectedButton]

