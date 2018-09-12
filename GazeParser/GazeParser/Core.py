"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import GazeParser
import numpy
import re
import sys
import locale

float_tolerance = 0.000000000001

class SaccadeData(object):
    """
    Holds various parameters of a single saccade such as start time,
    end time, amplitude and so on.
    """

    def __init__(self, t, d, Tlist):
        """
        :param t: Timestamp (start, endTime).
        :param d: Tuple of 6 elements (Startpoint X, Y, Endpoint X, Y,
                  amplitude, length).
        :param Tlist: List of TimeStamps.
        """

        self._startTime = t[0]
        self._endTime = t[1]
        self._duration = d[0]
        self._start = numpy.array((d[1], d[2]))
        self._end = numpy.array((d[3], d[4]))
        self._amplitude = d[5]
        self._length = numpy.sqrt((d[3] - d[1]) ** 2 + (d[4] - d[2]) ** 2)
        self._direction = numpy.arctan2(d[4] - d[2], d[3] - d[1])
        self._parent = None

        idx = numpy.where(Tlist == t[0])[0]
        if len(idx) != 1:
            raise ValueError('SaccadeData: could not find index.')
        else:
            self._startIndex = idx[0]

        idx = numpy.where(Tlist == t[1])[0]
        if len(idx) != 1:
            raise ValueError('SaccadeData: could not find index.')
        else:
            self._endIndex = idx[0]

    startTime = property(lambda self: self._startTime)
    """Saccade onset time in msec."""

    endTime = property(lambda self: self._endTime)
    """Saccade offset time in msec."""

    duration = property(lambda self: self._duration)
    """Saccade duration in msec."""

    start = property(lambda self: self._start)
    """Saccade start location in screen coordinate (x, y)."""

    end = property(lambda self: self._end)
    """Saccade end location in screen coordinate (x, y)."""

    amplitude = property(lambda self: self._amplitude)
    """Saccade length in degree."""

    length = property(lambda self: self._length)
    """Saccade length in screen coordinate."""

    direction = property(lambda self: self._direction)
    """Saccade direction in radian."""

    startIndex = property(lambda self: self._startIndex)
    """Saccade onset index in the timestamp list."""

    endIndex = property(lambda self: self._endIndex)
    """Saccade offset index in the timestamp list."""

    parent = property(lambda self: self._parent)
    """Parent GazeData object."""

    def relativeStartTime(self, time):
        """
        Saccade onset time relative to indicated time.
        Unit is msec.

        :param time:
            reference time. Unit is msec. If objects that has 'time' attribute
            (e.g. GazeParser.Core.MessageData) is passed, the value of 'time'
            attribute is used.
        """
        if hasattr(time, 'time'):
            return self.startTime - time.time
        else:
            return self.startTime - time

    def relativeEndTime(self, time):
        """
        Saccade offset time relative to indicated time.
        Unit is msec.

        :param time:
            reference time. Unit is msec. If objects that has 'time' attribute
            (e.g. GazeParser.Core.MessageData) is passed, the value of 'time'
            attribute is used.
        """
        if hasattr(time, 'time'):
            return self.endTime - time.time
        else:
            return self.endTime - time

    def _setParent(self, obj):
        if self in obj._Sac:
            self._parent = obj
        else:
            raise ValueError('Argument does not include this saccade.')

    def getTraj(self, eye=None):
        """
        Get saccade trajectory.
        If eye is 'L' or 'R', the returned value is a numpy.ndarray object.
        If 'B', the returned value is a tuple of two numpy.ndarray objects.
        The first and second element represent left and right eye's trajectory,
        respectively.

        :param str eye: 'L', 'R' or 'B'.  If none, recorded eye is used.
        """
        if eye is None:
            eye = self._parent._recordedEye

        s = self.startIndex
        e = self.endIndex
        if eye == 'L':
            return self._parent.L[s:e+1]
        elif eye == 'R':
            return self._parent.R[s:e+1]
        elif eye == 'B':
            return (self._parent.L[s:e+1], self._parent.R[s:e+1])
        else:
            raise ValueError('Eye must be \'L\', \'R\', \'B\' or None.')

    def getNextEvent(self, step=1, eventType=None):
        return self._parent.getNextEvent(self, step=step, eventType=eventType)

    def getPreviousEvent(self, step=1, eventType=None):
        return self._parent.getPreviousEvent(self, step=step, eventType=eventType)
    
    def __eq__(self, other):
        if not isinstance(other, SaccadeData):
            return False
        for attr in ('startTime', 'endTime', 'duration', 'amplitude', 'length'):
            if getattr(self, attr) != getattr(other, attr):
                return False
        for attr in ('direction',):
            # return value of arctan2() may be different between 32bit and 64bit Python.
            if getattr(self, attr) - getattr(other, attr) > float_tolerance:
                return False
        for attr in ('start', 'end'):
            if (getattr(self, attr) != getattr(other, attr)).any():
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)
        
        msg += '{:.3f}s, [ {} {}], {:.1f}, {:.1f}>'.format(
            self.startTime/1000.0, self.start[0], self.start[1],
            numpy.rad2deg(self.direction), self.length)
        
        return msg


