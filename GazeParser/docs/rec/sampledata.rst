Format of the GazeParser.Tracker CSV data file
======================================================

Here is a sample of the GazeParser.Tracker CSV data file.
At the beginning of the data file, recording conditions are output (line 1-3).
Following it, data blocks are output.

A data block starts with #START_REC and ends with #STOP_REC, which are inserted by :func:`~GazeParser.TrackingToools.BaseController.startRecording` and :func:`~GazeParser.TrackingToools.BaseController.stopRecording`, respectively.
Numbers after #START_REC shows recorded year, month, day, hour, minute and second.
#MESSAGE is inserted if startRecording() is called with a message string (line 5).
#XPARAM and #YPARAM indicate calibration parameters (line 6-7).

The recorded data follows these lines (line 8-).
The first element of the recorded data is the timestamp when the gaze position is recorded.
The second and the thrid element indicate horizontal and vertical gaze position in the screen coordinate if recording mode is monocluar.
If recording mode is binocular, the second and third element indicate horizontal and vertical gaze position of the left eye, and the fourth and fifth element indidate gaze position of the right eye.::

    001: #SCREEN_WIDTH,1920
    002: #SCREEN_HEIGHT,1080
    003: #VIEWING_DISTANCE,57.3
    004: #START_REC,2012,1,30,16,10,24
    005: #MESSAGE,0,trial1
    006: #XPARAM,-53.020081,-2.346666,979.127991,0.000000,0.000000
    007: #YPARAM,-0.342159,-66.443535,-397.927063,0.000000,0.000000
    008: 1.2,618.3,515.7
    009: 2.6,622.7,509.0
    010: 4.4,622.9,525.8

At the end of the data block, messages inseted by :func:`~GazeParser.TrackingToools.BaseController.sendMessage`, are output (line 825-837).
If recording duration is very long (depending on sampling frequency of the camera), messages are output in between the recorded data to prevent buffer overrun.
#STOP_REC is output at the end of the block (line 838).::

    825: 6781.7,1165.4,444.3
    826: 6790.6,1173.3,440.3
    827: #MESSAGE,500.0,STIM 960 540
    828: #MESSAGE,1516.5,STIM 860 740
    (snip)
    837: #MESSAGE,10516.0,STIM 960 340
    838: #STOP_REC

If several pair of startRecording() and stopRecording() are called in a single recording, corresponding number of data block are output in a single data file.


