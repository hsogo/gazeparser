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
paramNames = ['startrec', 'startmsg', 'stoprec', 'stopmsg']

class GazeParserRecComponent(BaseComponent):
    """Recording with GazeParser.TrackingTools"""
    categories = ['GazeParser']
    thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
    iconFile = path.join(thisFolder,'GazeParserRec.png')
    tooltip = 'GazeParserRec: recording with GazeParser.TrackingTools'

    def __init__(self, exp, parentName, name='GazeParserRec', startrec=True, stoprec=True, startmsg='routine start', stopmsg='routine end'):
        super(GazeParserRecComponent, self).__init__(exp, parentName, name)
        
        self.type='GazeParserRec'
        self.url="http://gazeparser.sourceforge.net/"
        self.exp=exp#so we can access the experiment if necess
        
        #params
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
        self.params['startrec']=Param(startrec, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Start recording at the beginning of this routine.  Uncheck this if recording is continuing from the preceding routine.",
            label="Start Recording")
        self.params['startmsg']=Param(startmsg, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=['constant','set every repeat'],
            hint="The message sent when recording is started.",
            label="Message (Start)")
        self.params['stoprec']=Param(stoprec, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Stop recording at the end of this routine.  Uncheck this if you want to continue recording in the next routine.",
            label="Stop Recording")
        self.params['stopmsg']=Param(stopmsg, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=['constant','set every repeat'],
            hint="The message sent when recording is stopped.",
            label="Message (End)")
        # these inherited params are harmless but might as well trim:
        for p in ['startType', 'startVal', 'startEstim', 'stopVal', 'stopType', 'durationEstim']:
            del self.params[p]

        self.depends += [  # allows params to turn each other off/on
            {"dependsOn": "startrec",  # must be param name
             "condition": "== True",  # val to check for
             "param": "startmsg",  # param property to alter
             "true": "enable",  # what to do with param if condition is True
             "false": "disable",  # permitted: hide, show, enable, disable
             },
            {"dependsOn": "stoprec",  # must be param name
             "condition": "== True",  # val to check for
             "param": "stopmsg",  # param property to alter
             "true": "enable",  # what to do with param if condition is True
             "false": "disable",  # permitted: hide, show, enable, disable
             }
        ]
    def writeRoutineStartCode(self,buff):
        if self.params['startrec'].val:
            buff.writeIndented('GazeParserTracker.startRecording(%(startmsg)s)\n' % (self.params))
            buff.writeIndented('routineTimer.add('+self.parentName+'Clock.getTime())\n')
            buff.writeIndented(self.parentName+'Clock.reset() # clock must be reset because startRecording() takes hundreds of milliseconds\n')
            buff.writeIndented('GazeParserTracker.sendMessage(\'rec_sync\')\n' % (self.params))
            buff.writeIndented('logging.exp(\'GazeParser rec_sync\')\n' % (self.params))

    def writeRoutineEndCode(self,buff):
        if self.params['stoprec'].val:
            buff.writeIndented('GazeParserTracker.stopRecording(%(stopmsg)s)\n' % (self.params))
        