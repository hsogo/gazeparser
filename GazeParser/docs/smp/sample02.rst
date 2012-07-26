.. _sample02:

Sample 02: Using units other than 'pix' (for PsyhcoPy)
=======================================================================

What does this sample do?
--------------------------

This sample shows how to use 'units' option when using PsychoPy.
Codes are the same as those of :ref:`sample01` except units.

Note that units of gaze positions are always 'pix' in the SimpleGazeTracker datafile.
In the sample script, calibration target locations are defined as following.

.. code-block:: python

    calTargetPos = [[   0,   0],
                    [-0.6,-0.6],[-0.6,  0],[-0.6,0.6],
                    [   0,-0.6],[   0,  0],[   0,0.6],
                    [ 0.6,-0.6],[ 0.6,  0],[ 0.6,0.6]]

    tracker.setCalibrationScreen(win)
    tracker.setCalibrationTargetPositions(calarea, calTargetPos,units='norm')

:func:`~GazeParser.TrackingTools.ControllerPsychoPyBackend.setCalibrationTargetPositions`. translates 
calibation target positions into 'pix' before sending them to the SimpleGazeTracker.
As a result, calibration positions are recorded in 'pix' in the SimpleGazeTracker data file as following.::

    #CALPOINT,-307.000000,0.000000
    #CALPOINT,-307.000000,-230.000000
    #CALPOINT,307.000000,230.000000
    #CALPOINT,0.000000,-230.000000
    #CALPOINT,-307.000000,230.000000
    #CALPOINT,307.000000,0.000000
    #CALPOINT,307.000000,-230.000000
    #CALPOINT,0.000000,0.000000
    #CALPOINT,0.000000,230.000000

Comparing these outputs with the script, 0.6 'norm' corresponds to 307 'pix' in horizontal direction and 230 'pix' in vertical direction.

In the SimpleGazeTracker data file, units of recorded gaze positions are also 'pix'.::

    2.525,-4.1,-19.3
    19.093,-3.9,-18.8
    35.692,-3.9,-22.3
    52.301,-4.7,-14.0
    68.924,0.1,-18.8
    85.546,-0.6,-15.0
    102.175,2.1,-25.4
    118.800,2.1,-17.4
    135.421,-0.7,-21.9
    152.057,-3.0,-14.7
    168.669,-1.9,-22.7
    185.294,-4.3,-30.5
    201.919,-8.0,-22.7
    218.542,-4.9,-23.5
    235.170,-5.3,-21.2
    251.680,-1.2,-21.8
    268.296,-9.0,-15.2

:func:`~GazeParser.TrackingTools.ControllerPsychoPyBackend.getEyePosition` receives gaze position in 'pix' and converts to desirable units.
In this sample, units of gaze positions are converted to 'norm' and are output to the local log file.::

    trial1
    getSpatialError: 0.1786,0.0234,-0.1771
    SentAt,ReceivedAt,Lag,TargetX,TargetY,EyeX,EyeY
    0.0,0.6,0.5,0.0000,0.0000,-0.0020,-0.0391
    14.0,14.3,0.3,0.0000,0.0000,0.0039,-0.0651
    18.3,18.6,0.3,0.0000,0.0000,0.0039,-0.0651
    33.6,33.9,0.3,0.0000,0.0000,0.0039,-0.0443
    50.3,50.6,0.3,0.0000,0.0000,-0.0020,-0.0573
    66.9,67.3,0.3,0.0000,0.0000,-0.0059,-0.0391
    83.7,84.0,0.3,0.0000,0.0000,-0.0039,-0.0599
    100.3,100.7,0.3,0.0000,0.0000,-0.0078,-0.0781
    117.0,117.3,0.3,0.0000,0.0000,-0.0156,-0.0599
    133.7,134.0,0.3,0.0000,0.0000,-0.0098,-0.0599
    150.4,150.7,0.3,0.0000,0.0000,-0.0098,-0.0547
    167.1,167.4,0.3,0.0000,0.0000,-0.0020,-0.0573
    183.7,184.1,0.3,0.0000,0.0000,-0.0176,-0.0391
    200.4,200.8,0.3,0.0000,0.0000,-0.0176,-0.0521
    217.1,217.4,0.3,0.0000,0.0000,0.0000,-0.0469
    233.8,234.1,0.3,0.0000,0.0000,-0.0254,-0.0651
    250.5,250.8,0.3,0.0000,0.0000,-0.0156,-0.0521



Codes (PsychoPy)
------------------

- :download:`Download source code (sample02_PsychoPy.py)<sample02_PsychoPy.py>`

Lines modified from sample01_PsychoPy.py are highlighted.

.. code-block:: python
    :emphasize-lines: 89-93,96,105,106,110,112,143,166,171

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

    win = psychopy.visual.Window(size=(1024,768),units='norm')

    tracker.openDataFile(dataFileName+'.csv')
    tracker.sendSettings(GazeParser.config.getParametersAsDict())


    calarea = [-0.8,-0.8,0.8,0.8]
    calTargetPos = [[   0,   0],
                    [-0.6,-0.6],[-0.6,  0],[-0.6,0.6],
                    [   0,-0.6],[   0,  0],[   0,0.6],
                    [ 0.6,-0.6],[ 0.6,  0],[ 0.6,0.6]]

    tracker.setCalibrationScreen(win)
    tracker.setCalibrationTargetPositions(calarea, calTargetPos,units='norm')

    while True:
        res = tracker.calibrationLoop()
        if res=='q':
            sys.exit(0)
        if tracker.isCalibrationFinished():
            break

    stim = psychopy.visual.Rect(win, width=0.03, height=0.04, units='norm')
    marker = psychopy.visual.Rect(win, width=0.009, height=0.012, units='norm', fillColor=(1,1,0),lineWidth=0.1)

    trialClock = psychopy.core.Clock()
    for tr in range(2):
        error = tracker.getSpatialError(message='Press space key', units='norm')
        
        targetPositionList = [(0.1*random.randint(-3,3),0.1*random.randint(-3,3)) for i in range(10)]
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
            eyePos= tracker.getEyePosition(units='norm')
            postGet = trialClock.getTime()
            if not eyePos[0] == None:
                data.append((1000*preGet,1000*postGet,1000*(postGet-preGet),
                             targetPosition[0],targetPosition[1],eyePos[0],eyePos[1]))
                marker.setPos((eyePos[0],eyePos[1]))
            else:
                data.append((1000*preGet,1000*postGet,1000*(postGet-preget),
                             targetPosition[0],targetPosition[1],-65536,-65536))
            
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
            fp.write('getSpatialError: %.4f,%.4f,%.4f\n' % (error[0],error[-1][0],error[-1][1]))
        else:
            fp.write('getSpatialError: None\n')
        fp.write('SentAt,ReceivedAt,Lag,TargetX,TargetY,EyeX,EyeY\n')
        for d in data:
            fp.write('%.1f,%.1f,%.1f,%.4f,%.4f,%.4f,%.4f\n' % d)
        fp.flush()
        
    tracker.closeDataFile()

    fp.close()

