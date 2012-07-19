How to control SimpleGazeTracker from a python script
======================================================

Example of experiment script (VisionEgg)
----------------------------------------

At the beginning of script, GazeParser.TrackingTools should be initialized.
In the following example, IP address of the Recorder PC is 192.168.0.1 and other parameters are set through a configuration file (TrackerSettings.cfg).
See :ref:`TrackingTools Configuration file <config-trackingtools-param>` for configuration file.
::

    #at first, prepaer a VisionEgg screen.
    screen = VisionEgg.Core.get_default_screen()
    
    #import GazeParser.TrackingTools.
    from GazeParser.TrackingTools import getController
    
    #get controller and connect to GazeParser.TrackingTools.
    tracker = getController(backend='VisionEgg',config='TrackerSettings.cfg')
    tracker.connect('192.168.0.1')
    
    #get controller and connect to GazeParser.TrackingTools.
    tracker.setCalibrationScreen(screen)

Set calibration area and calibration target positions. ::

    (sx,sy) = screen.size
    cx = sx/2
    cy = sy/2
    calibrationArea = (0,0,sx,sy)
    taretPositions = ((cx    ,cy    ),
                      (cx-350,cy-250),(cx,cy-250),(cx+350,cy-250),
                      (cx-350,cy    ),(cx,cy    ),(cx+350,cy    ),
                      (cx-350,cy+250),(cx,cy+250),(cx+350,cy+250))
    
    tracker.setCalibrationTargetPositions(calibrationArea, targetPositions)

Set the name of data file.  The extension of the data file is recommended to be '.csv'.::

    tracker.openDataFile('test.csv')

Then, send recording parameters.::

    config = GazeParser.Configuration()
    config.VIEWING_DISTANCE = 57.3
    config.SCREEN_WIDTH = 1024
    config.SCREEN_HEIGHT = 768
    # (snip)
    tracker.sendSettings(config.getParametersAsDict())

You can load parameters from :class:`GazeParser.Configuration` file. See also :ref:`config-gazeparser` for the configuration file.
It is recommended that you prepare a configuration file for each hardware setting.::

    GazeParser.Configuration.load('settings.cfg')
    tracker.sendSettings(config.getParametersAsDict())


Now it is ready to perform calibration. Calibration can be stopped by pressing ESC or Q key on the keyboard.
In the following example, terminate script when Q is pressed while continue processing when ESC is pressed.
You can check whether calibration is performed at least once by calling isCalibrationFinished() method.::

    while True:
        res = tracker.calibrationLoop()
        if res=='q':
            sys.exit(0)
        else:
            if tracker.isCalibrationFinished():
                break

Now you can start recording. Call startRecording() method when you want to start recording.
It is recommended that startRecording() is called immediately before starting a trial.
When a trial is finished, call stopRecording() method.
You can pass an ASCII string to startRecording() and stopRecording().
The string is recorded in the data file.::

    for trialNo in range(numOfTrials):
        #
        #setting parameters for the current trial
        #
        tracker.startRecording(message='Trial No.%d' % trialNo)
        
        isTrialFinshed = False
        while not isTrialFinished:
            #
            #Updating stimuli
            #
            screen.clear()
            viewport.draw()
            VisionEgg.Core.swap_buffers()
            
        tracker.stopRecording(message='Response %s', key)

If you want to record an event such as onset of a stimulus, call sendMessage() method.
::

    tracker.sendMessage('Target green right')

