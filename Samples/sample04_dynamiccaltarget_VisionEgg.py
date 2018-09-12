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

tracker.openDataFile(dataFileName+'.csv', config=GazeParser.config)

calarea = (SX/2-400,SY/2-300,SX/2+400,SY/2+300)
calTargetPos = [[   0,   0],
                [-350,-250],[-350,  0],[-350,250],
                [   0,-250],[   0,  0],[   0,250],
                [ 350,-250],[ 350,  0],[ 350,250]]

for i in range(len(calTargetPos)):
    calTargetPos[i] = (calTargetPos[i][0]+SX/2, calTargetPos[i][1]+SY/2)

tracker.setCalibrationScreen(screen)
tracker.setCalibrationTargetPositions(calarea, tuple(calTargetPos))

calstim = [VisionEgg.MoreStimuli.Target2D(size=(5,5),color=(1,1,1)),
           VisionEgg.MoreStimuli.Target2D(size=(2,2),color=(0,0,0))]
tracker.setCalibrationTargetStimulus(calstim)

def callback(self, t, index, targetPos, currentPos):
    if index==0:
        return
    else:
        if t<1.0:
            self.caltarget[0].parameters.size = ((20.0-19.0*t)*5,(20.0-19.0*t)*5)
        else:
            self.caltarget[0].parameters.size = (5,5)

type(tracker).updateCalibrationTargetStimulusCallBack = callback

while True:
    res = tracker.calibrationLoop()
    if res=='q':
        sys.exit(0)
    if tracker.isCalibrationFinished():
        break

