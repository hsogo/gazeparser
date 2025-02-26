# GazeParser

Please read `<http://gazeparser.sourceforge.net/ins/index.html>`_ for detail.

## For Windows users

* Install following file or use pip.
    - GazeParser-0.12.2/GazeParser-0.12.2.zip

* GazeParser supports gaze data recorded by SimpleGazeTracker.  To install SimpleGazeTracker, downlowad the appropriate installer for your camera from the list below.

    - SimpleGazeTracker-0.12.0/SimpleGazeTracker-0.12.0-OptiTrack-2.2.0.msi
    - SimpleGazeTracker-0.12.0/SimpleGazeTracker-0.12.0-OpenCV-4.5.1.msi
    - SimpleGazeTracker-0.12.0/SimpleGazeTracker-0.12.0-FlyCapture2-2.13.61.msi
    - SimpleGazeTracker-0.12.0/SimpleGazeTracker-0.12.0-Spinnaker2-2.3.0.77.msi

  GazeParser includes webcam-based tracker.  This tracker is not as fast and accurate as SimpleGazeTracker, but it does not require IR light source and  restriction of head movement.  To use this tracker, following Python packages are required.

    - opencv-python 
    - dlib
    - tensorflow
    - psychopy

  


## For Linux users

* Install following file or use pip.  Debian .deb package is available.
    - GazeParser-0.12.0/GazeParser-0.12.0.zip
    - GazeParser-0.12.0/gazeparser_0.12.0_all.deb

* GazeParser supports gaze data recorded by SimpleGazeTracker.  SimpleGazeTracker is distributed as the source code or Debian .deb packages.
    - SimpleGazeTracker-0.12.0/SimpleGazeTracker-0.12.0.tar.gz
    - SimpleGazeTracker-0.12.0/simplegazetracker_0.12.0_amd64.deb
    - SimpleGazeTracker-0.12.0/simplegazetracker-flycap_0.12.0_amd64.deb
    - SimpleGazeTracker-0.12.0/simplegazetracker-spinnaker_0.12.0_amd64.deb

  GazeParser includes webcam-based tracker.  This tracker is not as fast and accurate as SimpleGazeTracker, but it does not require IR light source and  restriction of head movement.  To use this tracker, following Python packages are required.

    - opencv-python 
    - dlib
    - tensorflow
    - psychopy


## For MacOS users

* Install following file or use pip.
    - GazeParser-0.12.0/GazeParser-0.12.0.zip

* SimpleGazeTracker 0.11.0 or later does not officially support MacOS.  Please use Linux or Windows to run SimpleGazeTracker.  GazeParser's buit-in tracker is not tested on MacOS, but it will work.

