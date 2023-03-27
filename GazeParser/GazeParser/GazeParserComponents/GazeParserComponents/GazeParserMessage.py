"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2016 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


try:
    from psychopy.experiment.components import *
except:
    from psychopy.app.builder.components._base import *
from os import path

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['time','timeType','text']

class GazeParserMessageComponent(BaseComponent):
    """Recording with GazeParser.TrackingTools"""
    categories = ['GazeParser']
    thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
    iconFile = path.join(thisFolder,'GazeParserMessage.png')
    tooltip = 'GazeParserMessage: sending a message to SimpleGazeTracker'

    def __init__(self, exp, parentName, name='GazeParserMessage', timeType='time (s)', time=0.0, text='message', sync=False):
        self.type='GazeParserMessage'
        self.url="http://gazeparser.sourceforge.net/"
        super(GazeParserMessageComponent, self).__init__(exp, parentName, name)

        #params
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
        self.params['time']=Param(time, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=['constant','set every repeat'],
            hint="When this message should be sent?",
            label='time')
        self.params['timeType']=Param(timeType, valType='str', allowedVals=['time (s)', 'frame N', 'condition'],
            updates='constant', allowedUpdates=[],
            hint="How do you want to define time?",
            label='time type')
        self.params['text']=Param(text, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=['constant','set every repeat'],
            hint="Message text",
            label="Message text")
        self.params['sync']=Param(text, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint='Message is recorded when the screen is flipped',
            label='Sync timing with screen')

        # these inherited params are harmless but might as well trim:
        for p in ['startType', 'startVal', 'startEstim', 'stopVal', 'stopType', 'durationEstim']:
            del self.params[p]

    def writeRoutineStartCode(self,buff):
        buff.writeIndented('%(name)s_sent=False\n' % (self.params))

    def writeFrameCode(self,buff):
        if self.params['sync'].val:
            code1 = 'win.callOnFlip(GazeParserTracker.sendMessage, %(text)s)\n' % (self.params)
            code2 = 'win.callOnFlip(logging.exp, \'GazeParser SendMessage, %%s=%(time)s\')\n)' % (self.params) 
        else:
            code1 = 'GazeParserTracker.sendMessage(%(text)s)\n' % (self.params)
            code2 = 'logging.exp(\'GazeParser SendMessage, %%s=%(time)s\')\n' % (self.params)

        if self.params['timeType'].val=='time (s)':
            buff.writeIndented('if %(name)s_sent==False and %(time)s<=t:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented(code1)
            buff.writeIndented(code2 % ('time'))
            buff.writeIndented('%(name)s_sent=True\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
        elif self.params['timeType'].val=='frame N':
            buff.writeIndented('if %(time)s==frameN:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented(code1)
            buff.writeIndented(code2 % ('frameN'))
            buff.setIndentLevel(-1, relative=True)
        else: # condition
            buff.writeIndented('if %(time)s:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented(code1)
            buff.writeIndented(code2 % ('condition'))
            buff.setIndentLevel(-1, relative=True)
