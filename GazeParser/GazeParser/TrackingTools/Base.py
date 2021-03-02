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

import socket
import select
import time
import datetime
import random

import os
import sys
import warnings

if sys.version_info[0] == 2:
    import ConfigParser as configparser
else:
    import configparser
import shutil

import numpy
import GazeParser
import GazeParser.Configuration

ControllerDefaults = {
    'IMAGE_WIDTH': 320,
    'IMAGE_HEIGHT': 240,
    'PREVIEW_WIDTH': 640,
    'PREVIEW_HEIGHT': 480,
    'VALIDATION_SHIFT': 20,
    'SHOW_CALDISPLAY': True,
    'NUM_SAMPLES_PER_TRGPOS': 10,
    'CALTARGET_MOTION_DURATION': 1.0,
    'CALTARGET_DURATION_PER_POS': 2.0,
    'CAL_GETSAMPLE_DELAY': 0.4,
    'CAL_SELF_PACED': False,
    'CAL_GETSAMPLE_DELAY_SELFPACED': 1.0,
    'TRACKER_IP_ADDRESS': '192.168.1.1',
    'MAX_CAL_POINTS':18,
    'MAX_SAMPLES_PER_TRGPOS':50,
    'CAMERA_SAMPLING_RATE':100.0
}

numKeyDict = {
        '1':1, 'num_1':1, '2':2, 'num_2':2, '3':3, 'num_3':3,
        '4':4, 'num_4':4, '5':5, 'num_5':5, '6':6, 'num_6':6,
        '7':7, 'num_7':7, '8':8, 'num_8':8, '9':9, 'num_9':9
    }

