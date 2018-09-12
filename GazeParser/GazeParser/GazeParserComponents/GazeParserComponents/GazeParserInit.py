"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2016 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


try:
    from psychopy.experiment.components import BaseVisualComponent, Param
except:
    from psychopy.app.builder.components._base import BaseVisualComponent, Param
from os import path

thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
iconFile = path.join(thisFolder,'GazeParserInit.png')
tooltip = 'GazeParserInit: initialize GazeParser.TrackingTools'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['gpconfigfile', 'trconfigfile', 'ipaddress', 'calarea', 'caltargetpos', 'datafile', 'calibration', 'units', 'mode', 'modevar']

useMonitorInfoCode = """import psychopy.misc
if GazeParser.config.SCREEN_ORIGIN != 'center':
    GazeParser.config.SCREEN_ORIGIN = 'center'
    logging.warn('GazeParser.config.SCREEN_ORIGIN is set to \\'center\\'')
if GazeParser.config.TRACKER_ORIGIN != 'center':
    GazeParser.config.TRACKER_ORIGIN = 'center'
    logging.warn('GazeParser.config.TRACKER_ORIGIN is set to \\'center\\'')
if not (GazeParser.config.DOTS_PER_CENTIMETER_H == GazeParser.config.DOTS_PER_CENTIMETER_V == psychopy.misc.cm2pix(1.0, win.monitor)):
    GazeParser.config.DOTS_PER_CENTIMETER_H = GazeParser.config.DOTS_PER_CENTIMETER_V = psychopy.misc.cm2pix(1.0, win.monitor)
    logging.warn('GazeParser.config.DOTS_PER_CENTIMETER_H and _V are set to %f' % psychopy.misc.cm2pix(1.0, win.monitor))
if GazeParser.config.SCREEN_WIDTH != win.size[0]:
    GazeParser.config.SCREEN_WIDTH = win.size[0]
    logging.warn('GazeParser.config.SCREEN_WIDTH is set to %d' % win.size[0])
if GazeParser.config.SCREEN_HEIGHT != win.size[1]:
    GazeParser.config.SCREEN_HEIGHT = win.size[1]
    logging.warn('GazeParser.config.SCREEN_HEIGHT is set to %d' % win.size[1])
if GazeParser.config.VIEWING_DISTANCE != win.monitor.getDistance():
    GazeParser.config.VIEWING_DISTANCE = win.monitor.getDistance()
    logging.warn('GazeParser.config.VIEWING_DISTANCE is set to %.f' % win.monitor.getDistance())
"""

