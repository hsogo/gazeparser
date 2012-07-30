.. _stim_cap_delay:

Delay from stimulus presentation to image capture
=======================================================

Delay estimation
---------------------

Suppose that we want to measure saccade lateny to a small dot briefly presented on a display using GazeParser and SimpleGazeTracker.
In such a case, 

* The dot is drawn on the back buffer and then the buffer is flipped to show the dot on the display.
* After flip is finished, a message is sent to the Recorder PC to record the onset time of the dot.
* Participant detects the dot and makes a saccade to it.
* Participant's eye movement is captured by a camera and sent to the Recorder PC.

This measurement would be simple if there was no delay but participant's response latency in these process:
however, unfortunately, there are many processes that would cause delay.  Following processes are main sources of delay.

1. Delay from calling flip (PsychoPy) or swap_buffers (VisionEgg) to updating the display
2. Delay from updating the display to capturing image by the camera.  For example, if sampling frequency of the camera is 60Hz, capture may be delayed about 16.7ms (i.e. 1/60sec) at worst.
3. Delay in transferring captured imaget to the Recorder PC.
4. Delay in transferring a message from the Presentation PC to the Recorder PC.

It is difficult to estimate these delay exactly, total delay can be roughly estimated by capturing stimuli on the display by the camera.
:func:`GazeParser.TrackingTools.cameraDelayEstimationHelper` is intended to help this estimation.
To use :func:`~GazeParser.TrackingTools.cameraDelayEstimationHelper`, adjust camera position so that the center of the display can be captured by the camera (Figure 1).

.. figure:: stim2capdelay001.jpg
    
    Figure 1

Run SimpleGazeTracker on the Recorder PC, and then run a script like following examples on the Presentation PC.
Please modify screen size, camera image size and IP address if necessary.

.. code-block:: python
    
    #For PsychoPy users
    import psychopy.visual
    import GazeParser.TrackingTools
    
    tracker = GazeParser.TrackingTools.getController(backend='PsychoPy')
    tracker.setReceiveImageSize((640,480))
    tracker.connect('192.168.11.6')
    
    win = psychopy.visual.Window(size=(1920,1200),fullscr=True)
    GazeParser.TrackingTools.cameraDelayEstimationHelper(win, tracker)

.. code-block:: python
    
    #For VisionEgg users
    import VisionEgg.Core
    import GazeParser.TrackingTools
    
    tracker = GazeParser.TrackingTools.getController(backend='VisionEgg')
    tracker.setReceiveImageSize((640,480))
    tracker.connect('192.168.11.6')
    
    screen = VisionEgg.Core.get_default_screen()
    GazeParser.TrackingTools.cameraDelayEstimationHelper(screen, tracker)

As shown in Figure 1, these sample script shows a counter on the center of a PsychoPy/VisionEgg window.
When space key on the Presentation PC is pressed, :func:`~GazeParser.TrackingTools.cameraDelayEstimationHelper`
sends a request to save the latest camera image that has been transferred to the Recorder PC.
The saved image is named 'FILE######.bmp', where ###### is the counter number that is drawn on the last flipped buffer before key press.
To stop script, press ESC key.

If there was no delay, the number in the filename should be equal to the number captured in that image.
Usually, the number in the image is smaller than the number in the filename due to delay.
Figure 2 shows how the number in the image delays from the number in the filename.
(1) to (4) in Figure 2 correspond to four sources of delay described above.

.. figure:: stim2capdelay002.png
    
    Figure 2

Figure 3 and 4 show examples of images obtained by :func:`~GazeParser.TrackingTools.cameraDelayEstimationHelper`.
Apparatus for these examples are shown in Table 1.
When PsychoPy ran in window mode (Figure 3), difference between numbers were 5 or 6 in most cases.
Considering reflesh rate of the display (60Hz), delay should be approximately 80-100 ms!

.. figure:: stim2capdelay003.jpg
    
    Figure 3

When PsychoPy ran in full screen mode (Figure 4), difference between numbers were 4 in most cases.
Although delay was reduced compared to that in window mode, it is not negligibly small (approximately 60-70 ms).

.. figure:: stim2capdelay004.jpg
    
    Figure 4

.. table:: Table 1

    ================ ============================================================
    Presentation PC  * [CPU] Core i7 920
                     * [GRAPHIC] GeForce GTX 550 Ti
                     * [LCD] EIZO S2411W (60Hz)
                     * Windows 7 Professional SP1
                     * Python 2.7.2
                     * PsychoPy 1.73.04
    Recorder PC      * [CPU] Core2 Duo E8500
                     * [CAMERA] IMI Tech IMB-11FT (IEEE1394 camera)
                     * Ubuntu 12.04
                     * GazeParser 0.5.1 OpenCV edition (USE_THREAD=1)
    ================ ============================================================

Unfortunately it is not clear why the delay is so long.  Probably (2) would be shorter than frame duration (16.7ms).
(4) would be a few milliseconds considering time spent by :func:`~GazeParser.TrackingTools.BaseController.getEyePosition` (see :ref:`pc_pc_delay`).
Therefore, the delay should be approximately equal to sum of (1) and (3).  Further investigation is necessary to determin sources of the delay.

Delay correction
---------------------

In my experience, the delay is almost constant as far as the same hardware is used.  SimpleGazeTracker has 'DELAY_CORRECTION' option to correct constant delay (See als :ref:`config-simpleazetracker`).
The value of this parameter is added to timestamp when SimpleGazeTracker received a message.  In the case of Figure 3, setting DELAY_CORRECTION=60 would be correct the delay.

**It is worth noting that (1) is a common source of delay to all experiments using PsychoPy and VisionEgg (and probably other libralies depending on OpenGL).
This correction may cause short saccade latency compared to measurement with other eye trackers and PsychoPy/VisionEgg.**


Digging into the problem: delay in the Recorder PC
---------------------------------------------------

To evaluate the delay in detail, eye movement was concurrently recorded by SimpleGazeTracker and direct-current electrooculography (DC-EOG).
Apparatus are shown in Table 2.

.. table:: Table 2

    ================ ==============================================================
    Presentation PC  * [CPU] Core2 Duo E6550
                     * [GRAPHIC] GeForce 8600 GTS
                     * [LCD] EIZO EV2313W (60Hz)
                     * Windows XP Professional SP3
                     * Python 2.5.4
                     * VisionEgg 1.2.1
    Recorder PC      * [CPU] Core i7 950
                     * [Camera]
                         - IMPERX Bobcat ICL-B0620 (@250Hz, for GPC5300 edition)
                         - OptiTrack V120Slim (@120Hz. for OptiTrack edition)
                         - IMI Tech IMB-11FT (@60Hz, for OpenCV edition)
                     * [DC-OEG] NIHON KODEN AN-601G with Interface PCI-3166
                     * Windows 7 Professional SP1
                     * GazeParser 0.5.1 all edition
    ================ ==============================================================




.. figure:: stim2capdelay005.png
    
    Figure 5


.. figure:: stim2capdelay006.png
    
    Figure 6

.. figure:: stim2capdelay007.png
    
    Figure 7

