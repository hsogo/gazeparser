"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""

from _visual import VisualComponent, Param
from os import path

thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
iconFile = path.join(thisFolder,'GazeParserInit.png')
tooltip = 'GazeParserInit: initialize GazeParser.TrackingTools'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['gpconfigfile', 'trconfigfile', 'ipaddress', 'calarea', 'caltargetpos', 'datafile', 'calibration', 'units', 'mode', 'modevar']


class GazeParserInitComponent(VisualComponent):
    """Initialize GazeParser.TrackingTools"""
    categories = ['Custom']
    def __init__(self, exp, parentName, name='GazeParserInit',gpconfigfile="",trconfigfile="",ipaddress="",calarea="[-400,-300,400,300]",
                 caltargetpos="[[0,0],[-350,-250],[-350,0],[-350,250],\n[0,-250],[0,0],[0,250],\n[350,-250],[350,0],[350,250]]",
                 datafile="data.csv",mode='Normal',modevar='',units="pix",calibration=True):
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
            hint="Set name of the variable. This parameter is effective only if 'Mode' is 'Follow the variable'\nThe experiment run in dummy mode if value of the variable is True. Otherwise, run in normal mode.",
            label="Mode Variable", categ="Advanced")
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
            isDummyMode = self.params['modevar'].val
        buff.writeIndented('import GazeParser\nimport GazeParser.Configuration\nimport GazeParser.TrackingTools\n')
        if self.params['gpconfigfile'].val != '':
            buff.writeIndented('GazeParser.config=GazeParser.Configuration.Config(%(gpconfigfile)s)\n' % (self.params))
        getControllerCommand = 'GazeParserTracker = GazeParser.TrackingTools.getController(backend="PsychoPy", '
        if self.params['trconfigfile'].val != '':
            getControllerCommand += 'configFile=%(trconfigfile)s, ' % (self.params)
        getControllerCommand += 'dummy=%s)\n' % (isDummyMode)
        buff.writeIndented(getControllerCommand)
        buff.writeIndented('GazeParserTracker.connect(%(ipaddress)s)\n' % (self.params))
        if self.params['datafile'].val != '':
            buff.writeIndented('GazeParserTracker.openDataFile(%(datafile)s)\n' % (self.params))
        buff.writeIndented('GazeParserTracker.sendSettings(GazeParser.config.getParametersAsDict())\n')
        buff.writeIndented('GazeParserTracker.setCalibrationScreen(win)\n')
        buff.writeIndented('GazeParserTracker.setCalibrationTargetPositions(%(calarea)s, %(caltargetpos)s, %(units)s)\n' % (self.params))
        if self.params['calibration'].val:
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
    def writeFrameCode(self,buff):
        pass
    def writeExperimentEndCode(self,buff):
        if self.params['datafile'].val != '':
            buff.writeIndented('GazeParserTracker.closeDataFile()\n')

        