import os
import numpy as np
import socket
import select
import queue
import threading
import time
import wx
import wx.lib.newevent
from datetime import datetime

import sys
import argparse

from ...core.config import config as configuration
from ...core.eye import eyedata, eye_filter
from ...core.face import facedata, get_face_boxes, get_face_landmarks
from ...core.screen import screen
from ...core.data import gazedata
from ...core.util import LM_calibration, calc_calibration_results
from .._dialogs import DlgAskopenfilename, DlgShowerror, DlgShowinfo
from ._util import load_gptracker_config

import dlib
import cv2

debug_mode = True

ID_LOAD_CAMERACONFIG = wx.NewIdRef()
ID_LOAD_FACEMODEL = wx.NewIdRef()
ID_SAVE_CAMERACONFIG = wx.NewIdRef()
ID_SAVE_FACEMODEL = wx.NewIdRef()
ID_CLOSE = wx.NewIdRef()
ID_CAMERA_EDIT = wx.NewIdRef()

ID_OUTPUTMODE_CAL = wx.NewIdRef()
ID_OUTPUTMODE_NOCAL = wx.NewIdRef()
ID_OUTPUTMODE_BOTH = wx.NewIdRef()

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

class CameraEditDlg(wx.Frame):
    def __init__(self, parent, id=wx.ID_ANY):
        super(CameraEditDlg, self).__init__(parent=parent, id=id)
        panel = wx.Panel(self, -1)
        bsizer = wx.BoxSizer()
        sizer_basicparam = wx.FlexGridSizer(rows=3, cols=2)
        self.textbox_camera_ID = wx.TextCtrl(panel, -1)
        self.textbox_camera_res = wx.TextCtrl(panel, -1)
        self.textbox_downscaling = wx.TextCtrl(panel, -1)
        sizer_basicparam.Add(wx.StaticText(panel, -1, 'OpenCV camera ID'), wx.GROW)
        sizer_basicparam.Add(self.textbox_camera_ID, wx.GROW)
        sizer_basicparam.Add(wx.StaticText(panel, -1, 'Resolution (H,V)'), wx.GROW)
        sizer_basicparam.Add(self.textbox_camera_res, wx.GROW)
        sizer_basicparam.Add(wx.StaticText(panel, -1, 'Downscaling factor'), wx.GROW)
        sizer_basicparam.Add(self.textbox_downscaling, wx.GROW)

        self.textbox_screen_w = wx.TextCtrl(panel, -1)
        self.textbox_screen_res = wx.TextCtrl(panel, -1)
        self.textbox_screen_offset = wx.TextCtrl(panel, -1)
        self.textbox_screen_rot = wx.TextCtrl(panel, -1)
        sizer_layout = wx.FlexGridSizer(rows=4, cols=2)
        sizer_layout.Add(wx.StaticText(panel, -1, 'Screen Width'), wx.GROW)
        sizer_layout.Add(self.textbox_screen_w, wx.GROW)
        sizer_layout.Add(wx.StaticText(panel, -1, 'Resolution (H)'), wx.GROW)
        sizer_layout.Add(self.textbox_screen_res, wx.GROW)
        sizer_layout.Add(wx.StaticText(panel, -1, 'Offset (X,Y,Z)'), wx.GROW)
        sizer_layout.Add(self.textbox_screen_offset, wx.GROW)
        sizer_layout.Add(wx.StaticText(panel, -1, 'Rotation (X)'), wx.GROW)
        sizer_layout.Add(self.textbox_screen_rot, -1, wx.GROW)

