import psychopy.visual
import psychopy.event
import psychopy.core
import sys

import Image
import ImageDraw
import numpy
import OpenGL.GL

import GazeParser.TrackingTools

import wx

class FileWindow(wx.Frame):
    def __init__(self,parent,id,title):
        wx.Frame.__init__(self,parent,id,title)
        
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
        filename = self.filenameEdit.GetValue()
        address = self.addressEdit.GetValue()
        imgsize = self.imgsizeEdit.GetValue()
        isdummy = self.isdummyCheck.GetValue()
        
        FileWindowValues = {'filename':filename,'address':address,'imgsize':imgsize,'isdummy':isdummy}
        self.Close(True)

FileWindowValues = {}
application = wx.App(False)
fw = FileWindow(None,wx.ID_ANY,"Sample03_PsychoPy")
application.MainLoop()


dataFileName = FileWindowValues['filename']
fp = open(dataFileName+'_local.csv','w')
xy = FileWindowValues['imgsize'].split(',')
cameraX = int(xy[0])
cameraY = int(xy[1])

tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=FileWindowValues['isdummy'])
tracker.setReceiveImageSize((cameraX,cameraY))
tracker.connect(FileWindowValues['address'])

win = psychopy.visual.Window(size=(1024,768),units='pix')

tracker.openDataFile(dataFileName+'.csv')
tracker.sendSettings(GazeParser.config.getParametersAsDict())


calarea = [-400,-300,400,300]
calTargetPos = [[   0,   0],
                [-350,-250],[-350,  0],[-350,250],
                [   0,-250],[   0,  0],[   0,250],
                [ 350,-250],[ 350,  0],[ 350,250]]

tracker.setCalibrationScreen(win)
tracker.setCalibrationTargetPositions(calarea, calTargetPos)

while True:
    res = tracker.calibrationLoop()
    if res=='q':
        sys.exit(0)
    if tracker.isCalibrationFinished():
        break

(SX,SY) = win.size
meshx,meshy = numpy.meshgrid(range(-SX/4,SX/4),range(-SY/4,SY/4))
imgArray = numpy.ones((SY/2,SX/2,4),numpy.uint8)*128
imgArray[:,:,3] = 255*(1-numpy.exp(-(meshx/36.0)**2-(meshy/36.0)**2))
maskimage = Image.fromarray(imgArray,mode='RGBA')
mask = psychopy.visual.PatchStim(win,maskimage)
stim = psychopy.visual.SimpleImageStim(win,fname)

for tr in range(2):
    tracker.StartRecording(message='trial'+str(tr+1))
    
    maskcenter = (0,0)
    flgLoop = True
    while flgLoop: 
        ex,ey = tracker.GetEyePosition()
        if not ex == None:
            maskcenter = (ex,ey)
        
        mask.setPos(maskcenter,units='pix')
        
        for e in pygame.event.get():
            if e.type == pygame.locals.KEYDOWN:
                if e.key == pygame.locals.K_SPACE:
                    tracker.SendMessage('SPACE pressed.')
                elif e.key == pygame.locals.K_ESCAPE:
                    flgLoop = False
        
        mask.draw()
        stim.draw()
        
        win.flip()
        
    tracker.StopRecording()
    

tracker.CloseDataFile()

