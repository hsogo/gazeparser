import wx
import cv2
import wx.lib.newevent
import numpy as np

cameraview_width = 640
cameraview_height = 480

class camera_view(wx.StaticBitmap):
    def __init__(self, *args, **kwargs):
        super(camera_view, self).__init__(*args, **kwargs)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.on_paint)

    def on_paint(self, event):
        try:
            image = self.GetBitmap()
            if not image:
                return
            dc = wx.AutoBufferedPaintDC(self)
            dc.Clear()
            dc.DrawBitmap(image, 0, 0, True)
        except:
            pass

class camera_id_selector_dlg(wx.Dialog):

    NewImageEvent, EVT_NEWIMAGE = wx.lib.newevent.NewEvent()

    def __init__(self, parent=None, max_try=8, standalone=False):
        super(wx.Dialog, self).__init__(parent, wx.ID_ANY)

        self.standalone = standalone
        self.running = False
        self.selected_cam = 0

        self.camera_previews = []
        self.IDs = []
        for i in range(max_try):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, im = cap.read()
                if ret:
                    self.camera_previews.append(im)
                    self.IDs.append(i)
                cap.release()

        if len(self.camera_previews) < 1:
            return
        
        view_panel = wx.Panel(self,wx.ID_ANY)
        self.camera_view = camera_view(view_panel, wx.ID_ANY, wx.Bitmap(cameraview_width,cameraview_height))
        self.radio_box = wx.RadioBox(view_panel, wx.ID_ANY, 'Cameras', 
            choices=[str(val) for val in self.IDs],
            style=wx.RA_HORIZONTAL)
        self.radio_box.Bind(wx.EVT_RADIOBOX, self.get_radio_selected)
        self.button_update = wx.Button(view_panel, wx.ID_ANY, 'Update this image (takes a while)')
        self.button_update.Bind(wx.EVT_BUTTON, self.get_new_image_manually)
        view_sizer = wx.BoxSizer(wx.VERTICAL)
        view_sizer.Add(self.camera_view)
        view_sizer.Add(self.radio_box)
        view_sizer.Add(self.button_update)
        view_panel.SetSizer(view_sizer)

        button_panel = wx.Panel(self, wx.ID_ANY)
        ok_button = wx.Button(button_panel, wx.ID_OK, 'Ok')
        cancel_button = wx.Button(button_panel, wx.ID_CANCEL, 'Cancel')
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(ok_button)
        button_sizer.Add(cancel_button)
        button_panel.SetSizer(button_sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(view_panel)
        sizer.Add(button_panel)
        self.SetSizerAndFit(sizer)

        self.update_cameraview(self.camera_previews[self.selected_cam])

        self.Show()
    
    def get_new_image_manually(self, evt):
        self.button_update.Enable(False)
        im = np.zeros((cameraview_height, cameraview_width), dtype=np.uint8)
        self.update_cameraview(im)

        cap = cv2.VideoCapture(self.IDs[self.selected_cam])
        if cap.isOpened():
            ret, im = cap.read()
            if ret:
                self.camera_previews[self.selected_cam] = im
                self.update_cameraview(self.camera_previews[self.selected_cam])
            else:
                wx.MessageBox('Could not get new image from this camera','Error')
            cap.release()
        else:
            wx.MessageBox('Could not re-initialize this camera','Error')
        self.button_update.Enable(True)

    def update_cameraview(self, img):
        x,y = (img.shape[1],img.shape[0])
        downscaling = cameraview_height/y
        if x*downscaling > cameraview_width:
            downscaling = cameraview_width/x
        (sx, sy) = (int(x*downscaling), int(y*downscaling))
        img = cv2.resize(img, (sx,sy))

        bmp = wx.Bitmap.FromBuffer(sx, sy, cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        self.camera_view.SetBitmap(bmp)

    def get_radio_selected(self, evt=None):
        self.selected_cam = self.radio_box.GetSelection()
        self.update_cameraview(self.camera_previews[self.selected_cam])


if __name__ == '__main__':
    app = wx.App(False)
    dlg = camera_id_selector_dlg(standalone=True)
    ret = dlg.ShowModal()
    if len(dlg.IDs) < 1:
        wx.MessageBox('No camera', 'Error')
    if ret == wx.ID_OK:
        wx.MessageBox('Camera {} is selected.'.format(dlg.IDs[dlg.selected_cam]),'Info')
    else:
        wx.MessageBox('Canceled', 'Info')
    app.Destroy()



