import argparse
import os
import queue
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import dlib
import numpy as np
import wx
import wx.lib.newevent

import GazeParser

from ...TrackingTools.Tracker.config import config as configuration
from ...TrackingTools.Tracker.data import gazedata
from ...TrackingTools.Tracker.eye import eye_filter, eyedata
from ...TrackingTools.Tracker.face import facedata, get_face_boxes, get_face_landmarks
from ...TrackingTools.Tracker.screen import screen
from ...TrackingTools.Tracker.iris_detectors import get_iris_detector
from .._dialogs import (DlgAskopenfilename, DlgAskyesno,
                        DlgAsksaveasfilename, DlgShowerror, DlgShowinfo)

debug_mode = True

ID_LOAD_MOVIE = wx.NewIdRef()
ID_LOAD_CAL = wx.NewIdRef()
ID_LOAD_CAMERACONFIG = wx.NewIdRef()
ID_LOAD_FACEMODEL = wx.NewIdRef()
ID_OPEN_DATAFILE = wx.NewIdRef()
ID_CLOSE_DATAFILE = wx.NewIdRef()
ID_RUN_REC = wx.NewIdRef()
ID_ABORT_REC = wx.NewIdRef()

ID_DFMODE_NEW = wx.NewIdRef()
ID_DFMODE_OVERWRITE = wx.NewIdRef()
ID_DFMODE_RENAME = wx.NewIdRef()
ID_OUTPUTMODE_CAL = wx.NewIdRef()
ID_OUTPUTMODE_NOCAL = wx.NewIdRef()
ID_OUTPUTMODE_BOTH = wx.NewIdRef()

menu_items_all = [
    ID_LOAD_MOVIE,
    ID_LOAD_CAL,
    ID_LOAD_CAMERACONFIG,
    ID_LOAD_FACEMODEL,
    ID_OPEN_DATAFILE,
    ID_CLOSE_DATAFILE,
    ID_RUN_REC,
    ID_DFMODE_NEW,
    ID_DFMODE_OVERWRITE,
    ID_DFMODE_RENAME,
    ID_OUTPUTMODE_CAL,
    ID_OUTPUTMODE_NOCAL,
    ID_OUTPUTMODE_BOTH,
]

module_dir = Path(__file__).parent.parent.parent

eye_image_width = 256
eye_image_height = 128

class CameraView(wx.StaticBitmap):
    def __init__(self, *args, **kwargs):
        super(CameraView, self).__init__(*args, **kwargs)
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


