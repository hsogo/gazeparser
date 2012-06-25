ChangeLog
====================

GazeParser 0.5.0alpha1
----------------------

(released 2012/06/25)

* CHANGED: GazeParser.Tracker is renamed to SimpleGazeTracker and now runs on Windows, Linux and Mac OS X.
    - ADDED: There are three editions of SimpleGazeTracker, OptiTrack, InterfaceGPC5300, and OpenCV.
        * OpenCV edition runs on Windows, Linux and Mac OS X.
        * Optitrack and InterfaceGPC5300 editions run on only Windows.
    - CHANGED: Location of configuration files is moved from %APPDATA%\GazeTracker to %HOMEDRIVE%%HOMEPATH%\GazeParser\SimpleGazeTracker in Windows.
    - CHANGED: New SimpleGazeTracker depends on SDL instead of DirectX and WinSock.
    - ADDED: Tentative binocular recording mode.
    - ADDED: Log 
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