class FixationData(object):
    """
    Holds various parameters of a single fixation such as start time,
    end time and so on.
    """

    def __init__(self, t, d, Tlist):
        """
        :param t: Timestamp (start, endTime)
        :param d: Tuple of 3 elements. (duration, center location X, Y)
        :param Tlist: List of TimeStamps.
        """
        self._startTime = t[0]
        self._endTime = t[1]
        self._duration = d[0]
        self._center = numpy.array((d[1], d[2]))
        self._parent = None

        idx = numpy.where(Tlist == t[0])[0]
        if len(idx) != 1:
            raise ValueError('FixationData: could not find index.')
        else:
            self._startIndex = idx[0]

        idx = numpy.where(Tlist == t[1])[0]
        if len(idx) != 1:
            raise ValueError('FixationData: could not find index.')
        else:
            self._endIndex = idx[0]

    startTime = property(lambda self: self._startTime)
    """Fixation onset time in msec."""

    endTime = property(lambda self: self._endTime)
    """Fixation offset time in msec."""

    duration = property(lambda self: self._duration)
    """Fixation duration in msec."""

    center = property(lambda self: self._center)
    """
    Fixation center in screen coordinate (x, y).
    'Fixation center' means an average of whole gaze
    trajectory during fixation.
    """

    startIndex = property(lambda self: self._startIndex)
    """Fixation onset index in the timestamp list."""

    endIndex = property(lambda self: self._endIndex)
    """Fixation offset index in the timestamp list."""

    parent = property(lambda self: self._parent)
    """Parent GazeData object."""

    def relativeStartTime(self, time):
        """
        Fixation onset time relative to indicated time.
        Unit is msec.

        :param time:
            reference time. Unit is msec. If objects that has 'time' attribute
            (e.g. GazeParser.Core.MessageData) is passed, the value of 'time'
            attribute is used.
        """
        if hasattr(time, 'time'):
            return self.startTime - time.time
        else:
            return self.startTime - time

    def relativeEndTime(self, time):
        """
        Fixation offset time relative to indicated time.
        Unit is msec.

        :param time:
            reference time. Unit is msec. If objects that has 'time' attribute
            (e.g. GazeParser.Core.MessageData) is passed, the value of 'time'
            attribute is used.
        """
        if hasattr(time, 'time'):
            return self.endTime - time.time
        else:
            return self.endTime - time

    def _setParent(self, obj):
        if self in obj._Fix:
            self._parent = obj
        else:
            raise ValueError('Argument does not include this fixation.')

    def getTraj(self, eye=None):
        """
        Get fixation trajectory.
        If eye is 'L' or 'R', the returned value is a numpy.ndarray object.
        If 'B', the returned value is a tuple of two numpy.ndarray objects.
        The first and second element represent left and right eye's trajectory,
        respectively.

        :param str eye: 'L', 'R' or 'B'.  If none, recorded eye is used.
        """
        if eye is None:
            eye = self._parent._recordedEye

        s = self.startIndex
        e = self.endIndex
        if eye == 'L':
            return self._parent.L[s:e+1]
        elif eye == 'R':
            return self._parent.R[s:e+1]
        elif eye == 'B':
            return (self._parent.L[s:e+1], self._parent.R[s:e+1])

    def getNextEvent(self, step=1, eventType=None):
        return self._parent.getNextEvent(self, step=step, eventType=eventType)

    def getPreviousEvent(self, step=1, eventType=None):
        return self._parent.getPreviousEvent(self, step=step, eventType=eventType)

    def __eq__(self, other):
        if not isinstance(other, FixationData):
            return False
        for attr in ('startTime', 'endTime', 'duration'):
            if getattr(self, attr) != getattr(other, attr):
                return False
        for attr in ('center', ):
            if (getattr(self, attr) != getattr(other, attr)).any():
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)
        
        msg += '{:.3f}s, {:.1f}ms, [ {:.1f} {:.1f}]>'.format(self.startTime/1000.0, self.duration, self.center[0], self.center[1])
        
        return msg


class MessageData(object):
    """
    Holds a message received during recording.
    """
    def __init__(self, m):
        """
        :param m:
            A tuple of 2 elements. The 1st element is timestamp (in msec).
            The 2nd element is received text.
        """
        self._time = m[0]
        self._text = m[1]
        self._parent = None

    time = property(lambda self: self._time)
    """Time when message was recorded."""

    text = property(lambda self: self._text)
    """Message text."""

    parent = property(lambda self: self._parent)
    """Parent GazeData object."""

    def _setParent(self, obj):
        if self in obj._Msg:
            self._parent = obj
        else:
            raise ValueError('Argument does not include this message.')

    def getNextEvent(self, step=1, eventType=None):
        return self._parent.getNextEvent(self, step=step, eventType=eventType)

    def getPreviousEvent(self, step=1, eventType=None):
        return self._parent.getPreviousEvent(self, step=step, eventType=eventType)

    def delete(self):
        self._parent.deleteMessage(self)

    def updateMessage(self, newTime=None, newText=None):
        """
        Update message time and/or text.

        :param newTime:
            New timestamp. If None, timestamp is not updated.
        :param newText:
            New text. If None, text is not updated.
        """
        if newText is not None:
            self._text = newText
        if newTime is not None:
            self._time = newTime

        if self._parent is not None:
            self._parent.sortMessagesByTime()
            self._parent.sortEventListByTime()

    def __eq__(self, other):
        if not isinstance(other, MessageData):
            return False
        for attr in ('time', 'text'):
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)

        if len(self.text) > 16:
            text = self.text[:13]+'...'
        else:
            text = self.text
        
        msg += '{:.3f}s, {}>'.format(self.time/1000.0, repr(text))
        
        return msg

    def __str__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)

        if len(self.text) > 16:
            text = self.text[:13]+'...'
        else:
            text = self.text
        
        if sys.version_info[0] == 2:
            msg += '{:.3f}s, {}>'.format(self.time/1000.0, text.encode(locale.getpreferredencoding()))
        else:
            msg += '{:.3f}s, {}>'.format(self.time/1000.0, text)
        
        return msg