This code inserts the passed ASCII string with time stamp into the data file as following.
The first element (#MESSAGE) indicates that this line is inserted by sendMessage().
The second element is the timestamp.
The last element is the passed string.::

    #MESSAGE,1213.356,Target green right

If you want to use gaze-contingent stimuli (such as moving window or moving mask),
you can get current gaze postion by calling getEyePosition().::

    gazePosition = tracker.getEyePosition()

At the end of the experiment, call closeDataFile() to close the data file on the Recorder PC.::

    tracker.closeDataFile()


Example of experiment script (PsychoPy)
---------------------------------------

Procedure of using GazeParser.TrackingTools with PsychoPy is similar to that with VisionEgg: however, there are several exceptions.
At first, :func:`GazeParser.TrackingTools.getController` has to be called with *backend='PsychoPy'*.
Then, pass a PsychoPy window to :func:`~GazeParser.TrackingTools.ControllerPsychoPyBackend.setCalibrationScreen`.
::

    myWin = psychopy.visual.Window()
    tracker = getController(backend='PsychoPy',config='TrackerSettings.cfg')
    tracker.connect('192.168.0.1')
    tracker.setCalibrationScreen(myWin)

Set calibration area and calibration target positions.
Note that the origin of the screen coordinate is aligned with the screen center in PsychoPy.
*If 'units' is not specified, units of the position is 'pix'.*::

    (sx,sy) = myWin.size
    calibrationArea = (0,0,sx,sy)
    taretPositions = ((   0,   0),
                      (-350,-250),(0,-250),(350,-250),
                      (-350,   0),(0,   0),(350,   0),
                      (-350, 250),(0, 250),(350, 250))
    
    tracker.setCalibrationTargetPositions(calibrationArea, targetPositions)

To use other units, use 'units' option of :func:`~GazeParser.TrackingTools.ControllerPsychoPyBackend.setCalibrationTargetPositions`.::

    taretPositions = (( 0.0, 0.0),
                      (-3.0,-2.5),(0.0,-2.5),(3.0,-2.5),
                      (-3.0, 0.0),(0.0, 0.0),(3.0, 0.0),
                      (-3.0, 2.5),(0.0, 2.5),(3.0, 2.5))
    
    tracker.setCalibrationTargetPositions(calibrationArea, targetPositions, units='deg')

.. important::
    Units of gaze position in the data file are fixed to 'pix' even if other units are used to initialize calibration target positions.

Returned values of :func:`~GazeParser.TrackingTools.ControllerPsychoPyBackend.getEyePosition` is 'pix' at default.
If other units are preferable, call getEyePosition with 'units' option.::

    gazePosition = tracker.getEyePosition(units='deg')


.. _config-trackingtools-param:

TrackingTools Configuration file
--------------------------------------

TrackingTools configuration file is a plain text file.
This is a sample of TrackingTools configuration file.

::

    [Controller]
    IMAGE_WIDTH = 320
    IMAGE_HEIGHT = 240
    PREVIEW_WIDTH = 640
    PREVIEW_HEIGHT = 480
    VALIDATION_SHIFT = 20
    SHOW_CALDISPLAY = True

Following table shows the meaning of these parameters.
These parameters can be set and changed without using TrackingTools configuration file.

================ ============================================================================ ===================================
parameter        description                                                                  how to set/change
================ ============================================================================ ===================================
IMAGE_WIDTH      Width of the image transfered from the Recorder PC.                          :func:`~GazeParser.TrackingTools.BaseController.setReceiveImageSize`
                 If you set non-zero value to ROI_WIDTH in SimpleGazeTracker configuration
                 file, this value must be equal to ROI_WIDTH.  Otherwise, this value must 
                 be equal to CAMERA_WIDTH in SimpleGazeTracker configuration file.
IMAGE_HEIGHT     Height of the image transfered from the Recorder PC.                         :func:`~GazeParser.TrackingTools.BaseController.setReceiveImageSize`
                 If you set non-zero value to ROI_HEIGHT in SimpleGazeTracker configuration
                 file, this value must be equal to ROI_HEIGHT.  Otherwise, this value must 
                 be equal to CAMERA_HEIGHT in SimpleGazeTracker configuration file.
PREVIEW_WIDTH    Width of the preview image on the presentation PC.                           :func:`~GazeParser.TrackingTools.BaseController.setPreviewImageSize`
PREVIEW_HEIGHT   Width of the preview image on the presentation PC.                           :func:`~GazeParser.TrackingTools.BaseController.setPreviewImageSize`
VALIDATION_SHIFT Shift of the target position in the Validation process.                      :func:`~GazeParser.TrackingTools.BaseController.setValidationShift`
                 If this parameter is 10, target position in the Validation is
                 10 pixel distant from target position in the Calibration process.
SHOW_CALDISPLAY  If this parameter is true, preview image is shown at the presentation PC.    (press 'a' key to toggle this 
                 Set this parameter false if you want to hide preview image from participant. parameter during calibration loop)
================ ============================================================================ ===================================


