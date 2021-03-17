"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    import Image
    import ImageDraw
except ImportError:
    from PIL import Image
    from PIL import ImageDraw

import warnings

from .PsychoPyBackend import ControllerPsychoPyBackend

class DummyPsychoPyBackend(ControllerPsychoPyBackend):
    """
    Dummy controller for PsychoPy.
    """
    def __init__(self, configFile):
        super().__init__(configFile)
        # from psychopy.event import Mouse
        # self.mouse = Mouse
        self.mousePosList = []
        self.messageList = []
        self.lastMousePosIndex = 0
        self.recStartTime = 0

    def isDummy(self):
        """
        Returns True if this controller is dummy.
        """
        return True

    def connect(self, address='', portSend=10000, portRecv=10001):
        """
        Dummy function for debugging. This method does nothing.
        """
        if address == '':
            print('connect to default IP address=%s (dummy)' % (self.TRACKER_IP_ADDRESS))
        else:
            print('connect to %s (dummy)' % (address))

    def openDataFile(self, filename, config=None):
        """
        Dummy function for debugging. This method does nothing.
        """
        print('openDataFile (dummy): ' + filename)
        self.datafilename = filename
        
        if config is None:
            print('no config object is specified.')
        else:
            print(config)

    def closeDataFile(self):
        """
        Dummy function for debugging. This method does nothing.
        """
        print('close (dummy)')
        self.datafilename = ''

    def getEyePosition(self, timeout=0.02, getPupil=False, units='pix', ma=1):
        """
        Dummy function for debugging. This method returns current mouse position.
        """
        e = self.mouse.getPos()
        if self.win.units == 'pix':
            return self.convertFromPix(e, units)
        else:
            return self.convertFromPix(self.convertToPix(e, self.win.units), units)

    def recordCurrentMousePos(self):
        """
        Record current mouse position.
        This method is for debugging --- included only in dummy controller.
        Therefore, make sure that your controller is dummy controller before
        calling this method.

        Example::

            if tracker.isDummy():
                tracker.recordCurrentMousePos()

        """
        e = self.mouse.getPos()
        if self.win.units != 'pix':
            e = self.convertToPix(e, self.win.units)  # record as 'pix'
        self.mousePosList.append([1000*(self.clock()-self.recStartTime), e[0], e[1], 0])

    def getEyePositionList(self, n, timeout=0.02, units='pix', getPupil=False):
        """
        Dummy function for debugging. This method returns mouse position list.
        Use recordCurrentMousePos() method to record mouse position.
        """
        l = len(self.mousePosList)
        while l <= numpy.abs(n):
            self.mousePosList.insert(0,self.mousePosList[0])
            l = len(self.mousePosList)
        ml = numpy.array(self.mousePosList)

        if units != 'pix':
            ml[1:3] = self.convertFromPix(ml[1:3].reshape((1, -1)), units).reshape((-1, 2))

        if n > 0:
            if getPupil:
                return ml[-1:l-n-1:-1]
            else:
                return ml[-1:l-n-1:-1, :3]
        else:
            nn = min(l-self.lastMousePosIndex, -n)
            self.lastMousePosIndex = l
            if getPupil:
                return ml[-1:l-nn-1:-1]
            else:
                return ml[-1:l-nn-1:-1, :3]

    def getWholeEyePositionList(self, timeout=0.02, units='pix', getPupil=False):
        """
        Dummy function for debugging. This method returns mouse position list.
        Use recordCurrentMousePos() method to record mouse position.
        """
        ml = numpy.array(self.mousePosList)
        if units != 'pix':
            ml[:, 1:3] = numpy.array(self.convertFromPix(ml[:, 1:3].reshape((1, -1)), units)).reshape((-1, 2))

        if getPupil:
            return ml
        else:
            return ml[:, :3]

    def getWholeMessageList(self, timeout=0.2):
        """
        Dummy function for debugging. This method emurates getWholeMessageList.
        """
        return self.messageList

    def sendMessage(self, message):
        """
        Dummy function for debugging. This method emurates sendMessage.
        """
        print('sendMessage (dummy) %s' % message)
        self.messageList.append(['#MESSAGE', 1000*(self.clock()-self.recStartTime), message])

    def sendSettings(self, configDict):
        """
        Dummy function for debugging. This method does nothing.
        """
        warnings.warn('sendSettings is deprecated. Use "config" option of openDataFile instead.')

    def startRecording(self, message='', wait=0.2):
        """
        Dummy function for debugging. This method does nothing.
        """
        print('startRecording (dummy): ' + message)
        self.mousePosList = []
        self.lastMousePosIndex = 0
        self.recStartTime = self.clock()

    def stopRecording(self, message='', wait=0.2):
        """
        Dummy function for debugging. This method does nothing.
        """
        print('stopRecording (dummy): ' + message)

    def startMeasurement(self, message='', wait=0.2):
        """
        Dummy function for debugging. This method does nothing.
        """
        print('startMeasurement (dummy): ' + message)
        self.mousePosList = []
        self.lastMousePosIndex = 0
        self.recStartTime = self.clock()

    def stopMeasurement(self, message='', wait=0.2):
        """
        Dummy function for debugging. This method does nothing.
        """
        print('stopMeasurement (dummy): ' + message)

    def getCurrentMenuItem(self, timeout=0.2):
        """
        Dummy function for debugging. This method does nothing.
        """
        return 'Dummy Controller'

    def getCalibrationResults(self, timeout=0.2):
        """
        Dummy function for debugging. This method does nothing.
        """
        return 'Dummy Results'

    def getCameraImage(self):
        """
        Dummy function for debugging. This method puts a text
        'Camera Preview' at the top-left corner of camera preview screen.

        *Usually, you don't need use this method.*
        """
        draw = ImageDraw.Draw(self.PILimg)
        draw.rectangle(((0, 0), (self.IMAGE_WIDTH, self.IMAGE_HEIGHT)), fill=0)
        draw.text((64, 64), 'Camera Preview', fill=255)
        return None

    def getCalibrationResultsDetail(self, timeout=0.2):
        """
        Dummy function for debugging. This method does nothing.
        """
        return None

    def sendCommand(self, command):
        """
        Dummy function for debugging. This method outputs commands to
        standard output instead of sending it to SimpleGazeTracker.
        """
        print('Dummy sendCommand: ' + command)

    def setCalibrationScreen(self, win, font=''):
        """
        Set calibration screen.
        """
        ControllerPsychoPyBackend.setCalibrationScreen(self, win, font)
        draw = ImageDraw.Draw(self.PILimgCAL)
        draw.rectangle(((0, 0), self.PILimgCAL.size), fill=0)
        draw.text((64, 64), 'Calibration/Validation Results', fill=255)
        self.putCalibrationResultsImage()

    def doCalibration(self):
        """
        Emurates calibration procedure.
        """
        super().doCalibration(self)
        if self.SHOW_CALDISPLAY:
            self.showCalImage = True
        else:
            self.showCalImage = False
        self.messageText = 'Dummy Results'

    def doValidation(self):
        """
        Emurates validation procedure.
        """
        super().doValidation(self)
        if self.SHOW_CALDISPLAY:
            self.showCalImage = True
        else:
            self.showCalImage = False
        self.messageText = 'Dummy Results'

    def isBinocularMode(self, timeout=0.2):
        """
        Currently dummy controller emulates only monocular recording.
        """
        return False

    def getCameraImageSize(self, timeout=0.2):
        """
        This dummy method simply returns current IMAGE_WIDTH and IMAGE_HEIGHT
        """
        return (self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

    def getCameraIFI(self, timeout=0.2):
        """
        This dummy method simply returns current 1000.0/CAMERA_SAMPLING_RATE
        """
        return 1000.0/self.CAMERA_SAMPLING_RATE

    def getBufferSizeInfo(self, timeout=0.2):
        """
        This dummy method simply returns 432000, MAX_CAL_POINTS*MAX_SAMPLES_PER_TRGPOS, MAX_CAL_POINTS
        """
        return (432000, self.MAX_CAL_POINTS*self.MAX_SAMPLES_PER_TRGPOS, self.MAX_CAL_POINTS)

