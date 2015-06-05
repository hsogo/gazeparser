import VisionEgg
import VisionEgg.Core
import Tkinter
import sys
import GazeParser.TrackingTools


class ParamWindow(Tkinter.Frame):
    def __init__(self,master=None):
        Tkinter.Frame.__init__(self,master)
        self.option_add('*font', 'Helvetica 12')
        self.screenSizeEntry = Tkinter.StringVar()
        self.screenSizeEntry.set('39.0,29.0')
        self.distanceEntry = Tkinter.StringVar()
        self.distanceEntry.set('57.3')
        self.IPAdressEntry = Tkinter.StringVar()
        self.IPAdressEntry.set('192.168.1.1')
        self.isDummy = Tkinter.BooleanVar()
        Tkinter.Label(self,text=u'SimpleGazeTracker address').grid(row=0,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.IPAdressEntry).grid(row=0,column=1,padx=5,pady=5)
        Tkinter.Label(self,text=u'Screen Size (cm)').grid(row=1,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.screenSizeEntry).grid(row=1,column=1,padx=5,pady=5)
        Tkinter.Label(self,text=u'Viewing Distance (cm)').grid(row=2,column=0,padx=5,pady=5)
        Tkinter.Entry(self,textvariable=self.distanceEntry).grid(row=2,column=1,padx=5,pady=5)
        Tkinter.Checkbutton(self,text=u'Use dummy mode (for standalone debug)',variable = self.isDummy).grid(row=3,columnspan=2,padx=5,pady=5)
        Tkinter.Button(self,text=u'OK',command=self.quit).grid(row=4,columnspan=2,ipadx=15,pady=5)
        self.pack()

wf = ParamWindow()
wf.mainloop()

screenSize = map(float, wf.screenSizeEntry.get().split(','))
distance = float(wf.distanceEntry.get())

wf.winfo_toplevel().destroy()

tracker = GazeParser.TrackingTools.getController(backend='VisionEgg',dummy=wf.isDummy.get())
tracker.connect(wf.IPAdressEntry.get())

# fitImageBufferToTracker() is equivalent to
#   tracker.setReceiveImageSize(tracker.getCameraImageSize()).
tracker.fitImageBufferToTracker()

if wf.isDummy.get():
    VisionEgg.config.VISIONEGG_HIDE_MOUSE = False

screen = VisionEgg.Core.get_default_screen();
SX,SY = screen.size

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

# Setting current screen parameters to configuration object.
# NOTE: setCalibrationScreen() must be called IN ADVANCE.
tracker.setCurrentScreenParamsToConfig(GazeParser.config, screenSize, distance)
tracker.sendSettings(GazeParser.config.getParametersAsDict())

while True:
    res = tracker.calibrationLoop()
    if res=='q':
        sys.exit(0)
    if tracker.isCalibrationFinished():
        break

