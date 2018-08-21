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
iconFile = path.join(thisFolder,'GazeParserGetPos.png')
tooltip = 'GazeParserGetPos: sending a GetPos to SimpleGazeTracker'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['filler','binocular','ma']

class GazeParserGetPosComponent(BaseVisualComponent):
    """Recording with GazeParser.TrackingTools"""
    categories = ['GazeParser']
    def __init__(self, exp, parentName, name='GazeParserGetPos',
                filler='-10000', binocular='Average', ma=1, units='from exp settings'):
        self.type='GazeParserGetPos'
        self.url="http://gazeparser.sourceforge.net/"
        super(GazeParserGetPosComponent, self).__init__(exp, parentName, name)

        #params
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
        self.params['filler']=Param(filler, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=['constant','set every repeat'],
            hint="If gaze position is not available, gaze position is filled by this value.",
            label="Filler", categ="Advanced")
        self.params['binocular']=Param(binocular, valType='str', allowedTypes=[], allowedVals=['Average','L','R'],
            updates='constant', allowedUpdates=['constant','set every repeat'],
            hint="Average: average of two eyes L: left eye, R: right eye",
            label="Binocular Data", categ="Advanced")
        self.params['ma']=Param(ma, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=['constant','set every repeat'],
            hint="Integer equal or greater than 1.",
            label="Moving average", categ="Advanced")

        # these inherited params are harmless but might as well trim:
        for p in ['startType', 'startVal', 'startEstim', 'stopVal', 'stopType', 'durationEstim']:
            del self.params[p]

        # these inherited params are harmless but might as well trim:
        for p in ['color','opacity','colorSpace','pos','size','ori']:
            del self.params[p]

    def writeRoutineStartCode(self,buff):
        buff.writeIndented('%(name)s = []\n\n' % self.params)

    def writeFrameCode(self,buff):
        buff.writeIndented('%(name)s = GazeParserTracker.getEyePosition(timeout=0.01, getPupil=False, ' % self.params)
        if self.params['units'].val=='from exp settings':
            buff.writeIndented('units=win.units,  ma=%(ma)s)\n' % self.params)
        else:
            buff.writeIndented('units=%(units)s,  ma=%(ma)s)\n' % (self.params))

        buff.writeIndented('if len(%(name)s) == 2: #monocular\n' % (self.params))
        buff.setIndentLevel(+1, relative=True)
        buff.writeIndented('if %(name)s[0] == None:\n' % (self.params))
        buff.setIndentLevel(+1, relative=True)
        buff.writeIndented('%(name)s = [%(filler)s, %(filler)s]\n' % (self.params))
        buff.setIndentLevel(-2, relative=True)
        buff.writeIndented('else: #binocular\n')
        buff.setIndentLevel(+1, relative=True)
        if self.params['binocular'] == 'L':
            buff.writeIndented('if %(name)s[0] == None:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('%(name)s = [%(filler)s, %(filler)s]\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented('else:\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('%(name)s = %(name)s[0:2]:\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
        elif self.params['binocular'] == 'R':
            buff.writeIndented('if %(name)s[2] == None:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('%(name)s = [%(filler)s, %(filler)s]\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented('else:\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('%(name)s = %(name)s[2:4]:\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
        else: #average
            buff.writeIndented('if %(name)s[0] == %(name)s[2] == None:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('%(name)s = [%(filler)s, %(filler)s]\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented('elif %(name)s[0] == None: #left eye is not available\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('%(name)s = %(name)s[2:4]\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented('elif %(name)s[2] == None: #right eye is not available\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('%(name)s = %(name)s[0:2]\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented('else:\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('%(name)s = [(%(name)s[0]+%(name)s[2])/2.0,(%(name)s[1]+%(name)s[3])/2.0]\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
        buff.setIndentLevel(-1, relative=True)