class Offline_Tracker(wx.Frame):
    debug = True
    NewImageEvent, EVT_NEWIMAGE = wx.lib.newevent.NewEvent()
 
    def __init__(self, config=None, batch=False, movie=None, cal=None, output=None, iris_detector=None, overwrite=False, force_calibrationless=False):
        self.config = config
        self.batch_mode = batch
        self.overwrite = overwrite

        self.cap = None
        self.movie_frames = None
        self.movie_fps = None

        if iris_detector is None:
            raise RuntimeError('Offline_Tracker: iris_detector must be specified.')
        self.iris_detector = iris_detector

        self.camera_matrix = config.camera_matrix
        self.downscaling_factor = config.downscaling_factor
        self.screen = screen()
        self.screen.set_parameters(
            conf.screen_width/conf.screen_h_res, 
            conf.screen_rot,
            conf.screen_offset)
        self.face_model = config.face_model
        self.eye_params = config.eye_params

        self.eye_filter_L = None
        self.eye_filter_R = None
        self.face_rvec = None
        self.face_tvec = None

        self.area_of_interest = None
        self.updating_aoi = False
        self.aoi_p0 = None
        self.orig_img = None

        self.run_offline_recording = False
        self.render_image = True
 
        self.calibration_sample = []
        self.calibration_debug_data = []
        
        self.fitting_param = None
        self.data = None

        self.calibration_precision = np.array([np.nan, np.nan])
        self.calibration_accuracy = np.array([np.nan, np.nan])
        self.calibration_max_error = np.array([np.nan, np.nan])
        self.calibration_results_detail = ''

        self.cameraview_size = (max(int(config.camera_resolution_v*self.downscaling_factor), eye_image_height), 
                                int(config.camera_resolution_h*self.downscaling_factor)+eye_image_width*2)

        style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        super(wx.Frame, self).__init__(None, wx.ID_ANY, style=style)

        self.mediapanel = wx.Panel(self, wx.ID_ANY, size=(self.cameraview_size[1],self.cameraview_size[0]))
        self.camera_view = self.init_cameraview(self.mediapanel)
        self.movie_frame_text = wx.StaticText(self, wx.ID_ANY, '-/- frames')

        self.statuspanel = wx.Panel(self, wx.ID_ANY)
        self.status_camera_param = wx.StaticText(self.statuspanel, wx.ID_ANY, self.config.camera_param_file)
        self.status_face_model = wx.StaticText(self.statuspanel, wx.ID_ANY, self.config.face_model_file)
        self.status_movie_file = wx.StaticText(self.statuspanel, wx.ID_ANY, '-')
        self.status_cal_file = wx.StaticText(self.statuspanel, wx.ID_ANY, '-')
        self.status_output_file = wx.StaticText(self.statuspanel, wx.ID_ANY, '-')
        statussizer = wx.FlexGridSizer(cols=2, gap=(10,0))
        statussizer.Add(wx.StaticText(self.statuspanel, wx.ID_ANY, 'Camera parameter file:'))
        statussizer.Add(self.status_camera_param)
        statussizer.Add(wx.StaticText(self.statuspanel, wx.ID_ANY, 'Face model file:'))
        statussizer.Add(self.status_face_model)
        statussizer.Add(wx.StaticText(self.statuspanel, wx.ID_ANY, 'Movie file:'))
        statussizer.Add(self.status_movie_file)
        statussizer.Add(wx.StaticText(self.statuspanel, wx.ID_ANY, 'Calibration file:'))
        statussizer.Add(self.status_cal_file)
        statussizer.Add(wx.StaticText(self.statuspanel, wx.ID_ANY, 'Output file:'))
        statussizer.Add(self.status_output_file)
        self.statuspanel.SetSizer(statussizer)
        
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(self.mediapanel, 4, wx.EXPAND)
        mainsizer.Add(self.movie_frame_text, 0, wx.EXPAND|wx.ALL, border=5)
        mainsizer.Add(self.statuspanel, 0, wx.EXPAND|wx.ALL, border=5)
        self.SetSizer(mainsizer)
        self.SetSize(self.BestSize)
        self.Bind(Offline_Tracker.EVT_NEWIMAGE, self.new_image)

        self.menu_bar = wx.MenuBar()
        self.menu_file = wx.Menu()
        self.menu_rec = wx.Menu()
        self.menu_bar.Append(self.menu_file, 'File')
        self.menu_file.Append(ID_LOAD_MOVIE, 'Load movie')
        self.menu_file.Append(ID_LOAD_CAL, 'Load calibration')
        self.menu_file.Append(ID_LOAD_CAMERACONFIG, 'Load Camera config')
        self.menu_file.Append(ID_LOAD_FACEMODEL, 'Load Face model')
        self.menu_file.AppendSeparator()
        self.menu_file.Append(ID_OPEN_DATAFILE, 'Open data file')
        self.menu_file.Append(ID_CLOSE_DATAFILE, 'Close data file')
        self.Bind(wx.EVT_MENU, self.load_movie, id=ID_LOAD_MOVIE)
        self.Bind(wx.EVT_MENU, self.open_calibration, id=ID_LOAD_CAL)
        self.Bind(wx.EVT_MENU, self.open_camera_config, id=ID_LOAD_CAMERACONFIG)
        self.Bind(wx.EVT_MENU, self.open_face_model, id=ID_LOAD_FACEMODEL)
        self.Bind(wx.EVT_MENU, self.open_datafile, id=ID_OPEN_DATAFILE)
        self.Bind(wx.EVT_MENU, self.close_datafile, id=ID_CLOSE_DATAFILE)

        self.menu_bar.Append(self.menu_rec, 'Run')
        self.menu_rec.Append(ID_RUN_REC, 'Run offline recording')
        self.menu_rec.Append(ID_ABORT_REC, 'Abort recording')
        self.Bind(wx.EVT_MENU, self.start_offline_recording, id=ID_RUN_REC)
        self.Bind(wx.EVT_MENU, self.abort_offline_recording, id=ID_ABORT_REC)
        self.menu_bar.Enable(ID_ABORT_REC,False) # disable Abort menu

        self.menu_option = wx.Menu()
        self.menu_bar.Append(self.menu_option, 'Option')
        self.menu_datafile_open_mode = wx.Menu()
        self.menu_output_mode = wx.Menu()
        self.menu_option.AppendSubMenu(self.menu_datafile_open_mode, 'Datafile open mode')
        self.menu_option.AppendSubMenu(self.menu_output_mode, 'Output mode')
        self.menu_datafile_open_mode.AppendRadioItem(ID_DFMODE_NEW, 'Don\'t overwrite existing file')
        self.menu_datafile_open_mode.AppendRadioItem(ID_DFMODE_OVERWRITE, 'Overwrite existing file')
        self.menu_datafile_open_mode.AppendRadioItem(ID_DFMODE_RENAME, 'Rename existing file')
        self.menu_output_mode.AppendRadioItem(ID_OUTPUTMODE_CAL, 'Calibrated')
        self.menu_output_mode.AppendRadioItem(ID_OUTPUTMODE_NOCAL, 'Calibrationless')
        self.menu_output_mode.AppendRadioItem(ID_OUTPUTMODE_BOTH, 'Both')
        # datafile open mode
        if self.config.datafile_open_mode == 'new':
            self.menu_datafile_open_mode.Check(ID_DFMODE_NEW, True)
        elif self.config.datafile_open_mode == 'overwrite':
            self.menu_datafile_open_mode.Check(ID_DFMODE_OVERWRITE, True)
        elif self.config.datafile_open_mode == 'rename':
            self.menu_datafile_open_mode.Check(ID_DFMODE_RENAME, True)
        else:
            raise ValueError('Invalid datafile open mode:{}'.format(self.config.datafile_open_mode))
        # output mode
        if self.config.calibrated_output and config.calibrationless_output:
            self.menu_output_mode.Check(ID_OUTPUTMODE_BOTH, True)
        elif self.config.calibrated_output:
            self.menu_output_mode.Check(ID_OUTPUTMODE_CAL, True)
        elif self.config.calibrationless_output:
            self.menu_output_mode.Check(ID_OUTPUTMODE_NOCAL, True)
        else:
            raise ValueError('Invalid datafile open mode')

        self.Bind(wx.EVT_MENU, self.update_option, id=ID_OUTPUTMODE_BOTH)
        self.Bind(wx.EVT_MENU, self.update_option, id=ID_OUTPUTMODE_CAL)
        self.Bind(wx.EVT_MENU, self.update_option, id=ID_OUTPUTMODE_NOCAL)

        self.SetMenuBar(self.menu_bar)

        notice_option_msg = []
        if overwrite:
            if batch:
                # force overwrite
                self.config.datafile_open_mode = 'overwrite'
            else:
                notice_option_msg.append('    --overwrite')
        if force_calibrationless:
            if batch:
                # force calibrationless output
                self.config.calibrated_output = False
                self.config.calibrationless_output = True
            else:
                notice_option_msg.append('    --force_calibrationless')

        if len(notice_option_msg)>0:
            DlgShowinfo(self, 'Info', 'Following option(s) are effective only in batch mode.\n{}'.format('\n'.join(notice_option_msg)))

        if cal is not None:
            self.open_calibration(cal)

        if movie is not None:
            self.load_movie(movie)

        if output is not None:
            self.open_datafile(output)

        self.queue = queue.Queue(1)
        self.run_main_loop = True
        self.thread = threading.Thread(target=self.main_loop) #, args=(self, self.queue, self.cap))
        self.thread.daemon = True
        self.thread.start()

        self.Show()

        if self.batch_mode:
            self.start_offline_recording(None)

    def init_cameraview(self, panel):
        camera_view = CameraView(panel, wx.ID_ANY, wx.Bitmap(self.cameraview_size[1],self.cameraview_size[0]))
        camera_view.Bind(wx.EVT_LEFT_DOWN, self.camera_view_leftdown)
        camera_view.Bind(wx.EVT_LEFT_UP, self.camera_view_leftup)
        camera_view.Bind(wx.EVT_LEAVE_WINDOW, self.camera_view_leave)
        camera_view.Bind(wx.EVT_LEFT_DCLICK, self.camera_view_leftdclick)
        camera_view.Bind(wx.EVT_MOTION, self.camera_view_motion)
        return camera_view
    
    def remove_cameraview(self, camera_view):
        camera_view.Unbind(wx.EVT_LEFT_DOWN)
        camera_view.Unbind(wx.EVT_LEFT_UP)
        camera_view.Unbind(wx.EVT_LEAVE_WINDOW)
        camera_view.Unbind(wx.EVT_LEFT_DCLICK)
        camera_view.Unbind(wx.EVT_MOTION)
        camera_view.Destroy()

    def load_movie(self, event):
        if isinstance(event, str):
            filename = event
        else:
            filename = DlgAskopenfilename(self)
            if filename == '':
                return
            
        self.cap = cv2.VideoCapture(filename)
        if self.cap.isOpened():
            img_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            img_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

            if img_width != self.config.camera_resolution_h or img_height != self.config.camera_resolution_v:
                DlgShowerror(self, 'Error', 'Movie resolution ({:.0f},{:.0f}) and camera parameter ({:.0f},{:.0f}) do not match.'.format(
                    img_width, img_height, self.config.camera_resolution_h, self.config.camera_resolution_v))
                self.cap.release()
                return
            
            self.movie_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.movie_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.movie_frame_text.SetLabel('-/{} frames'.format(self.movie_frames))

            self.status_movie_file.SetLabel(filename)

            #read and show the first frame
            ret, im = self.cap.read()
            if ret:
                #draw AOI
                self.orig_img = im.copy()
                if self.area_of_interest is not None:
                    cv2.rectangle(im, (self.area_of_interest.left(),self.area_of_interest.top()),
                                        (self.area_of_interest.right(),self.area_of_interest.bottom()),
                                        (0,255,255), thickness=2)

                im = self.get_preview_image(im, None, None)
                bmp = wx.Bitmap.FromBuffer(im.shape[1], im.shape[0], cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
                self.camera_view.SetBitmap(bmp)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        else:
            if self.batch_mode:
                print('Error: cannot open {} as a movie.'.format(filename))
                self.cap = None
                self.Destroy()
            else:
                DlgShowerror(self,'Error','Cannot open {} as a movie'.format(filename))
                self.cap = None
        
    def open_camera_config(self,event):
        filename = DlgAskopenfilename(self, filetypes='Camera config (*.cfg)|*.cfg')
        if filename == '':
            return
        
        tmpconfig = configuration()
        try:
            tmpconfig.load_camera_param(filename)
        except:
            DlgShowerror(self, 'Error', 'Cannot open {} as a camera parameter file'.format(filename))
            return
        
        if self.cap is not None and self.cap.isOpened():
            w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            if w != tmpconfig.camera_resolution_h or h != tmpconfig.camera_resolution_v:
                # this function is not called in batch mode.
                if DlgAskyesno(self, 'Info',
                    'Resolution defined in this cameara parameter file ({:.0f},{:.0f}) does not match with that of the current movie ({:.0f},{:.0f})\n Do you want to close movie?'.format(
                        tmpconfig.camera_resolution_h, tmpconfig.camera_resolution_v, w, h)):
                    self.cap.release()
                    self.cap = None
                else:
                    DlgShowinfo(self,'Info','Camera configuration was not updated.')
                    return

        self.config.load_camera_param(filename)

        self.camera_matrix = self.config.camera_matrix
        self.downscaling_factor = self.config.downscaling_factor

        self.screen = screen()
        self.screen.set_parameters(
            self.config.screen_width/conf.screen_h_res, 
            self.config.screen_rot,
            self.config.screen_offset)

        self.cameraview_size = (max(int(self.config.camera_resolution_v*self.downscaling_factor), eye_image_height), 
                                int(self.config.camera_resolution_h*self.downscaling_factor)+eye_image_width*2)
        sizer = self.GetSizer()
        sizer.Remove(0)
        self.remove_cameraview(self.camera_view)
        self.mediapanel.Destroy()
        self.mediapanel = wx.Panel(self, wx.ID_ANY, size=(self.cameraview_size[1],self.cameraview_size[0]))
        self.camera_view = self.init_cameraview(self.mediapanel)
        sizer.Prepend(self.mediapanel, 4, wx.EXPAND)
        self.Layout()
        self.SetSize(self.GetBestSize())

        self.status_camera_param.SetLabel(filename)
        DlgShowinfo(self, 'Info', 'Camera parameters are updated.')

    def open_face_model(self,event):
        filename = DlgAskopenfilename(self, filetypes='Face model (*.cfg)|*.cfg')
        if filename == '':
            return
        
        self.config.load_face_model(filename)
        self.face_model = self.config.face_model
        self.eye_params = self.config.eye_params

        self.status_face_model.SetLabel(filename)
        DlgShowinfo(self, 'Info', 'Face model is updated.')

    def open_calibration(self, event):
        if isinstance(event, str):
            filename = event
        else:
            filename = DlgAskopenfilename(self, filetypes='Calibration result (*.npz)|*.npz')
            if filename == '':
                return
        
        try:
            data = np.load(filename)
        except:
            if self.batch_mode:
                print('Error: cannot open {} as the calibration result.'.format(filename))
                self.Destroy()
            else:
                DlgShowerror(self,'Error','Cannot open {} as the calibration result'.format(filename))

        try:
            self.fitting_param = data['fitting_param']
            self.calibration_accuracy = data['accuracy']
            self.calibration_precision = data['precision']
            aoi = data['area_of_interest']
            self.area_of_interest = dlib.rectangle(*aoi) if not np.isnan(aoi[0]) else None
            # max_error, results_detail
        except:
            if self.batch_mode:
                print('Error: cannot open {} as the calibration result.'.format(filename))
                self.Destroy()
            else:
                DlgShowerror(self,'Error','Cannot open {} as the calibration result'.format(filename))

        self.status_cal_file.SetLabel(filename)

    def update_option(self,event):
        id = event.GetId()
        if id == ID_DFMODE_NEW:
            self.config.datafile_open_mode = 'new'
        elif id == ID_DFMODE_OVERWRITE:
            self.config.datafile_open_mode = 'overwrite'
        elif id == ID_DFMODE_RENAME:
            self.config.datafile_open_mode = 'rename'
        elif id == ID_OUTPUTMODE_BOTH:
            self.config.calibrated_output = True
            self.config.calibrationless_output = True
        elif id == ID_OUTPUTMODE_CAL:
            self.config.calibrated_output = True
            self.config.calibrationless_output = False
        elif id == ID_OUTPUTMODE_NOCAL:
            self.config.calibrated_output = False
            self.config.calibrationless_output = True
        else:
            print('update_option: invalid event ID')

    def start_offline_recording(self, event):
        if self.cap is None:
            if not self.batch_mode:
                DlgShowerror(self, 'Error', 'Movie file is not opened.')
            return 
        if self.config.calibrated_output and self.fitting_param is None:
            if not self.batch_mode:
                DlgShowerror(self, 'Error', 'Calibration data is not loaded.')
            return
        if not self.data.is_opened():
            if not self.batch_mode:
                DlgShowerror(self, 'Error', 'Datafile is not opened.')
            return
        else:
            self.data.start_recording('-')

        for id in menu_items_all:
            self.menu_bar.Enable(id,False)
        self.menu_bar.Enable(ID_ABORT_REC,True) # enable Abort menu

        self.run_offline_recording = True
        self.capture_time = 0.0
    
    def abort_offline_recording(self, event):
        self.run_offline_recording = False
        if self.batch_mode:
            self.data.stop_recording()
            self.data.close()
            self.Destroy()
        else:
            self.data.stop_recording()
            self.data.flush()
            for id in menu_items_all:
                self.menu_bar.Enable(id, True)
            self.menu_bar.Enable(ID_ABORT_REC, False)
            DlgShowinfo(self, 'Info', 'Abort.')

            self.aoi_update()
            #im = self.get_preview_image(self.orig_img, None, None)
            #if self.area_of_interest is not None:
            #    print('(',self.area_of_interest)
            #    cv2.rectangle(im, (self.area_of_interest.left(),self.area_of_interest.top()),
            #                        (self.area_of_interest.right(),self.area_of_interest.bottom()),
            #                        (0,255,255), thickness=2)
            #bmp = wx.Bitmap.FromBuffer(im.shape[1], im.shape[0], cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
            #self.camera_view.SetBitmap(bmp)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # seek to first frame

    def new_image(self, event):
        if not self.queue.empty():
            img = self.queue.get(False)
            bmp = wx.Bitmap.FromBuffer(img.shape[1], img.shape[0], cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            self.camera_view.SetBitmap(bmp)

    def camera_view_leftdown(self,event):
        if self.run_offline_recording:
            return

        if not self.updating_aoi:
            self.aoi_p0 = event.GetPosition()
            self.updating_aoi = True

    def camera_view_leftup(self,event):
        if self.run_offline_recording:
            return

        if self.updating_aoi:
            p1 = event.GetPosition()
            left = int(min(self.aoi_p0[0],p1[0]) / self.downscaling_factor)
            right = int(max(self.aoi_p0[0],p1[0]) / self.downscaling_factor)
            top = int(min(self.aoi_p0[1],p1[1]) / self.downscaling_factor)
            bottom = int(max(self.aoi_p0[1],p1[1]) / self.downscaling_factor)

            if right >= self.config.camera_resolution_h:
                right = self.config.camera_resolution_h-1

            if (right-left) * (bottom-top) != 0:
                self.area_of_interest =  dlib.rectangle(left, top, right, bottom)
            self.updating_aoi = False

            self.aoi_update()

    def camera_view_leave(self,event):
        if self.run_offline_recording:
            return

        if self.updating_aoi:
            p1 = event.GetPosition()
            left = int(min(self.aoi_p0[0],p1[0]) / self.downscaling_factor)
            right = int(max(self.aoi_p0[0],p1[0]) / self.downscaling_factor)
            top = int(min(self.aoi_p0[1],p1[1]) / self.downscaling_factor)
            bottom = int(max(self.aoi_p0[1],p1[1]) / self.downscaling_factor)

            if right >= self.config.camera_resolution_h:
                right = self.config.camera_resolution_h-1

            if (right-left) * (bottom-top) != 0:
                self.area_of_interest =  dlib.rectangle(left, top, right, bottom)
            self.updating_aoi = False

            self.aoi_update()
    
    def camera_view_leftdclick(self,event):
        if self.run_offline_recording:
            return

        if self.updating_aoi:
            self.updating_aoi = False
        self.aoi_p0 = None
        self.area_of_interest = None

        self.aoi_update()
    
    def camera_view_motion(self,event):
        if self.run_offline_recording:
            return
        if self.orig_img is None:
            return
        
        if self.updating_aoi:
            im = self.orig_img.copy()
            p1 = self.camera_view.ScreenToClient(wx.GetMousePosition())
            left = int(min(self.aoi_p0[0],p1[0]) / self.downscaling_factor)
            right = int(max(self.aoi_p0[0],p1[0]) / self.downscaling_factor)
            top = int(min(self.aoi_p0[1],p1[1]) / self.downscaling_factor)
            bottom = int(max(self.aoi_p0[1],p1[1]) / self.downscaling_factor)
            cv2.rectangle(im, (left, top),(right,bottom),(0,255,255), thickness=1)

            im = self.get_preview_image(im, None, None)
            bmp = wx.Bitmap.FromBuffer(im.shape[1], im.shape[0], cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
            self.camera_view.SetBitmap(bmp)

    def aoi_update(self):
        if self.orig_img is None:
            return
        im = self.orig_img.copy()
        if self.area_of_interest is not None:
            cv2.rectangle(im, (self.area_of_interest.left(),self.area_of_interest.top()),
                                (self.area_of_interest.right(),self.area_of_interest.bottom()),
                                (0,255,255), thickness=2)

        im = self.get_preview_image(im, None, None)
        bmp = wx.Bitmap.FromBuffer(im.shape[1], im.shape[0], cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
        self.camera_view.SetBitmap(bmp)

    def open_datafile(self, event):
        if isinstance(event, str):
            filename = event
            open_mode = self.config.datafile_open_mode
        else:
            filename = DlgAsksaveasfilename(self, filetypes='GazeParser Tracker datafile (*.csv)|*.csv')
            if filename == '':
                return
            if Path(filename).exists():
                # User selects "overwrite" on File dialog.
                open_mode = 'overwrite'
            else:
                open_mode = self.config.datafile_open_mode
        
        if self.batch_mode:
            if self.overwrite:
                self.data = gazedata(filename, open_mode='overwrite',
                    calibrated_output=self.config.calibrated_output,
                    calibrationless_output=self.config.calibrationless_output)
            else:
                if os.path.exists(filename):
                    print('Error: output file ({}) already exists.'.format(filename))
                    self.Destroy()
                self.data = gazedata(filename, open_mode='new',
                    calibrated_output=self.config.calibrated_output,
                    calibrationless_output=self.config.calibrationless_output)
        
        else:
            self.data = gazedata(filename, open_mode=open_mode, 
                calibrated_output=self.config.calibrated_output,
                calibrationless_output=self.config.calibrationless_output)
            if not self.data.is_opened():
                DlgShowerror(self, 'Error', 'Could not open datafile ({}).\nCheck filename and datafile_open_mode.'.format(filename))
        
        self.status_output_file.SetLabel(filename)
        
    def close_datafile(self, event):
        # this method is not called in batch mode
        if self.data is None:
            DlgShowerror(self, 'Error', 'Data file is not opened.')
            return
        
        self.data.close()
        self.data = None
    
    def get_preview_image(self, frame, leye_img, reye_img):
        if self.downscaling_factor != 1.0:
            frame = cv2.resize(frame, None, fx=self.downscaling_factor, fy=self.downscaling_factor)

        canvas = np.zeros((self.cameraview_size[0],self.cameraview_size[1],3), dtype=np.uint8)

        canvas[:frame.shape[0],:frame.shape[1],:] = frame
        if leye_img is not None:
            canvas[:eye_image_height, frame.shape[1]:(frame.shape[1]+eye_image_width), :] = leye_img
        else:
            cv2.rectangle(canvas, (frame.shape[1],0), (frame.shape[1]+eye_image_width,eye_image_height), (64,64,64), thickness=1)

        if reye_img is not None:
            canvas[:eye_image_height, (frame.shape[1]+eye_image_width):(frame.shape[1]+eye_image_width*2), :] = reye_img
        else:
            cv2.rectangle(canvas, (frame.shape[1]+eye_image_width,0), (frame.shape[1]+eye_image_width*2,eye_image_height), (64,64,64), thickness=1)

        return canvas
    
    def main_loop(self):
        detect_face = False
        while self.run_main_loop:
            if not self.run_offline_recording:
                time.sleep(1.0)
                continue

            # process image
            ret, frame = self.cap.read()
            if ret:
                current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                self.movie_frame_text.SetLabel('{}/{} frames'.format(int(current_frame-1), self.movie_frames))
                frame_mono = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                reye_img = None
                leye_img = None
                
                if self.downscaling_factor == 1.0: # original size
                    dets, _ = get_face_boxes(frame_mono, engine='dlib_hog')
                else: # downscale camera image
                    dets, _ = get_face_boxes(cv2.resize(frame_mono, None, fx=self.downscaling_factor, fy=self.downscaling_factor), engine='dlib_hog') # detections, scores, weight_indices
                    inv = 1.0/self.downscaling_factor
                    # recover rectangle size
                    for i in range(len(dets)):
                        dets[i] = dlib.rectangle(int(dets[i].left()*inv), int(dets[i].top()*inv),
                                                int(dets[i].right()*inv), int(dets[i].bottom()*inv))

                detect_face = False
                if self.area_of_interest is None:
                    if len(dets) > 0:
                        detect_face = True
                        target_idx = 0
                else:
                    for target_idx in range(len(dets)):
                        if self.area_of_interest.contains(dets[target_idx]):
                            detect_face = True
                            break

                if detect_face: # face is found
                    detect_face = True
                    
                    # only first face is used
                    landmarks = get_face_landmarks(frame_mono, dets[target_idx])
                    
                    # create facedata
                    face = facedata(landmarks, camera_matrix=self.camera_matrix, face_model=self.face_model,
                        eye_params=self.eye_params, prev_rvec=self.face_rvec, prev_tvec=self.face_tvec)

                    # create eyedata
                    left_eye = eyedata(frame_mono, landmarks, eye='L', iris_detector=self.iris_detector)
                    right_eye = eyedata(frame_mono, landmarks, eye='R', iris_detector=self.iris_detector)

                    if not (left_eye.detected and right_eye.detected):
                        # Eyes are too close to the edges of the image
                        detect_face = False

                    # save previous rvec and tvec
                    self.face_rvec = face.rotation_vector
                    self.face_tvec = face.translation_vector

                else: # face is not found
                    detect_face = False
                    self.face_rvec = None
                    self.face_tvec = None
                
                if detect_face:
                    if self.data is not None:
                        self.data.append_data(self.capture_time, face, left_eye, right_eye, self.screen, self.fitting_param, self.eye_filter_L, self.eye_filter_R)

                else:
                    pass
                
                # update timestamp
                self.capture_time += 1000/self.movie_fps

                # render image

                if self.area_of_interest is not None:
                    cv2.rectangle(frame, (self.area_of_interest.left(),self.area_of_interest.top()),
                                        (self.area_of_interest.right(),self.area_of_interest.bottom()),
                                        (0,255,255), thickness=2)

                if detect_face:
                    if not left_eye.blink:
                        #left_eye.draw_marker(frame)
                        leye_img = left_eye.draw_marker_on_eye_image()
                    if not right_eye.blink:
                        #right_eye.draw_marker(frame)
                        reye_img = right_eye.draw_marker_on_eye_image()

                    face.draw_marker(frame)
                    face.draw_eyelids_landmarks(frame)
                
                if not self.queue.full():
                    canvas = self.get_preview_image(frame, leye_img, reye_img)
                    self.queue.put(canvas, False)
                    try:
                        wx.PostEvent(self, Offline_Tracker.NewImageEvent())
                    except:
                        break
            
            else: # movie is finished
                self.run_offline_recording = False
                if self.batch_mode:
                    self.data.stop_recording()
                    self.data.close()
                    self.Destroy()
                    break
                else:
                    self.data.stop_recording()
                    self.data.flush()
                    for id in menu_items_all:
                        self.menu_bar.Enable(id, True)
                    self.menu_bar.Enable(ID_ABORT_REC, False)
                    DlgShowinfo(self, 'Info', 'Done.')

                    self.aoi_update()
                    #im = self.get_preview_image(self.orig_img, None, None)
                    #if self.area_of_interest is not None:
                    #    cv2.rectangle(im, (self.area_of_interest.left(),self.area_of_interest.top()),
                    #                        (self.area_of_interest.right(),self.area_of_interest.bottom()),
                    #                        (0,255,255), thickness=2)
                    #bmp = wx.Bitmap.FromBuffer(im.shape[1], im.shape[0], cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
                    #self.camera_view.SetBitmap(bmp)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # seek to first frame


if __name__ == '__main__':

    camera_param_file = None
    face_model_file = None

    conf = configuration()
    arg_parser = argparse.ArgumentParser(description='GazeParser offline tracker')
    arg_parser.add_argument('--camera_param', type=str, help='camera parameters file')
    arg_parser.add_argument('--face_model', type=str, help='face model file')
    arg_parser.add_argument('--iris_detector', type=str, help='iris detector (ert, peak, enet or path to detector')
    arg_parser.add_argument('-b', '--batch', action='store_true', help='batch execution (movie and calibration are required')
    arg_parser.add_argument('-m', '--movie', type=str, help='movie file (required for batch execution)')
    arg_parser.add_argument('-c', '--cal', type=str, help='calibration file (required for batch execution)')
    arg_parser.add_argument('-o', '--output', type=str, help='output file (required for batch execution)')
    arg_parser.add_argument('--overwrite', action='store_true', help='overwrite output file (batch mode)')
    arg_parser.add_argument('--force_calibrationless', action='store_true', help='Force calibrationless output (batch mode)')
    args = arg_parser.parse_args()

    appConfigDir = Path(GazeParser.configDir)/'app'

    if not appConfigDir.exists():
        Path.mkdir(appConfigDir)
        print('info: {} is created.'.format(appConfigDir))

    defaultconfig = appConfigDir/'tracker.cfg'
    if not defaultconfig.exists():
        shutil.copy(module_dir/'app'/'tracker'/'tracker.cfg',defaultconfig)
        print('info: default config file is created in {}.'.format(appConfigDir))
    conf.load_application_param(defaultconfig)

    if args.camera_param is None:
        # read default file
        cfgfile = appConfigDir/'CamearaParam.cfg'
        if not cfgfile.exists():
            shutil.copy(module_dir/'TrackingTools'/'Tracker'/'resources'/'CameraParam.cfg', cfgfile)
            print('info: default camera parameter file is created in {}.'.format(appConfigDir))
        conf.load_camera_param(str(cfgfile))
        camera_param_file = str(cfgfile)
    else:
        conf.load_camera_param(args.camera_param)

    if args.face_model is None:
        cfgfile = appConfigDir/'FaceModel.cfg'
        if not cfgfile.exists():
            shutil.copy(module_dir/'TrackingTools'/'Tracker'/'resources'/'FaceModel.cfg',cfgfile)
            print('info: default face model file is created in {}.'.format(appConfigDir))
        conf.load_face_model(str(cfgfile))
        face_model_file = str(cfgfile)
    else:
        conf.load_face_model(face_model_file)
    
    if args.iris_detector is None:
        iris_detector = get_iris_detector(conf.iris_detector)
    else:
        iris_detector = get_iris_detector(args.iris_detector)
    if iris_detector is None:
        sys.exit()

    if args.batch:
        if args.movie is None or args.output is None:
            print('Movie and output are required to run in batch mode.')
            sys.exit()
        if args.cal is None:
            if conf.calibrated_output and (not args.force_calibrationless):
                print('Calibration file is not specified while CALIBRATED_OUTPUT is set to be True in the configuration file.  '\
                      'Specify calibration file, edit/change configuration file, or use --force_calibrationless option to run in batch mode.')
                sys.exit()
            
    app = wx.App(False)
    offline_tracker = Offline_Tracker(conf, batch=args.batch, movie=args.movie, cal=args.cal, output=args.output,
        iris_detector = iris_detector, overwrite=args.overwrite, force_calibrationless=args.force_calibrationless)
    app.MainLoop()

