
Install GazeParser (Windows)
==================================

Dependencies
-------------------------

**Python 2.5, 2.6 or 2.7** is necessary to use GazePaser.
The author mainly uses Python 2.7.
GazeParser depends on following Python modules.

- **numpy**
- **scipy**
- **matplotlib**
- **PIL (Python Imaging Library)**
- **Tkinter (Python-TK)**
- **VisionEgg** and/or **PsychoPy** (experimental control library)

Download
---------------------------

GazeParser installer can be downloaded from following page.

`<http://sourceforge.net/projects/gazeparser/files/>`_

Install either of these files to computers which you plan to use stimulus presentation and data analysis.

- **GazeParser-x.x.x-pyx.x.egg**: python egg file
- **GazeParser-x.x.x.win32.exe**: Windows installer
- **GazeParser-x.x.x.zip**: zipped file

If you plan to record gaze data, install one of following files to a computer which you plan to use recording gaze data.

- **SimpleGazeTracker-x.x.x-optitrack-y.y.yyy.msi**: SimpleGazeTracker installer for OptiTrack V120 or V100R2 cameras
    Probably OptiTrack Baseline 2D SDK will be necessary to use SimpleGazeTracker.
    The SDK can be downloaded from OptiTrack Downloads page.

    `<http://www.naturalpoint.com/optitrack/downloads/archives.html>`_

    Version number following 'optitrack-' in the SimpleGazeTracker installer indicates which version of SDK is necessary.
    For example, if name of the SimpleGazeTracker installer is SimpleGazeTracker-0.4.0-optitrack-**1.3.038**.msi, OptiTrack 2D SDK 1.3.038 is necessary.

- **SimpleGazeTracker-x.x.x-opencv-y.y.yyy.msi**: SimpleGazeTracker installer for cameras supported by OpenCV.
    Necessary interfaces, drivers and other applications depend on camera unit.  Confirm user manual of the camera.

- **SimpleGazeTracker-x.x.x-interface-gpc5300.msi**: SimpleGazeTracker installer for CameraLink image grabber manufactured by `Interface Corporation <http://www.interface.co.jp/>`_.
    A CameraLink image grabber supported by Interface GPC5300 software must be installed to the recording PC.


