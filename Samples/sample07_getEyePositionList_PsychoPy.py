import psychopy.visual
import psychopy.event
import psychopy.core
import sys
import numpy
import random

import GazeParser.TrackingTools

import wx

class FileWindow(wx.Frame):
    def __init__(self,parent,id,title):
        wx.Frame.__init__(self,parent,id,title,size=(400,420))
        
        panel = wx.Panel(self,wx.ID_ANY)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        filenameBox = wx.BoxSizer(wx.HORIZONTAL)
        filenameBox.Add(wx.StaticText(panel,wx.ID_ANY,'Datafile name',size=(160,30)),0)
        self.filenameEdit = wx.TextCtrl(panel,wx.ID_ANY)
        filenameBox.Add(self.filenameEdit,1)
        filenameBox.Add(wx.StaticText(panel,wx.ID_ANY,'.csv'),0)
        vbox.Add(filenameBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        addressBox = wx.BoxSizer(wx.HORIZONTAL)
        addressBox.Add(wx.StaticText(panel,wx.ID_ANY,'SimpleGazeTracker address',size=(160,30)),0)
        self.addressEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.addressEdit.SetValue('localhost')
        addressBox.Add(self.addressEdit,1)
        vbox.Add(addressBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        imgsizeBox = wx.BoxSizer(wx.HORIZONTAL)
        imgsizeBox.Add(wx.StaticText(panel,wx.ID_ANY,'Capture image size',size=(160,30)),0)
        self.imgsizeEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.imgsizeEdit.SetValue('640,480')
        imgsizeBox.Add(self.imgsizeEdit,1)
        vbox.Add(imgsizeBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        isdummyBox = wx.BoxSizer(wx.HORIZONTAL)
        self.isdummyCheck = wx.CheckBox(panel,wx.ID_ANY,'Use dummy mode (for standalone debug)')
        isdummyBox.Add(self.isdummyCheck)
        vbox.Add(isdummyBox, 0, wx.ALIGN_CENTER | wx.CENTER, 10)
        
        fpsBox = wx.BoxSizer(wx.HORIZONTAL)
        fpsBox.Add(wx.StaticText(panel,wx.ID_ANY,'Camera FPS',size=(160,30)),0)
        self.fpsEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.fpsEdit.SetValue('200')
        fpsBox.Add(self.fpsEdit,1)
        vbox.Add(fpsBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        dpdBox = wx.BoxSizer(wx.HORIZONTAL)
        dpdBox.Add(wx.StaticText(panel,wx.ID_ANY,'Dots per degree',size=(160,30)),0)
        self.dpdEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.dpdEdit.SetValue('37.7')
        dpdBox.Add(self.dpdEdit,1)
        vbox.Add(dpdBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        threshBox = wx.BoxSizer(wx.HORIZONTAL)
        threshBox.Add(wx.StaticText(panel,wx.ID_ANY,'Threshold (deg/s)',size=(160,30)),0)
        self.threshEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.threshEdit.SetValue('40.0')
        threshBox.Add(self.threshEdit,1)
        vbox.Add(threshBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        nsampBox = wx.BoxSizer(wx.HORIZONTAL)
        nsampBox.Add(wx.StaticText(panel,wx.ID_ANY,'Number of samples',size=(160,30)),0)
        self.nsampEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.nsampEdit.SetValue('4')
        nsampBox.Add(self.nsampEdit,1)
        vbox.Add(nsampBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        offsetsizeBox = wx.BoxSizer(wx.HORIZONTAL)
        offsetsizeBox.Add(wx.StaticText(panel,wx.ID_ANY,'Offset (pix)',size=(160,30)),0)
        self.offsetsizeEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.offsetsizeEdit.SetValue('5')
        offsetsizeBox.Add(self.offsetsizeEdit,1)
        vbox.Add(offsetsizeBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
        vbox.Add((-1, 10))
        
        okBox = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(panel,wx.ID_ANY, 'Ok', size=(70, 30))
        self.Bind(wx.EVT_BUTTON, self.quitfunc, okButton)
        okBox.Add(okButton)
        vbox.Add(okBox, 0, wx.ALIGN_CENTER | wx.CENTER, 10)
        
        panel.SetSizer(vbox)
        
        self.Show(True)
        
    def quitfunc(self, event):
        global FileWindowValues
        filename = self.filenameEdit.GetValue()
        address = self.addressEdit.GetValue()
        imgsize = self.imgsizeEdit.GetValue()
        isdummy = self.isdummyCheck.GetValue()
        fps = self.fpsEdit.GetValue()
        dpd = self.dpdEdit.GetValue()
        threshold = self.threshEdit.GetValue()
        nsamp = self.nsampEdit.GetValue()
        offsetsize = self.offsetsizeEdit.GetValue()
        
        FileWindowValues = {'filename':filename,'address':address,'imgsize':imgsize,'isdummy':isdummy,
                            'fps':fps,'dpd':dpd,'threshold':threshold,'nsamp':nsamp,'offsetsize':offsetsize}
        self.Close(True)

FileWindowValues = {}
application = wx.App(False)
fw = FileWindow(None,wx.ID_ANY,"Sample07_PsychoPy")
application.MainLoop()


dataFileName = FileWindowValues['filename']
xy = FileWindowValues['imgsize'].split(',')
cameraX = int(xy[0])
cameraY = int(xy[1])

threshold = float(FileWindowValues['threshold'])
dpd = float(FileWindowValues['dpd'])
fps = float(FileWindowValues['fps'])
nsamp = int(FileWindowValues['nsamp'])
offsetsize = float(FileWindowValues['offsetsize'])

tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=FileWindowValues['isdummy'])
tracker.setReceiveImageSize((cameraX,cameraY))
tracker.connect(FileWindowValues['address'])

win = psychopy.visual.Window(size=(1024,768),units='pix',monitor='testMonitor', fullscr=True)

tracker.openDataFile(dataFileName+'.csv')
tracker.sendSettings(GazeParser.config.getParametersAsDict())


calarea = [-400,-300,400,300]
calTargetPos = [[   0,   0],
                [-350,-250],[-350,  0],[-350,250],
                [   0,-250],[   0,  0],[   0,250],
                [ 350,-250],[ 350,  0],[ 350,250]]

tracker.setCalibrationScreen(win)
tracker.setCalibrationTargetPositions(calarea, calTargetPos)

if not tracker.isDummy():
    while True:
        res = tracker.calibrationLoop()
        if res=='q':
            sys.exit(0)
        if tracker.isCalibrationFinished():
            break

stim = psychopy.visual.Rect(win, width=10, height=10, units='pix', fillColor=(1.0,1.0,0.0), lineColor=None)
answer = psychopy.visual.Rect(win, width=10, height=10, units='pix', fillColor=None, lineColor=(1.0,1.0,0.0))

trialClock = psychopy.core.Clock()

for tr in range(10):
    error = tracker.getSpatialError(message='Press space key')
    
    tracker.startRecording(message='trial'+str(tr+1))
    trialClock.reset()
    
    offset = offsetsize*(2*random.randint(0,1)-1)
    saccade_detected = False
    stim_moved = False
    arrow_pressed = False
    
    while True:
        if tracker.isDummy():
            tracker.recordCurrentMousePos()
        
        gazedata = tracker.getEyePositionList(nsamp)
        vel = numpy.diff(gazedata, axis=0)[:,1:3]
        absvel = numpy.apply_along_axis(numpy.linalg.norm, 1, vel)
        if (absvel>threshold*dpd/fps).all():
            if not saccade_detected and trialClock.getTime()>=1.5:
                saccade_detected = True
                tracker.sendMessage('JUMP %d' % (offset))
        
        if trialClock.getTime() < 1.5:
            fixpos_x = -400
        else:
            if not stim_moved:
                tracker.sendMessage('GO')
                stim_moved = True
            if saccade_detected:
                fixpos_x = 400+offset
            else:
                fixpos_x = 400
        
        if trialClock.getTime()>3.0:
            keyList = psychopy.event.getKeys()
            if 'space' in keyList:
                break
            if not arrow_pressed:
                if 'right' in keyList:
                    tracker.sendMessage('RESPONSE RIGHT')
                    arrow_pressed = True
                elif 'left' in keyList:
                    tracker.sendMessage('RESPONSE LEFT')
                    arrow_pressed = True
        
        stim.setPos((fixpos_x,0))
        stim.draw()
        if arrow_pressed:
            answer.setPos((400,0))
            answer.draw()
        win.flip()
        
    tracker.stopRecording(message='end trial')
    
    
    
tracker.closeDataFile()

