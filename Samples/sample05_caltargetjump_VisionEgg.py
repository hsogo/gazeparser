import VisionEgg
import VisionEgg.Core
import Tkinter
import pygame
import pygame.locals
import sys
import random
import VisionEgg.WrappedText

import GazeParser.TrackingTools


class FileWindow(Tkinter.Frame):
    def __init__(self,master=None):
        Tkinter.Frame.__init__(self,master)
        self.option_add('*font', 'Helvetica 12')
        self.IPAdressEntry = Tkinter.StringVar()
        self.IPAdressEntry.set('192.168.1.1')
        self.cameraSize = Tkinter.StringVar()
        self.cameraSize.set('320,240')
        self.isDummy = Tkinter.BooleanVar()
        Tkinter.Label(self,text=u'SimpleGazeTracker address').grid(row=1,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.IPAdressEntry).grid(row=1,column=1,padx=5,pady=5)
        Tkinter.Label(self,text=u'Capture image size').grid(row=2,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.cameraSize).grid(row=2,column=1,padx=5,pady=5)
        Tkinter.Checkbutton(self,text=u'Use dummy mode (for standalone debug)',variable = self.isDummy).grid(row=3,columnspan=3,padx=5,pady=5)
        Tkinter.Button(self,text=u'OK',command=self.quit).grid(row=4,columnspan=3,ipadx=15,pady=5)
        self.pack()

wf = FileWindow()
wf.mainloop()

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

calarea = (SX/2-400,SY/2-300,SX/2+400,SY/2+300)
calTargetPos = [[   0,   0],
                [-350,-250],[-350,  0],[-350,250],
                [   0,-250],[   0,  0],[   0,250],
                [ 350,-250],[ 350,  0],[ 350,250]]

for i in range(len(calTargetPos)):
    calTargetPos[i] = (calTargetPos[i][0]+SX/2, calTargetPos[i][1]+SY/2)

tracker.setCalibrationScreen(screen)
tracker.setCalibrationTargetPositions(calarea, tuple(calTargetPos))


msg = VisionEgg.WrappedText.WrappedText(position=(SX/4,SY/2),size=(SX/2,SY/2))
msgviewport = VisionEgg.Core.Viewport(screen=screen, stimuli=[msg])

#Jumping + getting samples immediately after jumping
#Note: this setting is for demonstration. It is not recommended for actual use.
tracker.setCalTargetMotionParams(durationPerPos=1.0, motionDuration=0.0)
tracker.setCalSampleAcquisitionParams(numSamplesPerPos=30, getSampleDelay=0.0)
msg.parameters.text = 'durationPerPos=1.0, motionDuration=0.0\nnumSamplesPerPos=30, getSampleDelay=0.0\n\n(for demonstration only)'
screen.clear()
msgviewport.draw()
VisionEgg.Core.swap_buffers()
isWaiting = True
while isWaiting:
    for e in pygame.event.get():
        if e.type==pygame.locals.KEYDOWN:
            isWaiting = False

tracker.calibrationLoop()