class BlinkData(object):
    """
    Holds start time, end time and duraton of a blink.
    """
    def __init__(self, t, d, Tlist):
        """
        :param sequence t: TimeStamp (start, endTime)
        :param float d:  duration of blink (msec)
        :param sequence Tlist: List of timestamps.
        """
        self._startTime = t[0]
        self._endTime = t[1]
        self._duration = d
        self._parent = None
        idx = numpy.where(Tlist == t[0])[0]
        if len(idx) != 1:
            raise ValueError('BlinkData: could not find index.')
        else:
            self._startIndex = idx[0]

        idx = numpy.where(Tlist == t[1])[0]
        if len(idx) != 1:
            raise ValueError('BlinkData: could not find index.')
        else:
            self._endIndex = idx[0]

    startTime = property(lambda self: self._startTime)
    """Blink onset time in msec."""

    endTime = property(lambda self: self._endTime)
    """Blink offset time in msec."""

    duration = property(lambda self: self._duration)
    """Blink duration in msec."""

    startIndex = property(lambda self: self._startIndex)
    """Blink onset index in the timestamp list."""

    endIndex = property(lambda self: self._endIndex)
    """Blink offset index in the timestamp list."""

    parent = property(lambda self: self._parent)
    """Parent GazeData object."""

    def relativeStartTime(self, time):
        """
        Blink onset time relative to indicated time.
        Unit is msec.

        :param time:
            reference time. Unit is msec. If objects that has 'time' attribute
            (e.g. GazeParser.Core.MessageData) is passed, the value of 'time'
            attribute is used.
        """
        if hasattr(time, 'time'):
            return self.startTime - time.time
        else:
            return self.startTime - time

    def relativeEndTime(self, time):
        """
        Blink offset time relative to indicated time.
        Unit is msec.

        :param time:
            reference time. Unit is msec. If objects that has 'time' attribute
            (e.g. GazeParser.Core.MessageData) is passed, the value of 'time'
            attribute is used.
        """
        if hasattr(time, 'time'):
            return self.endTime - time.time
        else:
            return self.endTime - time

    def _setParent(self, obj):
        if self in obj._Blink:
            self._parent = obj
        else:
            raise ValueError('Argument does not include this blink.')

    def getNextEvent(self, step=1, eventType=None):
        return self._parent.getNextEvent(self, step=step, eventType=eventType)

    def getPreviousEvent(self, step=1, eventType=None):
        return self._parent.getPreviousEvent(self, step=step, eventType=eventType)

    def __eq__(self, other):
        if not isinstance(other, BlinkData):
            return False
        for attr in ('startTime', 'endTime', 'duration'):
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)
        
        msg += '{:.3f}s, {:.1f}ms>'.format(self.startTime/1000.0, self.duration)
        
        return msg


class CalPointData(object):
    """
    Holds accuracy and precision at calibration points.
    """
    def __init__(self, point, accuracy, precision, recordedEye):
        self._point = numpy.array(point)
        self._accuracy = numpy.array(accuracy)
        self._precision = numpy.array(precision)
        self._recordedEye = recordedEye
    
    point = property(lambda self: self._point)
    """Location of calibration target in screen coordinate (x,y)"""
    
    accuracy = property(lambda self: self._accuracy)
    """
    Accuracy in screen coordinate (Lelt-X, Left-Y, Right-X, Right-Y).
    None if not available.
    """
    
    precision = property(lambda self: self._precision)
    """Precision in screen coordinate (Lelt-X, Left-Y, Right-X, Right-Y).
    None if not available.
    """
    
    recordedEye = property(lambda self: self._precision)
    """Precision in screen coordinate (Lelt-X, Left-Y, Right-X, Right-Y).
    None if not available.
    """
    def getAccuracy(self, eye=None):
        """
        Get accuracy. If data is binocular, 4 values (LX, LY, RX, RY) are 
        returned.  If monocular, 2 values (X, Y) are returned. If the value
        is numpy.NaN, no data is available at this calibration point.

        :param str eye:
            Output both-eye ('B'), left-eye ('L'), right-eye ('R') data or
            None (recorded eye). Default value is None.
        """
        if eye is None:
            eye = self._recordedEye
        
        if eye=='L':
            return self._accuracy[0:2]
        elif eye=='R':
            return self._accuracy[2:4]
        else: # B
            return self._accuracy[0:4]    

    def getPrecision(self, eye=None):
        """
        Get precision. If data is binocular, 4 values (LX, LY, RX, RY) are 
        returned.  If monocular, 2 values (X, Y) are returned. If the value
        is numpy.NaN, no data is available at this calibration point.

        :param str eye:
            Output both-eye ('B'), left-eye ('L'), right-eye ('R') data or
            None (recorded eye). Default value is None.
        """
        if eye is None:
            eye = self._recordedEye
        
        if eye=='L':
            return self._precision[0:2]
        elif eye=='R':
            return self._precision[2:4]
        else: # B
            return self._precision[0:4]

    def __eq__(self, other):
        if not isinstance(other, MessageData):
            return False
        for attr in ('recordedEye', ):
            if getattr(self, attr) != getattr(other, attr):
                return False
        for attr in ('point', 'accuracy', 'precision'):
            if (getattr(self, attr) != getattr(other, attr)).any():
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)
        
        msg += '{accuracy:.3f}, {precision:.3f}>'.format(self.accuracy, self.precision)
        
        return msg


