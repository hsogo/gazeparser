.. _config-simpleazetracker:

Configure SimpleGazeTracker
=============================================================

General Opions (in CONFIG)
--------------------------------------

**CONFIG** is a plain text file where camera-independent SimpleGazeTracker parameters are specified.
Lines start with '#' are ignored.  This is an example of CONFIG.

::

    BINOCULAR=0
    THRESHOLD=17
    MAXPOINTS=243
    MINPOINTS=72
    PURKINJE_THRESHOLD=236
    PURKINJE_SEARCHAREA=29
    PURKINJE_EXCLUDEAREA=8
    CAMERA_WIDTH=320
    CAMERA_HEIGHT=224
    PREVIEW_WIDTH=640
    PREVIEW_HEIGHT=480

.. note::
    Parameter name is case sensitive. Do not insert any space before and behind '='.::
    
        #correct
        BINOCULAR=0
        
        #wrong
        BINOCULAR = 0
        Binocular=0
    

===================== ============================================================== =========================
Parameter             Description                                                    Adjustable at run-time
===================== ============================================================== =========================
BINOCULAR             This parameter must be **0** or **1**.  If the value is 1,     NO
                      SimpleGazeTracker runs at binocular recording mode.            
                      Otherwise, it runs at monocular recording mode.                
THRESHOLD             This parameter affects detection of pupil.                     YES
                      See :ref:`adjusting-camera` for detal.                         
MAXPOINTS             This parameter affects detection of pupil.                     YES
                      See :ref:`adjusting-camera` for detal.                         
MINPOINTS             This parameter affects detection of pupil.                     YES
                      See :ref:`adjusting-camera` for detal.                         
PURKINJE_THRESHOLD    This parameter affects detection of the first Purkinje image.  YES
                      See :ref:`adjusting-camera` for detal.                         
PURKINJE_SEARCHAREA   This parameter affects detection of the first Purkinje image.  YES
                      See :ref:`adjusting-camera` for detal.                         
PURKINJE_EXCLUDEAREA  This parameter affects detection of pupil center.              YES
                      See :ref:`adjusting-camera` for detal.                         
CAMERA_WIDTH          Width of the image sent from the camear.                       NO
CAMERA_HEIGHT         Height of the image sent from the camear.                      NO
PREVIEW_WIDTH         Width of the preview image on the screen of the Recorder PC.   NO
PREVIEW_HEIGHT        Height of the preview image on the screen of the Recorder PC.  NO
===================== ============================================================== =========================

Opions for OpenCV edition (in CONFIG_OPENCV)
---------------------------------------------

**CONFIG_OPENCV** is a plain text file where camera-dependent parameters are specified.
Lines start with '#' are ignored.  This is an example of CONFIG_OPENCV.

::

    USE_THREAD=1
    SLEEP_DURATION=0
    FRAME_RATE=60

.. note::
    Parameter name is case sensitive. Do not insert any space before and behind '='.::
    
        #correct
        USE_THREAD=0
        
        #wrong
        Use_Thread=0
        USE_THREAD = 0

.. warning::
    Whether these parameters work correctly depends on camera unit.
    Probably it also depends on build options of OpenCV.
    *It is recommended to delete unnecessary options from CONFIG_OPENCV 
    because such options may cause unexpected effects*.
    

===================== ============================================================== =========================
Parameter             Description                                                    Adjustable at run-time
===================== ============================================================== =========================
CAMERA_ID             This integer is passed to the constructor or CV::VideoCapture. NO
                      Usually you need not write this parameter to the configuration 
                      file if you connect only one camera to your PC.  If you have 
                      multiple cameras on your PC and SimpleGazeTracker does not
                      use desirable camera, use this parameter to tell
                      SimpleGazeTracker which camera should be used.
USE_THREAD            This parameter must be **0** or **1**.  A saparate thread is   NO
                      used to capture image if the value is 1.  Generally, using 
                      separate thread results in better performance: however, 
                      it will cause segmentation fault if your opencv library 
                      is not built with multithreading support.  Set this value 0
                      if segmentation fault occurs.
SLEEP_DURATION        When USE_THREAD is 0, performance of SimpleGazeTracker         NO
                      may severely spoiled because captring camera image may 
                      lock process until capture is finished.  In such a case,
                      set SLEEP_DURATION to wait to capture image until a 
                      specified amount of time has elapsed.  The Unit of the 
                      value is *milliseconds*.  This value should 
                      be a bit smaller than inter-frame interval of the camera.
                      For example, about 15-16 would work fine if your camera 
                      capture image at 60Hz (1000ms/60frames = 16.667ms).
FRAME_RATE            Set this value to CV_CAP_PROP_FPS using cv::VideoCapture::set. NO
                      Frame rate of the camera is set to this value if it is 
                      configurable from cv::VideoCapture::set.
EXPOSURE              Set this value to CV_CAP_PROP_EXPOSURE using                   NO
                      cv::VideoCapture::set.
                      Exposure of the camera is set to this value if it is 
                      configurable from cv::VideoCapture::set.
BRIGHTNESS            Set this value to CV_CAP_PROP_BRIGHTNESS using                 NO
                      cv::VideoCapture::set.
                      Brightness of the camera is set to this value if it is 
                      configurable from cv::VideoCapture::set.
CONTRAST              Set this value to CV_CAP_PROP_CONTRAST using                   NO
                      cv::VideoCapture::set.
                      Contrast of the camera is set to this value if it is 
                      configurable from cv::VideoCapture::set.
GAIN                  Set this value to CV_CAP_PROP_GAIN using                       NO
                      cv::VideoCapture::set.
                      Gain of the camera is set to this value if it is 
                      configurable from cv::VideoCapture::set.
===================== ============================================================== =========================

.. note::
    Image size (CV_CAP_PROP_FRAME_WIDTH and CV_CAP_PROP_FRAME_HEIGHT) are 
    configured by CAMERA_WIDTH and CAMERA_HEIGHT options in 'CONFIG'.


Opions for OptiTrack edition (in CONFIG_OPTITRACK)
---------------------------------------------------

**CONFIG_OPTITRACK** is a plain text file where camera-dependent parameters are specified.
Lines start with '#' are ignored.  This is an example of CONFIG_OPTITRACK.

::

    #For V120:slim
    #FRAME_RATE=120
    #EXPOSURE=200
    #INTENSITY=1
    #
    #For V100
    #FRAME_RATE=100
    #EXPOSURE=200
    #INTENSITY=1
    #
    FRAME_RATE=120
    EXPOSURE=200
    INTENSITY=1

.. note::
    Parameter name is case sensitive. Do not insert any space before and behind '='.::
    
        #correct
        FRAME_RATE=120
        
        #wrong
        Frame_rate=120
        FRAME_RATE = 120

===================== ============================================================== =========================
Parameter             Description                                                    Adjustable at run-time
===================== ============================================================== =========================
FRAME_RATE            Frame rate of the camera.                                      NO
EXPOSURE              Exposure duration.                                             YES
INTENSITY             (ONLY FOR V100R2) Intensity of built-in IR LED illumination.   YES
===================== ============================================================== =========================

Opions for Interface GPC5300 edition (in CAMERA.cfg)
----------------------------------------------------------

CAMERA.cfg specifies camera parameters which is necessary for GPC5300 to control the camera.
Usually, this file is created with a configuration file generator that comes with GPC5300.
See the manual of GPC5300 for detail.
