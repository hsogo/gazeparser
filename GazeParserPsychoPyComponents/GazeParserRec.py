
from _base import * #to get the template visual component
from os import path
from psychopy.app.builder.experiment import Param

thisFolder = path.abspath(path.dirname(__file__))#the absolute path to the folder containing this path
iconFile = path.join(thisFolder,'GazeParserRec.png')
tooltip = 'GazeParserRec: recording with GazeParser.TrackingTools'

# want a complete, ordered list of codeParams in Builder._BaseParamsDlg, best to define once:
paramNames = ['startmsg', 'stopmsg', 'msglist']


class GazeParserRecComponent(BaseComponent):
    """Recording with GazeParser.TrackingTools"""
    categories = ['Custom']
    def __init__(self, exp, parentName, name='GazeParserRec', startmsg='routine start', stopmsg='routine end', msglist=[], units='time (s)'):
        self.type='GazeParserRec'
        self.url="http://gazeparser.sourceforge.net/"
        self.exp=exp#so we can access the experiment if necess
        #params
        self.categories=['misc']
        self.order = ['name'] + paramNames[:] # want a copy, else codeParamNames list gets mutated
        self.params={}
        self.params['name']=Param(name, valType='code', allowedTypes=[],
            hint="The message sent when recording is started.",
            label="Name") #This name does not actually need to be independent of the others.
        self.params['startmsg']=Param(startmsg, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint=".",
            label="Message (Start)")
        self.params['stopmsg']=Param(stopmsg, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="The message sent when recording is stopped.",
            label="Message (End)")
        self.params['msglist']=Param(msglist, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint="List of messages.",
            label="Message List")
        self.params['units']=Param(units, valType='str', allowedVals=['frame N', 'time (s)'],
            hint="Units of message sending time",
            label="Units")
    def writeRoutineStartCode(self,buff):
        buff.writeIndented('GazeParserTrackerSendMessages = %(msglist)s\n' % (self.params))
        buff.writeIndented('GazeParserTracker.startRecording(%(startmsg)s)\n' % (self.params))

    def writeFrameCode(self,buff):
        buff.writeIndented('for GazeParserTrackerTmpmsg in GazeParserTrackerSendMessages:\n')
        buff.setIndentLevel(+1, relative=True)
        if self.params['units'].val=='time (s)':
            buff.writeIndented('if 0<=GazeParserTrackerTmpmsg[0]<=t:\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('GazeParserTracker.sendMessage(GazeParserTrackerTmpmsg[1])\n')
            buff.writeIndented('GazeParserTrackerTmpmsg[0]=-1\n')
            buff.setIndentLevel(-2, relative=True)
        else: # frame N
            buff.writeIndented('if GazeParserTrackerTmpmsg[0]==frameN:\n')
            buff.setIndentLevel(+1, relative=True)
            buff.writeIndented('GazeParserTracker.sendMessage(GazeParserTrackerTmpmsg[1])\n')
            buff.setIndentLevel(-2, relative=True)

    def writeRoutineEndCode(self,buff):
        buff.writeIndented('GazeParserTracker.stopRecording(%(stopmsg)s)\n' % (self.params))
        