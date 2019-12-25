"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from .PsychoPyBackend import ControllerPsychoPyBackend
from .DummyPsychoPyBackend import DummyPsychoPyBackend

def getController(backend, configFile=None, dummy=False):
    """
    Get Tracker controller object.

    :param str backend: specify screen type. Currently, only 'PsychoPy'
        is accepted ('VisionEgg' is obsolated).
    :param stt configFile: Controller configuration file.
        If None, Tracker.cfg in the application directory is used.
        Default value is None.
    :param bool dummy: Get dummy controller for standalone debugging.
        Default value is False.
    """
    if backend == 'VisionEgg':
        raise ValueError('VisionEgg controller is obsolated.')
    elif backend == 'PsychoPy':
        if dummy:
            return DummyPsychoPyBackend(configFile)
        else:
            return ControllerPsychoPyBackend(configFile)
    else:
        raise ValueError('Unknown backend: '+str(backend))


def cameraDelayEstimationHelper(screen, tracker):
    """
    A simple tool to help estimating measurement delay.
    See documents of GazeParser for detail.

    :param screen: an instance of psychopy.visual.Window.
    :param tracker: an instance of GazeParser.TrackingTools.ControllerPsychoPyBackend.
    """
    if isinstance(tracker, ControllerPsychoPyBackend):
        import psychopy.event
        import psychopy.visual
        msg = psychopy.visual.TextStim(screen, pos=(0, 0))

        msg.setText('press space')
        isWaiting = True
        while isWaiting:
            msg.draw()
            screen.flip()
            for key in psychopy.event.getKeys():
                if key == 'space':
                    isWaiting = False

        tracker.sendCommand('inhibitRendering'+chr(0))

        frame = 0
        isRunning = True
        while isRunning:
            msg.setText(str(frame))
            msg.draw()
            screen.flip()

            for key in psychopy.event.getKeys():
                if key == 'escape':
                    isRunning = False
                elif key == 'space':
                    tracker.sendCommand('saveCameraImage'+chr(0)+'FRAME'+str(frame).zfill(8)+'.bmp'+chr(0))

            frame += 1

        tracker.sendCommand('allowRendering'+chr(0))

    else:
        raise ValueError('Unknown controller.')
