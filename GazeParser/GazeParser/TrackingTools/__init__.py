"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2023 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

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
            try:
                from .Controller.DummyPsychoPyBackend import DummyPsychoPyBackend
            except:
                raise RuntimeError('Failed to import dummy PsychoPy backend.  Is PsychoPy available?')
            return DummyPsychoPyBackend(configFile)
        else:
            try:
                from .Controller.PsychoPyBackend import ControllerPsychoPyBackend
            except:
                raise RuntimeError('Failed to import PsychoPy backend.  Is PsychoPy available?')
            return ControllerPsychoPyBackend(configFile)
    else:
        raise ValueError('Unknown backend: '+str(backend))

def cameraDelayEstimationHelper(screen, tracker):
    """
    This function is obsolete.  Use GazeParser.app.tools.CameraDelayEstimator.
    """
    raise RuntimeError("This function is obsolete.  Use GazeParser.app.tools.CameraDelayEstimator.")

