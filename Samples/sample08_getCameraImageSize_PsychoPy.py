import psychopy.visual
import psychopy.gui
import GazeParser.TrackingTools
import sys

info = {'Tracker IP address':'localhost','Dummy mode':False}
psychopy.gui.DlgFromDict(info,title='Sample08_PsychoPy')

tracker = GazeParser.TrackingTools.getController(backend='PsychoPy',dummy=info['Dummy mode'])
tracker.connect(info['Tracker IP address'])

# fitImageBufferToTracker() is equivalent to
#   tracker.setReceiveImageSize(tracker.getCameraImageSize()).
tracker.fitImageBufferToTracker()

win = psychopy.visual.Window(size=(1024,768),units='pix',monitor='testMonitor')

calarea = [-400,-300,400,300]
calTargetPos = [[   0,   0],
                [-350,-250],[-350,  0],[-350,250],
                [   0,-250],[   0,  0],[   0,250],
                [ 350,-250],[ 350,  0],[ 350,250]]

tracker.setCalibrationScreen(win)
tracker.setCalibrationTargetPositions(calarea, calTargetPos)

# Setting current screen parameters to configuration object.
# If you want to specify physical screen size and viewing distance 
# (in centimeters), give them as arguments of setCurrentScreenParamsToConfig().
# NOTE: setCalibrationScreen() must be called IN ADVANCE.
tracker.setCurrentScreenParamsToConfig(GazeParser.config)

tracker.sendSettings(GazeParser.config.getParametersAsDict())



while True:
    res = tracker.calibrationLoop()
    if res=='q':
        sys.exit(0)
    if tracker.isCalibrationFinished():
        break