class GazeParserInitComponent(BaseVisualComponent):
    """Initialize GazeParser.TrackingTools"""
    categories = ['GazeParser']
    def __init__(self, exp, parentName, name='GazeParserInit',gpconfigfile="",trconfigfile="",ipaddress="",calarea="[-1.0,-1.0,1.0,1.0]",
                 caltargetpos="[[0.0,0.0],[-0.8,-0.8],[-0.8,0.0],[-0.8,0.8],[0.0,-0.8],[0.0,0.0],[0.0,0.8],[0.8,-0.8],[0.8,0.0],[0.8,0.8]]",
                 datafile="data.csv",mode='Normal',modevar='',units="pix",calibration=True,useMonitorInfo=True,fitImageBuffer=True):
        super(GazeParserInitComponent, self).__init__(exp, parentName, name)
        self.type='GazeParserInit'
        self.url="http://gazeparser.sourceforge.net/"

        #params
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
        self.params['gpconfigfile']=Param(ipaddress, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="GazeParser configuration file",
            label="GazeParser configuration file")
        self.params['trconfigfile']=Param(ipaddress, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="GazeParser.TrackingTools configuration file",
            label="GazeParser.TrackingTools configuration file")
        self.params['ipaddress']=Param(ipaddress, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="IP address of SimpleGazeTracker. If empty, default value is used.",
            label="SimpleGazeTracker IP address")
        self.params['calarea']=Param(calarea, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Calibration area (left, bottom, right, top).",
            label="Calibration Area")
        self.params['caltargetpos']=Param(caltargetpos, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="List of calibration target positions ([[x1,y1],[x2,y2],...]).",
            label="Calibration Target Position")
        self.params['calibration']=Param(calibration, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Perform calibration after initialization is finished.",
            label="Calibration")
        self.params['datafile']=Param(datafile, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Name of SimpleGazeTracker data file.",
            label="SimpleGazeTracker Data File")
        self.params['mode']=Param(mode, valType='str', allowedVals=['Normal','Dummy','Follow the variable'],
            updates='constant', allowedUpdates=[],
            hint="Choose 'Dummy' to force dummy mode. If you want to choose mode at run time,\nchoose 'Follow the variable' and set name of the variable to 'Mode Variable'",
            label="Mode", categ="Advanced")
        self.params['modevar']=Param(modevar, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Set name of the variable. This parameter is effective only if 'Mode' is 'Follow the variable'\nThe experiment run in dummy mode if value of the variable is 'True' or 'Dummy'. Otherwise, run in normal mode.",
            label="Mode Variable", categ="Advanced")
        self.params['useMonitorInfo']=Param(useMonitorInfo, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="If true, monitor infomation is used to send screen width, screen height, cm/deg and screen directions to SimpleGazeTracker.",
            label="Use Monitor Info", categ="Advanced")
        self.params['fitImageBuffer']=Param(fitImageBuffer, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="If true, size of the Preview Image Buffer to SimpleGazeTracker's camera image size.",
            label="Fit Preview Buffer", categ="Advanced")
        # these inherited params are harmless but might as well trim:
        for p in ['startType', 'startVal', 'startEstim', 'stopVal', 'stopType', 'durationEstim']:
            del self.params[p]
        for p in ['color','opacity','colorSpace','pos','size','ori']:
            del self.params[p]
    def writeInitCode(self,buff):
        if self.params['mode'].val == 'Normal':
            isDummyMode = False
        elif self.params['mode'].val == 'Dummy':
            isDummyMode = True
        else: # Follow the variable
            if self.params['modevar'].val == '':
                raise ValueError('GazeParserInit: ModeVar must not be empty when "Mode" property is "Follow the variable"')
            buff.writeIndented('if %(modevar)s in [\'True\', \'Dummy\']:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('GazeParser_isDummyMode = True\n')
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented('else:\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('GazeParser_isDummyMode = False\n')
            buff.setIndentLevel(-1, relative=True)
        buff.writeIndented('import GazeParser\nimport GazeParser.Configuration\nimport GazeParser.TrackingTools\n')
        if self.params['gpconfigfile'].val != '':
            buff.writeIndented('GazeParser.config=GazeParser.Configuration.Config(%(gpconfigfile)s)\n' % (self.params))
        if self.params['useMonitorInfo'].val:
            buff.writeIndented(useMonitorInfoCode)
        getControllerCommand = 'GazeParserTracker = GazeParser.TrackingTools.getController(backend="PsychoPy", '
        if self.params['trconfigfile'].val != '':
            getControllerCommand += 'configFile=%(trconfigfile)s, ' % (self.params)
        if self.params['mode'].val in ['Normal', 'Dummy']:
            getControllerCommand += 'dummy=%s)\n' % (isDummyMode)
        else: # Follow the variable
            getControllerCommand += 'dummy=GazeParser_isDummyMode)\n'
        buff.writeIndented(getControllerCommand)
        buff.writeIndented('GazeParserTracker.connect(%(ipaddress)s)\n' % (self.params))
        if self.params['datafile'].val != '':
            buff.writeIndented('GazeParserTracker.openDataFile(%(datafile)s, config=GazeParser.config)\n' % (self.params))
        buff.writeIndented('GazeParserTracker.setCalibrationScreen(win)\n')
        if self.params['fitImageBuffer'].val:
            buff.writeIndented('GazeParserTracker.fitImageBufferToTracker()\n')
        if self.params['units'].val=='from exp settings':
            buff.writeIndented('GazeParserTracker.setCalibrationTargetPositions(%(calarea)s, %(caltargetpos)s, win.units)\n' % (self.params))
        else:
            buff.writeIndented('GazeParserTracker.setCalibrationTargetPositions(%(calarea)s, %(caltargetpos)s, %(units)s)\n' % (self.params))
        if self.params['calibration'].val:
            buff.writeIndented('logging.exp(\'Start GazeParser calibration\')\n')
            buff.writeIndented('tmpGazeParserLogLevel = logFile.level\n')
            buff.writeIndented('logFile.setLevel(logging.WARNING)\n')
            buff.writeIndented('while True:\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('GazeParserRes = GazeParserTracker.calibrationLoop()\n')
            buff.writeIndented('if GazeParserRes=="q":\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('core.quit()\n')
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented('if GazeParserTracker.isCalibrationFinished():\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('break\n')
            buff.setIndentLevel(-2, relative=True)
            buff.writeIndented('logFile.setLevel(tmpGazeParserLogLevel)\n')
            buff.writeIndented('logging.exp(\'End GazeParser calibration\')\n\n')
    def writeFrameCode(self,buff):
        pass
    def writeExperimentEndCode(self,buff):
        if self.params['datafile'].val != '':
            buff.writeIndented('GazeParserTracker.closeDataFile()\n')

        