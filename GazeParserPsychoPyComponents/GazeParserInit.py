
from _base import *
from os import path
from psychopy.app.builder.experiment import Param

thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
iconFile = path.join(thisFolder,'GazeParserInit.png')
tooltip = 'GazeParserInit: initialize GazeParser.TrackingTools'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['gpconfigfile', 'trconfigfile', 'ipaddress', 'calarea', 'caltargetpos', 'datafile', 'dummymode', 'units']


class GazeParserInitComponent(BaseComponent):
    """Initialize GazeParser.TrackingTools"""
    categories = ['Custom']
    def __init__(self, exp, parentName, name='GazeParserInit',gpconfigfile="",trconfigfile="",ipaddress="",calarea="[-400,-300,400,300]",
                 caltargetpos="[[0,0],[-350,-250],[-350,0],[-350,250],\n[0,-250],[0,0],[0,250],\n[350,-250],[350,0],[350,250]]",
                 datafile="data.csv",dummymode=False,units="pix"):
        self.type='GazeParserInit'
        self.url="http://gazeparser.sourceforge.net/"
        self.exp=exp#so we can access the experiment if necess
        #params
        self.categories=['misc']
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
        self.params={}
        self.params['name']=Param(name, valType='code', allowedTypes=[],
            hint="",
            label="Name")
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
            hint="List ",
            label="Calibration Target Position")
        self.params['datafile']=Param(datafile, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Name of SimpleGazeTracker data file.",
            label="SimpleGazeTracker Data File")
        self.params['dummymode']=Param(dummymode, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Dummy mode",
            label="Dummy Mode")
        self.params['units']=Param(units, valType='str', allowedVals=['deg', 'cm', 'pix', 'norm'],
            hint="Units for calibration area and calibration target positions",
            label="Units")
    def writeInitCode(self,buff):
        buff.writeIndented('import GazeParser\nimport GazeParser.Configuration\nimport GazeParser.TrackingTools\n')
        if self.params['gpconfigfile'].val != '':
            buff.writeIndented('GazeParser.config=GazeParser.Configuration.Config(%(gpconfigfile)s)\n' % (self.params))
        if self.params['trconfigfile'].val == '':
            buff.writeIndented('GazeParserTracker = GazeParser.TrackingTools.getController(backend="PsychoPy",dummy=%(dummymode)s)\n' % (self.params))
        else:
            buff.writeIndented('GazeParserTracker = GazeParser.TrackingTools.getController(backend="PsychoPy",configFile=%(trconfigfile)s,dummy=%(dummymode)s)\n' % (self.params))
        buff.writeIndented('GazeParserTracker.connect(%(ipaddress)s)\n' % (self.params))
        if self.params['datafile'].val != '':
            buff.writeIndented('GazeParserTracker.openDataFile(%(datafile)s)\n' % (self.params))
        buff.writeIndented('GazeParserTracker.sendSettings(GazeParser.config.getParametersAsDict())\n')
        buff.writeIndented('GazeParserTracker.setCalibrationScreen(win)\n')
        buff.writeIndented('GazeParserTracker.setCalibrationTargetPositions(%(calarea)s, %(caltargetpos)s, %(units)s)\n' % (self.params))
        buff.writeIndented('while True:\n')
        buff.setIndentLevel(+1, relative=True)
        buff.writeIndented('GazeParserRes = GazeParserTracker.calibrationLoop()\n')
        buff.writeIndented('if GazeParserRes=="q":\n')
        buff.setIndentLevel(+1, relative=True)
        buff.writeIndented('core.quit(0)\n')
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndented('if GazeParserTracker.isCalibrationFinished():\n')
        buff.setIndentLevel(+1, relative=True)
        buff.writeIndented('break\n\n')
        buff.setIndentLevel(-2, relative=True)
    def writeExperimentEndCode(self,buff):
        if self.params['datafile'].val != '':
            buff.writeIndented('GazeParserTracker.closeDataFile()\n')

        