class Tracker(wx.Frame):
    debug = True
    pressed_keys = {'Q':False, 'UP':False, 'DOWN':False, 'LEFT':False, 'RIGHT':False}
    NewImageEvent, EVT_NEWIMAGE = wx.lib.newevent.NewEvent()
 
    def __init__(self, camera, config, port_send=10001, port_receive=10000, iris_detector=None):

        self.config = config
        self.camera = camera

        if iris_detector is None:
            raise RuntimeError('Tracker: iris_detector must be specified.')
        self.iris_detector = iris_detector

        # init TCP/IP connection
        self.server_connected = False
        self.port_send = port_send
        self.port_receive = port_receive
        self.readsock_list = []

        self.sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock_server.bind(('', self.port_receive))
        self.sock_server.listen(1)
        self.sock_server.setblocking(0)
        self.readsock_list.append(self.sock_server)

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

        self.in_recording = False
        self.in_calibration = False
        self.calibrated = False
        self.render_image = True
        
        self.calibration_sample = []
        self.calibration_debug_data = []
        
        self.fitting_param = None
        self.data = None

        self.calibration_precision = np.array([np.nan, np.nan])
        self.calibration_accuracy = np.array([np.nan, np.nan])
        self.calibration_max_error = np.array([np.nan, np.nan])
        self.calibration_results_detail = ''

        self.rec_start_time = time.perf_counter()
    
        self.cameraview_size = (max(int(config.camera_resolution_v*self.downscaling_factor), eye_image_height), 
                                int(config.camera_resolution_h*self.downscaling_factor)+eye_image_width*2)
 
        style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        super(wx.Frame, self).__init__(None, wx.ID_ANY, style=style)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = wx.Panel(self, wx.ID_ANY, size=(self.cameraview_size[1],self.cameraview_size[0]))
        self.camera_view = CameraView(self.panel, wx.ID_ANY, wx.Bitmap(self.cameraview_size[1],self.cameraview_size[0]))
        sizer.Add(self.panel)
        self.SetSizerAndFit(sizer)
        self.Bind(Tracker.EVT_NEWIMAGE, self.newImage)

        menu_bar = wx.MenuBar()
        menu_file = wx.Menu()
        menu_load = wx.Menu()
        menu_save = wx.Menu()
        menu_camera = wx.Menu()
        menu_option = wx.Menu()
        menu_datafile_open_mode = wx.Menu()
        menu_output_mode = wx.Menu()

        menu_bar.Append(menu_file, 'File')
        menu_file.AppendSubMenu(menu_load, 'Load config')
        menu_file.AppendSubMenu(menu_save, 'Save config')
        menu_file.Append(ID_CLOSE, 'Close')
        menu_load.Append(ID_LOAD_CAMERACONFIG, 'Camera config')
        menu_load.Append(ID_LOAD_FACEMODEL, 'Face model')
        menu_save.Append(ID_SAVE_CAMERACONFIG, 'Camera config')
        menu_save.Append(ID_SAVE_FACEMODEL, 'Face model')
        menu_save.FindItemById(ID_SAVE_CAMERACONFIG).Enable(False) # not implemented
        menu_save.FindItemById(ID_SAVE_FACEMODEL).Enable(False) # not implemented

        menu_bar.Append(menu_camera, 'Camera')
        menu_camera.Append(ID_CAMERA_EDIT, 'Edit Camera parameters')
        menu_camera.FindItemById(ID_CAMERA_EDIT).Enable(False) # not implemented

        menu_bar.Append(menu_option, 'Option')
        menu_option.AppendSubMenu(menu_output_mode, 'Output mode')
        menu_output_mode.AppendRadioItem(ID_OUTPUTMODE_CAL, 'Calibrated')
        menu_output_mode.AppendRadioItem(ID_OUTPUTMODE_NOCAL, 'Calibrationless')
        menu_output_mode.AppendRadioItem(ID_OUTPUTMODE_BOTH, 'Both')
        # output mode
        if config.calibrated_output and config.calibrationless_output:
            menu_output_mode.Check(ID_OUTPUTMODE_BOTH, True)
        elif config.calibrated_output:
            menu_output_mode.Check(ID_OUTPUTMODE_CAL, True)
        elif config.calibrationless_output:
            menu_output_mode.Check(ID_OUTPUTMODE_NOCAL, True)
        else:
            raise ValueError('Invalid datafile open mode')

        self.SetMenuBar(menu_bar)
        self.Bind(wx.EVT_MENU, self.load_camera_config, id=ID_LOAD_CAMERACONFIG)
        self.Bind(wx.EVT_MENU, self.load_face_model, id=ID_LOAD_FACEMODEL)
        self.Bind(wx.EVT_MENU, self.close, id=ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.update_option, id=ID_OUTPUTMODE_BOTH)
        self.Bind(wx.EVT_MENU, self.update_option, id=ID_OUTPUTMODE_CAL)
        self.Bind(wx.EVT_MENU, self.update_option, id=ID_OUTPUTMODE_NOCAL)

        self.Show()

        self.queue = queue.Queue(1)
        self.run_main_loop = True
        self.thread = threading.Thread(target=self.main_loop) #, args=(self, self.queue, self.cap))
        self.thread.start()
    
    def close(self, event):
        self.Close()

    def load_camera_config(self,event):
        filename = DlgAskopenfilename(self, filetypes='Camera config (*.cfg)|*.cfg')
        if filename == '':
            return
        
        conf = configuration()
        try:
            conf.load_camera_param(filename)
        except:
            DlgShowerror(self, 'Error', 'Could not read {} as a configuration file.'.format(filename))
            return
        
        if self.config.camera_resolution_h != conf.camera_resolution_h or self.config.camera_resolution_v != conf.camera_resolution_v:
            DlgShowinfo(self, 'Info', 'Camera resolution ({},{}) defined in "{}" differs from the current resolution ({},{}). '
                        'Camera resolution can be set only at startup. No other settings were changed either.'.format(
                conf.camera_resolution_h, conf.camera_resolution_v, filename,
                self.config.camera_resolution_h, self.config.camera_resolution_v
            ))
            return
        
        self.config = conf
        self.camera_matrix = self.config.camera_matrix
        self.downscaling_factor = self.config.downscaling_factor

        self.screen = screen()
        self.screen.set_parameters(
            self.config.screen_width/conf.screen_h_res, 
            self.config.screen_rot,
            self.config.screen_offset)

    def load_face_model(self,event):
        filename = DlgAskopenfilename(self, filetypes='Face model (*.cfg)|*.cfg')
        if filename == '':
            return
        
        self.config.load_face_model(filename)
        self.face_model = self.config.face_model
        self.eye_params = self.config.eye_params

    def update_option(self,event):
        id = event.GetId()
        if id == ID_OUTPUTMODE_BOTH:
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

    def newImage(self, event):
        if not self.queue.empty():
            img = self.queue.get(False)
            bmp = wx.Bitmap.FromBuffer(img.shape[1], img.shape[0], cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            self.camera_view.SetBitmap(bmp)
            
    def tcp_accept(self):
        # accept TCP/IP connection
        if self.sock_server is None or self.server_connected:
            return

        [r, w, c] = select.select(self.readsock_list, [], [], 0)
        for x in r:
            if x is self.sock_server:
                (conn, addr) = self.sock_server.accept()
                self.readsock_list.append(conn)
                self.server_connected = True
                print('accepted: {}'.format(addr))
                
                self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock_send.connect((addr[0], self.port_send))
                self.sock_send.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                break

    def send_command(self, command):
        if isinstance(command, str):
            command = command.encode('utf-8')
        self.sock_send.send(command)

    def process_message(self):
        # receive message
        if self.sock_server is None or not self.server_connected:
            return

        data = b''
        [r, w, c] = select.select(self.readsock_list, [], [], 0)
        for x in r:
            try:
                newData = x.recv(4096)
            except:
                # connection closed
                self.server_connected = False
                self.tcp_accept()
                continue
            if newData:
                data = newData.split(b'\0')[:-1]
                i = 0
                while i<len(data) and data[i] != b'': # last item will be b''
               
                    command = data[i]
                    if command == b'key_Q':
                        self.pressed_keys[b'Q'] = True
                        i += 1
                    elif command == b'key_UP':
                        self.pressed_keys[b'UP'] = True
                        i += 1
                    elif command == b'key_DOWN':
                        self.pressed_keys[b'DOWN'] = True
                        i += 1
                    elif command == b'key_LEFT':
                        self.pressed_keys[b'LEFT'] = True
                        i += 1
                    elif command == b'key_RIGHT':
                        self.pressed_keys[b'RIGHT'] = True
                        i += 1
                    elif command == b'openDataFile':
                        self.open_datafile(data[i+1], int(data[i+2])) # filename and overwrite-flag
                        i += 3
                    elif command == b'insertSettings':
                        self.insert_settings(data[i+1])
                        i += 2
                    elif command == b'closeDataFile':
                        self.close_datafile()
                        i += 1
                    elif command == b'getCurrMenu':
                        self.get_current_menu()
                        i += 1
                    elif command == b'getImageData':
                        self.get_image_data()
                        i += 1
                    elif command == b'startCal':
                        param = list(map(int, data[i+1].split(b',')))
                        param.append(int(data[i+2]))
                        self.start_calibration(*param)
                        i += 3
                    elif command == b'getCalSample':
                        param = list(map(int, data[i+1].split(b',')))
                        self.get_calibration_sample(*param)
                        i += 2
                    elif command == b'endCal':
                        self.end_calibration()
                        i += 1
                    elif command == b'startVal':
                        i += 1
                    elif command == b'getValSample':
                        i += 1
                    elif command == b'endVal':
                        i += 1
                    elif command == b'toggleCalResult':
                        param = int(data[i+1])
                        i += 2
                    elif command == b'getCalResults':
                        response = '{:.2f},{:.2f},{:.2f},{:.2f}'.format(
                            self.calibration_precision[0],
                            self.calibration_max_error[0],
                            self.calibration_precision[1],
                            self.calibration_max_error[1])+chr(0)
                        self.send_command(response)
                        i += 1
                    elif command == b'getCalResultsDetail':
                        self.send_command(self.calibration_results_detail+chr(0))
                        i += 1
                    elif command == b'saveCalValResultsDetail':
                        i += 1
                    elif command == b'startRecording':
                        message = data[i+1]
                        self.start_recording(message)
                        i += 2
                    elif command == b'stopRecording':
                        message = data[i+1]
                        self.stop_recording(message)
                        i += 2
                    elif command == b'startMeasurement':
                        i += 1
                    elif command == b'stopMeasurement':
                        i += 1
                    elif command == b'insertMessage':
                        self.insert_message(data[i+1])
                        i += 2
                    elif command == b'getEyePosition':
                        ma = int(data[i+1])
                        if self.data is not None and self.data.has_data():
                            (lx, ly, rx, ry) = self.data.get_latest_gazepoint(ma)
                            # TODO: support pupil size
                            response = ('{:.0f},{:.0f},{:.0f},{:.0f},{:.0f},{:.0f}'+chr(0)).format(
                                lx, ly, rx, ry, 0.0, 0.0)
                        else:
                            response = 'nan,nan,nan,nan,nan,nan'+chr(0)
                        self.send_command(response)
                        i += 2
                    elif command == b'getWholeEyePositionList':
                        i += 1
                    elif command == b'getWholeMessageList':
                        i += 1
                    elif command == b'getEyePositionList':
                        i += 1
                    elif command == b'saveCameraImage':
                        i += 1
                    elif command == b'allowRendering':
                        i += 1
                    elif command == b'inhibitRendering':
                        i += 1
                    elif command == b'isBinocularMode':
                        i += 1
                    elif command == b'getCameraImageSize':
                        response = '{},{}'.format(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH),self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) + chr(0)
                        self.send_command(response)
                        i += 1
                    elif command == b'deleteCalData':
                        points = np.array([int(v) for v in data[i+1].split(b',')]).reshape(-1,2)
                        self.delete_CalibrationData_Subset(points)
                        i += 1
                    # TODO test if simple calibration practically works.
                    elif command == b'startSimpleCalibration':
                        param = list(map(int, data[i+1].split(b',')))
                        param.append(int(data[i+2]))
                        self.start_simple_calibration(*param)
                        i += 3
                    elif command == b'endSimpleCalibration':
                        self.end_calibration()
                        i += 1
                    else:
                        print('Unknown command {} in {}'.format(data[i], newData))
                        i += 1
    
    def open_datafile(self, filename, overwrite):
        if self.data is not None and self.data.is_opened():
            self.data.close()
        
        if isinstance(filename, bytes):
            filename = filename.decode('utf-8')
        
        if overwrite == 0:
            mode = 'rename'
        elif overwrite == 1:
            mode = 'overwrite'
        else:
            mode = self.config.datafile_open_mode

        self.data = gazedata(filename, open_mode=mode,
            calibrated_output=self.config.calibrated_output,
            calibrationless_output=self.config.calibrationless_output)
        
    def insert_settings(self, settings):
        settings_list = settings.split('/')
        self.data.insert_settings(settings_list)
    
    def close_datafile(self):
        self.data.close()
        self.data = None
  
    def start_calibration(self, x1, y1, x2, y2, clear):
        self.in_calibration = True
        if clear==1:
            self.calibration_data = []
            self.calibration_debug_data = []
        self.calibration_sample_count = 0
        self.calibration_sample_point = (0, 0)
    
    def end_calibration(self):
        self.in_calibration = False
        
        self.fitting_param = LM_calibration(self.calibration_data, self.screen)
        results = calc_calibration_results(self.calibration_data, self.screen, self.fitting_param)

        self.calibration_precision = results[0]
        self.calibration_accuracy = results[1]
        self.calibration_max_error = results[2]
        self.calibration_results_detail = results[3]

    def start_simple_calibration(self, x, y):
        self.in_calibration = True
        self.calibration_data = []
        self.calibration_debug_data = []
        self.calibration_sample_count = 65536
        self.calibration_sample_point = (x, y)

    def get_calibration_sample(self, x, y, n):
        self.calibration_sample_count = n
        self.calibration_sample_point = (x, y)
    
    def delete_CalibrationData_Subset(self, points):
        for p in points:
            # search p from tail of self.calibration_data
            for idx in range(len(self.calibration_data)-1, -1, -1):
                if (p[0] == self.calibration_data[idx][0][0]) and \
                   (p[1] == self.calibration_data[idx][0][1]):
                    # remove entry
                    self.calibration_data.pop(idx)

    def start_recording(self, message):
        print('start_recording')
        self.data.start_recording(datetime.now().strftime('%Y,%m,%d,%H,%M,%S'))
        self.in_recording = True
        self.rec_start_time = time.perf_counter()
    
    def stop_recording(self, message):
        print('stop_recording')
        self.in_recording = False
        self.data.stop_recording()
    
    def insert_message(self, message):
        if self.data is not None and self.data.is_opened() and self.in_recording:
            t = 1000* (time.perf_counter() - self.rec_start_time)
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            self.data.append_message(t, message)
    
    def connected(self):
        return self.server_connected

    def get_current_menu(self):
        self.send_command('Press C to start calibration'+chr(0))
        return
    
    def __del__(self):
        # clean-up
        # close sockets
        for i in range(len(self.readsock_list)):
            self.readsock_list[-(i+1)].close()
        self.readsock_list = []

        if hasattr(self, 'sock_send') and self.sock_send is not None:
            self.sock_send.close()
        if hasattr(self, 'sock_server') and self.sock_server is not None:
            self.sock_server.close()

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
            # process TCP/IP 
            if self.connected():
                self.process_message()
            else:
                self.tcp_accept()

            # process image
            ret, frame = self.camera.read()
            capture_time = time.perf_counter()
            if ret:
                frame_mono = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                reye_img = None
                leye_img = None
                
                if self.downscaling_factor == 1.0: # original size
                    dets, scores = get_face_boxes(frame_mono, engine='dlib_hog')
                else: # downscale camera image
                    dets, scores = get_face_boxes(cv2.resize(frame_mono, None, fx=self.downscaling_factor, fy=self.downscaling_factor), engine='dlib_hog') # detections, scores, weight_indices
                    inv = 1.0/self.downscaling_factor
                    # recover rectangle size
                    for i in range(len(dets)):
                        dets[i] = dlib.rectangle(int(dets[i].left()*inv), int(dets[i].top()*inv),
                                                int(dets[i].right()*inv), int(dets[i].bottom()*inv))

                if len(dets) > 0: # face is found
                    detect_face = True
                    
                    # only first face is used
                    landmarks = get_face_landmarks(frame_mono, dets[0])
                    
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
                
                # during calibration
                if self.in_calibration:
                    if self.calibration_sample_count > 0 and detect_face and (not left_eye.blink) and (not right_eye.blink):
                        
                        self.calibration_data.append((self.calibration_sample_point, face, left_eye, right_eye))
                        self.calibration_sample_count -= 1
                
                # during recording
                elif self.in_recording and detect_face:
                    # convert sec -> ms
                    t = 1000* (capture_time - self.rec_start_time)
                    self.data.append_data(t, face, left_eye, right_eye, self.screen, self.fitting_param, self.eye_filter_L, self.eye_filter_R)

                # neither calibration nor recording
                else:
                    # do nothing
                    pass

                # render image
                if self.render_image:
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
                            wx.PostEvent(self, Tracker.NewImageEvent())
                        except:
                            break

