from _base import * #to get the template visual component
from os import path
from psychopy.app.builder.experiment import Param

thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
iconFile = path.join(thisFolder,'GazeParserMessage.png')
tooltip = 'GazeParserMessage: sending a message to SimpleGazeTracker'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['time','text','units']

class GazeParserMessageComponent(BaseComponent):
    """Recording with GazeParser.TrackingTools"""
    categories = ['Custom']
    def __init__(self, exp, parentName, name='GazeParserMessage', time=0, text='message', units='time (s)'):
        self.type='GazeParserMessage'
        self.url="http://gazeparser.sourceforge.net/"
        self.exp=exp#so we can access the experiment if necess
        #params
        self.categories=['misc']
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
        self.params={}
        self.params['name']=Param(name, valType='code', allowedTypes=[],
            hint="",
            label="Name")
        self.params['time']=Param(time, valType='code', allowedTypes=[],
            hint="Message time",
            label="Time")
        self.params['text']=Param(text, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="Message text.",
            label="Message text.")
        self.params['units']=Param(units, valType='str', allowedVals=['frame N', 'time (s)'],
            hint="Units of message sending time",
            label="Unit of time")

    def writeRoutineStartCode(self,buff):
        buff.writeIndented('%(name)s_sent=False\n' % (self.params))

    def writeFrameCode(self,buff):
        if self.params['units'].val=='time (s)':
            buff.writeIndented('if %(name)s_sent=False and %(time)s<=t:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('GazeParserTracker.sendMessage(%(text)s)\n' % (self.params))
            buff.writeIndented('%(name)s_sent=True\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
        else: # frame N
            buff.writeIndented('if %(time)s==frameN:\n' % (self.params))
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('GazeParserTracker.sendMessage(%(text)s)\n' % (self.params))
            buff.setIndentLevel(-1, relative=True)
