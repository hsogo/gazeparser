# -*- coding: utf-8 -*-

import numpy as np
import cv2
import wx
import wx.lib.newevent
import threading
import queue
import os

PREVIEW_WIDTH = 960
PREVIEW_HEIGHT = 540

# http://russeng.hatenablog.jp/entry/2015/06/16/231801
# https://kamino.hatenablog.com/entry/opencv_calibrate_camera#sec4


class cal_results_dlg(wx.Dialog):
    def __init__(self, parent, resolution, results):
        wx.Dialog.__init__(self, parent)
        self.SetTitle('Calibration results')

        self.x, self.y = resolution
        self.RMS, self.K, self.d = results
        msg = 'RMS\n{}\n\nK\n{}\n\nd\n{}'.format(self.RMS, self.K, self.d)
        text = wx.TextCtrl(self, wx.ID_ANY, msg, style=wx.TE_READONLY|wx.TE_MULTILINE, size=(400,200))
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
        if self.x > 640 or self.y > 480:
            scale = 0.5
        else:
            scale = 1.0
        basic_text = (
        '[Basic Parameters]\n'
        'CAMERA_ID = \n'
        'RESOLUTION_HORIZ = {}\n'
        'RESOLUTION_VERT = {}\n'
        'DOWNSCALING = {}\n'
        ).format(
            self.x, self.y,scale
        )
        calparam_text = (
        '[Calibration Parameters]\n'
        'CAMERA_MATRIX_R0C0={}\n'
        'CAMERA_MATRIX_R0C1={}\n'
        'CAMERA_MATRIX_R0C2={}\n'
        'CAMERA_MATRIX_R1C0={}\n'
        'CAMERA_MATRIX_R1C1={}\n'
        'CAMERA_MATRIX_R1C2={}\n'
        'CAMERA_MATRIX_R2C0={}\n'
        'CAMERA_MATRIX_R2C1={}\n'
        'CAMERA_MATRIX_R2C2={}\n'
        'DIST_COEFFS_R0C0={}\n'
        'DIST_COEFFS_R1C0={}\n'
        'DIST_COEFFS_R2C0={}\n'
        'DIST_COEFFS_R3C0={}\n'
        'DIST_COEFFS_R4C0={}\n').format(
            self.K[0,0],self.K[0,1],self.K[0,2],
            self.K[1,0],self.K[1,1],self.K[1,2],
            self.K[2,0],self.K[2,1],self.K[2,2],
            self.d[0,0],self.d[0,1],self.d[0,2],self.d[0,3],self.d[0,3]
        )
        layout_text = (
        '[Screen Layout Parameters]\n'
        'WIDTH=\n'
        'HORIZ_RES=\n'
        'OFFSET_X=\n'
        'OFFSET_Y=\n'
        'OFFSET_Z=\n'
        'ROT_X=\n'
        'ROT_Y=\n'
        'ROT_Z=\n'
        )

        formatted_text = basic_text + '\n' + calparam_text + '\n' + layout_text

        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(formatted_text))
            wx.TheClipboard.Close()
            wx.MessageBox('Copied','Info')

