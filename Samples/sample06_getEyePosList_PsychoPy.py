import psychopy.visual
import psychopy.event
import psychopy.core
import sys
import random
import Image
import ImageDraw

import GazeParser.TrackingTools

import wx

class FileWindow(wx.Frame):
    def __init__(self,parent,id,title):
        wx.Frame.__init__(self,parent,id,title)
        
        panel = wx.Panel(self,wx.ID_ANY)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        samplesBox = wx.BoxSizer(wx.HORIZONTAL)
        samplesBox.Add(wx.StaticText(panel,wx.ID_ANY,'Samples',size=(160,30)),0)
        self.samplesEdit = wx.TextCtrl(panel,wx.ID_ANY)
        self.samplesEdit.SetValue('200')
        samplesBox.Add(self.samplesEdit,1)
        vbox.Add(samplesBox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        
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
        samples = self.samplesEdit.GetValue()
        address = self.addressEdit.GetValue()
        imgsize = self.imgsizeEdit.GetValue()
        isdummy = self.isdummyCheck.GetValue()
        
        FileWindowValues = {'samples':samples,'address':address,'imgsize':imgsize,'isdummy':isdummy}
        self.Close(True)

FileWindowValues = {}
application = wx.App(False)
fw = FileWindow(None,wx.ID_ANY,"Sample06_PsychoPy")
application.MainLoop()


numSamples = int(FileWindowValues['samples'])
xy = FileWindowValues['imgsize'].split(',')
cameraX = int(xy[0])
cameraY = int(xy[1])

tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=FileWindowValues['isdummy'])
tracker.setReceiveImageSize((cameraX,cameraY))
tracker.connect(FileWindowValues['address'])

win = psychopy.visual.Window(size=(1024,768),units='pix',monitor='testMonitor')

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

image = Image.new('RGBA',win.size,(128,128,128))
draw = ImageDraw.Draw(image)

colorlist = ('red','blue','green','cyan','magenta','yellow')
colorindex = 0

canvas = psychopy.visual.SimpleImageStim(win, image)
marker = psychopy.visual.Rect(win, width=2, height=2, units='pix', fillColor=(1,1,0),lineWidth=0.1)

tracker.getSpatialError()
tracker.startRecording()

while True: 
    if tracker.isDummy():
        tracker.recordCurrentMousePos()
    
    eyePos= tracker.getEyePosition()
    if not eyePos[0] == None:
        marker.setPos((eyePos[0],eyePos[1]))
    
    keyList = psychopy.event.getKeys()
    if 'escape' in keyList:
        break
    if 'z' in keyList:
        draw.rectangle((0,0,win.size[0],win.size[1]),(128,128,128))
        canvas.setImage(image)
    if 'space' in keyList:
        data = tracker.getEyePositionList(numSamples)
        if data!=None and len(data)>2:
            for i in range(len(data)-1):
                if -win.size[0]/2>data[i,1] or win.size[0]/2<data[i,1] or -win.size[0]/2>data[i+1,1] or win.size[0]/2<data[i+1,1]:
                    continue
                if -win.size[1]/2>data[i,2] or win.size[1]/2<data[i,2] or -win.size[1]/2>data[i+1,2] or win.size[1]/2<data[i+1,2]:
                    continue
                draw.line((win.size[0]/2+data[i,1],  win.size[1]/2-data[i,2],
                           win.size[0]/2+data[i+1,1],win.size[1]/2-data[i+1,2]),fill=colorlist[colorindex])
            canvas.setImage(image)
            colorindex+=1
            colorindex%=len(colorlist)
    
    canvas.draw()
    marker.draw()
    win.flip()
    
tracker.stopRecording()

