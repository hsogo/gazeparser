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
iconFile = path.join(thisFolder,'GazeParserCheck.png')
tooltip = 'GazeParserCheck: Checking fixation with GazeParser.TrackingTools'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['pos', 'maxtry', 'permerror', 'key', 'mousebutton', 'units', 'mode', 'message1', 'message2', 'message3']


class GazeParserCheckComponent(BaseVisualComponent):
    """Checking fixation with GazeParser.TrackingTools"""
    categories = ['GazeParser']
    def __init__(self, exp, parentName, name='GazeParserCheck', pos=[0,0], maxtry=3, permerror=0.1, key="'space'",
                 mousebutton=0, units="pix", mode='check', message1="", message2="", message3=""):
        super(GazeParserCheckComponent, self).__init__(exp, parentName, name)
        self.type='GazeParserCheck'
        self.url="http://gazeparser.sourceforge.net/"

        #params
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
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
            label="Mouse button")
        self.params['mode']=Param(mode, valType='str', allowedVals=['check', 'cal+check', 'cal'],
            hint="check: perfom verifyFixation() only, cal+check: perform verifyFixation() after calibrationloop(), cal: perform calibrationloop() only.",
            label="Calibration mode")
        self.params['message1']=Param(message1, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Initial message. If all of message1-3 are empty, default messages are used.",
            label="Message1", categ="Advanced")
        self.params['message2']=Param(message2, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Message prompting retry. If all of message1-3 are empty, default messages are used.",
            label="Message2", categ="Advanced")
        self.params['message3']=Param(message3, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Message prompting to call experimenter. If all of message1-3 are empty, default messages are used.",
            label="Message3", categ="Advanced")
        # these inherited params are harmless but might as well trim:
        for p in ['startType', 'startVal', 'startEstim', 'stopVal', 'stopType', 'durationEstim']:
            del self.params[p]
        for p in ['color','opacity','colorSpace','size','ori']:
            del self.params[p]
    def writeRoutineStartCode(self,buff):
        task = self.params['mode'].val
        if task in ['cal', 'cal+check']:
            buff.writeIndented('logging.exp(\'Start GazeParser calibration\')\n')
            buff.writeIndented('tmpGazeParserLogLevel = logFile.level\n')
            buff.writeIndented('logFile.setLevel(logging.WARNING)\n')
            buff.writeIndented('while True:\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('GazeParserRes = GazeParserTracker.calibrationLoop()\n')
            buff.writeIndented('if GazeParserRes=="q":\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('core.quit(0)\n')
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented('if GazeParserTracker.isCalibrationFinished():\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('break\n')
            buff.setIndentLevel(-2, relative=True)
            buff.writeIndented('logFile.setLevel(tmpGazeParserLogLevel)\n')
            buff.writeIndented('logging.exp(\'End GazeParser calibration\')\n\n')
        if task in ['check', 'cal+check']:
            buff.writeIndented('logging.exp(\'Start GazeParser verifyFixation\')\n')
            buff.writeIndented('tmpGazeParserLogLevel = logFile.level\n')
            buff.writeIndented('logFile.setLevel(logging.WARNING)\n')
            buff.writeIndented('GazeParserTracker.verifyFixation(maxTry=%(maxtry)s, permissibleError=%(permerror)s ,key=%(key)s, \n' % (self.params))
            buff.writeIndented('    position=%(pos)s, mouseButton=%(mousebutton)s, \n' % (self.params))
            if self.params['units'].val=='from exp settings':
                buff.writeIndented('    units=win.units, \n')
            else:
                buff.writeIndented('    units=%(units)s, \n' % (self.params))
            if self.params['message1'].val == self.params['message2'].val == self.params['message3'].val == '':
                buff.writeIndented('    message=None)\n\n')
            else:
                buff.writeIndented('    message=[%(message1)s, %(message2)s, %(message3)s])\n' % (self.params))
            buff.writeIndented('logFile.setLevel(tmpGazeParserLogLevel)\n')
            buff.writeIndented('logging.exp(\'End GazeParser verifyFixation\')\n')
            buff.writeIndented('routineTimer.reset()\n\n')
    def writeFrameCode(self,buff):
        pass
