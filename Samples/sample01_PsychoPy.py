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
fw = FileWindow(None,wx.ID_ANY,"Sample01_PsychoPy")
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

stim = psychopy.visual.Rect(win, width=5, height=5, units='pix')
marker = psychopy.visual.Rect(win, width=2, height=2, units='pix', fillColor=(1,1,0),lineWidth=0.1)

trialClock = psychopy.core.Clock()
for tr in range(2):
    error = tracker.getSpatialError(message='Press space key')
    
    targetPositionList = [(100*random.randint(-3,3),100*random.randint(-3,3)) for i in range(10)]
    targetPositionList.insert(0,(0,0))
    currentPosition = 0
    previousPosition = 0
    stim.setPos(targetPositionList[currentPosition])
    marker.setPos(targetPositionList[currentPosition])
    
    waitkeypress = True
    while waitkeypress:
        if 'space' in psychopy.event.getKeys():
            waitkeypress = False
        
        stim.draw()
        win.flip()

    tracker.startRecording(message='trial'+str(tr+1))
    tracker.sendMessage('STIM %s %s'%targetPositionList[currentPosition])
    
    data = []
    trialClock.reset()
    while True: 
        currentTime = trialClock.getTime()
        currentPosition = int(currentTime)
        if currentPosition>=len(targetPositionList):
            break
        targetPosition = targetPositionList[currentPosition]
        if previousPosition != currentPosition:
            tracker.sendMessage('STIM %s %s'%targetPosition)
            previousPosition = currentPosition
        
        preGet = trialClock.getTime()
        eyePos= tracker.getEyePosition()
        postGet = trialClock.getTime()
        if not eyePos[0] == None:
            data.append((1000*preGet,1000*postGet,1000*(postGet-preGet),targetPosition[0],targetPosition[1],eyePos[0],eyePos[1]))
            marker.setPos((eyePos[0],eyePos[1]))
        else:
            data.append((1000*preGet,1000*postGet,1000*(postGet-preget),targetPosition[0],targetPosition[1],-65536,-65536))
        
        keyList = psychopy.event.getKeys()
        if 'space' in keyList:
            tracker.sendMessage('press space')
        
        stim.setPos(targetPosition)
        stim.draw()
        marker.draw()
        win.flip()
        
    tracker.stopRecording(message='end trial')
    
    fp.write('trial%d\n' % (tr+1))
    if error[0] != None:
        fp.write('getSpatialError: %.2f,%.2f,%.2f\n' % (error[0],error[-1][0],error[-1][1]))
    else:
        fp.write('getSpatialError: None\n')
    fp.write('SentAt,ReceivedAt,Lag,TargetX,TargetY,EyeX,EyeY\n')
    for d in data:
        fp.write('%.1f,%.1f,%.1f,%d,%d,%.1f,%.1f\n' % d)
    fp.flush()
    
tracker.closeDataFile()

fp.close()

