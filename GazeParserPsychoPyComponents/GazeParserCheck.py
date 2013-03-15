
from _base import *
from os import path
from psychopy.app.builder.experiment import Param

thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
iconFile = path.join(thisFolder,'GazeParserCheck.png')
tooltip = 'GazeParserCheck: Checking fixation with GazeParser.TrackingTools'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['pos', 'maxtry', 'permerror', 'key', 'mousebutton', 'units', 'mode', 'message1', 'message2', 'message3']


class GazeParserCheckComponent(BaseComponent):
    """Checking fixation with GazeParser.TrackingTools"""
    categories = ['Custom']
    def __init__(self, exp, parentName, name='GazeParserCheck', pos=[0,0], maxtry=3, permerror=48, key="'space'", mousebutton=0, units="pix", mode='check', message1="", message2="", message3=""):
        self.type='GazeParserCheck'
        self.url="http://gazeparser.sourceforge.net/"
        self.exp=exp#so we can access the experiment if necess
        #params
        self.categories=['misc']
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
        self.params={}
        self.params['name']=Param(name, valType='code', allowedTypes=[],
            hint="",
            label="Name")
        self.params['pos']=Param(pos, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Center of target position.",
            label="Target position")
        self.params['maxtry']=Param(maxtry, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Specify how many times gaze position is measured before prompting readjustment.",
            label="Max Try")
        self.params['permerror']=Param(permerror, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Limit of permissible error between target position and gaze position.",
            label="Permissible error")
        self.params['key']=Param(key, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Responce key.",
            label="Key")
        self.params['mousebutton']=Param(mousebutton, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="0:left, 1:center, 2:right button",
            label="Responce mouse button.")
        self.params['units']=Param(units, valType='str', allowedVals=['deg', 'cm', 'pix', 'norm'],
            hint="Units of permissible error",
            label="Units")
        self.params['mode']=Param(mode, valType='str', allowedVals=['check', 'cal+check', 'cal'],
            hint="check: perfom verifyFixation() only, cal+check: perform verifyFixation() after calibrationloop(), cal: perform calibrationloop() only.",
            label="Calibration mode")
        self.params['message1']=Param(message1, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Initial message. If all of message1-3 are empty, default messages are used.",
            label="Message1")
        self.params['message2']=Param(message2, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Message prompting retry. If all of message1-3 are empty, default messages are used.",
            label="Message2")
        self.params['message3']=Param(message3, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Message prompting to call experimenter. If all of message1-3 are empty, default messages are used.",
            label="Message3")
    def writeRoutineStartCode(self,buff):
        task = self.params['mode'].val
        if task in ['cal', 'cal+check']:
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
        if task in ['check', 'cal+check']:
            buff.writeIndented('GazeParserTracker.verifyFixation(maxTry=%(maxtry)s, permissibleError=%(permerror)s ,key=%(key)s, \n' % (self.params))
            buff.writeIndented('    position=%(pos)s, mouseButton=%(mousebutton)s, units=%(units)s,\n' % (self.params))
            if self.params['message1'].val == self.params['message2'].val == self.params['message3'].val == '':
                buff.writeIndented('    message=None)\n\n')
            else:
                buff.writeIndented('    message=[%(message1)s, %(message2)s, %(message3)s])\n\n' % (self.params))
            buff.writeIndented('routineTimer.reset()\n')
        