class BaseController(object):
    """
    Base class for SimpleGazeTracker controllers. Following methods must be
    overridden.

    - self.setCalibrationScreen(self, screen)
    - self.updateScreen(self)
    - self.setCameraImage(self)
    - self.putCalibrationResultsImage(self)
    - self.setCalibrationTargetStimulus(self, stim)
    - self.setCalibrationTargetPositions(self, area, calposlist)
    - self.getKeys(self)
    - self.getMousePressed(self)
    - self.verifyFixation(self, maxTry, permissibleError, key, message, ...)
    - self.setCurrentScreenParamsToConfig(self)
    """
    def __init__(self, configFile=None):
        """
        Initialize controller.

        :param str configFile: name of the configuration file.
            If None, TrackingTools.cfg in the GazeParser configuration directory
            is used. Default value is None.
        """
        cfgp = configparser.SafeConfigParser()
        cfgp.optionxform = str

        if configFile is None:  # use default settings
            ConfigFile = os.path.join(GazeParser.configDir, 'TrackingTools.cfg')
            if not os.path.isfile(ConfigFile):  # TrackingTools.cfg is not found
                shutil.copyfile(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'TrackingTools.cfg'), ConfigFile)
        else:
            ConfigFile = configFile
        cfgp.read(ConfigFile)

        for key in list(ControllerDefaults.keys()):
            try:
                value = cfgp.get('Controller', key)
                if isinstance(ControllerDefaults[key], int):
                    if value == 'True':
                        setattr(self, key, True)
                    elif value == 'False':
                        setattr(self, key, False)
                    else:
                        setattr(self, key, int(value))
                elif isinstance(ControllerDefaults[key], float):
                    setattr(self, key, float(value))
                else:
                    setattr(self, key, value)

            except:
                print('Warning: %s is not properly defined in TrackingTools.cfg. Default value is used.' % (key))
                setattr(self, key, ControllerDefaults[key])

        self.showCalImage = False
        self.showCameraImage = False
        self.showCalTarget = False
        self.calTargetPosition = (0, 0)
        self.messageText = '----'
        self.PILimg = Image.new('L', (self.IMAGE_WIDTH, self.IMAGE_HEIGHT))

        self.calArea = []
        self.calTargetPos = []
        self.valTargetPos = []
        self.calibrationResults = None
        self.calAreaSet = False
        self.calTargetPosSet = False

        self.prevBuffer = b''

        self.captureNo = 0
        self.datafilename = ''

        if sys.platform == 'win32':
            self.clock = time.clock
        else:
            self.clock = time.time

        self.latestCalibrationResultsList = None

    def isDummy(self):
        """
        Returns True if this controller is dummy.
        """
        return False

    def setReceiveImageSize(self, size):
        """
        Set size of camera image to IMAGE_WIDTH and IMAGE_HEIGHT, then
        resize image buffer.

        :param sequence size: sequence of two integers (width, height).
        """
        self.IMAGE_WIDTH = size[0]
        self.IMAGE_HEIGHT = size[1]
        self.PILimg = Image.new('L', size)

    def setPreviewImageSize(self, size):
        """
        Set size of preview image. It is recommened that ratio of height and width
        is set to be the same as that of camera image.

        :param sequence size: sequence of two integers (width, height).
        """
        self.PREVIEW_WIDTH = size[0]
        self.PREVIEW_HEIGHT = size[1]

    def setCalibrationTargetPositions(self, area, calposlist):
        """
        Send calibration area and calibration target positions to the Tracker
        Host PC. This method must be called before starting calibration.

        The order of calibration target positions is shuffled each time calibration
        is performed. However, the first target position (i.e. the target position
        at the beginning of calibration) is always the first element of the list.
        In the following example, the target is always presented at (512, 384) a the
        beginning of calibration. ::

            calArea = (0, 0, 1024, 768)
            calPos = ((512, 384),
                      (162, 134), (512, 134), (862, 134),
                      (162, 384), (512, 384), (862, 384),
                      (162, 634), (512, 634), (862, 634))
            tracker.CalibrationTargetPositions(calArea, calPos)

        :param sequence area: a sequence of for elements which represent
            left, top, right and bottom of the calibration area.
        :param sequence calposlist: a list of (x, y) positions of calibration
            target.
        """
        area = list(area)
        calposlist = list(calposlist)

        if len(area) != 4:
            print('Calibration area must be a sequence of 4 integers.')
            self.calAreaSet = False
            return
        try:
            for i in range(4):
                area[i] = int(area[i])
        except:
            print('Calibration area must be a sequence of 4 integers.')
            self.calAreaSet = False
            return

        if area[2] < area[0] or area[3] < area[1]:
            print('Calibration area is wrong.')
            self.calAreaSet = False
            return

        self.calArea = tuple(area)
        self.calAreaSet = True

        for i in range(len(calposlist)):
            if len(calposlist[i]) != 2:
                print('Calibration position must be a sequence of 2 integers.')
                self.calTargetPosSet = False
                return
            try:
                calposlist[i] = (int(calposlist[i][0]), int(calposlist[i][1]))
            except:
                print('Calibration position must be a sequence of 2 integers.')
                self.calTargetPosSet = False
                return

        isDifferentPositionIncluded = False
        for i in range(1, len(calposlist)):
            if calposlist[i][0] != calposlist[0][0] or calposlist[i][1] != calposlist[0][1]:
                isDifferentPositionIncluded = True
                break
        if not isDifferentPositionIncluded:
            print('At least one different position must be specified.')
            self.calTargetPosSet = False
            return

        self.calTargetPos = calposlist[:]
        self.calTargetPosSet = True

    def setValidationShift(self, size):
        """
        Set shift of the target position in the Validation process.
        If this parameter is 10, target position in the Validation is
        10 pixel distant from target position in the Calibration process.

        :param float size: amount of shift.
        """

        self.VALIDATION_SHIFT = size

    def connect(self, address='', portSend=10000, portRecv=10001):
        """
        Connect to the Tracker Host PC. Because most of methods communicate with
        the Tracker Host PC, this method should be called immediately after
        controller object is created.

        :param str address: IP address of SimpeGazeTracker (e.g. '192.168.1.2').
            If the value is '', TRACKER_IP_ADDRESS in the configuration file is
            used.  Default value is ''.
        :param int portSend: TCP/IP port for sending command to Tracker.
            This value must be correspond to configuration of the Tracker.
            Default value is 10000.
        :param int portRecv: TCP/IP port for receiving data from Tracker.
            This value must be correspond to configuration of the Tracker.
            Default value is 10001.
        """
        if address == '':
            address = self.TRACKER_IP_ADDRESS

        print('Tracker IP address:' + address)
        print('Port send:%d  receive:%d' % (portSend, portRecv))
        print('Request connection ...')
        self.sendSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sendSock.connect((address, portSend))
        self.sendSock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSock.bind(('', portRecv))
        self.serverSock.listen(1)
        self.serverSock.setblocking(0)

        self.readSockList = [self.serverSock]

        print('Waiting connection... ', end='')
        self.sv_connected = False
        while not self.sv_connected:
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                if x is self.serverSock:
                    (conn, addr) = self.serverSock.accept()
                    self.readSockList.append(conn)
                    self.sv_connected = True
                    print('Accepted')

    def __del__(self):
        try:
            if hasattr(self, 'readSockList'):
                for i in range(len(self.readSockList)):
                    self.readSockList[-(i+1)].close()
                self.readSockList = []

            if hasattr(self, 'sendSock'):
                self.sendSock.close()
            if hasattr(self, 'serverSock'):
                self.serverSock.close()
        except:
            print('Warning: server socket may not be correctly closed.')

    def openDataFile(self, filename, overwrite=False, config=None):
        """
        Send a command to open data file on the Tracker Host PC.
        The data file is created in the DATA directory at the
        Tracker Host PC.

        Currently, relative or absolute paths are NOT supported.

        :param str filename: Name of data file.
        :param bool overwrite: If true, SimpleGazeTracker overwrites
            existing data file.  If false, SimpleGazeTracker renames
            existing data file. Default value is False.
        :param config: If parameters of GazeParser is provided as
            a dict or :class:`GazeParser.Configuration.Config` object,
            parameters are inserted in SimpleGazeTracker data file.
            Default value is None.

        .. note::
            Non-ascii code is not supprted as a file name.
        """
        if config is None:
            pass
        elif isinstance(config, GazeParser.Configuration.Config):
            config_dict = config.getParametersAsDict()
        elif isinstance(config, dict):
            config_dict = config
        else:
            raise ValueError('config must be dict or GazeParser.Configuration.Config obejct.')

        if overwrite:
            self.sendCommand('openDataFile'+chr(0)+filename+chr(0)+'1'+chr(0))
        else:
            self.sendCommand('openDataFile'+chr(0)+filename+chr(0)+'0'+chr(0))
        self.datafilename = filename
        
        if config is not None:
            configlist = []
            for key in GazeParser.Configuration.GazeParserOptions:
                if key in config_dict:
                    configlist.append('#'+key+','+str(config_dict[key]))

            message = '/'.join(configlist)
            self.sendCommand('insertSettings'+chr(0)+message+chr(0))

    def closeDataFile(self):
        """
        Send a command to close data file on the Tracker Host PC.
        """
        self.sendCommand('closeDataFile'+chr(0))
        self.datafilename = ''

    def sendMessage(self, message):
        """
        Send a command to insert message to data file.
        Timestamp is automatically appended at the Tracker Host PC.

        :param str message: Message text to be inserted.

        .. note::
            If an unicode string is passed as a message,
            it is converted to UTF-8 before sending.
        """
        if sys.version_info[0] == 2 and isinstance(message, unicode):
            message = message.encode('utf-8')
        self.sendCommand('insertMessage'+chr(0)+message+chr(0))

    def sendSettings(self, configDict):
        """
        This method is deprecated. Use "config" option of 
        :func:`~GazeParser.TrackingTools.BaseController.openDataFile` instead.
        """
        warnings.warn('sendSettings is deprecated. Use "config" option of openDataFile instead.')

        configlist = []
        # for key in configDict.keys():
        #    configlist.append('#'+key+','+str(configDict[key]))
        for key in GazeParser.Configuration.GazeParserOptions:
            if key in configDict:
                configlist.append('#'+key+','+str(configDict[key]))

        message = '/'.join(configlist)
        self.sendCommand('insertSettings'+chr(0)+message+chr(0))

    def startRecording(self, message='', wait=0.1):
        """
        Send a command to start recording.
        Message can be inserted to describe trial condition and so on.

        :param str message:
            message text. Default value is ''
        :param float wait:
            Duration of waiting for processing on the Tracker Host PC.
            Unit is second. Default value is 0.1

        .. note::
            If an unicode string is passed as a message,
            it is converted to UTF-8 before sending.
        """
        if sys.version_info[0] == 2 and isinstance(message, unicode):
            message = message.encode('utf-8')
        self.sendCommand('startRecording'+chr(0)+message+chr(0))
        time.sleep(wait)

    def stopRecording(self, message='', wait=0.1):
        """
        Send a command to stop recording.
        Message can be inserted to describe exit code and so on.

        :param str message:
            message text. Default value is ''
        :param float wait:
            Duration of waiting for processing on the Tracker Host PC.
            Unit is second. Default value is 0.1

        .. note::
            If an unicode string is passed as a message,
            it is converted to UTF-8 before sending.
        """
        if sys.version_info[0] == 2 and isinstance(message, unicode):
            message = message.encode('utf-8')
        self.sendCommand('stopRecording'+chr(0)+message+chr(0))
        time.sleep(wait)

    def startMeasurement(self, wait=0.1):
        """
        Send a command to start measurement without recording.
        This method is the same as startRecording() except data is not output
        to the data file.  This method is called by getSpatialError().
        Usually, you need not call this method.

        :param float wait:
            Duration of waiting for processing on the Tracker Host PC.
            Unit is second. Default value is 0.1
        """
        self.sendCommand('startMeasurement'+chr(0))
        time.sleep(wait)

    def stopMeasurement(self, wait=0.1):
        """
        Send a command to stop measurement.
        See satrtMeasurement() for detail.

        :param float wait:
            Duration of waiting for processing on the Tracker Host PC.
            Unit is second. Default value is 0.1
        """
        self.sendCommand('stopMeasurement'+chr(0))
        time.sleep(wait)

    def getEyePosition(self, timeout=0.02, getPupil=False, ma=1):
        """
        Send a command to get current gaze position.

        :param float timeout:
            If the Tracker Host PC does not respond within this duration, tuple of
            Nones are returned. Unit is second. Default value is 0.02
        :param bool getPupil:
            If true, pupil size is returned with gaze position.
        :param int ma:
            If this value is 1, the latest position is returned. If more than 1,
            moving average of the latest N samples is returned (N is equal to
            the value of this parameter). Default value is 1.
        :return:
            When recording mode is monocular, return value is a tuple of 2 or 3
            elements.  The first two elements represents holizontal(X) and
            vertical(Y) gaze position in screen corrdinate. If getPupil is true,
            area of pupil is returned as the third element of the tuple.
            When recording mode is binocular and getPupil is False, return value
            is (Left X, Left Y, Right X, Right Y). If getPupil is True, return
            value is (Left X, Left Y, Right X, Right Y, Left Pupil, Right Pupil).
        """
        if ma < 1:
            raise ValueError('ma must be equal or larger than 1.')
        self.sendCommand('getEyePosition'+chr(0)+str(ma)+chr(0))
        hasGotEye = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                # print('GetEyePosition timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getEyePosition: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotEye = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        if hasGotEye:
            try:
                retval = [int(x) for x in data.split(b',')]
                if self.isMonocularRecording:
                    # if recording mode is monocular, length of retval must be 3.
                    if len(retval) == 3:
                        if getPupil:
                            return retval
                        else:
                            return retval[:2]
                else:
                    # if recording mode is binocular, length of retval must be 6.
                    if len(retval) == 6:
                        if getPupil:
                            return retval
                        else:
                            return retval[:4]
            except:
                print('getEyePosition: non-float value is found in the received data.')

        # timeout or wrong data length
        if self.isMonocularRecording:
            if getPupil:
                return [None, None, None]
            else:
                return [None, None]
        else:
            if getPupil:
                return [None, None, None, None, None, None]
            else:
                return [None, None, None, None]

    def getEyePositionList(self, n, timeout=0.02, getPupil=False):
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
        if getPupil:
            getPupilFlagStr = '1'
        else:
            getPupilFlagStr = '0'
        self.sendCommand('getEyePositionList'+chr(0)+str(n)+chr(0)+getPupilFlagStr+chr(0))
        hasGotEye = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                # print('GetEyePositionList timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(8192)
                except:
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getEyePositionList: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotEye = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        if hasGotEye:
            if len(data) == 0:
                print('getEyePositionList: No data')
                return None

            try:
                retval = numpy.array([float(x) for x in data.split(b',')])
            except:
                print('getEyePositionList: non-float value is found in the received data.')
                return None

            try:
                if self.isMonocularRecording:
                    if getPupil:
                        return retval.reshape((-1, 4))
                    else:
                        return retval.reshape((-1, 3))
                else:
                    if getPupil:
                        return retval.reshape((-1, 7))
                    else:
                        return retval.reshape((-1, 5))
            except:
                print('getEyePositionList: data was not successfully received.')
                return None

        return None

    def getWholeEyePositionList(self, timeout=0.2, getPupil=False):
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
        if getPupil:
            getPupilFlagStr = '1'
        else:
            getPupilFlagStr = '0'
        self.sendCommand('getWholeEyePositionList'+chr(0)+getPupilFlagStr+chr(0))
        hasGotEye = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                # print('GetWholeEyePositionList timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(8192)
                except:
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getWholeEyePositionList: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotEye = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        if hasGotEye:
            if len(data) == 0:
                print('getWholeEyePositionList: No data')
                return None
            try:
                retval = numpy.array([float(x) for x in data.split(b',')])
            except:
                print('getWholeEyePositionList: non-float value is found in the received data.')
                return None

            try:
                if self.isMonocularRecording:
                    if getPupil:
                        return retval.reshape((-1, 4))
                    else:
                        return retval.reshape((-1, 3))
                else:
                    if getPupil:
                        return retval.reshape((-1, 7))
                    else:
                        return retval.reshape((-1, 5))
            except:
                print('getWholeEyePositionList: data was not successfully received.')
                return None

        return None

    def getWholeMessageList(self, timeout=0.2):
        """
        Transfer whole messages inserted during the most recent recording.
        It is recommended that this method is called immediately after
        :func:`~GazeParser.TrackingTools.BaseController.stopRecording` is called.

        .. note:: This method can be called during recording - but please note
            that this method takes tens or hundreds milliseconds. It may cause
            failure in data acquisition and/or stimulus presentation.

        :param float timeout:
            If the Tracker Host PC does not respond within this duration, tuple of
            Nones are returned. Unit is second. Default value is 0.2
        :return:
            A list of messages. Each message has three elements. The first one is
            '#MESSAGE', the second one is timestamp, and the last one is message
            text.

            If length of received data is zero or data conversion is failed,
            [] is returned.
        """
        self.sendCommand('getWholeMessageList'+chr(0))
        hasGotData = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                # print('GetWholeEyePositionList timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(8192)
                except:
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getWholeMessageList: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotData = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        ret = []
        try:
            msglist = data.split('\n')
            for msg in msglist:
                m = msg.split(',')
                if(len(m) == 3):
                    ret.append([float(m[1]), m[2]])
                elif(len(m) > 3):
                    ret.append([float(m[1]), ','.join(m[2:])])
        except:
            print('getWholeMessageList:conversion failed - possibly failure in data transfer.')
            return []

        return ret

    def getCurrentMenuItem(self, timeout=0.2):
        """
        Get current menu item on the Tracker Host PC as a text.
        *Usually, you don't need use this method.*

        :param float timeout:
            If the Tracker Host PC does not respond within this duration, '----'
            is returned. Unit is second. Default value is 0.2
        :return:
            Text.
        """
        self.sendCommand('getCurrMenu'+chr(0))
        hasGotMenu = False
        isInLoop = True
        data = self.prevBuffer
        startTime = self.clock()
        while isInLoop:
            if b'\0' in data:
                delimiterIndex = data.index(b'\0')
                if delimiterIndex+1 < len(data):
                    print('getCurrentMenuItem: %d bytes after \\0' % (len(data)-(delimiterIndex+1)))
                    self.prevBuffer = data[(delimiterIndex+1):]
                data = data[:delimiterIndex]
                hasGotMenu = True
                isInLoop = False
                break
            if self.clock()-startTime > timeout:
                # print('timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    # print('recv error in getCalibrationResults')
                    isInLoop = False
                if newData:
                    data += newData

        if hasGotMenu:
            if sys.version_info[0] > 2:
                return data.decode()
            else:
                return data
        return 'WARNING: menu string was not received.'

    def getCalibrationResults(self, timeout=0.2):
        """
        Get a summary of calibration results.
        *Usually, you don't need use this method.*

        :param float timeout:
            If the Host Tracker PC does not respond within this duration, '----'
            is returned. Unit is second. Default value is 0.2
        :return:
            a tuple mean error and maximum error. Mean and maximum error are
            the distance between calibration taget position and gaze position
            in screen corrdinate. When recording mode is monocular, return
            value is (mean error, maximum error). When binocular, return
            value is a tuple of 4 elements: the former 2 elements correspond to
            left eye and the latter 2 elements correspond to right eye.

        """
        self.sendCommand('getCalResults'+chr(0))
        hasGotCal = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                # print('timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    # print('recv error in getCalibrationResults')
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getCalibrationResults: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotCal = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        if hasGotCal:
            try:
                retval = [float(x) for x in data.split(b',')]
            except:
                print('getCalibrationResults: non-float value is found in the received data.')

            try:
                if len(retval) == 2:
                    self.isMonocularRecording = True
                    return retval
                elif len(retval) == 4:
                    self.isMonocularRecording = False
                    return retval
            except:
                print('getCalibrationResults: data was not successfully received.')

        return None

    def getCameraImage(self, timeout=0.2):
        """
        Get current camera image. If image data is successfully received,
        the data is set to self.PILimg.
        *Usually, you don't need use this method.*

        :param float timeout:
            If the Host Tracker PC does not respond within this duration, image
            is not updated. Unit is second. Default value is 0.2

        """
        self.sendCommand('getImageData'+chr(0))
        hasGotImage = False
        data = self.prevBuffer
        imgdata = []
        startTime = self.clock()
        while not hasGotImage:
            if b'\0' in data:
                delimiterIndex = data.index(b'\0')
                if delimiterIndex+1 < len(data):
                    print('getCameraImage: %d bytes after \\0' % (len(data)-(delimiterIndex+1)))
                    self.prevBuffer = data[(delimiterIndex+1):]
                if sys.version_info[0] > 2:
                    imgdata = [data[idx] for idx in range(delimiterIndex)]
                else:
                    imgdata = [ord(data[idx]) for idx in range(delimiterIndex)]
                hasGotImage = True
            if self.clock()-startTime > timeout:
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(16384)
                except:
                    # print('recv error in getameraImage')
                    hasGotImage = True
                    continue
                if newData:
                    data += newData

        if len(imgdata) == self.IMAGE_WIDTH*self.IMAGE_HEIGHT:
            self.PILimg.putdata(imgdata)
        elif len(imgdata) < self.IMAGE_WIDTH*self.IMAGE_HEIGHT:
            print('getCameraImage: got ', len(imgdata), 'bytes /expected ', self.IMAGE_WIDTH*self.IMAGE_HEIGHT, 'bytes IMAGE_WIDTH and IMAGE_HIGHT may be wrong, otherwise trouble occurs in communication with SimpleGazeTracker.')
            imgdata.extend([0 for i in range(self.IMAGE_WIDTH*self.IMAGE_HEIGHT-len(imgdata))])
            self.PILimg.putdata(imgdata)
        else:
            print('getCameraImage: got ', len(imgdata), 'bytes /expected ', self.IMAGE_WIDTH*self.IMAGE_HEIGHT, 'bytes IMAGE_WIDTH and IMAGE_HIGHT may be wrong, otherwise trouble occurs in communication with SimpleGazeTracker.')
            self.PILimg.putdata(imgdata[:self.IMAGE_WIDTH*self.IMAGE_HEIGHT])

    def sendCommand(self, command):
        """
        Send a raw Tracker command to the Tracker Host PC.

        *Usually, you don't need use this method.*
        """
        if sys.version_info[0] > 2 and isinstance(command, str):
            command = command.encode('utf-8')
        self.sendSock.send(command)

    def calibrationLoop(self):
        """
        Start calibration loop.  Following keys can be used to perform calibration.

        ======== ================================================
        Key      Description
        -------- ------------------------------------------------
        Z        Toggle camera image display.
        X        Toggle calibration results display.
        C        Start calibration (call doCalibration() method)
        V        Start validation (call doValidation() method)
        A        Toggle on/off of Z key functions.
        S        Save the latest calibration/validation data to
                 SimpleGazeTracker data file.
        I        Save camera image to SimpleGazeTracker data 
                 directory.
        ESC or Q Exit calibration
        ======== ================================================

        :return: 'escape' or 'q'
            depending on which key is pressed to terminate calibration loop.
        """
        if not (self.calTargetPosSet and self.calAreaSet):
            raise ValueError('Calibration parameters are not set.')

        if self.CAL_GETSAMPLE_DELAY + self.NUM_SAMPLES_PER_TRGPOS / self.CAMERA_SAMPLING_RATE > self.CALTARGET_DURATION_PER_POS-self.CALTARGET_MOTION_DURATION:
            warnings.warn('NUM_SAMPLES_PER_TRGPOS may be too large to complete sample acquisition.'
                '\nCAL_GETSAMPLE_DELAY + (NUM_SAMPLES_PER_TRGPOS / CAMERA_SAMPLING_RATE) must be '
                'shorter than CALTARGET_DURATION_PER_POS-CALTARGET_MOTION_DURATION\n'
                'NUM_SAMPLES_PER_TRGPOS:{}\nCAMERA_SAMPLING_RATE:{}\nCAL_GETSAMPLE_DELAY:{}\n'
                'CALTARGET_DURATION_PER_POS:{}\nCALTARGET_MOTION_DURATION:{}'.format(
                    self.NUM_SAMPLES_PER_TRGPOS, self.CAMERA_SAMPLING_RATE, self.CAL_GETSAMPLE_DELAY,
                    self.CALTARGET_DURATION_PER_POS, self.CALTARGET_MOTION_DURATION
                ))

        if self.NUM_SAMPLES_PER_TRGPOS > self.MAX_SAMPLES_PER_TRGPOS:
            warnings.warn('NUM_SAMPLES_PER_TRGPOS ({}) is smaller than MAX_SAMPLES_PER_TRGPOS ({}).'.format(
                self.NUM_SAMPLES_PER_TRGPOS, self.MAX_SAMPLES_PER_TRGPOS))

        self.messageText = self.getCurrentMenuItem()
        self.showCalTarget = False
        self.showCameraImage = False
        self.showCalImage = False
        self.sendCommand('toggleCalResult'+chr(0)+'0'+chr(0))
        while True:
            keys = self.getKeys()
            for key in keys:
                if key == 'escape':
                    return 'escape'
                elif key == 'up':
                    self.sendCommand('key_UP'+chr(0))
                    time.sleep(0.05)
                    self.messageText = self.getCurrentMenuItem()
                elif key == 'down':
                    self.sendCommand('key_DOWN'+chr(0))
                    time.sleep(0.05)
                    self.messageText = self.getCurrentMenuItem()
                elif key == 'a':
                    if self.SHOW_CALDISPLAY:
                        self.SHOW_CALDISPLAY = False
                        self.showCameraImage = False
                        self.showCalImage = False
                    else:
                        self.SHOW_CALDISPLAY = True
                elif key == 'z':
                    if self.SHOW_CALDISPLAY:
                        self.showCameraImage = not self.showCameraImage
                    else:
                        self.showCameraImae = False
                elif key == 'x':
                    if self.SHOW_CALDISPLAY:
                        self.showCalImage = not self.showCalImage
                        if self.showCalImage:
                            self.sendCommand('toggleCalResult'+chr(0)+'1'+chr(0))
                        else:
                            self.sendCommand('toggleCalResult'+chr(0)+'0'+chr(0))
                    else:
                        self.showCalImage = False
                        self.sendCommand('toggleCalResult'+chr(0)+'0'+chr(0))
                elif key == 'c':
                    self.doCalibration()
                elif key == 'v':
                    if self.calibrationResults is not None:
                        self.showCameraImage = False
                        self.showCalImage = False
                        self.doValidation()
                elif key == 'm':
                    self.doManualCalibration()
                elif key == 's':
                    self.sendCommand('saveCalValResultsDetail'+chr(0))
                elif key == 'i':
                    self.captureNo += 1
                    datestr = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
                    if self.datafilename == '':
                        self.sendCommand('saveCameraImage'+chr(0)+'GP_'+datestr+'_'+str(self.captureNo)+'.bmp'+chr(0))
                    else:
                        self.sendCommand('saveCameraImage'+chr(0)+self.datafilename+'_'+datestr+'_'+str(self.captureNo)+'.bmp'+chr(0))
                elif key == 'q':
                    self.sendCommand('key_Q'+chr(0))
                    return 'q'

                elif key == 'left':
                    self.sendCommand('key_LEFT'+chr(0))
                    time.sleep(0.05)
                    self.messageText = self.getCurrentMenuItem()
                elif key == 'right':
                    self.sendCommand('key_RIGHT'+chr(0))
                    time.sleep(0.05)
                    self.messageText = self.getCurrentMenuItem()

            # get camera image
            if self.showCameraImage:
                self.getCameraImage()
                self.setCameraImage()

            # draw screen
            self.updateScreen()

    def getCalibrationResultsDetail(self, timeout=0.2):
        """
        Get detailed calibration results.

        *Usually, you don't need use this method because this method
        is automatically called form doCalibration() and doValidation().*

        :param float timeout:
            If the Tracker Host PC does not respond within this duration, '----'
            is returned. Unit is second. Default value is 0.2
        :return:
            Detailed Calibration
        """
        self.sendCommand('getCalResultsDetail'+chr(0))
        hasGotCal = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                # print('timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    # print('recv error in getCalibrationResults')
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getCalibrationResultsDetail: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotCal = True
                        isInLoop = False
                        break
                    else:
                        data += newData

        self.latestCalibrationResultsList = None

        if hasGotCal:
            try:
                retval = [float(x) for x in data.split(b',')]
            except:
                print('getCalibrationResultsDetail: non-float value is found in the received data.')

            try:
                if self.isMonocularRecording:
                    if len(retval) % 4 != 0:
                        print('getCalibrationResultsDetail: illeagal data', retval)
                        self.putCalibrationResultsImage()
                        return None

                    self.latestCalibrationResultsList = []
                    for i in range(int(len(retval)/4)):
                        self.latestCalibrationResultsList.append(retval[4*i:4*i+4])
                else:
                    if len(retval) % 6 != 0:
                        print('getCalibrationResultsDetail: illeagal data', retval)
                        self.putCalibrationResultsImage()
                        return None

                    for i in range(int(len(retval)/6)):
                        self.latestCalibrationResultsList.append(retval[6*i:6*i+6])

            except:
                print('plotCalibrationResultsDetail: data was not successfully received.')

        self.plotCalibrationResultsDetail()

    def plotCalibrationResultsDetail(self):
        """
        Plot detailed calibration results.
        """

        draw = ImageDraw.Draw(self.PILimgCAL)
        draw.rectangle(((0, 0), self.PILimgCAL.size), fill=128)
        if self.SHOW_CALDISPLAY:
            self.showCalImage = True
        else:
            self.showCalImage = False

        if self.latestCalibrationResultsList is not None and len(self.latestCalibrationResultsList) > 0:
            if self.isMonocularRecording:
                for i in range(len(self.latestCalibrationResultsList)):
                    (x1,y1,x2,y2) = self.latestCalibrationResultsList[i]
                    draw.line(((x1+self.calResultScreenOrigin[0], y1+self.calResultScreenOrigin[1]),
                              (x2+self.calResultScreenOrigin[0], y2+self.calResultScreenOrigin[1])),
                              fill=32)
            else:
                for i in range(len(self.latestCalibrationResultsList)):
                    (x1,y1,x2,y2,x3,y3) = self.latestCalibrationResultsList[i]
                    draw.line(((x1+self.calResultScreenOrigin[0], y1+self.calResultScreenOrigin[1]),
                              (x2+self.calResultScreenOrigin[0], y2+self.calResultScreenOrigin[1])),fill=32)
                    draw.line(((x1+self.calResultScreenOrigin[0], y1+self.calResultScreenOrigin[1]),
                              (x3+self.calResultScreenOrigin[0], y3+self.calResultScreenOrigin[1])),fill=224)


        self.putCalibrationResultsImage()

    def overlayMarkersToCalScreen(self, marker1=[], marker2=[]):
        '''
        Draw markers and frame on the calibration result.
        
        :param marker1: a list of positions of open cirlces.
        :param marker2: a list of positions of filled cirlces.
        '''

        draw = ImageDraw.Draw(self.PILimgCAL)

        for j in range(len(marker1)):
            x1 = marker1[j][0]+self.calResultScreenOrigin[0]-16
            x2 = marker1[j][0]+self.calResultScreenOrigin[0]+16
            y1 = marker1[j][1]+self.calResultScreenOrigin[1]-16
            y2 = marker1[j][1]+self.calResultScreenOrigin[1]+16
            draw.arc((x1,y1,x2,y2), 0, 360, 64)

        for j in range(len(marker2)):
            x1 = marker2[j][0]+self.calResultScreenOrigin[0]-8
            x2 = marker2[j][0]+self.calResultScreenOrigin[0]+8
            y1 = marker2[j][1]+self.calResultScreenOrigin[1]-8
            y2 = marker2[j][1]+self.calResultScreenOrigin[1]+8
            draw.ellipse((x1,y1,x2,y2), 0)

        self.putCalibrationResultsImage()


    def doCalibration(self, allowRecalibration = True):
        """
        Start calibration process.
        """
        
        #all points are used for the first time
        self.indexList = list(range(1, len(self.calTargetPos)))
        while True:
            random.shuffle(self.indexList)
            if self.calTargetPos[self.indexList[0]][0] != self.calTargetPos[0][0] or self.calTargetPos[self.indexList[0]][1] != self.calTargetPos[0][1]:
                break
        self.indexList.insert(0, 0)

        self.sendCommand('startCal'+chr(0)+str(self.calArea[0])+','+str(self.calArea[1])+','
                         + str(self.calArea[2])+','+str(self.calArea[3])+chr(0)+'1'+chr(0))

        isCalibrationLoop = True
        
        while isCalibrationLoop:
            self.showCameraImage = False
            self.showCalImage = False

            calCheckList = [False for i in range(len(self.indexList))]
            self.showCalTarget = True
            prevSHOW_CALDISPLAY = self.SHOW_CALDISPLAY
            self.SHOW_CALDISPLAY = False
            self.calTargetPosition = self.calTargetPos[self.indexList[0]]

            elimlist = []

            isWaitingKey = True
            while isWaitingKey:
                if self.getMousePressed()[0] == 1:  # left mouse button
                    isWaitingKey = False
                    break
                keys = self.getKeys()
                for key in keys:
                    if key == 'space':
                        isWaitingKey = False
                        break
                self.updateCalibrationTargetStimulusCallBack(0, 0, self.calTargetPos[self.indexList[0]], self.calTargetPosition)
                self.updateScreen()

            prevTargetPosition = 0  # 0 is starting position
            currentTargetPosition = 1 # 1 is the first position
            startTime = self.clock()
            samplingStartTime = None

            while True:
                keys = self.getKeys()
                if self.CAL_SELF_PACED:
                    t = self.clock()-startTime
                    if not calCheckList[prevTargetPosition] and t > self.CALTARGET_MOTION_DURATION:
                        if 'space' in keys:
                            self.sendCommand('getCalSample'+chr(0)+str(self.calTargetPos[self.indexList[currentTargetPosition]][0])
                                             + ','+str(self.calTargetPos[self.indexList[currentTargetPosition]][1])+','+str(self.NUM_SAMPLES_PER_TRGPOS)+chr(0))
                            calCheckList[prevTargetPosition] = True
                            samplingStartTime = t
                    if samplingStartTime is not None:
                        if t > samplingStartTime+self.CAL_GETSAMPLE_DELAY_SELFPACED:
                            # prepare for next position
                            startTime = self.clock()
                            samplingStartTime = None
                            prevTargetPosition = currentTargetPosition
                            currentTargetPosition += 1
                            if currentTargetPosition >= len(self.indexList): # all positions have been measured
                                break
                            continue
                else:
                    currentTime = self.clock()-startTime
                    t = currentTime % self.CALTARGET_DURATION_PER_POS
                    prevTargetPosition = int((currentTime-t)/self.CALTARGET_DURATION_PER_POS)
                    currentTargetPosition = prevTargetPosition+1
                    if currentTargetPosition >= len(self.indexList): # all positions have been measured
                        break
                    if t > self.CALTARGET_MOTION_DURATION+self.CAL_GETSAMPLE_DELAY:
                        if not calCheckList[prevTargetPosition]:
                            self.sendCommand('getCalSample'+chr(0)+str(self.calTargetPos[self.indexList[currentTargetPosition]][0])
                                             + ','+str(self.calTargetPos[self.indexList[currentTargetPosition]][1])+','+str(self.NUM_SAMPLES_PER_TRGPOS)+chr(0))
                            calCheckList[prevTargetPosition] = True
                
                # calc target position
                if t < self.CALTARGET_MOTION_DURATION: # target is moving
                    p1 = t/self.CALTARGET_MOTION_DURATION
                    p2 = 1.0-t/self.CALTARGET_MOTION_DURATION
                    x = p1*self.calTargetPos[self.indexList[currentTargetPosition]][0] + p2*self.calTargetPos[self.indexList[prevTargetPosition]][0]
                    y = p1*self.calTargetPos[self.indexList[currentTargetPosition]][1] + p2*self.calTargetPos[self.indexList[prevTargetPosition]][1]
                    self.calTargetPosition = (x, y)
                else: # target is at the position
                    self.calTargetPosition = self.calTargetPos[self.indexList[currentTargetPosition]]
                
                # draw screen
                self.updateCalibrationTargetStimulusCallBack(t, currentTargetPosition, self.calTargetPos[self.indexList[currentTargetPosition]], self.calTargetPosition)
                self.updateScreen()

            self.showCalTarget = False
            self.SHOW_CALDISPLAY = prevSHOW_CALDISPLAY
            self.sendCommand('endCal'+chr(0))

            self.calibrationResults = self.getCalibrationResults()
            try:
                if self.isMonocularRecording:
                    self.messageText = 'AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
                else:
                    self.messageText = 'LEFT(black) AvgError:%.2f MaxError:%.2f / RIGHT(white) AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
                if allowRecalibration:
                    self.messageText += '\nUp/Down: select point  Left/Right/1-9: toggle mark\nSpace: retry  Enter: exit cal'
            except:
                self.messageText = 'Calibration/Validation failed.'

            self.getCalibrationResultsDetail()

            if not allowRecalibration:
                break

            markerIndex = 1
            self.overlayMarkersToCalScreen(marker2=[self.calTargetPos[markerIndex]])
            self.updateScreen()

            while True:
                keys = self.getKeys()
                if 'space' in keys:
                    if len(elimlist)==0:
                        #if elimlist is empty, then continue
                        continue
                    #delete marked points
                    self.deleteCalibrationDataSubset(elimlist)

                    #rebuild calibration target position list
                    elimidx = []
                    for idx in range(1,len(self.calTargetPos)):
                        if self.calTargetPos[idx] in elimlist:
                            elimidx.append(idx)
                    if len(elimidx) == 0:
                        #no recalibration point.
                        #usually this cannot be happen.
                        continue
                    elif len(elimidx) == 1: #only one recabliration point
                        #if recabliration point is equal to calTargetPos[0], the first position must not be equal to it.
                        if self.calTargetPos[elimidx[0]][0] == self.calTargetPos[0][0] and self.calTargetPos[elimidx[0]][1] == self.calTargetPos[0][1]:
                            while True:
                                tmpidx = random.randint(1, len(self.calTargetPos))
                                if tmpidx != elimidx[0]:
                                    break
                            self.indexList = [tmpidx, elimidx[0]]
                        #if recabliration point is not equal to calTargetPos[0], the first position should be 0.
                        else:
                            self.indexList = [0, elimidx[0]]
                    else:
                        while True:
                            random.shuffle(elimidx)
                            if self.calTargetPos[elimidx[0]][0] != self.calTargetPos[0][0] or self.calTargetPos[elimidx[0]][1] != self.calTargetPos[0][1]:
                                break
                        self.indexList = elimidx
                        self.indexList.insert(0,0)

                    #re-start manual calibration without flushing data
                    self.sendCommand('startCal'+chr(0)+str(self.calArea[0])+','+str(self.calArea[1])+','
                                     + str(self.calArea[2])+','+str(self.calArea[3])+chr(0)+'0'+chr(0))
                    break
                elif 'return' in keys:
                    isCalibrationLoop = False
                    break
                elif 'up' in keys:
                    markerIndex = markerIndex+1 if markerIndex<len(self.calTargetPos)-1 else 1  # avoid 0!
                elif 'down' in keys:
                    markerIndex = markerIndex-1 if markerIndex>1 else len(self.calTargetPos)-1   # avoid 0!
                elif 'left' in keys or 'right' in keys:
                    if self.calTargetPos[markerIndex] in elimlist:
                        elimlist.remove(self.calTargetPos[markerIndex])
                    else:
                        elimlist.append(self.calTargetPos[markerIndex])
                else:
                    for key in keys:
                        if key in numKeyDict and numKeyDict[key]<len(self.calTargetPos):
                            markerIndex = numKeyDict[key]
                            if self.calTargetPos[markerIndex] in elimlist:
                                elimlist.remove(self.calTargetPos[markerIndex])
                            else:
                                elimlist.append(self.calTargetPos[markerIndex])

                self.plotCalibrationResultsDetail()
                self.overlayMarkersToCalScreen(marker1=elimlist, marker2=[self.calTargetPos[markerIndex]])
                self.updateScreen()

        if allowRecalibration:
            nindex = self.messageText.find('\n')  #remove instruction
            if nindex>0:
                self.messageText = self.messageText[:nindex]
        self.plotCalibrationResultsDetail()
        self.updateScreen()


    def doValidation(self):
        """
        Start validation process.
        """
        self.sendCommand('startVal'+chr(0)+str(self.calArea[0])+','+str(self.calArea[1])+','
                         + str(self.calArea[2])+','+str(self.calArea[3])+chr(0))

        self.valTargetPos = []
        for p in self.calTargetPos:
            self.valTargetPos.append([p[0]+int((random.randint(0, 1)-0.5)*2*self.VALIDATION_SHIFT), p[1]+int((random.randint(0, 1)-0.5)*2*self.VALIDATION_SHIFT)])

        self.indexList = list(range(1, len(self.valTargetPos)))
        while True:
            random.shuffle(self.indexList)
            if self.valTargetPos[self.indexList[0]][0] != self.valTargetPos[0][0] or self.valTargetPos[self.indexList[0]][1] != self.valTargetPos[0][1]:
                break
        self.indexList.insert(0, 0)

        calCheckList = [False for i in range(len(self.valTargetPos))]
        self.showCalTarget = True
        prevSHOW_CALDISPLAY = self.SHOW_CALDISPLAY
        self.SHOW_CALDISPLAY = False
        self.calTargetPosition = self.valTargetPos[0]

        isWaitingKey = True
        while isWaitingKey:
            if self.getMousePressed()[0] == 1:  # left mouse button
                isWaitingKey = False
                break
            keys = self.getKeys()
            for key in keys:
                if key == 'space':
                    isWaitingKey = False
                    break
            self.updateScreen()

        prevTargetPosition = 0  # 0 is starting position
        currentTargetPosition = 1 # 1 is the first position
        startTime = self.clock()
        samplingStartTime = None

        while True:
            keys = self.getKeys()
            if self.CAL_SELF_PACED:
                t = self.clock()-startTime
                if not calCheckList[prevTargetPosition] and t > self.CALTARGET_MOTION_DURATION:
                    if 'space' in keys:
                        self.sendCommand('getValSample'+chr(0)+str(self.valTargetPos[self.indexList[currentTargetPosition]][0])
                                         + ','+str(self.valTargetPos[self.indexList[currentTargetPosition]][1])+','+str(self.NUM_SAMPLES_PER_TRGPOS)+chr(0))
                        calCheckList[prevTargetPosition] = True
                        samplingStartTime = t
                if samplingStartTime is not None:
                    if t > samplingStartTime+self.CAL_GETSAMPLE_DELAY_SELFPACED:
                        # prepare for next position
                        startTime = self.clock()
                        samplingStartTime = None
                        prevTargetPosition = currentTargetPosition
                        currentTargetPosition += 1
                        continue
                if currentTargetPosition >= len(self.indexList): # all positions have been measured
                    break
            else:
                currentTime = self.clock()-startTime
                t = currentTime % self.CALTARGET_DURATION_PER_POS
                prevTargetPosition = int((currentTime-t)/self.CALTARGET_DURATION_PER_POS)
                currentTargetPosition = prevTargetPosition+1
                if currentTargetPosition >= len(self.indexList):
                    break
                if t > self.CALTARGET_MOTION_DURATION+self.CAL_GETSAMPLE_DELAY:
                    if not calCheckList[prevTargetPosition]:
                        self.sendCommand('getValSample'+chr(0)+str(self.valTargetPos[self.indexList[currentTargetPosition]][0])
                                         + ','+str(self.valTargetPos[self.indexList[currentTargetPosition]][1])+','+str(self.NUM_SAMPLES_PER_TRGPOS)+chr(0))
                        calCheckList[prevTargetPosition] = True
            
            # calc target position
            if t < self.CALTARGET_MOTION_DURATION:
                p1 = t/self.CALTARGET_MOTION_DURATION
                p2 = 1.0-t/self.CALTARGET_MOTION_DURATION
                x = p1*self.valTargetPos[self.indexList[currentTargetPosition]][0] + p2*self.valTargetPos[self.indexList[prevTargetPosition]][0]
                y = p1*self.valTargetPos[self.indexList[currentTargetPosition]][1] + p2*self.valTargetPos[self.indexList[prevTargetPosition]][1]
                self.calTargetPosition = (x, y)
            else:
                self.calTargetPosition = self.valTargetPos[self.indexList[currentTargetPosition]]

            self.updateCalibrationTargetStimulusCallBack(t, currentTargetPosition, self.valTargetPos[self.indexList[currentTargetPosition]], self.calTargetPosition)
            self.updateScreen()

        self.showCalTarget = False
        self.SHOW_CALDISPLAY = prevSHOW_CALDISPLAY
        self.sendCommand('endVal'+chr(0))

        self.calibrationResults = self.getCalibrationResults()
        try:
            if self.isMonocularRecording:
                self.messageText = 'AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
            else:
                self.messageText = 'LEFT AvgError:%.2f MaxError:%.2f / RIGHT AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
        except:
            self.messageText = 'Calibration/Validation failed.'

        self.getCalibrationResultsDetail()

    def isCalibrationFinished(self):
        """
        Check whether calibration is performed at least once.

        :return: True if calibration is performed at least once.
        """
        if self.calibrationResults is None:
            return False
        else:
            return True

    def removeCalibrationResults(self):
        """
        Delete current calibration results.
        """
        self.calibrationResults = None

    def doManualCalibration(self):
        """
        Start manual calibration process.
        """
        self.sendCommand('startCal'+chr(0)+str(self.calArea[0])+','+str(self.calArea[1])+','
                         + str(self.calArea[2])+','+str(self.calArea[3])+chr(0)+'1'+chr(0))

        isCalibrationLoop = True
        
        while isCalibrationLoop:
            self.showCameraImage = False
            self.showCalImage = False

            self.showCalTarget = True
            prevSHOW_CALDISPLAY = self.SHOW_CALDISPLAY
            self.SHOW_CALDISPLAY = False
            calIndex = -1
            prevPos = (None, None)
            currentPos = (None, None)
            
            elimlist = []
            
            isCalibrating = True
            isWaitingSampleAcquisition = False
            startTime = self.clock()
            startAcquisitionTime = 0
            while isCalibrating:
                keys = self.getKeys()
                t = self.clock()
                if isWaitingSampleAcquisition:
                    if self.clock()-startAcquisitionTime > 1.0:
                        isWaitingSampleAcquisition = False
                else:
                    for key in keys:
                        if key == 'space':
                            if (0 <= calIndex < len(self.calTargetPos)) and (self.CALTARGET_MOTION_DURATION < t):
                                self.sendCommand('getCalSample'+chr(0)+str(self.calTargetPos[calIndex][0])
                                                 + ','+str(self.calTargetPos[calIndex][1])+','+str(self.NUM_SAMPLES_PER_TRGPOS)+chr(0))
                                isWaitingSampleAcquisition = True
                                startAcquisitionTime = self.clock()
                        isNumKeyPressed = False
                        if key == 'return':
                            isCalibrating = False
                        elif key in ('0', 'num_0'):
                            isNumKeyPressed = True
                            calIndex = -1
                        elif key in numKeyDict and numKeyDict[key]<len(self.calTargetPos):
                            isNumKeyPressed = True     # Note that self.calTargetPos[0] is initial position.
                            calIndex = numKeyDict[key] # so calIndex=0 is not necessary
                        
                        if isNumKeyPressed:
                            startTime = self.clock()
                            prevPos = currentPos
                            if calIndex == -1:
                                currentPos = (None, None)
                            else:
                                currentPos = self.calTargetPos[calIndex]
                
                    if calIndex >= len(self.calTargetPos):
                        print('Warning: invalid target position index (length of target position list is %d)' % len(self.calTargetPosition))
                        calIndex = -1
                
                self.updateManualCalibrationTargetStimulusCallBack(t, currentPos, prevPos)
                self.updateScreen()

            self.showCalTarget = False
            self.SHOW_CALDISPLAY = prevSHOW_CALDISPLAY
            self.sendCommand('endCal'+chr(0))

            self.calibrationResults = self.getCalibrationResults()
            try:
                if self.isMonocularRecording:
                    self.messageText = 'AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
                else:
                    self.messageText = 'LEFT(black) AvgError:%.2f MaxError:%.2f / RIGHT(white) AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
                self.messageText += '\n1-9: toggle mark 0:remove marked points\nSpace: retry Enter:exit cal'
            except:
                self.messageText = 'Calibration/Validation failed.'

            self.getCalibrationResultsDetail()
            self.overlayMarkersToCalScreen()
            self.updateScreen()
            
            while True:
                isNumKeyPressed = False
                keys = self.getKeys()
                if 'space' in keys:
                    #re-start manual calibration without flushing data
                    self.sendCommand('startCal'+chr(0)+str(self.calArea[0])+','+str(self.calArea[1])+','
                                     + str(self.calArea[2])+','+str(self.calArea[3])+chr(0)+'0'+chr(0))
                    break
                elif 'return' in keys:
                    isCalibrationLoop = False
                    break
                else:
                    for key in keys:
                        if key in ('0', 'num_0'):
                            if len(elimlist)>0:
                                self.deleteCalibrationDataSubset(elimlist)
                                elimlist = []
                                
                                self.calibrationResults = self.getCalibrationResults()
                                try:
                                    if self.isMonocularRecording:
                                        self.messageText = 'AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
                                    else:
                                        self.messageText = 'LEFT(black) AvgError:%.2f MaxError:%.2f / RIGHT(white) AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
                                    self.messageText += '\n1-9: toggle mark 0:remove marked points\nSpace: retry Enter:exit cal'
                                except:
                                    self.messageText = 'Calibration/Validation failed.'
                                
                                self.getCalibrationResultsDetail()
                                self.overlayMarkersToCalScreen()
                                self.updateScreen()

                        elif key in numKeyDict and numKeyDict[key]<len(self.calTargetPos):
                            isNumKeyPressed = True     # Note that self.calTargetPos[0] is initial position.
                            calIndex = numKeyDict[key] # so calIndex=0 is not necessary

                if isNumKeyPressed:
                    if self.calTargetPos[calIndex] in elimlist:
                        elimlist.remove(self.calTargetPos[calIndex])
                    else:
                        elimlist.append(self.calTargetPos[calIndex])
                    self.plotCalibrationResultsDetail()
                    self.overlayMarkersToCalScreen(marker1=elimlist)
                    self.updateScreen()
        
        nindex = self.messageText.find('\n')  #remove instruction
        if nindex>0:
            self.messageText = self.messageText[:nindex]
        self.plotCalibrationResultsDetail()
        self.updateScreen()

    def deleteCalibrationDataSubset(self, points=[], wait=0.1):
        '''
        Delete specified calibration data.
        
        :param points:
            Points to be removed.
        '''
        
        if self.latestCalibrationResultsList is None or len(self.latestCalibrationResultsList) == 0:
            return
        
        if len(points) == 0:
            return
        
        pointsStr = ','.join(['%d,%d' % tuple(p) for p in points])
        self.sendCommand('deleteCalData'+chr(0)+pointsStr+chr(0))
        
        time.sleep(wait)

    '''
    # obsolete
    def getSpatialError(self, position=None, responseKey='space', message=None, responseMouseButton=None):
        """
        Verify measurement error at a given position on the screen.

        :param position:
            A tuple of two numbers that represents target position in screen
            coordinate.  If None, the center of the screen is used.
            Default value is None.
        :param responseKey:
            When this key is pressed, eye position is measured and spatial error is
            evaluated.  Default value is 'space'.
        :param message:
            If a string is given, the string is presented on the screen.
            Default value is None.
        :param responseMouseButton:
            If this value is 0, left button of the mouse is also used to
            measure eye position.  If the value is 2, right button is used.
            If None, mouse buttons are ignored.
            Default value is None.

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
        if position is None:
            position = self.screenCenter

        self.calTargetPosition = position

        self.showCameraImage = False
        self.showCalImage = False
        self.showCalTarget = True
        if message is None:
            self.SHOW_CALDISPLAY = False
        else:
            self.SHOW_CALDISPLAY = True
            self.messageText = message

        self.startMeasurement()

        isWaitingKey = True
        while isWaitingKey:
            if responseMouseButton is not None:
                if self.getMousePressed()[responseMouseButton] == 1:
                    isWaitingKey = False
                    eyepos = self.getEyePosition()
                    break
            keys = self.getKeys()
            for key in keys:
                if key == responseKey:
                    isWaitingKey = False
                    eyepos = self.getEyePosition()
                    break
            self.updateScreen()

        self.stopMeasurement()

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
    '''

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
        return
    
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
        


    def setCalTargetMotionParams(self, durationPerPos, motionDuration):
        """
        Set parameters for calibration/validation target motion.
        If durationPerPos=2.5 and motionDuration=1.0, the calibration target moves
        to the next position over 1.0 second and stays for 1.5 (= 2.5-1.0) seconds
        at that position.

        :param float durationPerPos:
            Duration in which target moves to and stays at a calibration position.
            Unit is second. Default value is defined by CALTARGET_DURATION_PER_POS
            parameter of GazeParser.TrackingTools configuration file.
            By default, CALTARGET_DURATION_PER_POS=2.0.
        :param float motionDuration:
            Duration in which target moves to a calibration position.
            This duration must be shorter than durationPerPos.
            Unit is second. Default value is defined by CALTARGET_MOTION_DURATION
            parameter of GazeParser.TrackingTools configuration file.
            By default, CALTARGET_MOTION_DURATION=1.0.

        .. note::
            If no configuration file is specified when Controller object is created,
            a file named 'TrackingTools.cfg ' in the GazeParser configuration
            directory is used as the configuration file.

        """
        if durationPerPos <= 0:
            raise ValueError('durationPerPos must be greater than 0.')
        if motionDuration < 0:
            raise ValueError('motionDuration must be greater than or equal to 0.')
        if durationPerPos <= motionDuration:
            raise ValueError('durationPerPos must be longer than motionDuration.')
        self.CALTARGET_DURATION_PER_POS = durationPerPos
        self.CALTARGET_MOTION_DURATION = motionDuration

    def setCalSampleAcquisitionParams(self, numSamplesPerPos, getSampleDelay):
        """
        Set parameters for calibration sample acquisition.

        :param int numSamplesPerPos:
            Number of samples collected at each calibration position.
            This value must be must be greater than 0. Default value is defined by
            NUM_SAMPLES_PER_TRGPOS parameter of GazeParser.TrackingTools
            configuration file. By default, NUM_SAMPLES_PER_TRGPOS=10.
        :param float getSampleDelay:
            Delay of starting sample acquisition from target arrived at calibration
            position. Unit is second. This value must not be negative.
            Default value is defined by CAL_GETSAMPLE_DELAY parameter of
            GazeParser.TrackingTools configuration file.
            By default, CAL_GETSAMPLE_DELAY=0.4.

        .. note::
            If no configuration file is specified when Controller object is
            created, a file named 'TrackingTools.cfg ' in the GazeParser
            configuration directory is used as the configuration file.
        """
        if numSamplesPerPos <= 0:
            raise ValueError('numSamplesPerPos must be greater than 0.')
        if getSampleDelay < 0:
            raise ValueError('getSampleDelay must not be negative.')
        self.NUM_SAMPLES_PER_TRGPOS = numSamplesPerPos
        self.CAL_GETSAMPLE_DELAY = getSampleDelay

    def verifyFixation(self, maxTry, permissibleError, key='space', mouseButton=None, message=None, position=None,
                       gazeMarker=None, backgroundStimuli=None, toggleMarkerKey='m', toggleBackgroundKey='m',
                       showMarker=False, showBackground=False, ma=1):
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
            backgroundStimuli = [self.VEFilledCircle(radius=permissibleError, color=(0.6, 0.6, 0.6), position=position)]

        numTry = 0
        error = self.getSpatialError(message=message[0], responseKey=key, responseMouseButton=mouseButton, position=None,
                                     gazeMarker=gazeMarker, backgroundStimuli=backgroundStimuli,
                                     toggleMarkerKey=toggleMarkerKey, toggleBackgroundKey=toggleBackgroundKey,
                                     showMarker=showMarker, showBackground=showBackground, ma=ma)
        if (error[0] is not None) and error[0] < permissibleError:
            time.sleep(0.5)
            return error

        numTry += 1
        while True:
            error = self.getSpatialError(message=message[1], responseKey=key, responseMouseButton=mouseButton, position=None,
                                         gazeMarker=gazeMarker, backgroundStimuli=backgroundStimuli,
                                         toggleMarkerKey=toggleMarkerKey, toggleBackgroundKey=toggleBackgroundKey,
                                         showMarker=showMarker, showBackground=showBackground, ma=ma)
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
                                                 showMarker=showMarker, showBackground=showBackground, ma=ma)
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

    def isBinocularMode(self, timeout=0.2):
        """
        Check SimpleGazeTracker is in monocular or binocular mode.

        :return:
            True: binocualr mode, False: monocular mode.
        """
        self.sendCommand('isBinocularMode'+chr(0))
        hasGot = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                print('timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    print('recv error in isBinocularMode')
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('isBinocularMode: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotCal = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        try:
            if int(data[0]) == 1:
                return True
            else:
                return False
        except:
            raise RuntimeError

    def saveCalValResultsDetail(self):
        """
        Save last calibration/validation results to SimpleGazeTracker data file.
        """
        self.sendCommand('saveCalValResultsDetail'+chr(0))

    def getCameraImageSize(self, timeout=0.2):
        """
        Get image size of SimpleGazeTracker's camera unit.

        :return:
            A tuple of two elements (width, height).  None if failed.
        """
        self.sendCommand('getCameraImageSize'+chr(0))
        hasGot = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                print('timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    print('recv error in getCameraImageSize')
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getCameraImageSize: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotCal = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        
        try:
            size = list(map(int,data.split(b',')))
        except:
            return None

        if len(size) != 2:
            return None

        return tuple(size)

    def fitImageBufferToTracker(self):
        """
        DEPRECATED: use getTrackerInfo() instead.
        
        fit image buffer to image size of the SimpleGazeTracker's camera unit.
        
         :return:
             A tuple of two elements which represents new width and hight of 
             the image buffer.  None if failed.
        """
        warnings.warn('DEPRECATED: use getTrackerInfo() instead.')
        size = self.getCameraImageSize()
        if size is None:
            return None
        
        self.setReceiveImageSize(size)
        return size

    def setCurrentScreenParamsToConfig(self, config, screenSize, distance):
        """
        This method simply returns "config" parameter.
        This method must be overridden.
        
        See also :func:`ControllerPsychoPyBackend.setCurrentScreenParamsToConfig`.
        """
        return config

    def getCameraIFI(self, timeout=0.2):
        """
        Get inter-frame interavl of the camera.

        :return:
            Mean inter-frame interval of the camera in milliseconds.
        """
        self.sendCommand('getCameraIFI'+chr(0))
        hasGot = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                print('timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    print('recv error in getCameraIFI')
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getCameraIFI: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotCal = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        
        try:
            ifi = float(data)
        except:
            return None

        return ifi

    def getBufferSizeInfo(self, timeout=0.2):
        """
        Get buffer size of eye data, calibration point data and max number
        of calibration points from Tracker.

        :return:
           A taple of max samples of eye data, calibration point data and 
           max nubmer of calibration points. 
        """
        self.sendCommand('getBufferSizeInfo'+chr(0))
        hasGot = False
        isInLoop = True
        data = b''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                print('timeout')
                break
            [r, w, c] = select.select(self.readSockList, [], [], 0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    print('recv error in getBufferSizeInfo')
                    isInLoop = False
                if newData:
                    if b'\0' in newData:
                        delimiterIndex = newData.index(b'\0')
                        if delimiterIndex+1 < len(newData):
                            print('getBufferSizeInfo: %d bytes after \\0' % (len(newData)-(delimiterIndex+1)))
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotCal = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        
        try:
            params = list(map(int,data.split(b',')))
        except:
            return None

        if len(params) != 3:
            return None

        return tuple(params)
    
    def getTrackerInfo(self):
        """
        Get inter-frame interval of the camera, buffer size of calibration 
        data and camera image size from Tracker.  This method updates following
        attributes and resize image buffer.
        
        - MAX_CAL_POINTS, 
        - MAX_SAMPLES_PER_TRGPOS
        - CAMERA_SAMPLING_RATE attributes.
        - IMAGE_WIDTH
        - IMAGE_HEIGHT
        """

        ifi = self.getCameraIFI()
        (maxdata, maxcaldata, maxcalpoint) = self.getBufferSizeInfo()

        self.CAMERA_SAMPLING_RATE = 1000.0/ifi # unit of ifi is milliseconds
        self.MAX_CAL_POINTS = maxcalpoint
        self.MAX_SAMPLES_PER_TRGPOS = int(maxcaldata/maxcalpoint)

        size = self.getCameraImageSize()
        self.setReceiveImageSize(size)

    def __repr__(self):
        msg = '<{}.{}>\n'.format(self.__class__.__module__,
                                self.__class__.__name__)

        for key in ControllerDefaults:
            msg += '    {}:{}\n'.format(key, getattr(self, key))

        return msg
