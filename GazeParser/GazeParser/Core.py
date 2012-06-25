"""
.. Part of GazeParser package.
.. Copyright (C) 2012 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""

import GazeParser
import numpy
import re

class SaccadeData(object):
    """
    Holds various parameters of a single saccade such as start time,
    end time, amplitude and so on.
    """
    
    def __init__(self,t,d,Tlist):
        """
        :param t: Timestamp (start, endTime).
        :param d: Tuple of 6 elements (Startpoint X, Y, Endpoint X, Y,
                  amplitude, length).
        :param Tlist: List of TimeStamps.
        """
        
        self._startTime = t[0]
        self._endTime = t[1]
        self._duration = d[0]
        self._start = (d[1],d[2])
        self._end = (d[3],d[4])
        self._amplitude = d[5]
        self._length = numpy.sqrt((d[3]-d[1])**2 + (d[4]-d[2])**2)
        self._direction = numpy.arctan2(d[4]-d[2],d[3]-d[1])
        self._parent = None
        
        idx = numpy.where(Tlist==t[0])[0]
        if len(idx)!=1:
            raise ValueError, 'SaccadeData: could not find index.'
        else:
            self._startIndex = idx[0]
            
        idx = numpy.where(Tlist==t[1])[0]
        if len(idx)!=1:
            raise ValueError, 'SaccadeData: could not find index.'
        else:
            self._endIndex = idx[0]
    
    startTime = property(lambda self: self._startTime)
    """Saccade onset time in msec."""
    
    endTime = property(lambda self: self._endTime)
    """Saccade offset time in msec."""
    
    duration = property(lambda self: self._duration)
    """Saccade duration in msec."""
    
    start = property(lambda self: self._start)
    """Saccade start location in screen coordinate (x,y)."""
    
    end = property(lambda self: self._end)
    """Saccade end location in screen coordinate (x,y)."""
    
    amplitude = property(lambda self: self._amplitude)
    """Saccade length in degree."""
    
    length = property(lambda self: self._length)
    """Saccade length in screen coordinate."""
    
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
        
        :param float time: reference time. Unit is msec.
        """
        return self.startTime - time
    
    def relativeEndTime(self, time):
        """
        Saccade offset time relative to indicated time.
        Unit is msec.
        
        :param float time: reference time. Unit is msec.
        """
        return self.endTime - time
    
    def _setParent(self, obj):
        if self in obj._Sac:
            self._parent = obj
        else:
            raise ValueError, 'Argument does not include this saccade.'
    
    def getTraj(self,eye=None):
        """
        
        """
        if eye==None:
            eye = self._parent._recordedEye
        
        s = self.startIndex
        e = self.endIndex
        if eye=='L':
            return self._parent.L[s:e+1]
        elif eye=='R':
            return self._parent.R[s:e+1]
        elif eye=='B':
            return (self._parent.L[s:e+1],self._parent.R[s:e+1])
        else:
            raise ValueError, 'Eye must be \'L\', \'R\', \'B\' or None'
    
    def getNextEvent(self,step=1,eventType=None):
        return self._parent.getNextEvent(self,step=step,eventType=eventType)
    
    def getPreviousEvent(self,step=1,eventType=None):
        return self._parent.getPreviousEvent(self,step=step,eventType=eventType)
    

