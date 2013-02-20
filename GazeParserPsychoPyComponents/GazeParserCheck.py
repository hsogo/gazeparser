
from _base import *
from os import path
from psychopy.app.builder.experiment import Param

thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
iconFile = path.join(thisFolder,'GazeParserCheck.png')
tooltip = 'GazeParserCheck: Checking fixation with GazeParser.TrackingTools'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['maxtry', 'torelance', 'key', 'mousebutton', 'message', 'units']


class GazeParserCheckComponent(BaseComponent):
    """Checking fixation with GazeParser.TrackingTools"""
    categories = ['Custom']
    def __init__(self, exp, parentName, name='GazeParserCheck', maxtry=3, torelance=48, key="'space'", mousebutton=0, message="", units="pix"):
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
        self.params['maxtry']=Param(maxtry, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint=".",
            label="Max Try")
        self.params['torelance']=Param(torelance, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Calibration area (left, bottom, right, top).",
            label="Torelance")
        self.params['key']=Param(key, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Responce key",
            label="Key")
        self.params['mousebutton']=Param(mousebutton, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="0:left, 1:center, 2:right button",
            label="Responce button")
        self.params['message']=Param(message, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="A list of three strings.",
            label="Message List")
        self.params['units']=Param(units, valType='str', allowedVals=['deg', 'cm', 'pix', 'norm'],
            hint="Units of tolerance",
            label="Units")
    def writeRoutineStartCode(self,buff):
        buff.writeIndented('GazeParserTracker.verifyFixation(maxTry=%(maxtry)s, permissibleError=%(torelance)s ,key=%(key)s, \n' % (self.params))
        buff.writeIndented('    mouseButton=%(mousebutton)s, units=%(units)s,\n' % (self.params))
        if self.params['message'].val == '':
            buff.writeIndented('    message=None)\n\n')
        else:
            buff.writeIndented('    message=%(message)s)\n\n' % (self.params))
        buff.writeIndented('routineTimer.reset()\n')
        