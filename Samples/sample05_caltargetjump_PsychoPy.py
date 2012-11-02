import psychopy.visual
import psychopy.event
import psychopy.core
import sys
import random

import GazeParser.TrackingTools

import wx

class FileWindow(wx.Frame):
    def __init__(self,parent,id,title):
        wx.Frame.__init__(self,parent,id,title)
        
        panel = wx.Panel(self,wx.ID_ANY)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        addressBox = wx.BoxSizer(wx.HORIZONTAL)
        addressBox.Add(wx.StaticText(panel,wx.ID_ANY,'SimpleGazeTracker address',size=(160,30)),0)
        self.addressEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.addressEdit.SetValue('192.168.1.1')
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
        
        vbox.Add((-1, 25))
        
        okBox = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(panel,wx.ID_ANY, 'Ok', size=(70, 30))
        self.Bind(wx.EVT_BUTTON, self.quitfunc, okButton)
        okBox.Add(okButton)
        vbox.Add(okBox, 0, wx.ALIGN_CENTER | wx.CENTER, 10)
        
        panel.SetSizer(vbox)
        
        self.Show(True)
        
    def quitfunc(self, event):
        global FileWindowValues
        address = self.addressEdit.GetValue()
        imgsize = self.imgsizeEdit.GetValue()
        isdummy = self.isdummyCheck.GetValue()
        
        FileWindowValues = {'address':address,'imgsize':imgsize,'isdummy':isdummy}
        self.Close(True)

FileWindowValues = {}
application = wx.App(False)
fw = FileWindow(None,wx.ID_ANY,"Sample04_PsychoPy")
application.MainLoop()


xy = FileWindowValues['imgsize'].split(',')
cameraX = int(xy[0])
cameraY = int(xy[1])

tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=FileWindowValues['isdummy'])
tracker.setReceiveImageSize((cameraX,cameraY))
tracker.connect(FileWindowValues['address'])

win = psychopy.visual.Window(size=(1024,768),units='pix')

tracker.sendSettings(GazeParser.config.getParametersAsDict())

calarea = (-400,-300,400,300)
calTargetPos = [[   0,   0],
                [-350,-250],[-350,  0],[-350,250],
                [   0,-250],[   0,  0],[   0,250],
                [ 350,-250],[ 350,  0],[ 350,250]]

tracker.setCalibrationScreen(win)
tracker.setCalibrationTargetPositions(calarea, calTargetPos)

msg = psychopy.visual.TextStim(win)

#Jumping + getting samples immediately after jumping
#Note: this setting is for demonstration. It is not recommended for actual use.
tracker.setCalTargetMotionParams(durationPerPos=1.0, motionDuration=0.0)
tracker.setCalSampleAcquisitionParams(numSamplesPerPos=30, getSampleDelay=0.0)
msg.setText('durationPerPos=1.0, motionDuration=0.0\nnumSamplesPerPos=30, getSampleDelay=0.0\n\n(for demonstration only)')
msg.draw()
win.flip()
psychopy.event.waitKeys()

tracker.calibrationLoop()

