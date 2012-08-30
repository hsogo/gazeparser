ChangeLog
====================

GazeParser 0.5.2
----------------------

(released 2012/08/27)

*SimpleGazeTracker is not updated. Please use SimpleGazeTracker 0.5.1 with GazeParser 0.5.2.*

* CHANGED: GazeParser.TrackingTools
    - CHANGED: :func:`GazeParser.TrackingTools.BaseController.calibrationLoop` raises ValueError if calibrationLoop is called before setting calibration area and calibration target positions.
    - CHANGED: :func:`GazeParser.TrackingTools.ControllerVisionEggBackend.setCalibrationTargetStimulus` and :func:`GazeParser.TrackingTools.ControllerPsychoPyBackend.setCalibrationTargetStimulus` support a list of stimulus objects as calibration target.
    - ADDED: :func:`GazeParser.TrackingTools.BaseController.updateCalibrationTargetStimulusCallBack` is added to support dynamic calibration target. See :ref:`sample04` for detail.
* FIXED: :func:`GazeParser.TrackingTools.ControllerVisionEggBackend.setCalibrationTargetStimulus` did not work correctly.
* FIXED: Tuple was not accepted by :func:`GazeParser.TrackingTools.ControllerVisionEggBackend.setCalibrationTargetPositions`.
* FIXED: :func:`GazeParser.Converter.TrackerToGazeParser` could not convert data files with CR/LF line feed code when running on Linux.
* FIXED: Size of converter dialog was too small when GazeParser/app/Converters.py was executed on Linux.

GazeParser 0.5.1
----------------------

(released 2012/07/31)

* CHANGED: SimpleGazeTracker 
    - CHANGED: Pupil detection algorithm is improved.  Rate of detection failure is reduced when shadows whose size is similar to pupil size are included in captured images.
    - CHANGED: SimpleGazeTracker edition is output to a log file.
    - ADDED: A parameter 'Camera ID' is added to OpenCV edition.  You can specify which camera should be used when multiple camearas are connected to the Recorder PC.
    - ADDED: A parameter 'SHOW_DETECTIONERROR_MSG' is added to all edition.
    - ADDED: Parameters 'ROI_WIDTH' and 'ROI_HEIGHT' are added to all edition.  You can specify a subregion where SimpleGazeTracker searches pupil and Purkinje image.
    - ADDED: Parameters 'PORT_RECV' and 'PORT_SEND' are added to all edition to customize TCP ports.
    - ADDED: A parameter 'DELAY_CORRECTION' is added to all adition .
* CHANGED: GazeParser.TrackingTools
    - CHANGED: Dummy mode is improved.  You can emurate eye movement with mouse when the controller runs as dummy mode.
    - CHANGED: Parameters 'port1' and 'port2' of :func:`GazeParser.TrackingTools.BaseController.connect` are renamed to portRecv' and 'portSend'
    - ADDED: :func:`GazeParser.TrackingTools.BaseController.getSpatialError`
    - ADDED: :func:`GazeParser.TrackingTools.cameraDelayEstimationHelper`
* CHANGED: GazeParser Home directory on Win32 is moved from %HOMEDRIVE%%HOMEPATH%\GazeParser to %USERPROFILE%\GazeParser.
* FIXED: :func:`GazeParser.TrackingTools.ControllerPsychoPyBackend.getSpatialError` did not work when 'units' was not 'pix'.
* FIXED: Some minor bugs.

GazeParser 0.5.0
----------------------

(released 2012/06/28)

* CHANGED: GazeParser.Tracker is renamed to SimpleGazeTracker and now runs on Windows, Linux and Mac OS X.
    - ADDED: There are three editions of SimpleGazeTracker, OptiTrack, InterfaceGPC5300, and OpenCV.
        * OpenCV edition runs on Windows, Linux and Mac OS X.
        * Optitrack and InterfaceGPC5300 editions run on Windows only.
    - CHANGED: Location of configuration files is moved from %APPDATA%\GazeTracker to %USERPROFILE%\SimpleGazeTracker in Windows.
    - CHANGED: New SimpleGazeTracker depends on SDL, SDL_net and SDL_ttf instead of DirectX and WinSock.
    - ADDED: Tentative binocular recording mode.
    - ADDED: Application log is output to Tracker.log in the data directory.
* ADDED: :func:`GazeParser.Core.GazeData.findMessage`
    

GazeParser 0.4.1
--------------------

(released 2012/05/25)

* ADDED: :func:`GazeParser.Converter.TobiiToGazeParser`
* CHANGED: GazeParser.TrackingTools module is updated.
    - :func:`GazeParser.TrackingTools.BaseController.calibrationLoop` returns **'space' and 'q'** instead of pygame.locals.K_SPACE and pygame.locals.K_q.
    - :class:`GazeParser.TrackingTools.ControllerPsychoPyBackend` supports pyglet window.
    - :class:`GazeParser.TrackingTools.ControllerPsychoPyBackend` supports *unit* options.
    
    .. note:: Gaze position is recorded in *pix* in the data file.

* ADDED: Installer of *CameraLink edition* of GazeParser.Tracker is released. CameraLink image grabbers manufactured by `Interface Corporation <http://www.interface.co.jp/>`_ is necessary to use this edition.
* FIXED: Installer of GazeParser.Tracker was localized to Japanese. Localization of the installer is now set to 'Neutral'.
* CHANGED: GazeParser.Tracker outputs calibration target poisitions to the data file. 
  This information would be helpful to convert the units of target position when calibration target positions are specified in a unit other than 'pix'
* CHANGED: GazeParser.app.Viewer is updated.
  * Messages are plotted in XY-T mode.
  * Number of fixations are plotted in XY mode.
* FIXED: GazeParser.Core.GazeData._getEventListByTime could not deal with data without any saccade.
* FIXED: bug with GazeParser.Microsaccade module.
* FIXED: process of GazeParser.Tracker did not terminate when multiple errors occurred while initialization.
* FIXED: GazeParser.app.Converters.interactiveConfig did not work.

GazeParser 0.4.0
---------------------

(released 2012/05/10)

* First release.

