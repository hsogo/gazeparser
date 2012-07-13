import psychopy.visual
import psychopy.event
import psychopy.core
import sys
import random

import GazeParser.TrackingTools

import Tkinter
import tkMessageBox

class FileWindow(Tkinter.Frame):
    def __init__(self,master=None):
        Tkinter.Frame.__init__(self,master)
        self.FileNameEntry = Tkinter.StringVar()
        self.IPAdressEntry = Tkinter.StringVar()
        self.IPAdressEntry.set('192.168.1.1')
        self.cameraSize = Tkinter.StringVar()
        self.cameraSize.set('320,240')
        self.isDummy = Tkinter.BooleanVar()
        Tkinter.Label(self,text=u'Datafile name',
                      font=('Helvetica', '12')).grid(row=0,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.FileNameEntry,
                      font=('Helvetica', '12')).grid(row=0,column=1,padx=5,pady=5)
        Tkinter.Label(self,text=u'.csv',
                      font=('Helvetica', '12')).grid(row=0,column=2,padx=5,pady=5)
        Tkinter.Label(self,text=u'SimpleGazeTracker address',
                      font=('Helvetica', '12')).grid(row=1,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.IPAdressEntry,
                      font=('Helvetica', '12')).grid(row=1,column=1,padx=5,pady=5)
        Tkinter.Label(self,text=u'Capture image size',
                      font=('Helvetica', '12')).grid(row=2,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.cameraSize,
                      font=('Helvetica', '12')).grid(row=2,column=1,padx=5,pady=5)
        Tkinter.Checkbutton(self,text=u'Use dummy mode',variable = self.isDummy,
                      font=('Helvetica', '12')).grid(row=3,columnspan=3,padx=5,pady=5)
        Tkinter.Button(self,text=u'OK',command=self.quit,
                      font=('Helvetica', '12')).grid(row=4,columnspan=3,ipadx=15,pady=5)
        self.pack()

wf = FileWindow()
wf.mainloop()

dataFileName = wf.FileNameEntry.get()
fp = open(dataFileName+'_local.csv','w')
xy = wf.cameraSize.get().split(',')
cameraX = int(xy[0])
cameraY = int(xy[1])

wf.winfo_toplevel().destroy()

tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=wf.isDummy.get())
tracker.setReceiveImageSize((cameraX,cameraY))
tracker.connect(wf.IPAdressEntry.get())

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

res = tracker.calibrationLoop()
if res=='q':
    sys.exit(0)

stim = psychopy.visual.Rect(win, width=5, height=5, units='pix')
marker = psychopy.visual.Rect(win, width=2, height=2, units='pix', fillColor=(1,1,0),lineWidth=0.1)

trialClock = psychopy.core.Clock()
for tr in range(2):
    error = tracker.getSpatialError()
    
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
        fp.write('getSpatialError: %.2f (%.2f,%.2f)\n' % (error[0],error[-1][0],error[-1][1]))
    else:
        fp.write('getSpatialError: None\n')
    fp.write('SentAt,ReceivedAt,Lag,TargetX,TargetY,EyeX,EyeY\n')
    for d in data:
        fp.write('%.1f,%.1f,%.1f,%d,%d,%.1f,%.1f\n' % d)
    fp.flush()
    
tracker.closeDataFile()

fp.close()

