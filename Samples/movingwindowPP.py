# -*- coding:shift_jis -*-
import GazeParser.GazeTrackerController
import psychopy.visual
import pygame
import pygame.locals
import time
import sys

import tkFileDialog
import Image
import ImageDraw
import numpy
import OpenGL.GL

########################################
# データファイルの設定
import Tkinter
import tkMessageBox
import sys

class FileWindow(Tkinter.Frame):
    def __init__(self,master=None):
        Tkinter.Frame.__init__(self,master)
        self.FileNameEntry = Tkinter.StringVar()
        self.IPAdressEntry = Tkinter.StringVar()
        self.IPAdressEntry.set('192.168.11.3')
        Tkinter.Label(self,text=u'ファイル名',
                      font=('Helvetica', '12')).grid(row=0,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.FileNameEntry,
                      font=('Helvetica', '12')).grid(row=0,column=1,padx=5,pady=5)
        Tkinter.Label(self,text=u'.csv',
                      font=('Helvetica', '12')).grid(row=0,column=2,padx=5,pady=5)
        Tkinter.Label(self,text=u'アイトラッカーIPアドレス',
                      font=('Helvetica', '12')).grid(row=1,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.IPAdressEntry,
                      font=('Helvetica', '12')).grid(row=1,column=1,padx=5,pady=5)
        Tkinter.Button(self,text=u'OK',command=self.quit,
                      font=('Helvetica', '12')).grid(row=2,columnspan=3,ipadx=15,pady=5)
        self.pack()

#wf = FileWindow()
#wf.mainloop()
#
#try:
#    subjectName = wf.FileNameEntry.get()
#except:
#    tkMessageBox.showerror('Error',u'終了します。')
#    sys.exit()
#
#wf.winfo_toplevel().destroy()
#
#fname = tkFileDialog.askopenfilename()
subjectName = 'test'
fname = 'penguins.jpg'

tracker = GazeParser.GazeTrackerController.Controller_PsychoPy()
tracker.SetReceiveImageSize(320,224)
tracker.connect('192.168.11.3')
#tracker.connect(wf.IPAdressEntry.get())

win = psychopy.visual.Window(size=(1024,768),winType='pygame')
SX=1024
SY=768

tracker.OpenDataFile(subjectName+'.csv')
tracker.SendSettings(ScreenSize=(SX,SY),ViewingDistance=57.296,DotsPerCentimeter=(37.7,37.7),ScreenOrigin='BottomLeft',TrackerOrigin='BottomLeft')


calarea = [SX/2-400,SY/2-300,SX/2+400,SY/2+300]

calTargetPos = [[   0,   0],
                [-350,-250],[-350,  0],[-350,250],
                [   0,-250],[   0,  0],[   0,250],
                [ 350,-250],[ 350,  0],[ 350,250]]

tracker.SetCalibrationTarget(calarea, calTargetPos)
tracker.setCalibrationScreen(win)

while True:
    res = tracker.CalibrationLoop()
    if res==pygame.locals.K_q:
        sys.exit(0)
    else:
        if tracker.calResults != None:
            break

meshx,meshy = numpy.meshgrid(range(-SX/4,SX/4),range(-SY/4,SY/4))
imgArray = numpy.ones((SY/2,SX/2,4),numpy.uint8)*128
imgArray[:,:,3] = 255*(1-numpy.exp(-(meshx/36.0)**2-(meshy/36.0)**2))
maskimage = Image.fromarray(imgArray,mode='RGBA')

#phototexture = VisionEgg.Textures.Texture(fname)
#masktexture = VisionEgg.Textures.Texture(maskimage)
#stim = VisionEgg.Textures.TextureStimulus(texture=phototexture, size=phototexture.size, anchor='center', position=(SX/2,SY/2))
#mask = VisionEgg.Textures.TextureStimulus(texture=masktexture, size=(SX*2,SY*2), anchor='center', position=(SX/2,SY/2), internal_format=OpenGL.GL.GL_RGBA)
#viewport = VisionEgg.Core.Viewport(screen=screen,stimuli=[stim,mask])

mask = psychopy.visual.PatchStim(win,maskimage)
stim = psychopy.visual.SimpleImageStim(win,fname)

for tr in range(2):
    tracker.StartRecording(message='trial'+str(tr+1))
    
    maskcenter = (SX/2,SY/2)
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