class set_chessboard_dlg(wx.Dialog):
    def __init__(self, parent, *args, **kwds):
        wx.Dialog.__init__(self, parent, *args, **kwds)
        self.SetTitle('Chessboard pattern')

        vbox  = wx.BoxSizer(wx.VERTICAL)
        
        sizer = wx.FlexGridSizer(rows=2, cols=2, gap=(10, 10))
        self.ctrl_square_size = wx.TextCtrl(self, wx.ID_ANY, str(parent.square_size))
        self.ctrl_pattern_size = wx.TextCtrl(self, wx.ID_ANY, "{},{}".format(*parent.pattern_size))
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Square size of Chessboard (mm; must be an integer)"))
        sizer.Add(self.ctrl_square_size)
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Size of Chessboard (N of corners; comma-separated)"))
        sizer.Add(self.ctrl_pattern_size)

        panel_buttons = wx.Panel(self, wx.ID_ANY)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(panel_buttons, wx.ID_OK, "OK")
        cancel_button = wx.Button(panel_buttons, wx.ID_CANCEL, "Cancel")
        hbox.Add(ok_button)
        hbox.Add(cancel_button)
        panel_buttons.SetSizer(hbox)

        vbox.Add(sizer, 1, wx.ALL | wx.EXPAND, 10)
        vbox.Add(panel_buttons, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.SetSizer(vbox)
        vbox.Fit(self)

        self.Layout()


class camera_id_dlg(wx.Dialog):
    def __init__(self, *args, **kwds):
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetTitle('Camera calibration')

        vbox  = wx.BoxSizer(wx.VERTICAL)
        
        sizer = wx.FlexGridSizer(rows=3, cols=2, gap=(10, 10))
        self.ctrl_camera_id = wx.TextCtrl(self, wx.ID_ANY, "0")
        self.ctrl_camera_xy = wx.TextCtrl(self, wx.ID_ANY, "")
        self.checkbox_flip = wx.CheckBox(self, wx.ID_ANY, "")
        self.checkbox_flip.SetValue(True)

        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Camear ID"))
        sizer.Add(self.ctrl_camera_id)
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Resolution X,Y (comma-separated; empty=default)"))
        sizer.Add(self.ctrl_camera_xy)
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Flip camera view"))
        sizer.Add(self.checkbox_flip)

        panel_buttons = wx.Panel(self, wx.ID_ANY)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(panel_buttons, wx.ID_OK, "OK")
        cancel_button = wx.Button(panel_buttons, wx.ID_CANCEL, "Cancel")
        hbox.Add(ok_button)
        hbox.Add(cancel_button)
        panel_buttons.SetSizer(hbox)

        vbox.Add(sizer, 1, wx.ALL | wx.EXPAND, 10)
        vbox.Add(panel_buttons, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        self.SetSizer(vbox)
        vbox.Fit(self)

        self.Layout()
    

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

class grab_image_dlg(wx.Dialog):

    NewImageEvent, EVT_NEWIMAGE = wx.lib.newevent.NewEvent()

    def __init__(self, parent):
        super(wx.Dialog, self).__init__(parent, wx.ID_ANY)
        self.parent = parent
        self.images = []
        self.img_points = []
        self.obj_points = []
        self.running = False

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = wx.Panel(self, wx.ID_ANY, size=self.parent.cameraview_size)
        self.camera_view = camera_view(self.panel, wx.ID_ANY, wx.Bitmap(self.parent.cameraview_size[0],self.parent.cameraview_size[1]))
        if not self.parent.use_camera:
            self.slider = wx.Slider(self, wx.ID_ANY, 0, 0, 1000,style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
            movie_frames = int(self.parent.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.slider.SetRange(0, movie_frames)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.add_image_button = wx.Button(self, wx.ID_ANY, "Add Image")
        self.remove_image_button = wx.Button(self, wx.ID_ANY, "Remove All Images")
        self.ok_button = wx.Button(self, wx.ID_OK, "OK")
        hbox.Add(self.add_image_button)
        hbox.Add(self.remove_image_button)
        hbox.Add(self.ok_button)
        text_res = wx.StaticText(self, wx.ID_ANY, "Image size:({},{}) Pattern size:({},{})  Square size: {}mm".format(
            self.parent.x,self.parent.y,self.parent.pattern_size[0],self.parent.pattern_size[1],self.parent.square_size))
        self.text_status = wx.StaticText(self, wx.ID_ANY, "0 image(s)")

        sizer.Add(self.panel)
        if not self.parent.use_camera:
            sizer.Add(self.slider,0,wx.EXPAND|wx.ALL, 10)
        sizer.Add(text_res, 0, wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP, 10)
        sizer.Add(self.text_status, 0, wx.ALIGN_RIGHT|wx.RIGHT, 10)
        sizer.Add(hbox, 0, wx.ALIGN_RIGHT|wx.ALL, 10)

        self.SetSizerAndFit(sizer)

        self.add_image_button.Bind(wx.EVT_BUTTON, self.add_sample_image)
        self.remove_image_button.Bind(wx.EVT_BUTTON, self.remove_sample_image)
        if self.parent.use_camera:
            self.Bind(grab_image_dlg.EVT_NEWIMAGE, self.new_image)
            self.queue = queue.Queue(1)
            self.running = True
            self.thread = threading.Thread(target=self.capture_image)
            self.thread.start()
        else:
            self.slider.Bind(wx.EVT_SLIDER, self.onSeek)
            self.capture_image_from_movie()

    def capture_image_from_movie(self):
        _, im = self.parent.cap.read()
        img = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

        found, corner = cv2.findChessboardCorners(im, self.parent.pattern_size)
        # If corners are found
        if found:
            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)
            cv2.cornerSubPix(img, corner, (5,5), (-1,-1), term)
            cv2.drawChessboardCorners(im, self.parent.pattern_size, corner, found)

        self.current_corner = corner
        if self.parent.downscaling != 0:
            im = cv2.resize(im, self.parent.cameraview_size)
        bmp = wx.Bitmap.FromBuffer(im.shape[1], im.shape[0], cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
        self.camera_view.SetBitmap(bmp)

    def capture_image(self):
        while self.running:
            ret, im = self.parent.cap.read()
            if not ret:
                break
            img = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

            found, corner = cv2.findChessboardCorners(im, self.parent.pattern_size)
            # If corners are found
            if found:
                term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)
                cv2.cornerSubPix(img, corner, (5,5), (-1,-1), term)
                cv2.drawChessboardCorners(im, self.parent.pattern_size, corner, found)
            
            if not self.queue.full():
                self.queue.put((im, corner), False)
                try:
                    wx.PostEvent(self, grab_image_dlg.NewImageEvent())
                except:
                    break
    
    def new_image(self, evt):
        if not self.queue.empty():
            img, self.current_corner = self.queue.get(False)
            if self.parent.flip_image:
                img = np.fliplr(img)
            if self.parent.downscaling != 0:
                img = cv2.resize(img, self.parent.cameraview_size)
            bmp = wx.Bitmap.FromBuffer(img.shape[1], img.shape[0], cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            self.camera_view.SetBitmap(bmp)
    
    def onSeek(self, evt):
        new_frame = max(self.slider.GetValue()-1,0)
        self.parent.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
        self.capture_image_from_movie()


    def add_sample_image(self, evt):
        if self.current_corner is None:
            wx.MessageBox('Chessboard was not detected.','Caution')
            return

        self.images.append(self.camera_view.GetBitmap())
        self.img_points.append(self.current_corner.reshape(-1, 2))
        self.obj_points.append(self.parent.pattern_points)
        self.text_status.SetLabel("{} image(s)".format(len(self.img_points)))

    def remove_sample_image(self, evt):
        self.images.clear()
        self.img_points.clear()
        self.obj_points.clear()
        self.text_status.SetLabel("{} image(s)".format(len(self.img_points)))


class camera_calibration_app(wx.Frame):

    ID_FromCamera = wx.NewIdRef()
    ID_FromMovie = wx.NewIdRef()
    ID_FromImages = wx.NewIdRef()
    ID_SetChessboard = wx.NewIdRef()
    ID_RunCal = wx.NewIdRef()

    def __init__(self, parent=None, config=None, cap=None):
        super(wx.Frame, self).__init__(parent, wx.ID_ANY)

        self.obj_points = []
        self.img_points = []
        self.images = []
        self.current_corner = None
        self.use_camera = False

        self.current_preview_index = 0

        self.square_size = 30
        self.pattern_size = (8, 5)
        self.pattern_points = np.zeros( (np.prod(self.pattern_size), 3), np.float32 ) #Chessboard (X,Y,Z) coordiate (Z=0)
        self.pattern_points[:,:2] = np.indices(self.pattern_size).T.reshape(-1, 2)
        self.pattern_points *= self.square_size

        menu_bar = wx.MenuBar()
        menu_grab = wx.Menu()
        menu_cal = wx.Menu()

        menu_bar.Append(menu_grab, 'Add images from...')
        menu_bar.Append(menu_cal, 'Calibration')

        menu_grab.Append(self.ID_FromCamera, 'Camera')
        menu_grab.Append(self.ID_FromMovie, 'Movie file')
        menu_grab.Append(self.ID_FromImages, 'Image files')
        self.Bind(wx.EVT_MENU, self.from_camera, id=self.ID_FromCamera)
        self.Bind(wx.EVT_MENU, self.from_movie, id=self.ID_FromMovie)
        self.Bind(wx.EVT_MENU, self.from_images, id=self.ID_FromImages)

        menu_cal.Append(self.ID_RunCal, 'Run')
        menu_cal.Append(self.ID_SetChessboard, 'Set Chessboard parameters')
        self.Bind(wx.EVT_MENU, self.run_calibration, id=self.ID_RunCal)
        self.Bind(wx.EVT_MENU, self.set_chessboard, id=self.ID_SetChessboard)

        self.SetMenuBar(menu_bar)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = wx.Panel(self, wx.ID_ANY, size=(PREVIEW_WIDTH,PREVIEW_HEIGHT))
        self.preview = camera_view(self.panel, wx.ID_ANY, wx.Bitmap(PREVIEW_WIDTH,PREVIEW_HEIGHT))

        self.text_current_image = wx.StaticText(self, wx.ID_ANY, "No image")

        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_panel = wx.Panel(self, wx.ID_ANY)
        self.button_prev = wx.Button(self.button_panel, wx.ID_ANY, "Prev")
        self.button_del = wx.Button(self.button_panel, wx.ID_ANY, "Remove this image")
        self.button_next = wx.Button(self.button_panel, wx.ID_ANY, "Next")
        buttonsizer.Add(self.button_prev)
        buttonsizer.Add(self.button_del)
        buttonsizer.Add(self.button_next)
        self.button_panel.SetSizer(buttonsizer)

        sizer.Add(self.panel)
        sizer.Add(self.text_current_image)
        sizer.Add(self.button_panel)
        self.SetSizerAndFit(sizer)

        self.button_prev.Bind(wx.EVT_BUTTON, self.show_prev_image)
        self.button_del.Bind(wx.EVT_BUTTON, self.delete_image)
        self.button_next.Bind(wx.EVT_BUTTON, self.show_next_image)

        self.Show()

    def from_camera(self, event=None):
        dlg = camera_id_dlg(self)
        if dlg.ShowModal() != wx.ID_OK:
            return

        try:
            camera_id = int(dlg.ctrl_camera_id.GetValue())
        except:
            wx.MessageBox("Invalid camera ID: {}".format(camera_id),"Error")
            return

        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            wx.MessageBox("Can't open Camera (ID:{})".format(camera_id),"Error")
            return

        self.flip_image = dlg.checkbox_flip.GetValue()

        xyval = dlg.ctrl_camera_xy.GetValue()
        if xyval != "":
            xys = xyval.split(',')
            try:
                x = int(xys[0])
                y = int(xys[1])
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, x)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, y)
            except:
                wx.MessageBox("Invalid Camera resolution ({})".format(xyval),"Error")
                return

        self.x = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.y = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.downscaling = PREVIEW_HEIGHT/self.y
        if self.x*self.downscaling > PREVIEW_WIDTH:
            self.downscaling = PREVIEW_WIDTH/self.x
        self.cameraview_size = (int(self.x*self.downscaling), int(self.y*self.downscaling))

        self.use_camera = True

        dlg = grab_image_dlg(self)
        if dlg.ShowModal() == wx.ID_OK:
            if len(dlg.images)>0:
                self.images.extend(dlg.images)
                self.obj_points.extend(dlg.obj_points)
                self.img_points.extend(dlg.img_points)
                self.update_preview()
        #dlg.running = False
        self.cap.release()
        dlg.Destroy()

    def from_movie(self, event=None):
        file_dlg = wx.FileDialog(self, style=wx.FD_OPEN)
        if file_dlg.ShowModal() == wx.ID_OK:
            file = file_dlg.GetPath()
        else:
            return

        self.cap = cv2.VideoCapture(file)
        if not self.cap.isOpened():
            wx.MessageBox("Can't open Movie ({})".format(file),"Error")
            return

        self.x = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.y = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.downscaling = PREVIEW_HEIGHT/self.y
        if self.x*self.downscaling > PREVIEW_WIDTH:
            self.downscaling = PREVIEW_WIDTH/self.x
        self.cameraview_size = (int(self.x*self.downscaling), int(self.y*self.downscaling))

        self.use_camera = False

        dlg = grab_image_dlg(self)
        if dlg.ShowModal() == wx.ID_OK:
            if len(dlg.images)>0:
                self.images.extend(dlg.images)
                self.obj_points.extend(dlg.obj_points)
                self.img_points.extend(dlg.img_points)
                self.update_preview()
        self.cap.release()
        dlg.Destroy()

    def from_images(self, event=None):
        file_dlg = wx.FileDialog(self, style=wx.FD_OPEN|wx.FD_MULTIPLE)
        if file_dlg.ShowModal() == wx.ID_OK:
            files = file_dlg.GetPaths()
        else:
            return
        
        if len(files) == 0:
            return
        
        tmp_images = []
        tmp_obj_points = []
        tmp_img_points = []

        not_detected = []
        for file in files:
            im = cv2.imread(file)

            self.x = im.shape[1]
            self.y = im.shape[0]
            self.downscaling = PREVIEW_HEIGHT/self.y
            if self.x*self.downscaling > PREVIEW_WIDTH:
                self.downscaling = PREVIEW_WIDTH/self.x
            self.cameraview_size = (int(self.x*self.downscaling), int(self.y*self.downscaling))

            img = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

            found, corner = cv2.findChessboardCorners(im, self.pattern_size)
            # If corners are found
            if found:
                term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)
                cv2.cornerSubPix(img, corner, (5,5), (-1,-1), term)
                cv2.drawChessboardCorners(im, self.pattern_size, corner, found)
            else:
                not_detected.append(file)
                continue

            if self.downscaling != 0:
                im = cv2.resize(im, self.cameraview_size)
            bmp = wx.Bitmap.FromBuffer(im.shape[1], im.shape[0], cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
            
            tmp_images.append(bmp)
            tmp_img_points.append(corner.reshape(-1, 2))
            tmp_obj_points.append(self.pattern_points)
        
        if tmp_images == []:
            wx.MessageBox('No image contains the target chessboard.','Error')
            return
        
        if len(not_detected) > 0:
            wx.MessageBox('The target chessboard was not found in {} image(s).'.format(len(not_detected)),'Warning')
        
        self.images.extend(tmp_images)
        self.obj_points.extend(tmp_obj_points)
        self.img_points.extend(tmp_img_points)

        self.update_preview()

    def set_chessboard(self, event=None):
        dlg = set_chessboard_dlg(self)
        if dlg.ShowModal() != wx.ID_OK:
            return

        prev_square_size = self.square_size

        try:
            self.square_size = int(dlg.ctrl_square_size.GetValue())
        except:
            wx.MessageBox('Invalid square size ({})'.format(dlg.ctrl_square_size.GetValue()),'Error')
            return

        try:
            ps = dlg.ctrl_pattern_size.GetValue().split(',')
            self.pattern_size = (int(ps[0]), int(ps[1]))
        except:
            wx.MessageBox('Invalid N of corners ({})'.format(dlg.ctrl_pattern_size.GetValue()),'Error')
            self.square_size = prev_square_size
            return

        self.pattern_points = np.zeros( (np.prod(self.pattern_size), 3), np.float32 ) #Chessboard (X,Y,Z) coordiate (Z=0)
        self.pattern_points[:,:2] = np.indices(self.pattern_size).T.reshape(-1, 2)
        self.pattern_points *= self.square_size


    def run_calibration(self, evt):
        if len(self.img_points) < 1:
            wx.MessageBox('Add images to run calibration.','Caution')
            return

        rms, K, d, r, t = cv2.calibrateCamera(
            self.obj_points, self.img_points, (self.x, self.y), None, None)

        dlg = cal_results_dlg(self,(self.x, self.y),(rms, K, d))
        res = dlg.ShowModal()

        # np.savetxt("rms.csv", rms, delimiter =',',fmt="%0.14f")
        # np.savetxt("K.csv", K, delimiter =',',fmt="%0.14f")

    def show_prev_image(self, evt):
        if self.images == []:
            return
        
        if self.current_preview_index > 0:
            self.current_preview_index -= 1
            self.update_preview()

    def show_next_image(self, evt):
        if self.images == []:
            return

        if self.current_preview_index < len(self.images)-1:
            self.current_preview_index += 1
            self.update_preview()

    def delete_image(self, evt):
        if self.images == []:
            return
        
        self.images.pop(self.current_preview_index)
        self.img_points.pop(self.current_preview_index)
        self.obj_points.pop(self.current_preview_index)

        if self.images == []:
            self.update_preview()

        else:
            if self.current_preview_index >= len(self.images):
                self.current_preview_index -= 1
            self.update_preview()
    
    def update_preview(self):
        if len(self.images) == 0:
            self.text_current_image.SetLabel("No image")
            self.preview.SetBitmap(wx.Bitmap.FromRGBA(PREVIEW_WIDTH, PREVIEW_HEIGHT, alpha=255))
        else:
            self.text_current_image.SetLabel("{} of {} images".format(self.current_preview_index+1, len(self.images)))
            self.preview.SetBitmap(self.images[self.current_preview_index])

if __name__ == '__main__':
    app = wx.App(False)
    dlg = camera_calibration_app()
    app.MainLoop()

