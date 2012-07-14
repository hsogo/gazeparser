"""
.. Part of GazeParser package.
.. Copyright (C) 2012 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).

"""


import Image
import ImageDraw

import socket
import select
import time
import random

import os
import sys
import ConfigParser

import numpy

ControllerDefaults = {
'IMAGE_WIDTH': 320,
'IMAGE_HEIGHT': 240,
'PREVIEW_WIDTH': 640,
'PREVIEW_HEIGHT': 480,
'VALIDATION_SHIFT':20,
'SHOW_CALDISPLAY':True
}


class BaseController:
    """
    Base class for SimpleGazeTracker controllers. Following methods must be overridden.
    
    - self.setCalibrationScreen(self, screen)
    - self.updateScreen(self)
    - self.setCameraImage(self)
    - self.drawCalibrationResults(self)
    - setCalibrationTargetPositions(self, area, calposlist)
    - self.getKeys(self)
    """
    def __init__(self, configFile=None):
        """
        Initialize controller.
        
        :param str configFile: name of the configuration file.
            If None, TrackingTools.cfg in the application directory is used.
            Default value is None.
        """
        cfgp = ConfigParser.SafeConfigParser()
        if configFile == None: #use default settings
            ConfigFile = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'TrackingTools.cfg')
        else:
            ConfigFile = configFile
        cfgp.read(ConfigFile)
        
        self.imageWidth = int(cfgp.get('Controller','IMAGE_WIDTH'))
        self.imageHeight = int(cfgp.get('Controller','IMAGE_HEIGHT'))
        self.previewWidth = int(cfgp.get('Controller','PREVIEW_WIDTH'))
        self.previewHeight = int(cfgp.get('Controller','PREVIEW_HEIGHT'))
        
        self.validationShift = float(cfgp.get('Controller','VALIDATION_SHIFT'))
        self.showCalDisplay = bool(cfgp.get('Controller','SHOW_CALDISPLAY'))
        self.showCalImage = False
        self.showCameraImage = False
        self.showCalTarget = False
        self.calTargetPosition = (0,0)
        self.messageText = '----'
        self.PILimg = Image.new('L',(self.imageWidth,self.imageHeight))
        
        self.calArea = []
        self.calTargetPos = []
        self.valTargetPos = []
        self.calibrationResults = None
        self.calAreaSet = False
        self.calTargetPosSet = False
        
        self.prevBuffer = ''
        
        if sys.platform == 'win32':
            self.clock = time.clock
        else:
            self.clock = time.time
    
    def setReceiveImageSize(self, size):
        """
        Set size of camera image sent from Tracker Host PC.
        
        :param sequence size: sequence of two integers (width, height).
        """
        self.imageWidth = size[0]
        self.imageHeight = size[1]
        self.PILimg = Image.new('L',(self.imageWidth,self.imageHeight))
    
    def setPreviewImageSize(self, size):
        """
        Set size of preview image. It is recommened that ratio of height and width
        is set to be the same as that of camera image.
        
        :param sequence size: sequence of two integers (width, height).
        """
        self.previewWidth = size[0]
        self.previewHeight = size[1]
    
    def setCalibrationTargetStimulus(self, stim):
        """
        Set calibration target.
        
        :param stim: Stimulus object such as circle, rectangle, and so on.
        """
        if not hasattr(self, 'caltarget'):
            print 'Warning: calibration target stimulus will be overridden when setCalibrationScreen is called.'
        self.caltarget = stim
    
    def setCalibrationTargetPositions(self, area, calposlist):
        """
        Send calibration area and calibration target positions to the Tracker Host PC.
        This method must be called before starting calibration.
        ::
        
            calArea = (0, 0, 1024, 768)
            calPos = ((162,134),(512,134),(862,134),
                      (162,384),(512,384),(862,384),
                      (162,634),(512,634),(862,634))
            tracker.CalibrationTargetPositions(calArea, calPos)
        
        :param sequence area: a sequence of for elements which represent
            left, top, right and bottom of the calibration area.
        :param sequence calposlist: a list of (x, y) positions of calibration
            target.
        """
        if len(area) != 4:
            print 'Calibration area must be a sequence of 4 integers.'
            self.calAreaSet = False
            return
        try:
            for i in range(4):
                area[i] = int(area[i])
        except:
            print 'Calibration area must be a sequence of 4 integers.'
            self.calAreaSet = False
            return
        
        if area[2]<area[0] or area[3]<area[1]:
            print 'Calibration area is wrong.'
            self.calAreaSet = False
            return
        
        self.calArea = area
        self.calAreaSet = True
        
        for i in range(len(calposlist)):
            if len(calposlist[i]) != 2:
                'Calibration position must be a sequence of 2 integers.'
                self.calTargetPosSet = False
                return
            try:
                calposlist[i][0] = int(calposlist[i][0])
                calposlist[i][1] = int(calposlist[i][1])
            except:
                'Calibration position must be a sequence of 2 integers.'
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
        
        self.validationShift = size
    
    def connect(self, address, port1=10000,port2=10001):
        """
        Connect to the Tracker Host PC. Because most of methods communicate with 
        the Tracker Host PC, this method should be called immediately after controller
        object is created.
        
        :param str address: IP address of SimpeGazeTracker (e.g. '192.168.1.2').
        :param int port1: TCP/IP port for sending command to Tracker.
            This value must be correspond to configuration of the Tracker.
            Default value is 10000.
        :param int port2: TCP/IP port for receiving data from Tracker.
            This value must be correspond to configuration of the Tracker.
            Default value is 10001.
        """
        print 'Request connection...'
        self.sendSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sendSock.connect((address,port1))
        res = self.sendSock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print res
        
        self.serverSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.serverSock.bind(('',port2))
        self.serverSock.listen(1)
        self.serverSock.setblocking(0)
        
        self.readSockList = [self.serverSock]
        
        print 'Waiting connection... ',
        self.sv_connected = False
        while not self.sv_connected:
            [r,w,c] = select.select(self.readSockList,[],[],0)
            for x in r:
                if x is self.serverSock:
                    (conn,addr) = self.serverSock.accept()
                    self.readSockList.append(conn)
                    self.sv_connected = True
                    print 'Accepted'
    
    def __del__(self):
        try:
            for i in range(len(self.readSockList)):
                self.readSockList[-(i+1)].close()
            
            self.readSockList = []
            self.serverSock.close()
        except:
            pass
        
    def openDataFile(self,filename):
        """
        Send a command to open data file on the Tracker Host PC.
        The data file is created in the DATA directory at the 
        Tracker Host PC. 
        
        Currently, relative or absolute paths are NOT supported.
        
        :param str filename: Name of data file.
        
        .. note::
            Non-ascii code is not supprted as a file name.
        """
        self.sendSock.send('openDataFile'+chr(0)+filename+chr(0))
    
    def closeDataFile(self):
        """
        Send a command to close data file on the Tracker Host PC.
        """
        self.sendSock.send('closeDataFile'+chr(0))
    
    def sendMessage(self,message):
        """
        Send a command to insert message to data file.
        Timestamp is automatically appended at the Tracker Host PC.
        
        :param str message: Message text to be inserted.
        
        .. note::
            Non-ascii code is not supprted as a message.
        """
        self.sendSock.send('insertMessage'+chr(0)+message+chr(0))
    
    def sendSettings(self, configDict):
        """
        Send a command to insert recording settings to data file.
        
        :parap dict config: a dictionary object which holds recording settings.
        """
        configlist = []
        for key in configDict.keys():
            configlist.append('#'+key+','+str(configDict[key]))
        
        message = '/'.join(configlist)
        self.sendSock.send('insertSettings'+chr(0)+message+chr(0))
    
    def startRecording(self,message='',wait=0.1):
        """
        Send a command to start recording.
        Message can be inserted to describe trial condition and so on.
        
        :param str message:
            message text. Default value is ''
        :param float wait:
            Duration of waiting for processing on the Tracker Host PC.
            Unit is second. Default value is 0.1
        """
        self.sendSock.send('startRecording'+chr(0)+message+chr(0))
        time.sleep(wait)
    
    def stopRecording(self,message='',wait=0.1):
        """
        Send a command to stop recording.
        Message can be inserted to describe exit code and so on.
        
        :param str message:
            message text. Default value is ''
        :param float wait:
            Duration of waiting for processing on the Tracker Host PC.
            Unit is second. Default value is 0.1
        """
        self.sendSock.send('stopRecording'+chr(0)+message+chr(0))
        time.sleep(wait)
    
    def getEyePosition(self,timeout=0.02):
        """
        Send a command to get current gaze position.
        
        :param float timeout:
            If the Tracker Host PC does not respond within this duration, tuple of Nones
            are returned. Unit is second. Default value is 0.02
        :return: a tuple representing holizontal(X) and vertical(Y) gaze position
            in screen corrdinate. When recording mode is monocular, return value is
            (X,Y).  When binocular, return value is (Left X, Left Y, Right X, Right Y).
        """
        self.sendSock.send('getEyePosition'+chr(0))
        hasGotEye = False
        isInLoop = True
        data = ''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                #print 'GetEyePosition timeout'
                break
            [r,w,c] = select.select(self.readSockList,[],[],0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    isInLoop = False
                if newData:
                    if '#' in newData:
                        delimiterIndex = newData.index('#')
                        if delimiterIndex+1 < len(newData):
                            print 'getEyePosition:', newData
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotEye = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        if hasGotEye:
            retval = [int(x) for x in data.split(',')]
            if self.isMonocularRecording:
                if len(retval) != 2:
                    return [None,None]
                else:
                    return retval
            else:
                #TODO: if only one eye is detected?
                if len(retval) != 4:
                    return [None,None,None,None]
                else:
                    return retval
        
        if self.isMonocularRecording:
            return [None,None]
        else:
            return [None,None,None,None]
        
    def getCurrentMenuItem(self,timeout=0.2):
        """
        Get current menu item on the Tracker Host PC as a text.
        Usually, you don't need use this method.
        
        :param float timeout:
            If the Tracker Host PC does not respond within this duration, '----'
            is returned. Unit is second. Default value is 0.2
        :return:
            Text.
        """
        self.sendSock.send('getCurrMenu'+chr(0))
        hasGotMenu = False
        isInLoop = True
        data = ''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                #print 'timeout'
                break
            [r,w,c] = select.select(self.readSockList,[],[],0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    #print 'recv error in getCalibrationResults'
                    isInLoop = False
                if newData:
                    if '#' in newData:
                        delimiterIndex = newData.index('#')
                        if delimiterIndex+1 < len(newData):
                            print 'getCurrentMenuItem:', newData
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotMenu = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        if hasGotMenu:
            return data
        return '----'
    
    def getCalibrationResults(self,timeout=0.2):
        """
        Get a summary of calibration results.
        
        :param float timeout:
            If the Host Tracker PC does not respond within this duration, '----'
            is returned. Unit is second. Default value is 0.2
        :return: a tuple representing goodness of calibration (GoC, horizontal and vertical),
            mean error and maximum error. Larger value of GoC means better recording.
            mean and maximum error are the distance between calibration taget position 
            and gaze position in screen corrdinate. When recording mode is monocular, 
            return value is (holizontal GoC, vertical GoC, mean error, maximum error).
            When binocular, return value is a tuple of 8 elements: the former 4 elements 
            correspond to left eye and the latter 4 elements correspond to right eye.
            
        .. note:: Usually, you don't need use this method.
        """
        self.sendSock.send('getCalResults'+chr(0))
        hasGotCal = False
        isInLoop = True
        data = ''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                #print 'timeout'
                break
            [r,w,c] = select.select(self.readSockList,[],[],0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    #print 'recv error in getCalibrationResults'
                    isInLoop = False
                if newData:
                    if '#' in newData:
                        delimiterIndex = newData.index('#')
                        if delimiterIndex+1 < len(newData):
                            print 'getCalibrationResults', newData
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotCal = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        if hasGotCal:
            retval = [float(x) for x in data.split(',')]
            if len(retval) == 4:
                self.isMonocularRecording = True
                return retval
            elif len(retval) == 8:
                self.isMonocularRecording = False
                return retval
        
        return None
    
    def getCameraImage(self, timeout=0.2):
        """
        Get current camera image. If image data is successfully received,
        the data is set to self.PILimg.
        
        :param float timeout:
            If the Host Tracker PC does not respond within this duration, image 
            is not updated. Unit is second. Default value is 0.2
        
        .. note:: Usually, you don't need use this method.
        """
        self.sendSock.send('getImageData'+chr(0))
        hasGotImage = False
        data = []
        startTime = self.clock()
        while not hasGotImage:
            if self.clock()-startTime > timeout:
                break
            [r,w,c] = select.select(self.readSockList,[],[],0)
            for x in r:
                try:
                    newData = x.recv(16384)
                except:
                    #print 'recv error in getameraImage'
                    hasGotImage = True
                    continue
                if newData:
                    for idx in range(len(newData)):
                        d = ord(newData[idx])
                        if d == 255:
                            hasGotImage = True
                        else:
                            data.append(d)
        
        if len(data) == self.imageWidth*self.imageHeight:
            self.PILimg.putdata(data)
        else:
            print 'getCameraImage: got ', len(data), ' expected ', self.imageWidth*self.imageHeight
    
    def sendCommand(self, command):
        """
        Send a raw Tracker command to the Tracker Host PC.
        
        .. note:: Usually, you don't need use this method.
        """
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
        V        Start validation (call doCalibration() method)
        ESC or Q Exit calibration
        ======== ================================================
        
        :return: 'space' or 'q'
            depending on which key is pressed to terminate calibration loop.
        """
        if not (self.calTargetPosSet and self.calAreaSet):
            print 'Calibration parameters are not set.'
            return
        
        self.messageText=self.getCurrentMenuItem()
        self.showCameraImage = False
        self.showCalImage = False
        while True:
            keys = self.getKeys()
            for key in keys:
                if key == 'escape':
                    return 'escape'
                elif key == 'up':
                    self.sendCommand('key_UP'+chr(0))
                    time.sleep(0.05)
                    self.messageText=self.getCurrentMenuItem()
                elif key == 'down':
                    self.sendCommand('key_DOWN'+chr(0))
                    time.sleep(0.05)
                    self.messageText=self.getCurrentMenuItem()
                elif key == 'space':
                    self.sendCommand('key_SPACE'+chr(0))
                elif key == 'a':
                    if self.showCalDisplay:
                        self.showCalDisplay = False
                        self.showCameraImage = False
                        self.showCalImage = False
                    else:
                        self.showCalDisplay = True
                elif key == 'z':
                    if self.showCalDisplay:
                        self.showCameraImage = not self.showCameraImage
                    else:
                        self.showCameraImae = False
                elif key == 'x':
                    self.sendCommand('toggleCalResult'+chr(0))
                    if self.showCalDisplay:
                        self.showCalImage = not self.showCalImage
                    else:
                        self.showCalImage = False
                elif key == 'c':
                    self.sendCommand('startCal'+chr(0)+str(self.calArea[0])+','+str(self.calArea[1])+','
                                     +str(self.calArea[2])+','+str(self.calArea[3])+chr(0))
                    self.showCameraImage = False
                    self.showCalImage = False
                    self.doCalibration()
                elif key == 'v':
                    self.sendCommand('startVal'+chr(0)+str(self.calArea[0])+','+str(self.calArea[1])+','
                                     +str(self.calArea[2])+','+str(self.calArea[3])+chr(0))
                    self.showCameraImage = False
                    self.showCalImage = False
                    self.doValidation()
                elif key == 's':
                    self.sendCommand('saveCameraImage'+chr(0)+str(time.clock())+'.bmp'+chr(0))
                elif key == 'q':
                    self.sendCommand('key_Q'+chr(0))
                    return 'q'
                
                elif key == 'left':
                    self.sendCommand('key_LEFT'+chr(0))
                    time.sleep(0.05)
                    self.messageText=self.getCurrentMenuItem()
                elif key == 'right':
                    self.sendCommand('key_RIGHT'+chr(0))
                    time.sleep(0.05)
                    self.messageText=self.getCurrentMenuItem()
            
            #get camera image
            if self.showCameraImage:
                self.getCameraImage()
                self.setCameraImage()
            
            #draw screen
            self.updateScreen()
    
    def getCalibrationResultsDetail(self,timeout=0.2):
        """
        Get detailed calibration results.
        
        :param float timeout:
            If the Tracker Host PC does not respond within this duration, '----'
            is returned. Unit is second. Default value is 0.2
        :return:
            Detailed Calibration
        
        .. note:: Usually, you don't need use this method because this method 
            is automatically called form doCalibration() and doValidation().
        """
        self.sendCommand('getCalResultsDetail'+chr(0))
        hasGotCal = False
        isInLoop = True
        data = ''
        startTime = self.clock()
        while isInLoop:
            if self.clock()-startTime > timeout:
                #print 'timeout'
                break
            [r,w,c] = select.select(self.readSockList,[],[],0)
            for x in r:
                try:
                    newData = x.recv(4096)
                except:
                    #print 'recv error in getCalibrationResults'
                    isInLoop = False
                if newData:
                    if '#' in newData:
                        delimiterIndex = newData.index('#')
                        if delimiterIndex+1 < len(newData):
                            print 'getCalibrationResultsDetail', newData
                            self.prevBuffer = newData[(delimiterIndex+1):]
                        data += newData[:delimiterIndex]
                        hasGotCal = True
                        isInLoop = False
                        break
                    else:
                        data += newData
        
        draw = ImageDraw.Draw(self.PILimgCAL)
        draw.rectangle(((0,0),(self.screenWidth,self.screenHeight)),fill=128)
        if self.showCalDisplay == True:
            self.showCalImage = True
        else:
            self.showCalImage = False
        
        if hasGotCal:
            retval = [float(x) for x in data.split(',')]
            if self.isMonocularRecording:
                if len(retval)%4 != 0:
                    print 'getCalibrationResultsDetail: illeagal data', retval
                    self.drawCalibrationResults()
                    return None
                
                for i in range(len(retval)/4):
                    draw.line(
                        ((retval[4*i]+self.calResultScreenOrigin[0],retval[4*i+1]+self.calResultScreenOrigin[1]),
                        (retval[4*i+2]+self.calResultScreenOrigin[0],retval[4*i+3]+self.calResultScreenOrigin[1])),
                        fill=32)
                self.drawCalibrationResults()
            else:
                if len(retval)%6 != 0:
                    print 'getCalibrationResultsDetail: illeagal data', retval
                    self.drawCalibrationResults()
                    return None
                
                for i in range(len(retval)/6):
                    draw.line(
                        ((retval[6*i]+self.calResultScreenOrigin[0],retval[6*i+1]+self.calResultScreenOrigin[1]),
                        (retval[6*i+2]+self.calResultScreenOrigin[0],retval[6*i+3]+self.calResultScreenOrigin[1])),
                        fill=32)
                    draw.line(
                        ((retval[6*i]+self.calResultScreenOrigin[0],retval[6*i+1]+self.calResultScreenOrigin[1]),
                        (retval[6*i+4]+self.calResultScreenOrigin[0],retval[6*i+5]+self.calResultScreenOrigin[1])),
                        fill=224)
                self.drawCalibrationResults()
            
            return None #Success
        
        self.drawCalibrationResults()
    
    def doCalibration(self):
        """
        Start calibration process.
        """
        idxlist = range(1,len(self.calTargetPos))
        random.shuffle(idxlist)
        idxlist.insert(0,0)
        
        calCheckList = [False for i in range(len(self.calTargetPos))]
        self.showCalTarget = True
        prevShowCalDisplay = self.showCalDisplay
        self.showCalDisplay = False
        self.calTargetPosition = self.calTargetPos[0]
        
        isWaitingKey = True
        while isWaitingKey:
            keys = self.getKeys()
            for key in keys:
                if key == 'space':
                    isWaitingKey = False
                    break
            self.updateScreen()
        
        isCalibrating = True
        startTime = self.clock()
        while isCalibrating:
            ct = self.clock()-startTime
            t1 = ct%2.0
            t2 = int((ct-t1)/2.0)
            if t2 >= len(self.calTargetPos)-1:
                isCalibrating = False
                break
            if t1<1.0:
                x = t1*self.calTargetPos[idxlist[t2+1]][0] + (1-t1)*self.calTargetPos[idxlist[t2]][0]
                y = t1*self.calTargetPos[idxlist[t2+1]][1] + (1-t1)*self.calTargetPos[idxlist[t2]][1]
                self.calTargetPosition = (x,y)
            elif 1.4<t1<1.8:
                if not calCheckList[t2]:
                    self.sendCommand('getCalSample'+chr(0)+str(self.calTargetPos[idxlist[t2+1]][0])
                                     +','+str(self.calTargetPos[idxlist[t2+1]][1])+chr(0))
                    calCheckList[t2] = True
            self.updateScreen()
        
        self.showCalTarget = False
        self.showCalDisplay = prevShowCalDisplay
        self.sendCommand('endCal'+chr(0))
        
        self.calibrationResults = self.getCalibrationResults()
        try:
            if self.isMonocularRecording:
                self.messageText='X:%.2f Y:%.2f AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
            else:
                self.messageText='LEFT(black) X:%.2f Y:%.2f AvgError:%.2f MaxError:%.2f / RIGHT(white) X:%.2f Y:%.2f AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
        except:
            self.messageText='Calibration/Validation failed.'
        
        self.getCalibrationResultsDetail()
        
    def doValidation(self):
        """
        Start validation process.
        """
        self.valTargetPos = []
        for p in self.calTargetPos:
            self.valTargetPos.append([p[0]+int((random.randint(0,1)-0.5)*2*self.validationShift),p[1]+int((random.randint(0,1)-0.5)*2*self.validationShift)])
        
        idxlist = range(1,len(self.valTargetPos))
        random.shuffle(idxlist)
        idxlist.insert(0,0)
        
        calCheckList = [False for i in range(len(self.valTargetPos))]
        self.showCalTarget = True
        prevShowCalDisplay = self.showCalDisplay
        self.showCalDisplay = False
        self.calTargetPosition = self.valTargetPos[0]
        
        isWaitingKey = True
        while isWaitingKey:
            keys = self.getKeys()
            for key in keys:
                if key == 'space':
                    isWaitingKey = False
                    break
            self.updateScreen()
        
        isCalibrating = True
        startTime = self.clock()
        while isCalibrating:
            ct = self.clock()-startTime
            t1 = ct%2.0
            t2 = int((ct-t1)/2.0)
            if t2 >= len(self.valTargetPos)-1:
                isCalibrating = False
                break
            if t1<1.0:
                x = t1*self.valTargetPos[idxlist[t2+1]][0] + (1-t1)*self.valTargetPos[idxlist[t2]][0]
                y = t1*self.valTargetPos[idxlist[t2+1]][1] + (1-t1)*self.valTargetPos[idxlist[t2]][1]
                self.calTargetPosition = (x,y)
            elif 1.4<t1<1.8:
                if not calCheckList[t2]:
                    self.sendCommand('getValSample'+chr(0)+str(self.valTargetPos[idxlist[t2+1]][0])
                                     +','+str(self.valTargetPos[idxlist[t2+1]][1])+chr(0))
                    calCheckList[t2] = True
            self.updateScreen()
        
        self.showCalTarget = False
        self.showCalDisplay = prevShowCalDisplay
        self.sendCommand('endVal'+chr(0))
        
        self.calibrationResults = self.getCalibrationResults()
        try:
            if self.isMonocularRecording:
                self.messageText='X:%.2f Y:%.2f AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
            else:
                self.messageText='LEFT X:%.2f Y:%.2f AvgError:%.2f MaxError:%.2f / RIGHT X:%.2f Y:%.2f AvgError:%.2f MaxError:%.2f' % tuple(self.calibrationResults)
        except:
            self.messageText='Calibration/Validation failed.'
        
        self.getCalibrationResultsDetail()
    
    def isCalibrationFinished(self):
        """
        Check whether calibration is performed at least once.
        
        :return: True if calibration is performed at least once.
        """
        if self.calibrationResults == None:
            return False
        else:
            return True
    
    def getSpatialError(self, position=None, responseKey='space', message=None):
        """
        Verify measurement error at a given position on the screen.
        
        :param position:
            A tuple of two numbers that represents target position in screen coordinate.
            If None, the center of the screen is used.  Default value is None.
        :param responseKey:
            When this key is pressed, eye position is measured and spatial error is 
            evaluated.  Default value is 'space'.
        :param message:
            If a string is given, the string is presented on the screen.
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
        if position==None:
            position = self.screenCenter
        
        self.calTargetPosition = position
        
        self.showCameraImage = False
        self.showCalImage = False
        self.showCalTarget = True
        if message == None:
            self.showCalDisplay = False
        else:
            self.showCalDisplay = True
            self.messageText = message
        
        isWaitingKey = True
        while isWaitingKey:
            keys = self.getKeys()
            for key in keys:
                if key == responseKey:
                    isWaitingKey = False
                    eyepos = self.getEyePosition()
                    break
            self.updateScreen()
        
        if len(eyepos)==2: #monocular
            if eyepos[0] == None:
                error = None
            else:
                error = numpy.linalg.norm((eyepos[0]-position[0],eyepos[1]-position[1]))
            retval = (error, eyepos)
            
        else: #binocular
            if eyepos[0] == None:
                errorL = None
            else:
                errorL = numpy.linalg.norm((eyepos[0]-position[0],eyepos[1]-position[1]))
            if eyepos[2] == None:
                errorR = None
            else:
                errorR = numpy.linalg.norm((eyepos[2]-position[0],eyepos[3]-position[1]))
            
            if errorL != None and errorR != None:
                error = (errorL+errorR)/2.0
            
            retval = (error, errorL, errorR, eyepos)
        
        return retval


class ControllerVisionEggBackend(BaseController):
    """
    SimpleGazeTracker controller for VisionEgg.
    """
    
    def __init__(self, configFile=None):
        """
        :param str configFile: Controller configuration file. If None, default configurations are used.
        """
        from VisionEgg.Core import swap_buffers
        from VisionEgg.Core import Viewport
        from VisionEgg.Text import Text
        from VisionEgg.Textures import Texture, TextureStimulus
        from VisionEgg.MoreStimuli import Target2D
        from VisionEgg.GL import GL_NEAREST
        from pygame import key, event
        from pygame.locals import KEYDOWN, K_LEFT, K_RIGHT
        self.VEswap_buffers = swap_buffers
        self.VEViewport = Viewport
        self.VETarget2D = Target2D
        self.VETexture = Texture
        self.VETextureStimulus = TextureStimulus
        self.VEText = Text
        self.VEGL_NEAREST = GL_NEAREST
        self.VEKEYDOWN = KEYDOWN
        self.VEkey = key
        self.VEevent = event
        self.VEK_LEFT = K_LEFT
        self.VEK_RIGHT = K_RIGHT
        self.backend = 'VisionEgg'
        BaseController.__init__(self,configFile)
    
    def setCalibrationScreen(self, screen):
        """
        Set calibration screen.
        
        :param VisionEgg.Core.Screen screen: instance of VisionEgg.Core.Screen 
            to display calibration screen.
        """
        self.screen = screen
        (self.screenWidth, self.screenHeight) = screen.size
        self.screenCenter = (screen.size[0]/2, screen.size[1]/2)
        self.caltarget = self.VETarget2D(size=(10,10),on=False,color=(0,0,0))
        self.PILimgCAL = Image.new('L',(self.screenWidth,self.screenHeight))
        self.texture = self.VETexture(self.PILimg)
        self.calTexture = self.VETexture(self.PILimgCAL)
        self.img = self.VETextureStimulus(texture=self.texture,
                                          size=(self.previewWidth,self.previewHeight),
                                          position=(self.screenWidth/2,self.screenHeight/2),anchor='center',
                                          on=False,
                                          texture_mag_filter=self.VEGL_NEAREST)
        self.imgCal = self.VETextureStimulus(texture=self.calTexture,
                                             size=(self.screenWidth,self.screenHeight),
                                             position=(self.screenWidth/2,self.screenHeight/2),anchor='center',
                                             on=False,
                                             texture_mag_filter=self.VEGL_NEAREST)
        self.msgtext = self.VEText(position=(self.screenWidth/2,self.screenHeight/2-self.previewHeight/2-12),
                                           anchor='center',font_size=24,text=self.getCurrentMenuItem())
        self.viewport = self.VEViewport(screen=screen, stimuli=[self.img,self.imgCal,self.caltarget,self.msgtext])
        self.calResultScreenOrigin = (0, 0)
        
    def updateScreen(self):
        self.img.parameters.on = self.showCameraImage
        self.imgCal.parameters.on = self.showCalImage
        self.msgtext.parameters.on = self.showCalDisplay
        self.caltarget.parameters.on = self.showCalTarget
        self.caltarget.parameters.position = self.calTargetPosition
        self.msgtext.parameters.text = self.messageText
        
        self.screen.clear()
        self.viewport.draw()
        self.VEswap_buffers()
    
    def setCameraImage(self):
        self.img.parameters.texture.get_texture_object().put_sub_image(self.PILimg)
    
    def drawCalibrationResults(self):
        self.imgCal.parameters.texture.get_texture_object().put_sub_image(self.PILimgCAL)
    
    def getKeys(self):
        keys = [self.VEkey.name(e.key) for e in self.VEevent.get(self.VEKEYDOWN)]
        
        keyin = self.VEkey.get_pressed()
        if keyin[self.VEK_LEFT] and (not 'left' in keys):
            keys.append('left')
        if keyin[self.VEK_RIGHT] and (not 'right' in keys):
            keys.append('right')
        
        return keys
    


class ControllerPsychoPyBackend(BaseController):
    """
    SimpleGazeTracker controller for PsychoPy.
    """
    def __init__(self, configFile=None):
        """
        :param str configFile: Controller configuration file. If None, default
            configurations are used.
        """
        from psychopy.visual import TextStim, SimpleImageStim, Rect
        from psychopy.event import getKeys
        from psychopy.misc import cm2pix,deg2pix,pix2cm,pix2deg
        self.PPSimpleImageStim = SimpleImageStim
        self.PPTextStim = TextStim
        self.PPRect = Rect
        self.cm2pix = cm2pix
        self.deg2pix = deg2pix
        self.pix2cm = pix2cm
        self.pix2deg = pix2deg
        self.backend = 'PsychoPy'
        BaseController.__init__(self,configFile)
        self.getKeys = getKeys #for psychopy, implementation of getKeys is simply importing psychopy.events.getKeys
    
    def setCalibrationScreen(self, win):
        """
        Set calibration screen.
        
        :param psychopy.visual.window win: instance of psychopy.visual.window to display
            calibration screen.
        """
        self.win = win
        (self.screenWidth, self.screenHeight) = win.size
        self.screenCenter = (0,0)
        self.caltarget = self.PPRect(self.win,width=10,height=10,units='pix')
        self.PILimgCAL = Image.new('L',(self.screenWidth,self.screenHeight))
        self.img = self.PPSimpleImageStim(self.win, self.PILimg)
        self.imgCal = self.PPSimpleImageStim(self.win, self.PILimgCAL)
        self.msgtext = self.PPTextStim(self.win, pos=(0,-self.previewHeight/2-12), units='pix', text=self.getCurrentMenuItem())
        self.calResultScreenOrigin = (self.screenWidth/2, self.screenHeight/2)
    
    def updateScreen(self):
        self.caltarget.setPos(self.calTargetPosition,units='pix')
        self.msgtext.setText(self.messageText)
        if self.showCameraImage:
            self.img.draw()
        if self.showCalImage:
            self.imgCal.draw()
        if self.showCalTarget:
            self.caltarget.draw()
        if self.showCalDisplay:
            self.msgtext.draw()
        
        self.win.flip()
    
    def setCameraImage(self):
        self.img.setImage(self.PILimg)
    
    def drawCalibrationResults(self):
        self.imgCal.setImage(self.PILimgCAL)
    
    #Override
    def setCalibrationTargetPositions(self, area, calposlist, units='pix'):
        """
        ..todo: write document.
        """
        pixArea = self.convertToPix(area, units, forceToInt = True)
        pixCalposlist = [self.convertToPix(calpos, units, forceToInt = True) for calpos in calposlist]
        """
        if units == 'norm':
            pixArea = [int(area[0]*self.win.size[0]/2),int(area[1]*self.win.size[1]/2),int(area[2]*self.win.size[0]/2),int(area[3]*self.win.size[1]/2)]
            pixCalposlist = [[int(p[0]*self.win.size[0]/2),int(p[1]*self.win.size[1]/2)] for p in calposlist]
        elif units == 'height':
            pixArea = [int(p*self.win.size[1]/2) for p in area]
            pixCalposlist = [[int(p[0]*self.win.size[1]/2),int(p[1]*self.win.size[1]/2)] for p in calposlist]
        elif units == 'cm':
            pixArea = [int(self.cm2pix(p)) for p in area]
            pixCalposlist = [[int(self.cm2pix(p[0])),int(self.cm2pix(p[1]))] for p in calposlist]
        elif units == 'deg':
            pixArea = [int(self.deg2pix(p)) for p in area]
            pixCalposlist = [[int(self.deg2pix(p[0])),int(self.deg2pix(p[1]))] for p in calposlist]
        elif units == 'pix':
            pixArea = area
            pixCalposlist = calposlist
        else:
            raise ValueError, 'units must bet norm, height, cm, deg or pix.'
        """
        
        BaseController.setCalibrationTargetPositions(self,pixArea,pixCalposlist)
    
    #Override
    def getEyePosition(self, timeout=0.02, units='pix'):
        e = BaseController.getEyePosition(self, timeout)
        return self.convertFromPix(e)
    
    #Override
    def getSpatialError(self, position=None, responseKey='space', units='pix', message=None):
        if position != None:
            posInPix = self.convertToPix(position, units)
        else:
            position = (0, 0)
            posInPix = (0, 0)
        
        error = BaseController.getSpatialError(self, position=posInPix, responseKey=responseKey, message=message)
        eyepos = self.convertFromPix(error[-1], units)
        
        # following part is copied from BaseController.getSpatialError
        if len(eyepos)==2: #monocular
            if eyepos[0] == None:
                error = None
            else:
                error = numpy.linalg.norm((eyepos[0]-position[0],eyepos[1]-position[1]))
            retval = (error, eyepos)
            
        else: #binocular
            if eyepos[0] == None:
                errorL = None
            else:
                errorL = numpy.linalg.norm((eyepos[0]-position[0],eyepos[1]-position[1]))
            if eyepos[2] == None:
                errorR = None
            else:
                errorR = numpy.linalg.norm((eyepos[2]-position[0],eyepos[3]-position[1]))
            
            if errorL != None and errorR != None:
                error = (errorL+errorR)/2.0
            
            retval = (error, errorL, errorR, eyepos)
        
        return retval
    
    def convertToPix(self, pos, units, forceToInt=False):
        retval = []
        if units == 'norm':
            for i in range(len(pos)):
                if pos[i] == None:
                    retval.append(None)
                else:
                    if i%2==0: #X
                        retval.append(pos[i]*self.win.size[0]/2)
                    else: #Y
                        retval.append(pos[i]*self.win.size[1]/2)
        elif units == 'height':
            for i in range(len(pos)):
                if pos[i] == None:
                    retval.append(None)
                else:
                    retval.append(pos[i]*self.win.size[1]/2)
        elif units == 'cm':
            for i in range(len(pos)):
                if pos[i] == None:
                    retval.append(None)
                else:
                    retval.append(self.cm2pix(pos[i]))
        elif units == 'deg':
            for i in range(len(pos)):
                if pos[i] == None:
                    retval.append(None)
                else:
                    retval.append(self.deg2pix(pos[i]))
        elif units == 'pix':
            retval = list(pos)
        else:
            raise ValueError, 'units must bet norm, height, cm, deg or pix.'
        
        if forceToInt:
            for i in range(len(retval)):
                if retval[i] != None:
                    retval[i] = int(retval[i])
        
        return retval
    
    def convertFromPix(self, pos, units):
        retval = []
        if units == 'norm':
            for i in range(len(pos)):
                if pos[i] == None:
                    retval.append(None)
                else:
                    if i%2==0: #X
                        retval.append(pos[i]/float(self.win.size[0]/2))
                    else: #Y
                        retval.append(pos[i]/float(self.win.size[1]/2))
        elif units == 'height':
            for i in range(len(pos)):
                if pos[i] == None:
                    retval.append(None)
                else:
                    retval.append(pos[i]/float(self.win.size[1]/2))
        elif units == 'cm':
            for i in range(len(pos)):
                if pos[i] == None:
                    retval.append(None)
                else:
                    retval.append(self.pix2cm(pos[i]))
        elif units == 'deg':
                if pos[i] == None:
                    retval.append(None)
                else:
                    retval.append(self.pix2deg(pos[i]))
        elif units == 'pix':
            retval =  list(pos)
        else:
            raise ValueError, 'units must bet norm, height, cm, deg or pix.'
        
        return retval
    

class DummyVisionEggBackend(ControllerVisionEggBackend):
    """
    
    """
    def __init__(self, configFile):
        ControllerVisionEggBackend.__init__(self, configFile)
        from pygame import mouse
        self.mouse = mouse
    
    def connect(self, address, port1=10000, port2=10001):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'connect (dummy)'
    
    def openDataFile(self,filename):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'openDataFile (dummy): ' + filename
    
    def closeDataFile(self):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'close (dummy)'
    
    def getEyePosition(self, timeout=0.02):
        """
        Dummy function for debugging. This method returns current mouse position.
        """
        pos = self.mouse.get_pos()
        return (pos[0], self.screenHeight-pos[1])
    
    def sendMessage(self, message):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'sendMessage (dummy): ' + message
    
    def sendSettings(self, configDict):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'sendSettings (dummy)'
    
    def startRecording(self, message='', wait=0.2):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'startRecording (dummy): ' + message
    
    def stopRecording(self, message='', wait=0.2):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'stopRecording (dummy): ' + message
    
    def getCurrentMenuItem(self,timeout=0.2):
        return 'Dummy Controller'
    
    def getCalibrationResults(self,timeout=0.2):
        return 'Dummy Results'
    
    def getCameraImage(self):
        draw = ImageDraw.Draw(self.PILimg)
        draw.rectangle(((0,0),(self.imageWidth,self.imageHeight)),fill=0)
        draw.text((64,64),'Camera Preview',fill=255)
        return None
    
    def getCalibrationResultsDetail(self,timeout=0.2):
        return None
    
    def sendCommand(self, command):
        print 'Dummy sendCommand: '+ command
    
    def setCalibrationScreen(self, screen):
        ControllerVisionEggBackend.setCalibrationScreen(self,screen)
        draw = ImageDraw.Draw(self.PILimgCAL)
        draw.rectangle(((0,0),(self.screenWidth,self.screenHeight)),fill=0)
        draw.text((64,64),'Calibration/Validation Results',fill=255)
        self.drawCalibrationResults()
    
    def doCalibration(self):
        BaseController.doCalibration(self)
        if self.showCalDisplay == True:
            self.showCalImage = True
        else:
            self.showCalImage = False
        self.messageText = 'Dummy Results'
    
    def doValidation(self):
        BaseController.doValidation(self)
        if self.showCalDisplay == True:
            self.showCalImage = True
        else:
            self.showCalImage = False
        self.messageText = 'Dummy Results'
    
class DummyPsychoPyBackend(ControllerPsychoPyBackend):
    """
    
    """
    def __init__(self, configFile):
        ControllerPsychoPyBackend.__init__(self, configFile)
        from psychopy.event import Mouse
        self.mouse = Mouse
    
    def connect(self, address, port1=10000, port2=10001):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'connect (dummy)'
    
    def openDataFile(self,filename):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'openDataFile (dummy): ' + filename
    
    def closeDataFile(self):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'close (dummy)'
    
    def getEyePosition(self, timeout=0.02):
        """
        Dummy function for debugging. This method returns current eye position
        """
        return self.myMouse.getPos()
    
    def sendMessage(self, message):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'sendMessage (dummy): ' + message
    
    def sendSettings(self, configDict):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'sendSettings (dummy)'
    
    def startRecording(self, message='', wait=0.2):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'startRecording (dummy): ' + message
    
    def stopRecording(self, message='', wait=0.2):
        """
        Dummy function for debugging. This method do nothing.
        """
        print 'stopRecording (dummy): ' + message
    
    def getCurrentMenuItem(self,timeout=0.2):
        return 'Dummy Controller'
    
    def getCalibrationResults(self,timeout=0.2):
        return 'Dummy Results'
    
    def getCameraImage(self):
        draw = ImageDraw.Draw(self.PILimg)
        draw.rectangle(((0,0),(self.imageWidth,self.imageHeight)),fill=0)
        draw.text((64,64),'Camera Preview',fill=255)
        return None
    
    def getCalibrationResultsDetail(self,timeout=0.2):
        return None
    
    def sendCommand(self, command):
        print 'Dummy sendCommand: '+ command
    
    def setCalibrationScreen(self, win):
        ControllerPsychoPyBackend.setCalibrationScreen(self,win)
        self.myMouse = self.mouse(win=self.win)
        draw = ImageDraw.Draw(self.PILimgCAL)
        draw.rectangle(((0,0),(self.screenWidth,self.screenHeight)),fill=0)
        draw.text((64,64),'Calibration/Validation Results',fill=255)
        self.drawCalibrationResults()
    
    def doCalibration(self):
        BaseController.doCalibration(self)
        if self.showCalDisplay == True:
            self.showCalImage = True
        else:
            self.showCalImage = False
        self.messageText = 'Dummy Results'
    
    def doValidation(self):
        BaseController.doValidation(self)
        if self.showCalDisplay == True:
            self.showCalImage = True
        else:
            self.showCalImage = False
        self.messageText = 'Dummy Results'

def getController(backend, configFile=None, dummy=False):
    """
    Get Tracker controller object.
    
    :param str backend: specify screen type. 'VisionEgg', 'PsychoPy.
    :param stt configFile: Controller configuration file.
        If None, Tracker.cfg in the application directory is used.
        Default value is None.
    :param bool dummy: Get dummy controller for standalone debugging.
        Default value is False.
    
    .. note::
        Currentry, PsychoPy controller must be used with pygame screen
        and 'deg' unit.
    """
    if backend=='VisionEgg':
        if dummy:
            return DummyVisionEggBackend(configFile)
        else:
            return ControllerVisionEggBackend(configFile)
    elif backend=='PsychoPy':
        if dummy:
            return DummyPsychoPyBackend(configFile)
        else:
            return ControllerPsychoPyBackend(configFile)
    elif backend.lower()=='dummy':
        return DummyController()
