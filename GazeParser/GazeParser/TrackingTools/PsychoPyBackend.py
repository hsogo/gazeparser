"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from .Base import BaseController

try:
    import Image
    import ImageDraw
except ImportError:
    from PIL import Image
    from PIL import ImageDraw

import numpy
import time

import psychopy.visual
import psychopy.event
import psychopy.monitors
from psychopy.misc import cm2pix, deg2pix, pix2cm, pix2deg

class ControllerPsychoPyBackend(BaseController):
    """
    SimpleGazeTracker controller for PsychoPy.
    """
    def __init__(self, configFile=None):
        """
        :param str configFile:
            Controller configuration file. If None, default configurations
            are used.
        """
        self.backend = 'PsychoPy'
        super().__init__(configFile)
        self.getKeys = psychopy.event.getKeys  # for psychopy, implementation of getKeys is simply importing psychopy.events.getKeys

    def setCalibrationScreen(self, win, font=''):
        """
        Set calibration screen.

        :param psychopy.visual.window win: instance of psychopy.visual.window to
            display calibration screen.
        :param str font: font name.
        """
        self.win = win
        (self.screenWidth, self.screenHeight) = win.size
        self.screenCenter = (0, 0)
        self.caltarget = [psychopy.visual.Rect(self.win, width=10, height=10, units='pix', lineWidth=1, fillColor=(1, 1, 1), lineColor=(1, 1, 1), name='GazeParserCalTarget'),
                          psychopy.visual.Rect(self.win, width=10, height=10, units='pix', lineWidth=1, fillColor=(1, 1, -1), lineColor=(-1, -1, -1), name='GazeParserCalTarget2')]
        self.PILimgCAL = Image.new('L', (self.screenWidth-self.screenWidth % 4, self.screenHeight-self.screenHeight % 4))
        self.img = psychopy.visual.SimpleImageStim(self.win, self.PILimg, name='GazeParserCameraImage')
        self.imgCal = psychopy.visual.SimpleImageStim(self.win, self.PILimgCAL, name='GazeParserCalibrationImage')
        self.msgtext = psychopy.visual.TextStim(self.win, pos=(0, -self.PREVIEW_HEIGHT/2-12), units='pix', text=self.getCurrentMenuItem(), font=font, name='GazeParserMenuText')
        self.calResultScreenOrigin = (self.screenWidth/2, self.screenHeight/2)
        self.mouse = psychopy.event.Mouse(win=self.win)

    def updateScreen(self):
        """
        Update calibration screen.

        *Usually, you don't need use this method.*
        """
        try:
            self.msgtext.setText(self.messageText, log=False)
        except:
            self.msgtext.setText('WARNING: menu string was not received correctly.', log=False)
        if self.showCameraImage:
            self.img.draw()
        if self.showCalImage:
            self.imgCal.draw()
        if self.showCalTarget:
            if hasattr(self.caltarget, '__iter__'):
                for s in self.caltarget:
                    s.setPos(self.calTargetPosition, log=False)
                    s.draw()
            else:
                self.caltarget.setPos(self.calTargetPosition, log=False)
                self.caltarget.draw()
        if self.SHOW_CALDISPLAY:
            self.msgtext.draw()

        self.win.flip()

    def setCameraImage(self):
        """
        Set camera preview image.

        *Usually, you don't need use this method.*
        """
        self.img.setImage(self.PILimg, log=False)

    def putCalibrationResultsImage(self):
        """
        Set calibration results screen.

        *Usually, you don't need use this method.*
        """
        self.imgCal.setImage(self.PILimgCAL.transpose(Image.FLIP_TOP_BOTTOM), log=False)

    # Override
    def setCalibrationTargetPositions(self, area, calposlist, units='pix'):
        """
        Send calibration area and calibration target positions to the Tracker
        Host PC. This method must be called before starting calibration.

        The order of calibration target positions is shuffled each time calibration
        is performed. However, the first target position (i.e. the target position
        at the beginning of calibration) is always the first element of the list.
        In the following example, the target is always presented at (0, 0) a the
        beginning of calibration. ::

            calArea = (-400, -300, 400, 300)
            calPos = ((   0,   0),
                      (-350, -250), (-350,  0), (-350, 250),
                      (   0, -250), (   0,  0), (   0, 250),
                      ( 350, -250), ( 350,  0), ( 350, 250))
            tracker.CalibrationTargetPositions(calArea, calPos)

        :param sequence area: a sequence of for elements which represent
            left, top, right and bottom of the calibration area.
        :param sequence calposlist: a list of (x, y) positions of calibration
            target.
        :param str units: units of 'area' and 'calposlist'.  'norm', 'height',
            'deg', 'cm' and 'pix' are accepted.  Default value is 'pix'.
        """
        pixArea = self.convertToPix(area, units, forceToInt=True)
        pixCalposlist = [self.convertToPix(calpos, units, forceToInt=True) for calpos in calposlist]
        super().setCalibrationTargetPositions(pixArea, pixCalposlist)

    # Override
    def getEyePosition(self, timeout=0.02, units='pix', getPupil=False, ma=1):
        """
        Send a command to get current gaze position.

        :param float timeout:
            If the Tracker Host PC does not respond within this duration, tuple of
            Nones are returned. Unit is second. Default value is 0.02
        :param str units: units of returned value.  'norm', 'height', 'deg', 'cm'
            and 'pix' are accepted.  Default value is 'pix'.
        :param bool getPupil:
            If true, pupil size is returned with gaze position.
        :param int ma:
            If this value is 1, the latest position is returned. If more than 1,
            moving average of the latest N samples is returned (N is equal to
            the value of this parameter). Default value is 1.
        :return:
            When recording mode is monocular, return value is a tuple of 2 or 3
            elements. The first two elements represents holizontal(X) and
            vertical(Y) gaze position in screen corrdinate. If getPupil is true,
            area of pupil is returned as the third element of the tuple.
            When recording mode is binocular and getPupil is False, return value
            is (Left X, Left Y, Right X, Right Y). If getPupil is True, return
            value is (Left X, Left Y, Right X, Right Y, Left Pupil, Right Pupil).
        """
        if ma < 1:
            raise ValueError('ma must be equal or larger than 1.')
        e = super().getEyePosition(timeout, getPupil=getPupil, ma=ma)
        if getPupil:
            return self.convertFromPix(e, units)
        else:
            if self.isMonocularRecording:
                return self.convertFromPix(e[:2], units) + e[2:]
            else:
                return self.convertFromPix(e[:4], units) + e[4:]

    # Override
    def getEyePositionList(self, n, timeout=0.02, units='pix', getPupil=False):
        """
        Get the latest N-samples of gaze position as a numpy.ndarray object.

        :param int n:
            Number of samples. If value is negative, data that have already
            transfered are not transfered again. For example, suppose that this
            method is called twice with n=-20. If only 15 samples are obtained
            between the first and second call, 15 samples are transfered by
            the second call. On the other hand, if n=20, 20 samples are transfered
            by each call. In this case, part of samples transfered by the second
            call is overlapped with those transfered by the first call.

            .. note:: setting value far below/above from zero will take long time,
               resulting failure in data acquisition and/or stimulus presentation.

        :param float timeout:
            If the Tracker Host PC does not respond within this duration, tuple of
            Nones are returned. Unit is second. Default value is 0.02
        :param str units: units of 'position' and returned value.  'norm', 'height',
            'deg', 'cm' and 'pix' are accepted.  Default value is 'pix'.
        :param bool getPupil:
            If true, pupil size is returned with gaze position.
        :return:
            If succeeded, an N x M shaped numpy.ndarray object is returned. N is
            number of transfered samples. M depends on recording mode and getPupil
            parameter.

            * monocular/getPupil=False: t, x, y    (M=3)
            * monocular/getPupil=True:  t, x, y, p (M=4)
            * binocular/getPupil=False: t, lx, ly, rx, ry (M=5)
            * binocular/getPupil=True:  t, lx, ly, rx, ry, lp, rp (M=7)

            (t=time, x=horizontal, y=vertical, l=left, r=right, p=pupil)

            If length of received data is zero or data conversion is failed,
            None is returned.
        """
        e = super().getEyePositionList(n, timeout, getPupil)

        if units == 'pix':
            return e

        if self.isMonocularRecording:
            converted = self.convertFromPix(e[:, 1:3].reshape((1, -1)), units)
            e[:, 1:3] = numpy.array(converted).reshape((-1, 2))
        else:
            converted = self.convertFromPix(e[:, 1:5].reshape((1, -1)), units)
            e[:, 1:5] = numpy.array(converted).reshape((-1, 4))

        return e

    # Override
    def getWholeEyePositionList(self, timeout=0.02, units='pix', getPupil=False):
        """
        Transfer whole gaze position data obtained by the most recent recording.
        It is recommended that this method is called immediately after
        :func:`~GazeParser.TrackingTools.BaseController.stopRecording` is called.

        .. note:: This method can be called during recording - but please note
            that this method takes tens or hundreds milliseconds. It may cause
            failure in data acquisition and/or stimulus presentation.

        :param float timeout:
            If the Tracker Host PC does not respond within this duration, tuple of
            Nones are returned. Unit is second. Default value is 0.2
        :param str units: units of 'position' and returned value.  'norm', 'height',
            'deg', 'cm' and 'pix' are accepted.  Default value is 'pix'.
        :param bool getPupil:
            If true, pupil size is returned with gaze position.
        :return:
            If succeeded, an N x M shaped numpy.ndarray object is returned. N is
            number of transfered samples. M depends on recording mode and getPupil
            parameter.

            * monocular/getPupil=False: t, x, y    (M=3)
            * monocular/getPupil=True:  t, x, y, p (M=4)
            * binocular/getPupil=False: t, lx, ly, rx, ry (M=5)
            * binocular/getPupil=True:  t, lx, ly, rx, ry, lp, rp (M=7)

            (t=time, x=horizontal, y=vertical, l=left, r=right, p=pupil)

            If length of received data is zero or data conversion is failed,
            None is returned.
        """
        e = super().getWholeEyePositionList(timeout, getPupil)

        if units == 'pix':
            return e

        if self.isMonocularRecording:
            converted = self.convertFromPix(e[:, 1:3].reshape((1, -1)), units)
            e[:, 1:3] = numpy.array(converted).reshape((-1, 2))
        else:
            converted = self.convertFromPix(e[:, 1:5].reshape((1, -1)), units)
            e[:, 1:5] = numpy.array(converted).reshape((-1, 4))

        return e

    def getSpatialError(self, position=None, responseKey='space', message=None, responseMouseButton=None,
                        gazeMarker=None, backgroundStimuli=None, toggleMarkerKey='m', toggleBackgroundKey=None,
                        showMarker=False, showBackground=False, ma=1, units='pix'):
        """
        Verify measurement error at a given position on the screen.

        :param position:
            A tuple of two numbers that represents target position in screen
            coordinate. If None, the center of the screen is used.
            Default value is None.
        :param responseKey:
            When this key is pressed, eye position is measured and spatial error
            is evaluated.  Default value is 'space'.
        :param str message:
            If a string is given, the string is presented on the screen.
            Default value is None.
        :param responseMouseButton:
            If this value is 0, left button of the mouse is also used to
            measure eye position.  If the value is 2, right button is used.
            If None, mouse buttons are ignored.
            Default value is None.
        :param gazeMarker:
            Specify a stimulus which is presented on the current gaze position.
            If None, default marker is used.
            Default value is None.
        :param backgroundStimuli:
            Specify a list of stimuli which are presented as background stimuli.
            If None, a gray circle is presented as background.
            Default value is None.
        :param str toggleMarkerKey:
            Specify name of a key to toggle visibility of gaze marker.
            Default value is 'm'.
        :param str toggleBackgroundKey:
            Specify name of a key to toggle visibility of background stimuli.
            Default value is None.
        :param bool showMarker:
            If True, gaze marker is visible when getSpatialError is called.
            Default value is False.
        :param bool showBackground:
            If True, gaze marker is visible when getSpatialError is called.
            Default value is False.
        :param int ma:
            If this value is 1, the latest position is returned. If more than 1,
            moving average of the latest N samples is returned (N is equal to
            the value of this parameter). Default value is 1.
        :param str units: units of 'position' and returned value.  'norm', 'height',
            'deg', 'cm' and 'pix' are accepted.  Default value is 'pix'.

        :return:
            If recording mode is monocular, a tuple of two elements is returned.
            The first element is the distance from target to measured eye position.
            The second element is a tuple that represents measured eye position.
            If measurement is failed, the first element is None.

            If recording mode is binocular, a tuple of four elements is returned.
            The first, second and third element is the distance from target to
            measured eye position.  The second and third element are the results
            for left eye and right eye, respectively.  These elements are None if
            measurement of corresponding eye is failed.  The first element is
            the average of the second and third element.  If measurement of either
            Left or Right eye is failed, the first element is also None.
            The fourth element is measured eye position.
        """
        if position is not None:
            posInPix = self.convertToPix(position, units)
        else:
            position = (0.0, 0.0)
            posInPix = (0.0, 0.0)

        if hasattr(self.caltarget, '__iter__'):
            for s in self.caltarget:
                s.setPos(posInPix, log=False)
        else:
            self.caltarget.setPos(posInPix, log=False)

        if message is not None:
            self.msgtext.setText(message, log=False)
            doDrawMessage = True
        else:
            doDrawMessage = False

        isMarkerVisible = showMarker
        isBackgroundVisible = showBackground
        if gazeMarker is None:
            gazeMarker = psychopy.visual.Rect(self.win, width=3, height=3, units='pix', lineWidth=1, fillColor=(1, 1, 0), lineColor=(1, 1, 0), name='GazeParserGazeMarker')
        if backgroundStimuli is None:
            backgroundStimuli = [psychopy.visual.Circle(self.win, radius=100, units='pix', lineWidth=1, lineColor=(0.5, 0.5, 0.5), name='GazeParserFPCircle')]

        self.startMeasurement()

        isWaitingKey = True
        while isWaitingKey:
            if responseMouseButton is not None:
                if self.getMousePressed()[responseMouseButton] == 1:
                    isWaitingKey = False
                    eyepos = self.getEyePosition(ma=ma, units=units)
                    break
            keys = self.getKeys()
            for key in keys:
                if key == responseKey:
                    isWaitingKey = False
                    eyepos = self.getEyePosition(ma=ma, units=units)
                    break
                if key == toggleMarkerKey:
                    isMarkerVisible = not isMarkerVisible
                if key == toggleBackgroundKey:
                    isBackgroundVisible = not isBackgroundVisible
            if isMarkerVisible:
                eyepos = self.getEyePosition(ma=ma, units=units)
                if len(eyepos) == 2:  # monocular
                    if eyepos[0] is not None:
                        gazeMarker.setPos(self.convertToPix(eyepos, units), log=False)
                else:  # binocular
                    if (eyepos[0] is not None) and (eyepos[1] is not None):
                        gazeMarker.setPos(self.convertToPix(((eyepos[0]+eyepos[2])/2.0, (eyepos[1]+eyepos[3])/2.0), units), log=False)

            # update screen
            if isBackgroundVisible:
                for s in backgroundStimuli:
                    s.draw()
            if hasattr(self.caltarget, '__iter__'):
                for s in self.caltarget:
                    s.draw()
            else:
                self.caltarget.draw()
            if doDrawMessage:
                self.msgtext.draw()
            if isMarkerVisible:
                gazeMarker.draw()
            self.win.flip()

        self.stopMeasurement()

        eyepos = self.convertFromPix(eyepos, units)

        if len(eyepos) == 2:  # monocular
            if eyepos[0] is None:
                error = None
            else:
                error = numpy.linalg.norm((eyepos[0]-position[0], eyepos[1]-position[1]))
            retval = (error, eyepos)

        else:  # binocular
            if eyepos[0] is None:
                errorL = None
            else:
                errorL = numpy.linalg.norm((eyepos[0]-position[0], eyepos[1]-position[1]))
            if eyepos[2] is None:
                errorR = None
            else:
                errorR = numpy.linalg.norm((eyepos[2]-position[0], eyepos[3]-position[1]))

            if (errorL is not None) and (errorR is not None):
                error = (errorL+errorR)/2.0

            retval = (error, errorL, errorR, eyepos)

        return retval

    def convertToPix(self, pos, units, forceToInt=False):
        """
        Convert units of parameters to 'pix'.  This method is called by
        setCalibrationTargetPositions, getEyePosition and getSpatialError.

        *Usually, you don't need use this method.*

        :param sequence pos:
            Sequence of positions. odd and even elements correspond to
            X and Y components, respectively.  For example, if two points
            (x1, y1) and (x2, y2) should be passed as (x1, y1, x2, y2).
            Sequence of points (i.e, ((x1, y1), (x2, y2))) is not supported.
        :param str units:
            'norm', 'height', 'cm', 'deg', 'degFlat', 'degFlatPos' and 'pix'
            are accepted.
        :param bool forceToInt:
            If true, returned values are forced to integer.
            Default value is False.

        :return: converted list.
        """
        retval = []
        if units == 'norm':
            for i in range(len(pos)):
                if pos[i] is None:
                    retval.append(None)
                else:
                    if i % 2 == 0:  # X
                        retval.append(pos[i]*self.win.size[0]/2)
                    else:  # Y
                        retval.append(pos[i]*self.win.size[1]/2)
        elif units == 'height':
            for i in range(len(pos)):
                if pos[i] is None:
                    retval.append(None)
                else:
                    retval.append(pos[i]*self.win.size[1]/2)
        elif units == 'cm':
            for i in range(len(pos)):
                if pos[i] is None:
                    retval.append(None)
                else:
                    retval.append(cm2pix(pos[i], self.win.monitor))
        elif units == 'deg':
            for i in range(len(pos)):
                if pos[i] is None:
                    retval.append(None)
                else:
                    retval.append(deg2pix(pos[i], self.win.monitor))
        elif units in ['degFlat', 'degFlatPos']:
            if len(pos)%2 == 0:
                for i in range(int(len(pos)/2)):
                    if pos[2*i] is None:
                        retval.extend([None, None])
                    else:
                        retval.extend(deg2pix(pos[2*i:2*i+2], self.win.monitor,
                            correctFlat=True))
            else:
                raise ValueError('Number of elements must be even.')
        elif units == 'pix':
            retval = list(pos)
        else:
            raise ValueError('units must bet norm, height, cm, deg, degFlat, degFlatPos or pix.')

        if forceToInt:
            for i in range(len(retval)):
                if retval[i] is not None:
                    retval[i] = int(retval[i])

        return retval

    def convertFromPix(self, pos, units):
        """
        Convert units of parameters from 'pix'.  This method is called by
        setCalibrationTargetPositions, getEyePosition and getSpatialError.

        *Usually, you don't need use this method.*

        :param sequence pos:
            Sequence of positions. odd and even elements correspond to
            X and Y components, respectively.  For example, if two points
            (x1, y1) and (x2, y2) should be passed as (x1, y1, x2, y2).
            Sequence of points (i.e, ((x1, y1), (x2, y2))) is not supported.
        :param str units:
            'norm', 'height', 'cm', 'deg', 'degFlat', 'degFlatPos' and 'pix'
            are accepted.

        :return: converted list.
        """
        retval = []
        if units == 'norm':
            for i in range(len(pos)):
                if pos[i] is None:
                    retval.append(None)
                else:
                    if i % 2 == 0:  # X
                        retval.append(pos[i]/float(self.win.size[0]/2))
                    else:  # Y
                        retval.append(pos[i]/float(self.win.size[1]/2))
        elif units == 'height':
            for i in range(len(pos)):
                if pos[i] is None:
                    retval.append(None)
                else:
                    retval.append(pos[i]/float(self.win.size[1]/2))
        elif units == 'cm':
            for i in range(len(pos)):
                if pos[i] is None:
                    retval.append(None)
                else:
                    retval.append(pix2cm(pos[i], self.win.monitor))
        elif units == 'deg':
            for i in range(len(pos)):
                if pos[i] is None:
                    retval.append(None)
                else:
                    retval.append(pix2deg(pos[i], self.win.monitor))
        elif units in ['degFlat', 'degFlatPos']:
            if len(pos)%2 == 0:
                for i in range(int(len(pos)/2)):
                    if pos[2*i] is None:
                        retval.extend([None, None])
                    else:
                        retval.extend(pix2deg(numpy.array(pos[2*i:2*i+2]),
                            self.win.monitor, correctFlat=True))
            else:
                raise ValueError('Number of elements must be even.')
        elif units == 'pix':
            retval = list(pos)
        else:
            raise ValueError('units must bet norm, height, cm, deg, degFlat, degFlatPos or pix.')

        return retval

    def getMousePressed(self):
        """
        Get mouse button status.

        *Usually, you don't need use this method.*

        """
        return self.mouse.getPressed()

    def setCalibrationTargetStimulus(self, stim):
        """
        Set calibration target.

        :param stim: Stimulus object such as circle, rectangle, and so on.
            A list of stimulus objects is also accepted.  If a list of stimulus
            object is provided, the order of stimulus object corresponds to
            the order of drawing.
        """

        self.caltarget = stim

    # Override
    def updateCalibrationTargetStimulusCallBack(self, t, index, targetPosition, currentPosition):
        """
        This method is called every time before updating calibration screen.
        In default, This method does nothing.  If you want to update calibration
        target during calibration, override this method.

        Following parameters defined in the configuration file determine
        target motion and acquisition of calibration samples.

        * CALTARGET_MOTION_DURATION
        * CALTARGET_DURATION_PER_POS
        * CAL_GETSAMPLE_DELAY

        These parameters can be overwrited by using
        :func:`~GazeParser.TrackingTools.BaseController.setCalibrationTargetMotionParameters`
        and
        :func:`~GazeParser.TrackingTools.BaseController.setCalibrationSampleAcquisitionParameters`.

        :param float t: time spent for current target position. The range of t is
            0<=t<CALTARGET_DURATION_PER_POS.  When 0<=t<CALTARGET_MOTION_DURATION,
            the calibration target is moving to the current position.  When
            CALTARGET_MOTION_DURATION<=t<CALTARGET_DURATION_PER_POS, the calibration
            target stays on the current position. Acquisition of calibration samples
            starts when (CALTARGET_MOTION_DURATION+CAL_GETSAMPLE_DELAY)<t.
        :param index: This value represents the order of current target position.
            This value is 0 before calibration is initiated by space key press.
            If the target is moving to or stays on 5th position, this value is 5.
        :param targetPosition: A tuple of two values.  The target is moving to or
            stays on the position indicated by this parameter.
        :param currentPosition: A tuple of two values that represents current
            calibration target position.  This parameter is equal to targetPosition
            when CALTARGET_MOTION_DURATION<=t.

        This is an example of using this method.
        Suppose that parameters are defined as following.

        * CALTARGET_MOTION_DURATION = 1.0
        * CALTARGET_DURATION_PER_POS = 2.0

        ::

            tracker = GazeParser.TrackingTools.getController(backend='PsychoPy')
            calstim = [psychopy.visual.Rect(win, width=4, height=4, units='pix'),
                       psychopy.visual.Rect(win, width=2, height=2, units='pix')]
            tracker.setCalibrationTargetStimulus(calstim)

            def callback(self, t, index, targetPos, currentPos):
                if t<1.0:
                    self.caltarget[0].setSize(((10-9*t)*4,(10-9*t)*4))
                else:
                    self.caltarget[0].setSize((4,4))

            type(tracker).updateCalibrationTargetStimulusCallBack = callback
        """
        
        t1 = self.CALTARGET_MOTION_DURATION+self.CAL_GETSAMPLE_DELAY
        t2 = t1 + max(self.NUM_SAMPLES_PER_TRGPOS / self.CAMERA_SAMPLING_RATE, 1.0/60*2)
        
        if index != 0 and (t1 < t < t2):
            self.caltarget[0].opacity = 0.0
            self.caltarget[1].opacity = 1.0
        else:
            self.caltarget[0].opacity = 1.0
            self.caltarget[1].opacity = 0.0
        
        return
    
    # Override
    def updateManualCalibrationTargetStimulusCallBack(self, t, currentPosition, prevPosition):
        """
        This method is called every time before updating calibration screen.
        In default, This method set "currentPos" parameter to caliration 
        target position.  If the first element of currentPos is None, 
        calibration target position is set to (100*screen width, 100*
        screen height) not to display calibration target.
        
        If you want to modify this behavior, override this method.

        :param float t: time spent for current target position.
        :param currentPosition: A tuple of two values that represents
            current calibration target position. This value is
            (None, None) if calibration target is not presented
            now.
        :param prevPosition: A tuple of two values that represents
            previous calibration target position. This value is
            (None, None) if calibration target was not presented
            previously.

        This is an example of using this method.

        ::

            tracker = GazeParser.TrackingTools.getController(backend='PsychoPy')
            calstim = [psychopy.visual.Rect(win, width=4, height=4, units='pix'),
                       psychopy.visual.Rect(win, width=2, height=2, units='pix')]
            tracker.setCalibrationTargetStimulus(calstim)

            def callback(self, t, targetPos, prevPos):
                self.calTargetPosition = currentPosition

                if t<1.0:
                    self.caltarget[0].setSize(((10-9*t)*4,(10-9*t)*4))
                else:
                    self.caltarget[0].setSize((4,4))

            type(tracker).updateManualCalibrationTargetStimulusCallBack = callback
        """

        if currentPosition[0] is None:
            self.calTargetPosition = (self.screenWidth*100, self.screenHeight*100)
        else:
            self.calTargetPosition = currentPosition
        
        t1 = self.CALTARGET_MOTION_DURATION+self.CAL_GETSAMPLE_DELAY
        t2 = t1 + max(self.NUM_SAMPLES_PER_TRGPOS / self.CAMERA_SAMPLING_RATE, 1.0/60*2) # flash at reast 2 frames (@60fps)
        
        if index != 0 and (t1 < t < t2):
            self.caltarget[0].visible=True
            self.caltarget[1].visible=False
        else:
            self.caltarget[1].visible=True
            self.caltarget[0].visible=False
        
        return

    # Override
    def verifyFixation(self, maxTry, permissibleError, key='space', mouseButton=None, message=None, position=None,
                       gazeMarker=None, backgroundStimuli=None, toggleMarkerKey='m', toggleBackgroundKey='m',
                       showMarker=False, showBackground=False, ma=1, units='pix'):
        """
        Verify spatial error of measurement. If spatial error is larger than a
        given amount, calibration loop is automatically called and velification
        is performed again.

        :param int maxTry:
            Specify how many times error is measured before prompting
            readjustment.
        :param float permissibleError:
            Permissible error. Unit of the value is deg.
        :param key:
            Specify a key to get participant's response.
            Default value is 'space'.
        :param mouseButton:
            Specify a mouse button to get participant's response.
            If None, mouse button is ignored. Default value is None.
            See also :func:`~GazeParser.TrackingTools.BaseController.getSpatialError`.
        :param message:
            A sequence of three sentences. The first sentence is presented
            when this method is called. The second sentence is presented
            when error is larger than permissibleError. The third sentence
            is presented when prompting readjustment.
            Default value is a list of following sentences.

            - 'Please fixate on a square and press space key.'
            - 'Please fixate on a square and press space key again.'
            - 'Gaze position could not be detected. Please call experimenter.'
        :param position:
            Specify position of the target. If None, the center of the screen is used.
            Default value is None.
        :param gazeMarker:
            Specify a stimulus which is presented on the current gaze position.
            If None, default marker is used.
            Default value is None.
        :param backgroundStimuli:
            Specify a list of stimuli which are presented as background stimuli.
            If None, a gray circle is presented as background.
            Default value is None.
        :param str toggleMarkerKey:
            Specify name of a key to toggle visibility of gaze marker.
            Default value is 'm'.
        :param str toggleBackgroundKey:
            Specify name of a key to toggle visibility of background stimuli.
            Default value is 'm'.
        :param bool showMarker:
            If True, gaze marker is visible when getSpatialError is called.
            Default value is False.
        :param bool showBackground:
            If True, gaze marker is visible when getSpatialError is called.
            Default value is False.
        :param int ma:
            If this value is 1, the latest position is used. If more than 1,
            moving average of the latest N samples is used (N is equal to
            the value of this parameter). Default value is 1.
        :param str units: units of 'area' and 'calposlist'.  'norm', 'height',
            'deg', 'cm' and 'pix' are accepted.  Default value is 'pix'.

        :return:
            If calibration is terminated by 'q' key, 'q' is returned.
            Otherwise, spatial error is returned.
            see :func:`~GazeParser.TrackingTools.BaseController.getSpatialError`
            for detail of the spatial error.
        """
        if message is None:
            message = ['Please fixate on a square and press space key.',
                       'Please fixate on a square and press space key again.',
                       'Gaze position could not be detected. Please call experimenter.']

        if backgroundStimuli is None:
            if position is None:
                position = self.screenCenter
            backgroundStimuli = [psychopy.visual.Circle(self.win, radius=permissibleError, units=units, lineWidth=1, lineColor=(0.5, 0.5, 0.5), name='GazeParserFPCircle')]

        numTry = 0
        error = self.getSpatialError(message=message[0], responseKey=key, responseMouseButton=mouseButton, position=None,
                                     gazeMarker=gazeMarker, backgroundStimuli=backgroundStimuli,
                                     toggleMarkerKey=toggleMarkerKey, toggleBackgroundKey=toggleBackgroundKey,
                                     showMarker=showMarker, showBackground=showBackground, ma=ma, units=units)
        if (error[0] is not None) and error[0] < permissibleError:
            time.sleep(0.5)
            return error

        numTry += 1
        while True:
            error = self.getSpatialError(message=message[1], responseKey=key, responseMouseButton=mouseButton, position=None,
                                         gazeMarker=gazeMarker, backgroundStimuli=backgroundStimuli,
                                         toggleMarkerKey=toggleMarkerKey, toggleBackgroundKey=toggleBackgroundKey,
                                         showMarker=showMarker, showBackground=showBackground, ma=ma, units=units)

            if (error[0] is not None) and error[0] < permissibleError:
                time.sleep(0.5)
                return error
            else:
                time.sleep(0.5)
                numTry += 1
                if numTry == maxTry:  # recalibration
                    # spatial error is unnecessary, but this is an easy way to show message and wait keypress.
                    error = self.getSpatialError(message=message[2], responseKey=key, responseMouseButton=mouseButton, position=None,
                                                 gazeMarker=gazeMarker, backgroundStimuli=backgroundStimuli,
                                                 toggleMarkerKey=toggleMarkerKey, toggleBackgroundKey=toggleBackgroundKey,
                                                 showMarker=showMarker, showBackground=showBackground, ma=ma, units=units)
                    self.removeCalibrationResults()
                    while True:
                        res = self.calibrationLoop()
                        if res == 'q':
                            return 'q'
                        if self.isCalibrationFinished():
                            break
                    time.sleep(0.5)
                    numTry = 0

        time.sleep(0.5)

    # Override
    def setCurrentScreenParamsToConfig(self, config, screenSize=None, distance=None):
        """
        Set current screen parameters to GazeParser.Configuration.Config object.
        Following parameters will be updated.
        
        * SCREEN_ORIGIN
        * TRACKER_ORIGIN
        * SCREEN_WIDTH
        * SCREEN_HEIGHT
        * DOTS_PER_CENTIMETER_H
        * DOTS_PER_CENTIMETER_V
        * VIEWING_DISTANCE
        

        :param GazeParser.Configuration.Config config: instance of 
            GazeParser.Configuration.Config config object.
        :param sequence screenSize: Size (width, height) of screen in 
            **centimeters**. If None, PsychoPy's monitor settings are 
            used.
        :param float distance:  Viewing distance in **centimeter**.
            If None, PsychoPy's monitor settings are used.
        :return:
            Updated configuration object.
        """
        
        try:
            (w, h) = self.win.size
        except:
            raise ValueError('Screen size is not available. Call setCalibrationScreen() first.')
        
        if distance is None:
            d = self.win.monitor.getDistance()
            if d is None:
                raise ValueError('Distance is not available in the current PsychoPy MonitorInfo.')
        else:
            try:
                d = float(distance)
            except:
                raise ValueError('Distance must be a real number.')
            
        if screenSize is None:
            dpcH = dpcV = cm2pix(1.0, self.win.monitor)
            if dpcH is None:
                raise ValueError('Requisite parameters are not available in the current PsychoPy MonitorInfo.')
        else:
            try:
                sw = float(screenSize[0])
                sh = float(screenSize[1])
            except:
                raise ValueError('Screen width and height must be real numbers.')

            dpcH = w/sw
            dpcV = h/sh
        
        config.SCREEN_ORIGIN = 'Center'
        config.TRACKER_ORIGIN = 'Center'
        config.SCREEN_WIDTH = w
        config.SCREEN_HEIGHT = h
        config.VIEWING_DISTANCE = d
        config.DOTS_PER_CENTIMETER_H = dpcH
        config.DOTS_PER_CENTIMETER_V = dpcV
        
        return config