if __name__ == '__main__':

    conf = configuration()
    arg_parser = argparse.ArgumentParser(description='GazeParser-Tracker realtime tracker')
    arg_parser.add_argument('--camera_param', type=str, help='camera parameters file')
    arg_parser.add_argument('--face_model', type=str, help='face model file')
    arg_parser.add_argument('--iris_detector', type=str, help='iris detector (ert, peak, enet or path to detector)')
    arg_parser.add_argument('--select_camera', action='store_true', help='open "Select camera" dialog')
    args = arg_parser.parse_args()

    camera_param_file, face_model_file, iris_detector = load_gptracker_config(conf, args)

    if iris_detector is None:
        sys.exit()    

    #select camera 
    camera_id = conf.camera_id
    app = wx.App(False)
    if args.select_camera:
        print('Launching camera selector...')
        from ..tools.CameraSelector import camera_id_selector_dlg
        dlg = camera_id_selector_dlg()
        if dlg.ShowModal()==wx.ID_OK:
            #dlg.release_cameras()
            camera_id = dlg.IDs[dlg.selected_cam]
            dlg.Destroy()
        else:
            #dlg.release_cameras()
            dlg.Destroy()
            print('canceled')
            sys.exit()

    print('Initializing camera...')

    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print('Error: cannot open camera ID={}'.format(camera_id))
        sys.exit()
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf.camera_resolution_h)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf.camera_resolution_v)

    h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    v = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if h != conf.camera_resolution_h or v != conf.camera_resolution_v:
        print('Warning: Tried to set resolution to ({},{}), but the result was ({},{})'.format(
            conf.camera_resolution_h, conf.camera_resolution_v, h, v))

    print('Creating main window...')

    tracker = Tracker(cap, conf, iris_detector=iris_detector)

    print('Start.')
    app.MainLoop()

    cap.release()