class FixationData(object):
    """
    Holds various parameters of a single fixation such as start time,
    end time and so on.
    """
    
    def __init__(self,t,d,Tlist):
        """
        :param t: Timestamp (start, endTime)
        :param d: Tuple of 3 elements. (duration, center location X, Y)
        :param Tlist: List of TimeStamps.
        """
        self._startTime = t[0]
        self._endTime = t[1]
        self._duration = d[0]
        self._center = (d[1],d[2])
        self._parent = None
        
        idx = numpy.where(Tlist==t[0])[0]
        if len(idx)!=1:
            raise ValueError, 'FixationData: could not find index.'
        else:
            self._startIndex = idx[0]
            
        idx = numpy.where(Tlist==t[1])[0]
        if len(idx)!=1:
            raise ValueError, 'FixationData: could not find index.'
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
    Fixation center in screen coordinate (x,y).
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
        
        :param float time: reference time. Unit is msec.
        """
        return self.startTime - time
    
    def relativeEndTime(self, time):
        """
        Fixation offset time relative to indicated time.
        Unit is msec.
        
        :param float time: reference time. Unit is msec.
        """
        return self.endTime - time
    
    def _setParent(self, obj):
        if self in obj._Fix:
            self._parent = obj
        else:
            raise ValueError, 'Argument does not include this fixation.'
    
    def getTraj(self,eye=None):
        """
        
        """
        if eye==None:
            eye = self._parent._recordedEye
        
        s = self.startIndex
        e = self.endIndex
        if eye=='L':
            return self._parent.L[s:e+1]
        elif eye=='R':
            return self._parent.R[s:e+1]
        elif eye=='B':
            return (self._parent.L[s:e+1],self._parent.R[s:e+1])
    
    def getNextEvent(self,step=1,eventType=None):
        return self._parent.getNextEvent(self,step=step,eventType=eventType)
    
    def getPreviousEvent(self,step=1,eventType=None):
        return self._parent.getPreviousEvent(self,step=step,eventType=eventType)

class MessageData(object):
    """
    Holds a message received during recording.
    """
    def __init__(self,m):
        """
        :param m: A tuple of 2 elements. The 1st element is timestamp (in msec).
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
            raise ValueError, 'Argument does not include this message.'
    
    def getNextEvent(self,step=1,eventType=None):
        return self._parent.getNextEvent(self,step=step,eventType=eventType)
    
    def getPreviousEvent(self,step=1,eventType=None):
        return self._parent.getPreviousEvent(self,step=step,eventType=eventType)