class GazeData(object):
    """
    Holds saccades, fixations, blinks, messages, timestamps and gaze
    trajectory in a single recording.
    """
    def __init__(self, Tlist, Llist, Rlist, SacList, FixList, MsgList, BlinkList, PupilList, recordedEye, config=None, recordingDate=None):
        """
        Constructor GazeData.
        """
        self.__version__ = GazeParser.__version__
        self._nSac = len(SacList)
        self._nFix = len(FixList)
        self._nMsg = len(MsgList)
        self._nBlink = len(BlinkList)
        if Llist is None:
            self._L = None
        else:
            self._L = numpy.array(Llist)
        if Rlist is None:
            self._R = None
        else:
            self._R = numpy.array(Rlist)
        self._T = numpy.array(Tlist)
        self._Sac = numpy.array(SacList)
        self._Fix = numpy.array(FixList)
        self._Msg = numpy.array(MsgList)
        self._Blink = numpy.array(BlinkList)
        self._recordedEye = recordedEye
        self._Pupil = PupilList
        self._CameraSpecificData = None
        self._USBIOChannels = None
        self._USBIOData = None
        self._CalPointData = None
        self._recordingDate = recordingDate

        self._EventList = self._getEventListByTime(self.T[0], self.T[-1])[0]
        for s in self._Sac:
            s._setParent(self)

        for f in self._Fix:
            f._setParent(self)

        for m in self._Msg:
            m._setParent(self)

        for b in self._Blink:
            b._setParent(self)

        if not isinstance(config, GazeParser.Configuration.Config):
            self._config = GazeParser.Configuration.Config()
        else:
            self._config = config

        cm2deg = 180 / numpy.pi * numpy.arctan(1.0 / self._config.VIEWING_DISTANCE)
        self._deg2pix = numpy.array((self._config.DOTS_PER_CENTIMETER_H / cm2deg,
                                     self._config.DOTS_PER_CENTIMETER_V / cm2deg))
        self._pix2deg = 1.0 / self._deg2pix

    def getFixTraj(self, index, eye=None):
        """
        Get gaze trajectory during a fixation.

        :param integer index:
            Index of fixation.  Give n-1 to get gaze trajectory during
            n-th fixation.
        :param str eye:
            Output both-eye ('B'), left-eye ('L'), right-eye ('R') data or
            None (recorded eye). Default value is None.
        """
        if eye is None:
            eye = self._parent._recordedEye

        if not (0 <= index < self.nFix):
            raise ValueError('Index is out of range.')
        s = self._Fix[index]._startIndex
        e = self._Fix[index]._endIndex

        if eye == 'L':
            return self._L[s:e+1]
        elif eye == 'R':
            return self._R[s:e+1]
        elif eye == 'B':
            return (self._L[s:e+1], self._R[s:e+1])
        else:
            raise ValueError('Eye must be \'L\', \'R\', \'B\' or None.')

    def getFixDur(self, index=None):
        """
        Get duration of fixations in milliseconds.

        :param index:
            An index or a list of indices of fixation(s).
            Give n-1 to get duration of n-th fixation.
            If None, all fixations are included.
            Default value is None.

        :return:
            If an integer is passed, a float value is returned.
            Otherwise, an *n x 1* numpy.ndarray object is returned.
        """
        if index is None:
            l = numpy.zeros([self.nFix, 1])
            for i in range(self.nFix):
                l[i] = self.Fix[i].duration
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nFix):
                raise ValueError('Index is out of range.')
            return self.Fix[index].duration
        else:  # list
            l = numpy.zeros([len(index), 1])
            for i in range(len(index)):
                l[i] = self.Fix[index[i]].duration
            return l

    def getFixCenter(self, index=None):
        """
        Get the center of fixations in screen coordinate.

        :param index:
            An index or a list of indices of fixation(s).
            Give n-1 to get the center of n-th fixation.
            If None, all fixations are included.
            Default value is None.

        :return:
            If an integer is passed, horizontal and vertical position
            of the fixation center is returned.
            Otherwise, an *n x 2* numpy.ndarray object is returned.
        """
        if index is None:
            l = numpy.zeros([self.nFix, 2])
            for i in range(self.nFix):
                l[i, :] = self.Fix[i].center
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nFix):
                raise ValueError('Index is out of range.')
            return self.Fix[index].center
        else:
            l = numpy.zeros([len(index), 2])
            for i in range(len(index)):
                l[i, :] = self.Fix[index[i]].center
            return l

    def getFixTime(self, index=None):
        """
        Get the start and end time of fixations.

        :param index:
            An index or a list of indices of fixation(s).
            Give n-1 to get the starting and finish time of n-th fixation.
            If None, all fixations are included.
            Default value is None.

        :return:
            If an integer is passed, starting and finish time of the fixation
            is returned. Otherwise, an *n x 2* numpy.ndarray object is
            returned.
        """
        if index is None:
            l = numpy.zeros([self.nFix, 2])
            for i in range(self.nFix):
                l[i, :] = [self.Fix[i].startTime, self.Fix[i].endTime]
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nFix):
                raise ValueError('Index is out of range.')
            return (self.Fix[index].startTime, self.Fix[index].endTime)
        else:
            l = numpy.zeros([len(index), 2])
            for i in range(len(index)):
                l[i, :] = [self.Fix[index[i]].startTime, self.Fix[index[i]].endTime]
            return l

    def getBlinkTime(self, index=None):
        """
        Get the start and end time of blinks.

        :param index:
            An index or a list of indices of blink(s).
            Give n-1 to get the start and end time of n-th blink.
            If None, all fixations are included.
            Default value is None.

        :return:
            If an integer is passed, starting and finish time of the blink
            is returned. Otherwise, an *n x 2* numpy.ndarray object is
            returned.
        """
        if index is None:
            l = numpy.zeros([self.nBlink, 2])
            for i in range(self.nBlink):
                l[i, :] = [self.Blink[i].startTime, self.Blink[i].endTime]
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nBlink):
                raise ValueError('Index is out of range.')
            return (self.Blink[index].startTime, self.Blink[index].endTime)
        else:
            l = numpy.zeros([len(index), 2])
            for i in range(len(index)):
                l[i, :] = [self.Blink[index[i]].startTime, self.Blink[index[i]].endTime]
            return l

    def getMsgTime(self, index=None):
        """
        Get the recorded time of messages.

        :param index:
            An index or a list of indices of message(s).
            Give n-1 to get timestamp of n-th message.
            If None, all messages are included.
            Default value is None.

        :return:
            If an integer is passed, a float value is returned.
            Otherwise, an *n x 1* numpy.ndarray object is returned.
        """
        if index is None:
            l = numpy.zeros([self.nMsg, 1])
            for i in range(self.nMsg):
                l[i] = self.Msg[i].time
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nMsg):
                raise ValueError('Index is out of range.')
            return self.Msg[index].time
        else:
            l = numpy.zeros([len(index), 1])
            for i in range(len(index)):
                l[i] = self.Msg[index[i]].time
            return l

    def getSacTraj(self, index, eye=None):
        """
        Get gaze trajectory during a saccade.

        :param integer index:
            Index of saccade.  Give n-1 to get gaze trajectory during n-th
            saccade.
        :param str eye:
            Output both-eye ('B'), left-eye ('L'), right-eye ('R') data or
            None (recorded eye). Default value is None.
        """
        if not (0 <= index < self.nSac):
            raise ValueError('Index is out of range.')

        if eye is None:
            eye = self._recordedEye

        s = self._Sac[index]._startIndex
        e = self._Sac[index]._endIndex
        if eye == 'L':
            return self._L[s:e+1]
        elif eye == 'R':
            return self._R[s:e+1]
        elif eye == 'B':
            return (self._L[s:e+1], self._R[s:e+1])
        else:
            raise ValueError('Eye must be \'L\', \'R\', \'B\' or None.')

    def getSacLen(self, index=None):
        """
        Get saccade length.

        :param index:
            An index or a list of indices of saccade(s).
            Give n-1 to get length of n-th saccade.
            If None, all saccades are included.
            Default value is None.

        :return:
            If an integer is passed, a float value is returned.
            Otherwise, an *n x 1* numpy.ndarray object is returned.
        """
        if index is None:
            l = numpy.zeros([self.nSac, 1])
            for i in range(self.nSac):
                l[i] = self.Sac[i].length
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nSac):
                raise ValueError('Index is out of range.')
            return self.Sac[index].length
        else:
            l = numpy.zeros([len(index), 1])
            for i in range(len(index)):
                l[i] = self.Sac[index[i]].length
            return l

    def getSacAmp(self, index=None):
        """
        Get saccade amplitude.

        :param index:
            An index or a list of indices of saccade(s).
            Give n-1 to get amplitude of n-th saccade.
            If None, all saccades are included.
            Default value is None.

        :return:
            If an integer is passed, a float value is returned.
            Otherwise, an *n x 1* numpy.ndarray object is returned.
        """
        if index is None:
            l = numpy.zeros([self.nSac, 1])
            for i in range(self.nSac):
                l[i] = self.Sac[i].amplitude
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nSac):
                raise ValueError('Index is out of range.')
            return self.Sac[index].amplitude
        else:
            l = numpy.zeros([len(index), 1])
            for i in range(len(index)):
                l[i] = self.Sac[index[i]].amplitude
            return l

    def getSacDur(self, index=None):
        """
        Get duration of saccades in milliseconds.

        :param index:
            An index or a list of indices of saccade(s).
            Give n-1 to get duration of n-th saccade.
            If None, all saccades are included.
            Default value is None.

        :return:
            If an integer is passed, a float value is returned.
            Otherwise, an *n x 1* numpy.ndarray object is returned.
        """
        if index is None:
            l = numpy.zeros([self.nSac, 1])
            for i in range(self.nSac):
                l[i] = self.Sac[i].duration
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nSac):
                raise ValueError('Index is out of range.')
            return self.Sac[index].duration
        else:
            l = numpy.zeros([len(index), 1])
            for i in range(len(index)):
                l[i] = self.Sac[index[i]].duration
            return l

    def getSacTime(self, index=None):
        """
        Get the start and end time of saccades.

        :param index:
            An index or a list of indices of saccade(s).
            Give n-1 to get the start and end time of n-th saccade.
            If None, all saccades are included.
            Default value is None.

        :return:
            If an integer is passed, starting and finish time of the saccade
            is returned. Otherwise, an *n x 2* numpy.ndarray object is
            returned.
        """
        if index is None:
            l = numpy.zeros([self.nSac, 2])
            for i in range(self.nSac):
                l[i, :] = [self.Sac[i].startTime, self.Sac[i].endTime]
            return l
        elif isinstance(index, int):
            if not (0 <= index < self.nSac):
                raise ValueError('Index is out of range.')
            return (self.Sac[index].startTime, self.Sac[index].endTime)
        else:
            l = numpy.zeros([len(index), 2])
            for i in range(len(index)):
                l[i, :] = [self.Sac[index[i]].startTime, self.Sac[index[i]].endTime]
            return l

    def _getEventListByTime(self, fromTime, toTime):
        """
        Build a list which contains all saccades, fixations, blinks and
        messages arranged in chronological order.

        :param float fromTime:
            Events that recorded after this time are included to the list.
        :param float endTime:
            Events that recorded before this time are included to the list.
        """
        st = self.getSacTime()[:, 0]
        evtimelist = st[(fromTime <= st) & (st <= toTime)]
        evlist = self.Sac[(fromTime <= st) & (st <= toTime)]
        for f in self.Fix:
            if len(evtimelist) == 0:
                evtimelist = numpy.array([float(f.startTime)])
                evlist = numpy.array([f])
            else:
                idx = numpy.where(f.startTime < evtimelist)[0]
                if idx.size > 0:
                    evtimelist = numpy.insert(evtimelist, idx[0], f.startTime)
                    evlist = numpy.insert(evlist, idx[0], f)
                else:
                    evtimelist = numpy.append(evtimelist, f.startTime)
                    evlist = numpy.append(evlist, f)
        for b in self.Blink:
            if len(evtimelist) == 0:
                evtimelist = numpy.array([float(b.startTime)])
                evlist = numpy.array([b])
            else:
                idx = numpy.where(b.startTime < evtimelist)[0]
                if idx.size > 0:
                    evtimelist = numpy.insert(evtimelist, idx[0], b.startTime)
                    evlist = numpy.insert(evlist, idx[0], b)
                else:
                    evtimelist = numpy.append(evtimelist, b.startTime)
                    evlist = numpy.append(evlist, b)
        for m in self.Msg:
            if len(evtimelist) == 0:
                evtimelist = numpy.array([float(m.time)])
                evlist = numpy.array([m])
            else:
                idx = numpy.where(m.time < evtimelist)[0]
                if idx.size > 0:
                    evtimelist = numpy.insert(evtimelist, idx[0], m.time)
                    evlist = numpy.insert(evlist, idx[0], m)
                else:
                    evtimelist = numpy.append(evtimelist, m.time)
                    evlist = numpy.append(evlist, m)
        return evlist, evtimelist

    def extractTraj(self, period, eye=None):
        """
        Extract trajectory in the specified period of time.
        
        :param tuple period:
            Specify time period.  The first element of the tuple specifies
            the start time of the period.  Use None to specify the beginning
            of the data.  The second element is the end time of the period.
            Use None to specify the end of the data.
            The unit of these values are millisecond.
        :param str eye:
            'L', 'R' or 'B'.  If none, recorded eye is used.
        :return:
            The first element is timestamp.  If monocular data is requested,
            The second element is extracted trajectory.  If binocular, 
            The second element is left eye's data 
        """
        if eye is None:
            eye = self._recordedEye

        if period[0] is None:
            si = 0
        else:
            si = numpy.where(self.T >= period[0])[0][0]
        
        if period[1] is None:
            ei = -1
        else:
            ei = numpy.where(self.T <= period[1])[0][-1]

        if eye == 'L':
            return (self.T[si:ei], self.L[si:ei])
        elif eye == 'R':
            return (self.T[si:ei], self.R[si:ei])
        elif eye == 'B':
            return (self.T[si:ei], self.L[si:ei], self.R[si:ei])
        else:
            raise ValueError('Eye must be \'L\', \'R\', \'B\' or None.')

    def findNearestIndexFromMessage(self, message):
        """
        Return index of the timestamp of the sample that is nearest to the time
        of given message.

        .. note:: This method is deprecated.
           Use :func:`~GazeParser.Core.GazeData`findIndexFromTime` instead.
           gazedata.findNearestIndexFromMessage(msg) is equivalent to
           gazedata.findIndexFromTime(msg.time)
        """
        if isinstance(message, int):
            return self.findIndexFromTime(self.Msg[message].time)
        elif isinstance(message, MessageData):
            return self.findIndexFromTime(message.time)
        else:
            raise ValueError('message must be integer or MessageData object.')

    def findIndexFromTime(self, time):
        """
        Return index of the timestamp of the sample that is nearest to the
        argument value.
        For example, 1000.0 is given as an argument and timestamp of the 251st
        and 252nd sample are 999.6 and 1003.4 respectively, 251 is returned.

        :param float time:
            Time in msec.
        """
        tdifflist = abs(self.T - time)
        mindiff = min(tdifflist)
        return numpy.where(mindiff == tdifflist)[0][0]

    def getMessageTextList(self):
        """
        Get a list of all message texts.
        """
        ret = []
        for i in range(self.nMsg):
            ret.append(self.Msg[i].text)

        return ret

    def findMessage(self, text, byIndices=False, useRegexp=False):
        """
        Get messages including specified text.

        :param str text:
            A text to be found.
        :param bool byIndices:
            If ture, matched messages are returned by a list of indices.
            Otherwise, matched messages are returned by a list of
            GazeParser.Core.MessageData objects.  Default value is False.
        :param bool useRegexp:
            If true, 'text' parapeter is considered as a regular expression.
            Default value is False.
        """
        ret = []

        if useRegexp:
            p = re.compile(text)
            for i in range(self.nMsg):
                if p.search(self.Msg[i].text) is not None:
                    if byIndices:
                        ret.append(i)
                    else:
                        ret.append(self.Msg[i])
        else:
            for i in range(self.nMsg):
                if text in self.Msg[i].text:
                    if byIndices:
                        ret.append(i)
                    else:
                        ret.append(self.Msg[i])

        return ret

    def deleteMessage(self, message):
        """
        Delete a message from message list.

        :param message:
            MessageData to be deleted. a :class:`~GazeParser.Core.MessageData`
            object or an integer is accepted.
        """

        if isinstance(message, int):
            idxMsg = message
        elif isinstance(message, GazeParser.Core.MessageData):
            try:
                idxMsg = numpy.where(self._Msg == message)[0]
            except:
                print('Could not find message.')
                raise
        else:
            raise ValueError('\'message\' must be an index or an instance of MessgeData object.')

        idxEvent = numpy.where(self._EventList == self.Msg[idxMsg])[0]

        self._Msg = numpy.delete(self.Msg, idxMsg)
        self._nMsg = self.nMsg - 1
        self._EventList = numpy.delete(self.EventList, idxEvent)

    def insertNewMessage(self, time, text):
        """
        Insert a new message to MessageList.

        :param time:
            Timestamp of the new message.
        :param text:
            Message text of the new message.
        """
        newmsg = MessageData([time, text])

        t = self.getMsgTime()
        idx = numpy.where(time < t)[0]
        if idx.size > 0:
            self._Msg = numpy.insert(self.Msg, idx[0], newmsg)
        else:
            self._Msg = numpy.append(self.Msg, newmsg)

        self._nMsg = self.nMsg + 1

        newmsg._setParent(self)

        t = []
        for e in self.EventList:
            if hasattr(e, 'startTime'):
                t.append(e.startTime)
            else:
                t.append(e.time)
        idx = numpy.where(time < numpy.array(t))[0]
        if idx.size > 0:
            self._EventList = numpy.insert(self.EventList, idx[0], newmsg)
        else:
            self._EventList = numpy.append(self.EventList, newmsg)

    def sortMessagesByTime(self):
        """
        Sort messages by time.
        """
        t = self.getMsgTime().flatten()
        index = numpy.argsort(t)
        self._Msg = self.Msg[index]

    def sortEventListByTime(self):
        """
        Sort event list by time.
        """
        t = []
        for e in self.EventList:
            if hasattr(e, 'startTime'):
                t.append(e.startTime)
            else:
                t.append(e.time)

        index = numpy.argsort(t)
        self._EventList = self.EventList[index]

    def getPreviousEvent(self, event, step=1, eventType=None):
        """
        Get an event previous to the argument.
        If no previous event, return None.

        :param event:
            An instance of SaccadeData, FixaionData, BlinkData or MessageData.
            Timestamp is also accepted.
        :param integer step:
            If an integer (n) is given, the n-th previous event is returned.
            Default value is 1.
        :param str eventType:
            If 'saccade', 'fixation', 'blink' or 'message' is given, only
            events of given type are considered.
        :return:
            Event object. If there is no previous event, return None.
        """
        if event in self.EventList:  # reference is an event
            index = numpy.where(self.EventList == event)[0][0]
            if eventType is None:
                if index - step < 0:
                    return None
                else:
                    return self.EventList[index - step]
            else:
                if eventType.lower() == 'saccade':
                    eventClass = GazeParser.Core.SaccadeData
                elif eventType.lower() == 'fixation':
                    eventClass = GazeParser.Core.FixationData
                elif eventType.lower() == 'message':
                    eventClass = GazeParser.Core.MessageData
                elif eventType.lower() == 'blink':
                    eventClass = GazeParser.Core.BlinkData
                else:
                    raise ValueError('Event must be saccade, fixation, message or blink.')

                i = index - 1
                count = 0
                while(i >= 0):
                    if isinstance(self.EventList[i], eventClass):
                        count += 1
                        if count == step:
                            return self.EventList[i]
                    i -= 1
                return None

        else:  # reference should be timestamp
            if eventType is None:
                diffList = numpy.zeros(len(self._EventList))
                for i in range(len(self._EventList)):
                    if isinstance(self._EventList[i], GazeParser.Core.MessageData):
                        diffList[i] = self._EventList[i].time - event
                    else:
                        diffList[i] = self._EventList[i].endTime - event

                prevIndices = numpy.where(diffList < 0)[0]
                if len(prevIndices) == 0:
                    return None
                else:
                    return self._EventList[prevIndices[-1]]
            else:
                if eventType.lower() == 'saccade':
                    targetList = self._Sac
                    diffList = self.getSacTime()[:, 1] - event
                elif eventType.lower() == 'fixation':
                    targetList = self._Fix
                    diffList = self.getFixTime()[:, 1] - event
                elif eventType.lower() == 'message':
                    targetList = self._Msg
                    diffList = self.getMsgTime() - event
                elif eventType.lower() == 'blink':
                    targetList = self._Blink
                    diffList = self.getBlinkTime()[:, 1] - event
                else:
                    raise ValueError('Event must be saccade, fixation, message or blink.')

                prevIndices = numpy.where(diffList < 0)[0]
                if len(prevIndices) == 0:
                    return None
                else:
                    return targetList[prevIndices[-1]]

    def getNextEvent(self, event, step=1, eventType=None):
        """
        Get an event next to the argument. If no next event, return None.

        :param event:
            An instance of SaccadeData, FixaionData, BlinkData or MessageData.
            Timestamp (a float value) is also accepted.
        :param integer step:
            If an integer (n) is given, the n-th next event is returned.
            Default value is 1.
        :param str eventType:
            If 'saccade', 'fixation', 'blink' or 'message' is given, only
            events of given type are considered.
        :return:
            Event object. If there is no next event, return None.
        """

        if event in self.EventList:  # reference is an event
            index = numpy.where(self.EventList == event)[0][0]
            if eventType is None:
                if index + step >= len(self.EventList):
                    return None
                else:
                    return self.EventList[index + step]
            else:
                if eventType.lower() == 'saccade':
                    eventClass = GazeParser.Core.SaccadeData
                elif eventType.lower() == 'fixation':
                    eventClass = GazeParser.Core.FixationData
                elif eventType.lower() == 'message':
                    eventClass = GazeParser.Core.MessageData
                elif eventType.lower() == 'blink':
                    eventClass = GazeParser.Core.BlinkData
                else:
                    raise ValueError('Event must be saccade, fixation, message or blink.')

                i = index + 1
                count = 0
                while(i < len(self.EventList)):
                    if isinstance(self.EventList[i], eventClass):
                        count += 1
                        if count == step:
                            return self.EventList[i]
                    i += 1
                return None
        else:  # reference should be timestamp
            if eventType is None:
                diffList = numpy.zeros(len(self._EventList))
                for i in range(len(self._EventList)):
                    if isinstance(self._EventList[i], GazeParser.Core.MessageData):
                        diffList[i] = self._EventList[i].time - event
                    else:
                        diffList[i] = self._EventList[i].startTime - event

                prevIndices = numpy.where(diffList > 0)[0]
                if len(prevIndices) == 0:
                    return None
                else:
                    return self._EventList[prevIndices[0]]
            else:
                if eventType.lower() == 'saccade':
                    targetList = self._Sac
                    diffList = self.getSacTime()[:, 0] - event
                elif eventType.lower() == 'fixation':
                    targetList = self._Fix
                    diffList = self.getFixTime()[:, 0] - event
                elif eventType.lower() == 'message':
                    targetList = self._Msg
                    diffList = self.getMsgTime() - event
                elif eventType.lower() == 'blink':
                    targetList = self._Blink
                    diffList = self.getBlinkTime()[:, 0] - event
                else:
                    raise ValueError('Event must be saccade, fixation, message or blink.')

                prevIndices = numpy.where(diffList > 0)[0]
                if len(prevIndices) == 0:
                    return None
                else:
                    return targetList[prevIndices[0]]

    def PixelToDeg(self, pixValue):
        """
        Convert screen pixel to visual angle.

        :param float pixValue:
            A value in visual angle.
        """
        return pixValue * self.pix2deg

    def DegToPixel(self, degValue):
        """
        Convert visual angle to screen pixel.

        :param float degValue:
            A value in screen pixel.
        """
        return degValue * self.deg2pix

    nSac = property(lambda self: self._nSac)
    """Number of saccades detected in this trial."""

    nFix = property(lambda self: self._nFix)
    """Number of fixations detected in this trial."""

    nMsg = property(lambda self: self._nMsg)
    """Number of messages recorded in this trial."""

    nBlink = property(lambda self: self._nBlink)
    """Number of blinks detected in this trial."""

    L = property(lambda self: self._L)
    """List of gaze position (x, y) of left eye."""

    R = property(lambda self: self._R)
    """List of gaze position (x, y) of right eye."""

    T = property(lambda self: self._T)
    """List of timestamps when each gaze position was recorded."""

    Sac = property(lambda self: self._Sac)
    """List of :class:`~SaccadeData` objects."""

    Fix = property(lambda self: self._Fix)
    """List of :class:`~FixationData` objects."""

    Msg = property(lambda self: self._Msg)
    """List of :class:`~MessageData` objects."""

    Blink = property(lambda self: self._Blink)
    """List of :class:`~BlinkData` objects."""

    recordedEye = property(lambda self: self._recordedEye)

    Pupil = property(lambda self: self._Pupil)

    CameraSpecificData = property(lambda self: self._CameraSpecificData)

    USBIOChannels = property(lambda self: self._USBIOChannels)

    USBIOData = property(lambda self: self._USBIOData)

    CalPointData = property(lambda self: self._CalPointData)

    recordingDate = property(lambda self: self._recordingDate)

    EventList = property(lambda self: self._EventList)
    """
    List of all events (saccades, fixations, blinks and messages) in
    chronological order.
    """

    config = property(lambda self: self._config)
    """
    :class:`~GazeParser.Configuration.Config` object which holds recording and
    parsing options.
    """

    def getPathLength(self, sac):
        """
        Get saccade length along saccade trajectory.  If a list of SaccadeData
        object is provided, a list of the length of each saccades in the input
        list is returned.

        :param sac:
            a SaccadeData object or a list of SaccadeData object.

        :return:
            a float value or a numpy.ndarray object depending on the argument
        """
        if isinstance(sac, GazeParser.Core.SaccadeData):
            if self._L is not None:
                dx = numpy.diff(self._L[sac._startIndex:sac._endIndex, 0])
                dy = numpy.diff(self._L[sac._startIndex:sac._endIndex, 1])
                l = numpy.sum(numpy.sqrt(dx ** 2 + dy ** 2))

            if self._R is not None:
                dx = numpy.diff(self._R[sac._startIndex:sac._endIndex, 0])
                dy = numpy.diff(self._R[sac._startIndex:sac._endIndex, 1])
                r = numpy.sum(numpy.sqrt(dx ** 2 + dy ** 2))

            if self._recordedEye == 'L':
                return l
            elif self._recordedEye == 'R':
                return r
            else:  # binocular
                return l + r / 2
        else:
            if self._recordedEye == 'L' or self._recordedEye == 'B':
                l = numpy.zeros((len(sac), 1))
                for i in range(len(sac)):
                    dx = numpy.diff(self._L[sac[i]._startIndex:sac[i]._endIndex, 0])
                    dy = numpy.diff(self._L[sac[i]._startIndex:sac[i]._endIndex, 1])
                    l[i] = numpy.sum(numpy.sqrt(dx ** 2 + dy ** 2))

            if self._recordedEye == 'R' or self._recordedEye == 'B':
                r = numpy.zeros((len(sac), 1))
                for i in range(len(sac)):
                    dx = numpy.diff(self._R[sac[i]._startIndex:sac[i]._endIndex, 0])
                    dy = numpy.diff(self._R[sac[i]._startIndex:sac[i]._endIndex, 1])
                    r[i] = numpy.sum(numpy.sqrt(dx ** 2 + dy ** 2))

            if self._recordedEye == 'L':
                return l
            elif self._recordedEye == 'R':
                return r
            else:  # binocular
                return (l + r) / 2.0

    def setCameraSpecificData(self, data):
        """
        Set camera specific data.

        :param data:
            Camera specific data.
        """
        self._CameraSpecificData = data

    def hasCameraSpecificData(self):
        """
        Return True if camera specific data is included.
        """
        if self._CameraSpecificData is not None:
            return True
        else:
            return False

    def setUSBIOData(self, channels, data):
        """
        Set USBIO data.

        :param channels:
            List of USBIO channels.
        :param data:
            USBIO data.
        """
        self._USBIOChannels = channels
        self._USBIOData = data

    def hasUSBIOData(self):
        """
        Return True if USBIO data is included.
        """
        if self._USBIOData is not None:
            return True
        else:
            return False

    def setCalPointData(self, calpointdata):
        """
        Set calibration point data.

        :param calpointdata:
            A list of calibration point location, accuracy and precision.
        """
        self._CalPointData = calpointdata
    
    def hasCalPointData(self):
        """
        Return True if calibration point data is included.
        """
        if self._CalPointData is not None:
            return True
        else:
            return False

    def getCalPointDataByList(self, contents='all'):
        """
        Get calibration point data by numpy.ndarray.
        
        :param contents:
            Contents of the list. 'point', 'accuracy', 'precision' and 'all'
            are supported. Default value is 'all'.
        """
        
        c = contents.lower()
        if c == 'point':
            return numpy.array([data._point for data in self._CalPointData])
        elif c == 'accuracy':
            return numpy.array([data._accuracy for data in self._CalPointData])
        elif c == 'precision':
            return numpy.array([data._precision for data in self._CalPointData])
        elif c == 'all':
            a = numpy.array([numpy.hstack([data._point, data._accuracy, data._precision]) for data in self._CalPointData])
            return a
        else:
            raise ValueError('contents must be \'point\', \'accuracy\', \'precision\' or \'All\'.')

    def __eq__(self, other):
        if not isinstance(other, GazeData):
            return False
        for attr in ('L', 'R', 'T', 'Pupil'):
            attr1 = getattr(self, attr)
            attr2 = getattr(other, attr)
            if isinstance(attr1, numpy.ndarray) and isinstance(attr2, numpy.ndarray):
                if not numpy.allclose(getattr(self, attr), getattr(other, attr), equal_nan=True):
                    return False
            elif attr1 is None and isinstance(attr2, numpy.ndarray):
                return False
            elif attr2 is None and isinstance(attr1, numpy.ndarray):
                return False
        for attr in ('nSac', 'nFix', 'nMsg', 'nBlink', 'recordedEye', 'recordingDate'):
            if getattr(self, attr) != getattr(other, attr):
                return False
        for attr in ('Sac', 'Fix', 'Msg', 'Blink'):
            if (getattr(self, attr) != getattr(other, attr)).any():
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)

        if hasattr(self, 'recordingDate'):
            date = '{:d}/{:02d}/{:02d}-{:02d}:{:02d}:{:02d}'.format(*self.recordingDate)
            msg += '{}, {}, {:.1f}s>'.format(date, self.recordedEye, self.T[-1]/1000.0)
        else:
            msg += 'no_date, {}, {:.1f}s>'.format(self.recordedEye, self.T[-1]/1000.0)
        
        return msg

    def _compare(self, other):
        """
        This functions is basically equal to __eq__, but outputs difference.
        """
        if not isinstance(other, GazeData):
            print('The parameter is not GazeData object.')
            return
        for attr in ('L', 'R', 'T', 'Pupil'):
            attr1 = getattr(self, attr)
            attr2 = getattr(other, attr)
            if isinstance(attr1, numpy.ndarray) and isinstance(attr2, numpy.ndarray):
                if not numpy.allclose(getattr(self, attr), getattr(other, attr), equal_nan=True):
                    print('"{}" is different'.format(attr))
            elif attr1 is None and isinstance(attr2, numpy.ndarray):
                print('"{}" is different'.format(attr))
            elif attr2 is None and isinstance(attr1, numpy.ndarray):
                print('"{}" is different'.format(attr))
        for attr in ('nSac', 'nFix', 'nMsg', 'nBlink', 'recordedEye', 'recordingDate'):
            if getattr(self, attr) != getattr(other, attr):
                print('"{}" is different'.format(attr))
                return
        for attr in ('Sac', 'Fix', 'Msg', 'Blink'):
            if (getattr(self, attr) != getattr(other, attr)).any():
                print('"{}" is different'.format(attr))
                return
