import psychopy.visual
import psychopy.event
import psychopy.core
import sys
import numpy
import OpenGL.GL
import os
try:
    import Image
except:
    from PIL import Image

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
        dlg = wx.FileDialog(None, 'select image file', '', '', '*.*', wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            fname = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
        dlg.Destroy()
        
        FileWindowValues = {'filename':filename,'address':address,'imgsize':imgsize,'isdummy':isdummy,'imgfilename':fname}
        self.Close(True)

FileWindowValues = {}
application = wx.App(False)
fw = FileWindow(None,wx.ID_ANY,"Sample03_movingwindow_PsychoPy")
application.MainLoop()

fname = FileWindowValues['imgfilename']

dataFileName = FileWindowValues['filename']
xy = FileWindowValues['imgsize'].split(',')
cameraX = int(xy[0])
cameraY = int(xy[1])

tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=FileWindowValues['isdummy'])
tracker.setReceiveImageSize((cameraX,cameraY))
tracker.connect(FileWindowValues['address'])

win = psychopy.visual.Window(size=(1024,768),units='pix')

tracker.openDataFile(dataFileName+'.csv', config=GazeParser.config)


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

maskImageSize = 512
meshx,meshy = numpy.meshgrid(range(-maskImageSize/2,maskImageSize/2),range(-maskImageSize/2,maskImageSize/2))
imgArray = numpy.ones((maskImageSize,maskImageSize,4),numpy.uint8)*128
maskimage = Image.fromarray(imgArray,mode='RGBA')

stim = psychopy.visual.ImageStim(win,fname)
mask = psychopy.visual.ImageStim(win,maskimage,interpolate='linear')
mask.setSize((max(win.size)*2,max(win.size)*2))

for tr in range(5):
    windowSize = 6.0*(tr+1)
    imgArray[:,:,3] = 255*(1-numpy.exp(-(meshx/windowSize)**2-(meshy/windowSize)**2))
    maskimage = Image.fromarray(imgArray,mode='RGBA')
    mask.setImage(maskimage)
    
    tracker.startRecording(message='trial'+str(tr+1))
    
    maskcenter = (0,0)
    flgLoop = True
    while flgLoop: 
        exy = tracker.getEyePosition()
        if exy[0] != None:
            if -win.size[0]/2<exy[0]<win.size[0]/2 and -win.size[1]/2<exy[1]<win.size[1]:
                maskcenter = (exy[0],exy[1])
        
        mask.setPos(maskcenter)
        
        keyList = psychopy.event.getKeys()
        if 'space' in keyList:
            flgLoop = False
        
        stim.draw()
        mask.draw()
        
        win.flip()
        
    tracker.stopRecording()
    

tracker.closeDataFile()

