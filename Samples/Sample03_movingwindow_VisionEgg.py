import VisionEgg
import VisionEgg.Core
import VisionEgg.Textures
import pygame
import pygame.locals
import sys
import numpy
import OpenGL.GL
try:
    import Image
except ImportError:
    from PIL import Image

import GazeParser.TrackingTools

import Tkinter
import tkMessageBox
import tkFileDialog


class FileWindow(Tkinter.Frame):
    def __init__(self,master=None):
        Tkinter.Frame.__init__(self,master)
        self.option_add('*font', 'Helvetica 12')
        self.FileNameEntry = Tkinter.StringVar()
        self.IPAdressEntry = Tkinter.StringVar()
        self.IPAdressEntry.set('192.168.1.1')
        self.cameraSize = Tkinter.StringVar()
        self.cameraSize.set('320,240')
        self.windowSize = Tkinter.StringVar()
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

fname = tkFileDialog.askopenfilename()

tracker = GazeParser.TrackingTools.getController(backend='VisionEgg',dummy=wf.isDummy.get())
tracker.setReceiveImageSize((cameraX,cameraY))
tracker.connect(wf.IPAdressEntry.get())

if wf.isDummy.get():
    VisionEgg.config.VISIONEGG_HIDE_MOUSE = False

screen = VisionEgg.Core.get_default_screen();
SX,SY = screen.size

tracker.openDataFile(dataFileName+'.csv', config=GazeParser.config)


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

meshx,meshy = numpy.meshgrid(range(-SX/4,SX/4),range(-SY/4,SY/4))
imgArray = numpy.ones((SY/2,SX/2,4),numpy.uint8)*128
maskimage = Image.fromarray(imgArray,mode='RGBA')

phototexture = VisionEgg.Textures.Texture(fname)
masktexture = VisionEgg.Textures.Texture(maskimage)
stim = VisionEgg.Textures.TextureStimulus(texture=phototexture, size=phototexture.size, anchor='center', position=(SX/2,SY/2))
mask = VisionEgg.Textures.TextureStimulus(texture=masktexture, size=(SX*2,SY*2), anchor='center', position=(SX/2,SY/2), internal_format=OpenGL.GL.GL_RGBA)
viewport = VisionEgg.Core.Viewport(screen=screen,stimuli=[stim,mask])

maskTextureObject = mask.parameters.texture.get_texture_object()

for tr in range(5):
    windowSize = 6.0*(tr+1)
    imgArray[:,:,3] = 255*(1-numpy.exp(-(meshx/windowSize)**2-(meshy/windowSize)**2))
    maskimage = Image.fromarray(imgArray,mode='RGBA')
    maskTextureObject.put_sub_image(maskimage)
    
    tracker.startRecording(message='trial'+str(tr+1))
    
    maskcenter = (SX/2,SY/2)
    flgLoop = True
    while flgLoop: 
        exy = tracker.getEyePosition()
        if exy[0] != None:
            if 0<exy[0]<SX and 0<exy[1]<SY:
                maskcenter = (exy[0],exy[1])
        
        mask.parameters.position = maskcenter
        
        for e in pygame.event.get():
            if e.type == pygame.locals.KEYDOWN:
                if e.key == pygame.locals.K_SPACE:
                    flgLoop = False
        
        screen.clear()
        viewport.draw()
        VisionEgg.Core.swap_buffers()
        
    tracker.stopRecording()
    

tracker.closeDataFile()

