import wx
from pathlib import Path
module_dir = Path(__file__).parent

class results_dlg(wx.Dialog):
    def __init__(self, parent, results):
        wx.Dialog.__init__(self, parent)
        self.SetTitle('Screen Layout')

        self.layout_text = (
        '[Screen Layout Parameters]\n'
        'WIDTH={}\n'
        'HORIZ_RES={}\n'
        'OFFSET_X={}\n'
        'OFFSET_Y={}\n'
        'OFFSET_Z={}\n'
        'ROT_X={}\n'
        'ROT_Y=0.0\n'
        'ROT_Z=0.0\n'
        ).format(*results)
        text = wx.TextCtrl(self, wx.ID_ANY, self.layout_text, style=wx.TE_READONLY|wx.TE_MULTILINE, size=(400,200))
        self.copy_button = wx.Button(self, wx.ID_ANY, 'Copy to clipboard (Config format)')
        self.ok_button = wx.Button(self, wx.ID_OK, 'OK')

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.copy_button)
        hbox.Add(self.ok_button)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, wx.EXPAND)
        sizer.Add(hbox, 0, wx.ALIGN_RIGHT|wx.ALL, 10)

        self.copy_button.Bind(wx.EVT_BUTTON, self.copy_to_clipboard)

        self.SetSizerAndFit(sizer)
        self.Layout()

    def copy_to_clipboard(self, evt):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.layout_text))
            wx.TheClipboard.Close()
            wx.MessageBox('Copied','Info')


class cross_panel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # self.Bind(wx.EVT_KEY_DOWN, self.on_keydown)
        self.Bind(wx.EVT_PAINT, self.on_paint)

    """def on_keydown(self, event):
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_ESCAPE:
            self.Parent.Destroy()
        else:
            event.Skip()"""
    
    def on_paint(self, event):
        w,h =self.GetSize()
        dc = wx.PaintDC(self)
        dc.Clear()
        dc.SetPen(wx.Pen(wx.BLACK, 2))
        dc.DrawLine(0, int(h/2), w, int(h/2))        
        dc.DrawLine(int(w/2), 0, int(w/2), h)        


class fullscreen_cross(wx.Frame):
    def __init__(self, parent=None, id=wx.ID_ANY, title=''):
        wx.Frame.__init__(self, parent, id, title)
        panel = cross_panel(self)
        #msg = wx.StaticText(panel, wx.ID_ANY, 'Press ESC key to exit',pos=(10,10))
        #font = wx.Font(48, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        #msg.SetFont(font)
        wx.StaticText(panel, wx.ID_ANY, 'Screen width (mm)', pos=(24,48))
        wx.StaticText(panel, wx.ID_ANY, 'Horizontal resolution (pix)', pos=(24,88))
        wx.StaticText(panel, wx.ID_ANY, 'Camera offset X (mm)', pos=(24,128))
        wx.StaticText(panel, wx.ID_ANY, 'Camera offset Y (mm)', pos=(24,168))
        wx.StaticText(panel, wx.ID_ANY, 'Camera offset Z (mm)', pos=(24,208))
        wx.StaticText(panel, wx.ID_ANY, 'Camera rotation X (deg)', pos=(24,248))
        self.tc_width = wx.TextCtrl(panel, wx.ID_ANY, pos=(164,48), size=(96,24))
        self.tc_hres = wx.TextCtrl(panel, wx.ID_ANY, pos=(164,88), size=(96,24))
        self.tc_offsetX = wx.TextCtrl(panel, wx.ID_ANY, pos=(164,128), size=(96,24))
        self.tc_offsetY = wx.TextCtrl(panel, wx.ID_ANY, pos=(164,168), size=(96,24))
        self.tc_offsetZ = wx.TextCtrl(panel, wx.ID_ANY, pos=(164,208), size=(96,24))
        self.tc_rotX = wx.TextCtrl(panel, wx.ID_ANY, pos=(164,248), size=(96,24))
        button_ok = wx.Button(panel, wx.ID_ANY, label='OK', pos=(24,288))
        button_cancel = wx.Button(panel, wx.ID_ANY, label='Cancel', pos=(164,288))
        button_ok.Bind(wx.EVT_BUTTON, self.on_OK)
        button_cancel.Bind(wx.EVT_BUTTON, self.on_Cancel)
        self.ShowFullScreen(True)
        
        bmp = wx.Image(str(module_dir/'img'/'screen_layout.png')).ConvertToBitmap()
        w,h = panel.GetSize()
        x,y = bmp.GetSize()
        nx = w//2-64
        ny = int(nx/x * y)
        if h//2+ny+64 > h:
            ny = h//2-64
            nx = int(ny/y * x)
        self.bmp_help = wx.StaticBitmap(panel, wx.ID_ANY, bmp, size=(nx,ny), pos=(w//2+32,32))
    
    def on_OK(self, event):
        #self.ShowFullScreen(False)
        results = (
            self.tc_width.GetValue(),
            self.tc_hres.GetValue(),
            self.tc_offsetX.GetValue(),
            self.tc_offsetY.GetValue(),
            self.tc_offsetZ.GetValue(),
            self.tc_rotX.GetValue()
        )
        dlg = results_dlg(self, results)
        dlg.ShowModal()
        self.Destroy()

    def on_Cancel(self, event):
        self.Destroy()


if __name__ == "__main__":
    app = wx.App()
    frame = fullscreen_cross()
    app.MainLoop()