class BlinkData(object):
    """
    Holds start time, end time and duraton of a blink.
    """
    def __init__(self,t,d,Tlist):
        """
        :param sequence t: TimeStamp (start, endTime)
        :param float d:  duration of blink (msec)
        :param sequence Tlist: List of timestamps.
        """
        self._startTime = t[0]
        self._endTime = t[1]
        self._duration = d
        self._parent = None
        idx = numpy.where(Tlist==t[0])[0]
        if len(idx)!=1:
            raise ValueError, 'BlinkData: could not find index.'
        else:
            self._startIndex = idx[0]
            
        idx = numpy.where(Tlist==t[1])[0]
        if len(idx)!=1:
            raise ValueError, 'BlinkData: could not find index.'
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
        
        :param float time: reference time. Unit is msec.
        """
        return self.startTime - time
    
    def relativeEndTime(self, time):
        """
        Blink offset time relative to indicated time.
        Unit is msec.
        
        :param float time: reference time. Unit is msec.
        """
        return self.endTime - time
    
    def _setParent(self, obj):
        if self in obj._Blink:
            self._parent = obj
        else:
            raise ValueError, 'Argument does not include this blink.'
    
    def getNextEvent(self,step=1,eventType=None):
        return self._parent.getNextEvent(self,step=step,eventType=eventType)
    
    def getPreviousEvent(self,step=1,eventType=None):
        return self._parent.getPreviousEvent(self,step=step,eventType=eventType)

class GazeData(object):
    """
    Holds saccades, fixations, blinks, messages, timestamps and gaze 
    trajectory in a single recording.
    """
    def __init__(self,Tlist,Llist,Rlist,SacList,FixList,MsgList,BlinkList,recordedEye,config=None):
        """
        Constructor GazeData.
        """
        self.__version__ = GazeParser.__version__
        self._nSac = len(SacList)
        self._nFix = len(FixList)
        self._nMsg = len(MsgList)
        self._nBlink = len(BlinkList)
        if Llist == None:
            self._L = None
        else:
            self._L = numpy.array(Llist)
        if Rlist == None:
            self._R = None
        else:
            self._R = numpy.array(Rlist)
        self._T = numpy.array(Tlist)
        self._Sac = numpy.array(SacList)
        self._Fix = numpy.array(FixList)
        self._Msg = numpy.array(MsgList)
        self._Blink = numpy.array(BlinkList)
        self._recordedEye = recordedEye
        
        self._EventList = self._getEventListByTime(self.T[0],self.T[-1])[0]
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
        
        cm2deg = 180/numpy.pi*numpy.arctan(1.0/self._config.VIEWING_DISTANCE)
        self._deg2pix = numpy.array((self._config.DOTS_PER_CENTIMETER_H/cm2deg,
                                     self._config.DOTS_PER_CENTIMETER_V/cm2deg))
        self._pix2deg = 1.0/self._deg2pix
        
    def getFixTraj(self,index,eye=None):
        """
        Get gaze trajectory during a fixation.
        
        :param integer index:
            Index of fixation.  Give n-1 to get gaze trajectory during n-th fixation.
        :param str eye:
            Output both-eye ('B'), left-eye ('L'), right-eye ('R') data or None (recorded eye).
            Default value is None.
        """
        if not (0 <= index < self.nFix):
            raise ValueError, 'Index is out of range.'
        s = self._Fix[index]._startIndex
        e = self._Fix[index]._endIndex
        if eye=='L':
            return self._L[s:e+1]
        elif eye=='R':
            return self._R[s:e+1]
        elif eye=='B':
            return (self._L[s:e+1],self._R[s:e+1])
        else:
            raise ValueError, 'Eye must be \'L\', \'R\', \'B\' or None'

    def getFixDur(self,*args):
        """
        Get duration of fixations in milliseconds.
        
        :param integer index:
            Index of fixation.  Give n-1 to get gaze trajectory during n-th fixation.
        :param str eye:
            Output both-eye ('B'), left-eye ('L') or right-eye ('R') data.
        """
        if len(args) == 0:
            l = numpy.zeros([self.nFix,1])
            for idx in range(self.nFix):
                l[idx] = self.Fix[idx].duration
            return l
        elif len(args) == 1:
            Idx = args[0]
            if not (0 <= Idx < self.nFix):
                raise ValueError, 'Index is out of range.'
            return self.Fix[Idx].duration
        else:
            raise ValueError, 'None or 1 arg is required.'
    
    def getFixCenter(self,*args):
        """
        Get the center of fixations in screen coordinate.
        
        :param args:
            If no argument is given, center of all fixations are obtained as 
            a numpy.ndarray object whose shape is (n,2).
            If an integer (n-1) is given, the center of n-th fixation is obtained.
        """
        if len(args) == 0:
            l = numpy.zeros([self.nFix,2])
            for idx in range(self.nFix):
                l[idx,:] = self.Fix[idx].center
            return l
        elif len(args) == 1:
            Idx = args[0]
            if not (0 <= Idx < self.nFix):
                raise ValueError, 'Index is out of range.'
            return self.Fix[Idx].center
        else:
            raise ValueError, 'None or 1 arg is required.'
    
    def getFixTime(self,*args):
        """
        Get the start and end time of fixations.
        
        :param args:
            If no argument is given, the start and end time of all fixations are 
            obtained as a numpy.ndarray object whose shape is (n,2).
            If an integer (n-1) is given, the start and end time of n-th fixation 
            is obtained.
        """
        if len(args) == 0:
            l = numpy.zeros([self.nFix,2])
            for idx in range(self.nFix):
                l[idx,:] = [self.Fix[idx].startTime,self.Fix[idx].endTime]
            return l
        elif len(args) == 1:
            Idx = args[0]
            if not (0 <= Idx < self.nFix):
                raise ValueError, 'Index is out of range.'
            return (self.Fix[Idx].startTime,self.Fix[Idx].endTime)
        else:
            raise ValueError, 'None or 1 arg is required.'
        
    def getBlinkTime(self,*args):
        """
        Get the start and end time of blinks.
        
        :param args:
            If no argument is given, the start and end time of all blinks are 
            obtained as a numpy.ndarray object whose shape is (n,2).
            If an integer (n-1) is given, the start and end time of n-th blink 
            is obtained.
        """
        if len(args) == 0:
            l = numpy.zeros([self.nBlink,2])
            for idx in range(self.nBlink):
                l[idx,:] = [self.Blink[idx].startTime,self.Blink[idx].endTime]
            return l
        elif len(args) == 1:
            Idx = args[0]
            if not (0 <= Idx < self.nBlink):
                raise ValueError, 'Index is out of range.'
            return (self.Blink[Idx].startTime,self.Blink[Idx].endTime)
        else:
            raise ValueError, 'None or 1 arg is required.'
    
    def getMsgTime(self,*args):
        """
        Get the recorded time of messages.
        
        :param args:
            If no argument is given, the received time of all messages obtained as 
            a numpy.ndarray object whose shape is (n,1).
            If an integer (n-1) is given, the recorded of n-th fixation is obtained.
        """
        if len(args) == 0:
            l = numpy.zeros([self.nMsg,1])
            for idx in range(self.nMsg):
                l[idx] = self.Msg[idx].time
            return l
        elif len(args) == 1:
            Idx = args[0]
            if not (0 <= Idx < self.nMsg):
                raise ValueError, 'Index is out of range.'
            return self.Msg[idx].time
        else:
            raise ValueError, 'None or 1 arg is required.'
    
    def getSacTraj(self,index,eye=None):
        """
        Get gaze trajectory during a saccade.
        
        :param integer index:
            Index of saccade.  Give n-1 to get gaze trajectory during n-th saccade.
        :param str eye:
            Output both-eye ('B'), left-eye ('L'), right-eye ('R') data or None (recorded eye).
            Default value is None.
        """
        if not (0 <= index < self.nSac):
            raise ValueError, 'Index is out of range.'
        
        if eye==None:
            eye = self._recordedEye
        
        s = self._Sac[index]._startIndex
        e = self._Sac[index]._endIndex
        if eye=='L':
            return self._L[s:e+1]
        elif eye=='R':
            return self._R[s:e+1]
        elif eye=='B':
            return (self._L[s:e+1],self._R[s:e+1])
        else:
            raise ValueError, 'Eye must be \'L\', \'R\', \'B\' or None'
    
    def getSacLen(self,*args):
        """
        Get saccade length.
        
        :param integer index:
            Index of saccade.  Give n-1 to get gaze trajectory during n-th saccade.
            If no index is supplied, length of all saccades are returned as a 
            numpy.ndarray object.
        :param str eye:
            Output both-eye ('B'), left-eye ('L') or right-eye ('R') data.
        """
        if len(args) == 0:
            l = numpy.zeros([self.nSac,1])
            for idx in range(self.nSac):
                l[idx] = self.Sac[idx].length
            return l
        elif len(args) == 1:
            Idx = args[0]
            if not (0 <= Idx < self.nSac):
                raise ValueError, 'Index is out of range.'
            return self.Sac[Idx].length
        else:
            raise ValueError, 'None or 1 arg is required.'
        
    def getSacDur(self,*args):
        """
        Get duration of saccades in milliseconds.
        
        :param integer index:
            Index of fixation.  Give n-1 to get gaze trajectory during n-th fixation.
            If no index is supplied, length of all saccades are returned as a 
            numpy.ndarray object.
        :param str eye:
            Output both-eye ('B'), left-eye ('L') or right-eye ('R') data.
        """
        if len(args) == 0:
            l = numpy.zeros([self.nSac,1])
            for idx in range(self.nSac):
                l[idx] = self.Sac[idx].duration
            return l
        elif len(args) == 1:
            Idx = args[0]
            if not (0 <= Idx < self.nSac):
                raise ValueError, 'Index is out of range.'
            return self.Sac[Idx].duration
        else:
            raise ValueError, 'None or 1 arg is required.'
        
    def getSacTime(self,*args):
        """
        Get the start and end time of saccades.
        
        :param args:
            If no argument is given, the start and end time of all saccades are 
            obtained as a numpy.ndarray object whose shape is (n,2).
            If an integer (n-1) is given, the start and end time of n-th saccade 
            is obtained.
        """
        if len(args) == 0:
            l = numpy.zeros([self.nSac,2])
            for idx in range(self.nSac):
                l[idx,:] = [self.Sac[idx].startTime,self.Sac[idx].endTime]
            return l
        elif len(args) == 1:
            Idx = args[0]
            if not (0 <= Idx < self.nSac):
                raise ValueError, 'Index is out of range.'
            return (self.Sac[Idx].startTime,self.Sac[Idx].endTime)
        else:
            raise ValueError, 'None or 1 arg is required.'
    
    def _getEventListByTime(self,fromTime,toTime):
        """
        Build a list which contains all saccades, fixations, blinks and messages
        arranged in chronological order.
        
        :param float fromTime:
            Events that recorded after this time are included to the list.
        :param float endTime:
            Events that recorded before this time are included to the list.
        """
        st = self.getSacTime()[:,0]
        evtimelist = st[(fromTime <= st) & (st <= toTime)]
        evlist = self.Sac[(fromTime <= st) & (st <= toTime)]
        for f in self.Fix:
            if len(evtimelist) == 0:
                evtimelist = numpy.array([float(f.startTime)])
                evlist = numpy.array([f])
            else:
                idx = numpy.where(f.startTime<evtimelist)[0]
                if idx.size>0:
                    evtimelist = numpy.insert(evtimelist,idx[0],f.startTime)
                    evlist = numpy.insert(evlist,idx[0],f)
                else:
                    evtimelist = numpy.append(evtimelist,f.startTime)
                    evlist = numpy.append(evlist,f)
        for b in self.Blink:
            if len(evtimelist) == 0:
                evtimelist = numpy.array([float(b.startTime)])
                evlist = numpy.array([b])
            else:
                idx = numpy.where(b.startTime<evtimelist)[0]
                if idx.size>0:
                    evtimelist = numpy.insert(evtimelist,idx[0],b.startTime)
                    evlist = numpy.insert(evlist,idx[0],b)
                else:
                    evtimelist = numpy.append(evtimelist,b.startTime)
                    evlist = numpy.append(evlist,b)
        for m in self.Msg:
            if len(evtimelist) == 0:
                evtimelist = numpy.array([float(m.time)])
                evlist = numpy.array([m])
            else:
                idx = numpy.where(m.time<evtimelist)[0]
                if idx.size>0:
                    evtimelist = numpy.insert(evtimelist,idx[0],m.time)
                    evlist = numpy.insert(evlist,idx[0],m)
                else:
                    evtimelist = numpy.append(evtimelist,m.time)
                    evlist = numpy.append(evlist,m)
        return evlist,evtimelist
    
    def findNearestIndexFromMessage(self,messageID):
        tdifflist = abs(self.T-self.Msg[messageID].time)
        mindiff = min(tdifflist)
        return numpy.where(mindiff==tdifflist)[0][0]
    
    def getMessageTextList(self):
        """
        Get a list of all message texts.
        """
        ret = []
        for i in range(self.nMsg):
            ret.append(self.Msg[i].text)
        
        return ret
        
    def findMessage(self,text,byIndices=False,useRegexp=False):
        """
        Get messages including specified text.
        
        :param str text:
            A text to be found.
        :param bool byIndices:
            If ture, matched messages are returned by a list of indices.
            Otherwise, matched messages are returned by a list of GazeParser.Core.MessageData objects.
            Default value is False.
        :param bool useRegexp:
            If true, 'text' parapeter is considered as a regular expression.
            Default value is False.
        """
        ret = []
        
        if useRegexp:
            p = re.compile(text)
            for i in range(self.nMsg):
                if p.search(self.Msg[i].text)!=None:
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
        
    
    def getPreviousEvent(self,event,step=1,eventType=None):
        """
        Get an event previous to the argument. If no previous event, return None.
        
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
        if event in self.EventList: #reference is an event
            index = numpy.where(self.EventList == event)[0][0]
            if eventType==None:
                if index-step<0:
                    return None
                else:
                    return self.EventList[index-step]
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
                    raise ValueError
                    
                i = index-1
                count=0
                while(i>=0):
                    if isinstance(self.EventList[i],eventClass):
                        count += 1
                        if count == step:
                            return self.EventList[i]
                    i-=1
                return None
        
        else: #reference should be timestamp
            if eventType==None:
                diffList = numpy.zeros(len(self._EventList))
                for i in range(len(self._EventList)):
                    if isinstance(self._EventList[i],GazeParser.Core.MessageData):
                        diffList[i] = self._EventList[i].time - event
                    else:
                        diffList[i] = self._EventList[i].endTime - event
                
                prevIndices = numpy.where(diffList<0)[0]
                if len(prevIndices)==0:
                    return None
                else:
                    return self._EventList[prevIndices[-1]]
            else:
                if eventType.lower() == 'saccade':
                    targetList = self._Sac
                    diffList = self.getSacTime()[:,1] - event
                elif eventType.lower() == 'fixation':
                    targetList = self._Fix
                    diffList = self.getFixTime()[:,1] - event
                elif eventType.lower() == 'message':
                    targetList = self._Msg
                    diffList = self.getMsgTime() - event
                elif eventType.lower() == 'blink':
                    targetList = self._Blink
                    diffList = self.getBlinkTime()[:,1] - event
                else:
                    raise ValueError
                
                prevIndices = numpy.where(diffList<0)[0]
                if len(prevIndices)==0:
                    return None
                else:
                    return targetList[prevIndices[-1]]                
    
    def getNextEvent(self,event,step=1,eventType=None):
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
        
        if event in self.EventList: #reference is an event
            index = numpy.where(self.EventList == event)[0][0]
            if eventType==None:
                if index+step>=len(self.EventList):
                    return None
                else:
                    return self.EventList[index+step]
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
                    raise ValueError
                
                i = index+1
                count = 0
                while(i<len(self.EventList)):
                    if isinstance(self.EventList[i],eventClass):
                        count += 1
                        if count == step:
                            return self.EventList[i]
                    i+=1
                return None
        else: #reference should be timestamp
            if eventType==None:
                diffList = numpy.zeros(len(self._EventList))
                for i in range(len(self._EventList)):
                    if isinstance(self._EventList[i],GazeParser.Core.MessageData):
                        diffList[i] = self._EventList[i].time - event
                    else:
                        diffList[i] = self._EventList[i].startTime - event
                
                prevIndices = numpy.where(diffList>0)[0]
                if len(prevIndices)==0:
                    return None
                else:
                    return self._EventList[prevIndices[0]]
            else:
                if eventType.lower() == 'saccade':
                    targetList = self._Sac
                    diffList = self.getSacTime()[:,0] - event
                elif eventType.lower() == 'fixation':
                    targetList = self._Fix
                    diffList = self.getFixTime()[:,0] - event
                elif eventType.lower() == 'message':
                    targetList = self._Msg
                    diffList = self.getMsgTime() - event
                elif eventType.lower() == 'blink':
                    targetList = self._Blink
                    diffList = self.getBlinkTime()[:,0] - event
                else:
                    raise ValueError
                
                prevIndices = numpy.where(diffList>0)[0]
                if len(prevIndices)==0:
                    return None
                else:
                    return targetList[prevIndices[0]]
    
    def PixelToDeg(self,pixValue):
        """
        Convert screen pixel to visual angle.
        
        :param float pixValue:
            A value in visual angle.
        """
        return pixValue*self.pix2deg
    
    def DegToPixel(self,degValue):
        """
        Convert visual angle to screen pixel.
        
        :param float degValue:
            A value in screen pixel.
        """
        return degValue*self.deg2pix
    
    nSac = property(lambda self: self._nSac)
    """Number of saccades detected in this trial."""
    
    nFix = property(lambda self: self._nFix)
    """Number of fixations detected in this trial."""
    
    nMsg = property(lambda self: self._nMsg)
    """Number of messages recorded in this trial."""
    
    nBlink = property(lambda self: self._nBlink)
    """Number of blinks detected in this trial."""
    
    L = property(lambda self: self._L)
    """List of gaze position (x,y) of left eye."""
    
    R = property(lambda self: self._R)
    """List of gaze position (x,y) of right eye."""
    
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
    
    EventList = property(lambda self: self._EventList)
    """List of all events (saccades, fixations, blinks and messages) in chronological order."""
    
    config = property(lambda self: self._config)
    """:class:`~GazeParser.Configuration.Config` object which holds recording and parsing options."""
    
    def getPathLength(self,sac):
        """
        Get saccade length along saccade trajectory.  If a list of SaccadeData object is provided,
        a list of the length of each saccades in the input list is returned.
        
        :param sac:
            a SaccadeData object or a list of SaccadeData object.
        
        :return:
            a float value or a numpy.ndarray object depending on the argument
        """
        if isinstance(sac, GazeParser.Core.SaccadeData):
            if self._L != None:
                dx = numpy.diff(self._L[sac._startIndex:sac._endIndex,0])
                dy = numpy.diff(self._L[sac._startIndex:sac._endIndex,1])
                l = numpy.sum(numpy.sqrt(dx**2 + dy**2))
                
            if self._R != None:
                dx = numpy.diff(self._R[sac._startIndex:sac._endIndex,0])
                dy = numpy.diff(self._R[sac._startIndex:sac._endIndex,1])
                r = numpy.sum(numpy.sqrt(dx**2 + dy**2))
            
            if self._recordedEye == 'L':
                return l
            elif self._recordedEye == 'R':
                return r
            else: #binocular
                return l+r/2
        else:
            if self._recordedEye == 'L' or self._recordedEye == 'B':
                l = numpy.zeros((len(sac),1))
                for i in range(len(sac)):
                    dx = numpy.diff(self._L[sac[i]._startIndex:sac[i]._endIndex,0])
                    dy = numpy.diff(self._L[sac[i]._startIndex:sac[i]._endIndex,1])
                    l[i] = numpy.sum(numpy.sqrt(dx**2 + dy**2))
            
            if self._recordedEye == 'R' or self._recordedEye == 'B':
                r = numpy.zeros((len(sac),1))
                for i in range(len(sac)):
                    dx = numpy.diff(self._R[sac[i]._startIndex:sac[i]._endIndex,0])
                    dy = numpy.diff(self._R[sac[i]._startIndex:sac[i]._endIndex,1])
                    r[i] = numpy.sum(numpy.sqrt(dx**2 + dy**2))
            
            if self._recordedEye == 'L':
                return l
            elif self._recordedEye == 'R':
                return r
            else: #binocular
                return (l+r)/2.0
            
    
    def getTimeInRectangleRegion(self,rectangle):
        pass
