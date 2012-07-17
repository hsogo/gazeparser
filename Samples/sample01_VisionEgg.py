import VisionEgg
import VisionEgg.Core
import Tkinter
import pygame
import pygame.locals
import sys
import random

import GazeParser.TrackingTools


class FileWindow(Tkinter.Frame):
    def __init__(self,master=None):
        Tkinter.Frame.__init__(self,master)
        self.option_add('*font', 'Helvetica 12')
        self.FileNameEntry = Tkinter.StringVar()
        self.IPAdressEntry = Tkinter.StringVar()
        self.IPAdressEntry.set('192.168.1.1')
        self.cameraSize = Tkinter.StringVar()
        self.cameraSize.set('320,240')
        self.isDummy = Tkinter.BooleanVar()
        Tkinter.Label(self,text=u'Datafile name').grid(row=0,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.FileNameEntry).grid(row=0,column=1,padx=5,pady=5)
        Tkinter.Label(self,text=u'.csv').grid(row=0,column=2,padx=5,pady=5)
        Tkinter.Label(self,text=u'SimpleGazeTracker address').grid(row=1,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.IPAdressEntry).grid(row=1,column=1,padx=5,pady=5)
        Tkinter.Label(self,text=u'Capture image size').grid(row=2,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.cameraSize).grid(row=2,column=1,padx=5,pady=5)
        Tkinter.Checkbutton(self,text=u'Use dummy mode (for standalone debug)',variable = self.isDummy).grid(row=3,columnspan=3,padx=5,pady=5)
        Tkinter.Button(self,text=u'OK',command=self.quit).grid(row=4,columnspan=3,ipadx=15,pady=5)
        self.pack()

wf = FileWindow()
wf.mainloop()

dataFileName = wf.FileNameEntry.get()
fp = open(dataFileName+'_local.csv','w')
xy = wf.cameraSize.get().split(',')
cameraX = int(xy[0])
cameraY = int(xy[1])

wf.winfo_toplevel().destroy()

tracker = GazeParser.TrackingTools.getController(backend='VisionEgg',dummy=wf.isDummy.get())
tracker.setReceiveImageSize((cameraX,cameraY))
tracker.connect(wf.IPAdressEntry.get())

if wf.isDummy.get():
    VisionEgg.config.VISIONEGG_HIDE_MOUSE = False

screen = VisionEgg.Core.get_default_screen();
SX,SY = screen.size

tracker.openDataFile(dataFileName+'.csv')
tracker.sendSettings(GazeParser.config.getParametersAsDict())


calarea = [SX/2-400,SY/2-300,SX/2+400,SY/2+300]
calTargetPos = [[   0,   0],
                [-350,-250],[-350,  0],[-350,250],
                [   0,-250],[   0,  0],[   0,250],
                [ 350,-250],[ 350,  0],[ 350,250]]


for p in calTargetPos:
    p[0] = p[0] + SX/2
    p[1] = p[1] + SY/2

tracker.setCalibrationScreen(screen)
tracker.setCalibrationTargetPositions(calarea, calTargetPos)

while True:
    res = tracker.calibrationLoop()
    if res=='q':
        sys.exit(0)
    if tracker.isCalibrationFinished():
        break

stim = VisionEgg.MoreStimuli.Target2D(size=(5,5))
marker = VisionEgg.MoreStimuli.Target2D(size=(2,2),color=(1,1,0))
viewport = VisionEgg.Core.Viewport(screen=screen,stimuli=[stim,marker])

for tr in range(2):
    error = tracker.getSpatialError(message='Press space key')
    
    targetPositionList = [(SX/2+100*random.randint(-3,3),SY/2+100*random.randint(-3,3)) for i in range(10)]
    targetPositionList.insert(0,(SX/2,SY/2))
    currentPosition = 0
    previousPosition = 0
    stim.parameters.position = targetPositionList[currentPosition]
    marker.parameters.position = targetPositionList[currentPosition]
    
    waitkeypress = True
    while waitkeypress:
        for e in pygame.event.get():
            if e.type == pygame.locals.KEYDOWN:
                if e.key == pygame.locals.K_SPACE:
                    waitkeypress = False
        screen.clear()
        viewport.draw()
        VisionEgg.Core.swap_buffers()

    tracker.startRecording(message='trial'+str(tr+1))
    tracker.sendMessage('STIM %s %s'%targetPositionList[currentPosition])
    
    data = []
    startTime = VisionEgg.time_func()
    while True: 
        currentTime = VisionEgg.time_func()
        currentPosition = int(currentTime-startTime)
        if currentPosition>=len(targetPositionList):
            break
        targetPosition = targetPositionList[currentPosition]
        if previousPosition != currentPosition:
            tracker.sendMessage('STIM %s %s'%targetPosition)
            previousPosition = currentPosition
        
        preGet = VisionEgg.time_func()
        eyePos= tracker.getEyePosition()
        postGet = VisionEgg.time_func()
        if not eyePos[0] == None:
            data.append((1000*(preGet-startTime),1000*(postGet-startTime),1000*(postGet-preGet),targetPosition[0],targetPosition[1],eyePos[0],eyePos[1]))
            marker.parameters.position = (eyePos[0],eyePos[1])
        else:
            data.append((1000*(preGet-startTime),1000*(postGet-startTime),1000*(postGet-preget),targetPosition[0],targetPosition[1],-65536,-65536))
        
        for e in pygame.event.get():
            if e.type == pygame.locals.KEYDOWN:
                if e.key == pygame.locals.K_SPACE:
                    tracker.sendMessage('press space')
        
        stim.parameters.position = targetPosition
        screen.clear()
        viewport.draw()
        VisionEgg.Core.swap_buffers()
        
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

