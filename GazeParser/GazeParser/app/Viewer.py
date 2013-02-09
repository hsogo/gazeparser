#!/usr/bin/env python
"""
Part of GazeParser library.
Copyright (C) 2012-2013 Hiroyuki Sogo.
Distributed under the terms of the GNU General Public License (GPL).

Thanks to following page for embedded plot.

* http://www.mailinglistarchive.com/html/matplotlib-users@lists.sourceforge.net/2010-08/msg00148.html

"""

import ConfigParser
import shutil
import Tkinter
import tkFileDialog
import tkMessageBox
import tkColorChooser
import Image
import ImageTk
import GazeParser
import GazeParser.Converter
import os
import sys
import re
import functools
import traceback
import numpy
import matplotlib
import matplotlib.figure
import matplotlib.font_manager
import matplotlib.patches
import GazeParser.app.ConfigEditor
import GazeParser.app.Converters
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from GazeParser.Converter import buildEventListBinocular, buildEventListMonocular, applyFilter

MAX_RECENT = 5
PLOT_OFFSET = 10

class jumpToTrialWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self,master)
        self.mainWindow = mainWindow
        
        self.newtrStr = Tkinter.StringVar()
        Tkinter.Label(self, text='Jump to... (0-%s)'%(len(mainWindow.D)-1)).grid(row=0,column=0)
        Tkinter.Entry(self, textvariable=self.newtrStr).grid(row=0,column=1)
        
        Tkinter.Button(self, text='OK', command=self.jump).grid(row=1,column=0,columnspan=2)
        self.pack()

    def jump(self, event=None):
        try:
            newtr = int(self.newtrStr.get())
        except:
            tkMessageBox.showerror('Error','Value must be an integer')
            return
        
        if newtr<0 or newtr>=len(self.mainWindow.D):
            tkMessageBox.showerror('Error','Invalid trial number')
            return
        
        self.mainWindow.tr = newtr
        if self.mainWindow.tr==0:
            self.mainWindow.menu_view.entryconfigure('Prev Trial', state = 'disabled')
        else:
            self.mainWindow.menu_view.entryconfigure('Prev Trial', state = 'normal')
        if self.mainWindow.tr==len(self.mainWindow.D)-1:
            self.mainWindow.menu_view.entryconfigure('Next Trial', state = 'disabled')
        else:
            self.mainWindow.menu_view.entryconfigure('Next Trial', state = 'normal')
        self.mainWindow.selectionlist = {'Sac':[], 'Fix':[], 'Msg':[], 'Blink':[]}
        self.mainWindow.selectiontype.set('Emphasize')
        self.mainWindow._plotData()
        self.mainWindow._updateMsgBox()

class exportToFileWindow(Tkinter.Frame):
    def __init__(self, data, additional, trial, master=None):
        Tkinter.Frame.__init__(self,master)
        self.D = data
        self.tr = trial
        
        self.flgSac = Tkinter.BooleanVar()
        self.flgFix = Tkinter.BooleanVar()
        self.flgBlk = Tkinter.BooleanVar()
        self.flgMsg = Tkinter.BooleanVar()
        self.flgSac.set(1)
        self.flgFix.set(1)
        self.flgBlk.set(1)
        self.flgMsg.set(1)
        self.flgTrials = Tkinter.StringVar()
        self.flgOrder = Tkinter.StringVar()
        self.flgTrials.set('ThisTrial')
        self.flgOrder.set('ByTime')
        
        itemFrame = Tkinter.LabelFrame(self, text='Check items to export.')
        itemFrame.grid(row=0,column=0)
        Tkinter.Checkbutton(itemFrame, text='Saccade', variable=self.flgSac).grid(row=0,column=0)
        Tkinter.Checkbutton(itemFrame, text='Fixation', variable=self.flgFix).grid(row=1,column=0)
        Tkinter.Checkbutton(itemFrame, text='Blink', variable=self.flgBlk).grid(row=0,column=1)
        Tkinter.Checkbutton(itemFrame, text='Message', variable=self.flgMsg).grid(row=1,column=1)
        
        trialFrame = Tkinter.LabelFrame(self, text='Range')
        trialFrame.grid(row=1,column=0)
        Tkinter.Radiobutton(trialFrame, text='This trial', variable=self.flgTrials, value='ThisTrial').grid(row=0,column=0)
        Tkinter.Radiobutton(trialFrame, text='All trials', variable=self.flgTrials, value='AllTrials').grid(row=0,column=1)
        
        groupFrame = Tkinter.LabelFrame(self, text='Grouping')
        groupFrame.grid(row=2,column=0)
        Tkinter.Radiobutton(groupFrame, text='By time', variable=self.flgOrder, value='ByTime').grid(row=0,column=0)
        Tkinter.Radiobutton(groupFrame, text='By events', variable=self.flgOrder, value='ByEvents').grid(row=0,column=1)
        
        Tkinter.Button(self, text='Export', command=self.export).grid(row=3,column=0)
        self.pack()
        
    def export(self, event=None):
        if self.flgSac.get() or self.flgFix.get() or self.flgBlk.get() or self.flgMsg.get():
            exportFileName = tkFileDialog.asksaveasfilename(initialdir=GazeParser.homeDir)
            fp = open(exportFileName, 'w')
            
            if self.flgOrder.get()=='ByTime':
                if self.flgTrials.get()=='ThisTrial':
                    trlist = [self.tr]
                else: #AllTrials
                    trlist = range(len(self.D))
                for tr in trlist:
                    fp.write('TRIAL%d\n' % (tr+1))
                    for e in self.D[self.tr].EventList:
                        if isinstance(e,GazeParser.SaccadeData) and self.flgSac.get():
                            fp.write('SAC,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n' % 
                                     (e.startTime, e.endTime, e.start[0], e.start[1], e.end[0], e.end[1]))
                        elif isinstance(e,GazeParser.FixationData) and self.flgFix.get():
                            fp.write('FIX,%.1f,%.1f,%.1f,%.1f\n' % 
                                     (e.startTime, e.endTime, e.center[0],e.center[1]))
                        elif isinstance(e,GazeParser.MessageData) and self.flgMsg.get():
                            fp.write('MSG,%.1f,%.1f,%s\n' % (e.time, e.time, e.text))
                        elif isinstance(e,GazeParser.BlinkData) and self.flgBlk.get():
                            fp.write('BLK,%.1f,%.1f\n' % (e.startTime, e.endTime))
                
            else: #ByEvents
                if self.flgTrials.get()=='ThisTrial':
                    trlist = [self.tr]
                else: #AllTrials
                    trlist = range(len(self.D))
                for tr in trlist:
                    fp.write('TRIAL%d\n' % (tr+1))
                    if self.flgSac.get():
                        for e in self.D[tr].Sac:
                            fp.write('SAC,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n' % 
                                     (e.startTime, e.endTime, e.start[0], e.start[1], e.end[0], e.end[1]))
                    if self.flgFix.get():
                        for e in self.D[tr].Fix:
                            fp.write('FIX,%.1f,%.1f,%.1f,%.1f\n' % 
                                     (e.startTime, e.endTime, e.center[0],e.center[1]))
                    if self.flgMsg.get():
                        for e in self.D[tr].Msg:
                            fp.write('MSG,%.1f,%.1f,%s\n' % (e.time, e.time, e.text))
                    if self.flgBlk.get():
                        for e in self.D[tr].Blink:
                            fp.write('BLK,%.1f,%.1f\n' % (e.startTime, e.endTime))
            
            fp.close()
            
            tkMessageBox.showinfo('Info','Done.')
        
        else:
            tkMessageBox.showinfo('Info','No items were selected.')

class GetSaccadeLatency(Tkinter.Frame):
    def __init__(self, data, additional, conf, master=None):
        Tkinter.Frame.__init__(self,master)
        self.D = data
        self.C = additional
        self.conf = conf
        
        self.messageStr = Tkinter.StringVar()
        self.useRegexp = Tkinter.BooleanVar()
        self.minLatencyStr = Tkinter.StringVar()
        self.maxLatencyStr = Tkinter.StringVar()
        self.minAmplitudeStr = Tkinter.StringVar()
        self.maxAmplitudeStr = Tkinter.StringVar()
        self.amplitudeUnit = Tkinter.StringVar()
        self.amplitudeUnit.set('pix')
        
        #plot frame
        plotFrame = Tkinter.Frame(self)
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, master=plotFrame)
        self.ax = self.fig.add_axes([0.1, 0.1, 0.8, 0.8])
        self.canvas._tkcanvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)
        plotFrame.pack(side=Tkinter.LEFT)
        
        #parameter frame
        paramFrame = Tkinter.Frame(self)
        
        messageFrame = Tkinter.LabelFrame(paramFrame,text='Message')
        Tkinter.Entry(messageFrame, textvariable=self.messageStr).pack()
        Tkinter.Checkbutton(messageFrame, text='Regular expression', variable=self.useRegexp).pack()
        messageFrame.pack(fill=Tkinter.X)
        
        latencyFrame = Tkinter.LabelFrame(paramFrame,text='Latency')
        Tkinter.Label(latencyFrame, text='Min').grid(row=0,column=0)
        Tkinter.Entry(latencyFrame, textvariable=self.minLatencyStr).grid(row=0,column=1)
        Tkinter.Label(latencyFrame, text='Max').grid(row=1,column=0)
        Tkinter.Entry(latencyFrame, textvariable=self.maxLatencyStr).grid(row=1,column=1)
        latencyFrame.pack(fill=Tkinter.X)
        
        amplitudeFrame = Tkinter.LabelFrame(paramFrame,text='Amplitude')
        Tkinter.Label(amplitudeFrame, text='Min').grid(row=0,column=0)
        Tkinter.Entry(amplitudeFrame, textvariable=self.minAmplitudeStr).grid(row=0,column=1)
        Tkinter.Label(amplitudeFrame, text='Max').grid(row=1,column=0)
        Tkinter.Entry(amplitudeFrame, textvariable=self.maxAmplitudeStr).grid(row=1,column=1)
        Tkinter.Radiobutton(amplitudeFrame, text='deg', variable=self.amplitudeUnit, value='deg').grid(row=2,column=1)
        Tkinter.Radiobutton(amplitudeFrame, text='pix', variable=self.amplitudeUnit, value='pix').grid(row=3,column=1)
        amplitudeFrame.pack(fill=Tkinter.X)
        
        Tkinter.Button(paramFrame, text='Search', command=self.calc).pack()
        
        paramFrame.pack(side=Tkinter.LEFT, anchor=Tkinter.NW)
        
        self.pack()
    
    def calc(self, event=None):
        minamp = None
        maxamp = None
        minlat = None
        maxlat = None
        try:
            if self.minAmplitudeStr.get() != '':
                minamp = float(self.minAmplitudeStr.get())
            if self.maxAmplitudeStr.get() != '':
                maxamp = float(self.maxAmplitudeStr.get())
            if self.minLatencyStr.get() != '':
                minlat = float(self.minLatencyStr.get())
            if self.maxLatencyStr.get() != '':
                maxlat = float(self.maxLatencyStr.get())
        except:
            tkMessageBox.showerror('Error','Invalid values are found in amplitude/latency.')
        for value in (minamp,maxamp,minlat,maxlat):
            if value!=None and value<0:
                tkMessageBox.showerror('Error','latency and amplitude must be zero or positive.')
                return
        
        nMsg = 0
        nSac = 0
        trdata = []
        sacdata = []
        for tr in range(len(self.D)):
            idxlist = self.D[tr].findMessage(self.messageStr.get(), byIndices=True, useRegexp=self.useRegexp.get())
            nMsg += len(idxlist)
            for msgidx in idxlist:
                isSaccadeFound = False
                sac = self.D[tr].Msg[msgidx].getNextEvent(eventType='saccade')
                if sac != None: #no saccade
                    while True:
                        tmplatency = sac.relativeStartTime(self.D[tr].Msg[msgidx])
                        if self.amplitudeUnit.get()=='deg':
                            tmpamplitude = sac.amplitude
                        else:
                            tmpamplitude = sac.length
                        if (minamp==None or minamp<=tmpamplitude) and (maxamp==None or maxamp>=tmpamplitude) and \
                           (minlat==None or minlat<=tmplatency) and (maxlat==None or maxlat>=tmplatency):
                            isSaccadeFound = True
                            break
                        sac = sac.getNextEvent(eventType='saccade')
                        if sac == None:
                            break
                if isSaccadeFound:
                    nSac += 1
                    trdata.append([tr,self.D[tr].Msg[msgidx].time,self.D[tr].Msg[msgidx].text])
                    sacdata.append([tmplatency,tmpamplitude])
        
        if nMsg>0:
            if nSac>0:
                self.ax.clear()
                latdata = numpy.array(sacdata)[:,0]
                self.ax.hist(latdata)
                self.fig.canvas.draw()
                ans = tkMessageBox.askyesno('Export','%d saccades/%d messages(%.1f%%).\nExport data?' % (nSac, nMsg, (100.0*nSac)/nMsg))
                if ans:
                    fname = tkFileDialog.asksaveasfilename()
                    if fname!='':
                        fp = open(fname, 'w')
                        fp.write('Trial\tMessageTime\tMessageText\tLatency\tAmplitude\n')
                        for n in range(nSac):
                            fp.write('%d\t%.2f\t%s\t' % tuple(trdata[n]))
                            fp.write('%.2f\t%.2f\n' % tuple(sacdata[n]))
                        fp.close()
                        tkMessageBox.showinfo('Info','Done.')
                    else:
                        tkMessageBox.showinfo('Info','Canceled.')
            else:
                tkMessageBox.showinfo('Info','No saccades are detected')
        else:
            tkMessageBox.showinfo('Info','No messages are found')


def getComplementaryColorStr(col):
    """
    get complementary color (e.g. '#00FF88' -> '#FF0077'
    """
    return '#'+hex(16777215-int(col[1:],base=16))[2:].upper()

def getTextColor(backgroundColor,thresh=0.3):
    minc =  min(int(backgroundColor[1:3],base=16),int(backgroundColor[3:5],base=16),int(backgroundColor[5:7],base=16))
    if minc/255.0 < 0.3:
        return '#FFFFFF'
    else:
        return '#000000'

def parsegeometry(geometry):
    m = re.match("(\d+)x(\d+)([-+]\d+)([-+]\d+)", geometry)
    if not m:
        raise ValueError("failed to parse geometry string")
    return map(int, m.groups())


class ViewerOptions(object):
    options = [
        ['Version',
         [['VIEWER_VERSION',str]]],
        ['Appearance',
         [['CANVAS_WIDTH',int],
          ['CANVAS_HEIGHT',int],
          ['CANVAS_DEFAULT_VIEW',str],
          ['CANVAS_SHOW_FIXNUMBER',bool],
          ['CANVAS_FONT_FILE',str],
          ['CANVAS_XYAXES_UNIT',str],
          ['CANVAS_GRID_ABSCISSA_XY',str],
          ['CANVAS_GRID_ORDINATE_XY',str],
          ['CANVAS_GRID_ABSCISSA_XYT',str],
          ['CANVAS_GRID_ORDINATE_XYT',str],
          ['COLOR_TRAJECTORY_L_SAC',str],
          ['COLOR_TRAJECTORY_R_SAC',str],
          ['COLOR_TRAJECTORY_L_FIX',str],
          ['COLOR_TRAJECTORY_R_FIX',str],
          ['COLOR_TRAJECTORY_L_X',str],
          ['COLOR_TRAJECTORY_L_Y',str],
          ['COLOR_TRAJECTORY_R_X',str],
          ['COLOR_TRAJECTORY_R_Y',str],
          ['COLOR_FIXATION_FC',str],
          ['COLOR_FIXATION_BG',str],
          ['COLOR_FIXATION_FC_E',str],
          ['COLOR_FIXATION_BG_E',str],
          ['COLOR_SACCADE_HATCH',str],
          ['COLOR_SACCADE_HATCH_E',str],
          ['COLOR_BLINK_HATCH',str],
          ['COLOR_MESSAGE_CURSOR',str],
          ['COLOR_MESSAGE_FC',str],
          ['COLOR_MESSAGE_BG',str]]],
        ['Recent',
         [['RECENT_DIR01',str],
          ['RECENT_DIR02',str],
          ['RECENT_DIR03',str],
          ['RECENT_DIR04',str],
          ['RECENT_DIR05',str]]]
    ]
    
    def __init__(self):
        initialConfigFile = os.path.join(os.path.dirname(__file__),'viewer.cfg')
        appConfigDir = os.path.join(GazeParser.configDir, 'app')
        if not os.path.isdir(appConfigDir):
            os.mkdir(appConfigDir)
        
        self.viewerConfigFile = os.path.join(appConfigDir, 'viewer.cfg')
        if not os.path.isfile(self.viewerConfigFile):
            shutil.copyfile(initialConfigFile,self.viewerConfigFile)
        
        appConf = ConfigParser.SafeConfigParser()
        appConf.optionxform = str
        appConf.read(self.viewerConfigFile)
        
        try:
            self.VIEWER_VERSION = appConf.get('Version','VIEWER_VERSION')
        except:
            ans = tkMessageBox.askyesno('Error','No VIEWER_VERSION option in configuration file (%s). Backup current file and then initialize configuration file?\n' % (self.viewerConfigFile))
            if ans:
                shutil.copyfile(self.viewerConfigFile,self.viewerConfigFile+'.bak')
                shutil.copyfile(initialConfigFile,self.viewerConfigFile)
                appConf = ConfigParser.SafeConfigParser()
                appConf.optionxform = str
                appConf.read(self.viewerConfigFile)
                self.VIEWER_VERSION = appConf.get('Version','VIEWER_VERSION')
            else:
                tkMessageBox.showinfo('info','Please correct configuration file manually.')
                sys.exit()
        
        doMerge = False
        if self.VIEWER_VERSION != GazeParser.__version__:
            ans = tkMessageBox.askyesno('Warning','VIEWER_VERSION of configuration file (%s) disagree with GazeParser version (%s). Backup current configuration file and build new configuration file?'%(self.VIEWER_VERSION, GazeParser.__version__))
            if ans:
                shutil.copyfile(self.viewerConfigFile,self.viewerConfigFile+'.bak')
                doMerge = True
            else:
                tkMessageBox.showinfo('info','Please update configuration file manually.')
                sys.exit()
        
        if doMerge:
            appNewConf = ConfigParser.SafeConfigParser()
            appNewConf.optionxform = str
            appNewConf.read(initialConfigFile)
            newOpts = []
            for section,params in self.options:
                for optName, optType in params:
                    if section=='Version' and optName=='VIEWER_VERSION':
                        setattr(self,optName,optType(appNewConf.get(section,optName)))
                        newOpts.append(' * '+optName)
                    elif appConf.has_option(section,optName):
                        setattr(self,optName,optType(appConf.get(section,optName)))
                    else:
                        setattr(self,optName,optType(appNewConf.get(section,optName)))
                        newOpts.append(' * '+optName)
            #new version number
            tkMessageBox.showinfo('info','Added:\n'+'\n'.join(newOpts))
        
        else:
            for section,params in self.options:
                for optName, optType in params:
                    setattr(self,optName,optType(appConf.get(section,optName)))
        
        #set recent directories
        self.RecentDir = []
        for i in range(5):
            d = getattr(self,'RECENT_DIR%02d' % (i+1))
            if d != '':
                self.RecentDir.append(d)
        
    
    def _write(self):
        #set recent directories
        for i in range(5):
            if i<len(self.RecentDir):
                setattr(self, 'RECENT_DIR%02d' % (i+1), self.RecentDir[i])
            else:
                setattr(self, 'RECENT_DIR%02d' % (i+1), '')
        
        with open(self.viewerConfigFile, 'w') as fp:
            for section,params in self.options:
                fp.write('[%s]\n' % section)
                for optName, optType in params:
                    fp.write('%s = %s\n' % (optName, getattr(self,optName)))
                fp.write('\n')
    

class configColorWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self,master)
        self.mainWindow = mainWindow
        r = 0
        self.newColorDict = {}
        self.origColorDict = {}
        self.buttonDict = {}
        for section in mainWindow.conf.options:
            if section[0] == 'Appearance':
                for item in section[1]:
                    if item[0][0:5] != 'COLOR':
                        continue
                    name = item[0]
                    self.origColorDict[name] = getattr(mainWindow.conf,name)
                    self.newColorDict[name] = getattr(mainWindow.conf,name)
                    Tkinter.Label(self, text=name).grid(row=r,column=0)
                    self.buttonDict[name] = Tkinter.Button(self, text=self.newColorDict[name],
                                                           command=functools.partial(self._chooseColor,name=name),
                                                           bg=self.newColorDict[name], fg=getTextColor(self.newColorDict[name]))
                    self.buttonDict[name].grid(row=r,column=1,sticky=Tkinter.W + Tkinter.E)
                    r+=1
        Tkinter.Button(self, text='Update plot', command=self._updatePlot).grid(row=r,column=0)
        Tkinter.Button(self, text='Reset', command=self._resetColor).grid(row=r,column=1)
        self.pack()
    
    def _chooseColor(self,name):
        ret = tkColorChooser.askcolor()
        if ret[1] != None:
            self.newColorDict[name] = ret[1].upper()
            self.buttonDict[name].config(text=self.newColorDict[name], bg=self.newColorDict[name], fg=getTextColor(self.newColorDict[name]))
    
    def _updatePlot(self,event=None):
        for name in self.newColorDict.keys():
            setattr(self.mainWindow.conf,name,self.newColorDict[name])
        self.mainWindow._plotData()
    
    def _resetColor(self,event=None):
        for name in self.origColorDict.keys():
            setattr(self.mainWindow.conf,name,self.origColorDict[name])
            self.newColorDict[name] = self.origColorDict[name]
            self.buttonDict[name].config(text=self.origColorDict[name], bg=self.origColorDict[name])

class plotRangeWindow(Tkinter.Frame):
    """
    .. deprecated:: 0.6.1
    """
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self,master)
        self.currentPlotArea = mainWindow.currentPlotArea
        self.ax = mainWindow.ax
        self.fig = mainWindow.fig
        
        self.strings = [Tkinter.StringVar() for i in range(4)]
        labels = ['Abcissa Min','Abcissa Max','Ordinate Min','Ordinate Max']
        Tkinter.Label(self, text='Current View (unit=pix)').grid(row=0,column=0,columnspan=2)
        for i in range(4):
            self.strings[i].set(str(self.currentPlotArea[i]))
            Tkinter.Label(self, text=labels[i]).grid(row=i+1,column=0)
            Tkinter.Entry(self, textvariable=self.strings[i]).grid(row=i+1,column=1)
        Tkinter.Button(self, text='Update plot', command=self._updatePlot).grid(row=5,column=0,columnspan=2)
        self.pack()
        
    def _updatePlot(self, event=None):
        tmpPlotArea = [0,0,0,0]
        try:
            for i in range(4):
                tmpPlotArea[i] = float(self.strings[i].get())
            
            for i in range(4):
                self.currentPlotArea[i] = tmpPlotArea[i]
            
            self.ax.axis(self.currentPlotArea)
            self.fig.canvas.draw()
        except:
            tkMessageBox.showinfo('Error','Illeagal values')

class configGridWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self,master)
        self.mainWindow = mainWindow
        self.choiceAbscissa = Tkinter.StringVar()
        self.choiceOrdinate = Tkinter.StringVar()
        self.strAbscissa = Tkinter.StringVar()
        self.strOrdinate = Tkinter.StringVar()
        
        if self.mainWindow.plotStyle == 'XY':
            xparams = self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XY.split('#')
            self.choiceAbscissa.set(xparams[0])
            yparams = self.mainWindow.conf.CANVAS_GRID_ORDINATE_XY.split('#')
            self.choiceOrdinate.set(yparams[0])
        else:
            xparams = self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XYT.split('#')
            self.choiceAbscissa.set(xparams[0])
            yparams = self.mainWindow.conf.CANVAS_GRID_ORDINATE_XYT.split('#')
            self.choiceOrdinate.set(yparams[0])
        
        if xparams[0] == 'INTERVAL' or xparams[0] == 'CUSTOM':
            self.strAbscissa.set(xparams[1])
        if yparams[0] == 'INTERVAL' or yparams[0] == 'CUSTOM':
            self.strOrdinate.set(yparams[1])
        
        
        xframe = Tkinter.LabelFrame(self, text='Abscissa')
        Tkinter.Radiobutton(xframe, text='No grid', variable=self.choiceAbscissa, value='NOGRID', command=self._onClickRadiobuttons).grid(row=0,column=0)
        Tkinter.Radiobutton(xframe, text='Show grid on current ticks', variable=self.choiceAbscissa, value='CURRENT', command=self._onClickRadiobuttons).grid(row=0,column=1)
        Tkinter.Radiobutton(xframe, text='Set interval ticks', variable=self.choiceAbscissa, value='INTERVAL', command=self._onClickRadiobuttons).grid(row=0,column=2)
        Tkinter.Radiobutton(xframe, text='Set custom ticks', variable=self.choiceAbscissa, value='CUSTOM', command=self._onClickRadiobuttons).grid(row=0,column=3)
        self.abscissaEntry = Tkinter.Entry(xframe, textvariable=self.strAbscissa)
        self.abscissaEntry.grid(row=1,column=0,columnspan=4,sticky=Tkinter.W+Tkinter.E)
        xframe.pack()
        
        yframe = Tkinter.LabelFrame(self, text='Ordinate')
        Tkinter.Radiobutton(yframe, text='No grid', variable=self.choiceOrdinate, value='NOGRID', command=self._onClickRadiobuttons).grid(row=0,column=0)
        Tkinter.Radiobutton(yframe, text='Show grid on current ticks', variable=self.choiceOrdinate, value='CURRENT', command=self._onClickRadiobuttons).grid(row=0,column=1)
        Tkinter.Radiobutton(yframe, text='Set interval ticks', variable=self.choiceOrdinate, value='INTERVAL', command=self._onClickRadiobuttons).grid(row=0,column=2)
        Tkinter.Radiobutton(yframe, text='Set custom ticks', variable=self.choiceOrdinate, value='CUSTOM', command=self._onClickRadiobuttons).grid(row=0,column=3)
        self.ordinateEntry = Tkinter.Entry(yframe, textvariable=self.strOrdinate)
        self.ordinateEntry.grid(row=1,column=0,columnspan=4,sticky=Tkinter.W+Tkinter.E)
        yframe.pack()
        
        Tkinter.Button(self, text='Update plot', command=self._updatePlot).pack()
        
        self._onClickRadiobuttons()
        
        self.pack()
    
    def _onClickRadiobuttons(self, event=None):
        gridtype = self.choiceAbscissa.get()
        if gridtype=='NOGRID' or gridtype=='CURRENT':
            self.abscissaEntry.configure(state='disabled')
        else:
            self.abscissaEntry.configure(state='normal')
        
        gridtype = self.choiceOrdinate.get()
        if gridtype=='NOGRID' or gridtype=='CURRENT':
            self.ordinateEntry.configure(state='disabled')
        else:
            self.ordinateEntry.configure(state='normal')
        
    def _updatePlot(self, event=None):
        gridtypeX = self.choiceAbscissa.get()
        gridtypeY = self.choiceOrdinate.get()
        if gridtypeX=='NOGRID':
            xstr = 'NOGRID'
        elif gridtypeX=='CURRENT':
            xstr = 'CURRENT'
        elif gridtypeX=='INTERVAL':
            xstr = 'INTERVAL#'+self.abscissaEntry.get()
        elif gridtypeX=='CUSTOM':
            xstr = 'CUSTOM#'+self.abscissaEntry.get()
        else:
            raise ValueError, 'Unknown abscissa grid type (%s)' % (gridtypeX)
        
        
        if gridtypeY=='NOGRID':
            ystr = 'NOGRID'
        elif gridtypeY=='CURRENT':
            ystr = 'CURRENT'
        elif gridtypeY=='INTERVAL':
            ystr = 'INTERVAL#'+self.ordinateEntry.get()
        elif gridtypeY=='CUSTOM':
            ystr = 'CUSTOM#'+self.ordinateEntry.get()
        else:
            raise ValueError, 'Unknown ordinate grid type (%s)' % (gridtypeY)
        
        if self.mainWindow.plotStyle == 'XY':
            self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XY = xstr
            self.mainWindow.conf.CANVAS_GRID_ORDINATE_XY = ystr
        else:
            self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XYT = xstr
            self.mainWindow.conf.CANVAS_GRID_ORDINATE_XYT = ystr
        
        self.mainWindow._updateGrid()
        self.mainWindow.fig.canvas.draw()

class InteractiveConfig(Tkinter.Frame):
    def __init__(self, data, additional, conf, master=None):
        self.configtypes = [('GazeParser Configuration File','*.cfg')]
        if data==None:
            tkMessageBox.showerror('Error','No data')
            return
        
        self.D = data
        self.C = additional
        self.conf = conf
        self.tr = 0
        self.newFixList = None
        self.newSacList = None
        self.newL = None
        self.newR = None
        self.newConfig = None
        
        if self.D[self.tr].config.SCREEN_ORIGIN.lower() == 'topleft':
            ymin = 0
            ymax = max(self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT)
        elif self.D[self.tr].config.SCREEN_ORIGIN.lower() == 'center':
            ymin = -max(self.D[self.tr].config.SCREEN_WIDTH/2.0, self.D[self.tr].config.SCREEN_HEIGHT/2.0)
            ymax = max(self.D[self.tr].config.SCREEN_WIDTH/2.0, self.D[self.tr].config.SCREEN_HEIGHT/2.0)
        else: #assume 'bottomleft'
            ymin = 0
            ymax = max(self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT)
        
        self.currentPlotArea = [0,3000,ymin,ymax]
        
        Tkinter.Frame.__init__(self,master)
        self.master.title('Interactive configuration')
        menu_bar = Tkinter.Menu(tearoff=False)
        menu_file = Tkinter.Menu(tearoff=False)
        self.menu_view = Tkinter.Menu(tearoff=False)
        menu_bar.add_cascade(label='File',menu=menu_file,underline=0)
        menu_bar.add_cascade(label='View',menu=self.menu_view,underline=0)
        menu_file.add_command(label='Export Config',under=0,command=self._exportConfig)
        menu_file.add_command(label='Close',under=0,command=self._close)
        self.menu_view.add_command(label='Prev Trial',under=0,command=self._prevTrial)
        self.menu_view.add_command(label='Next Trial',under=0,command=self._nextTrial)
        self.master.configure(menu = menu_bar)
        
        ########
        # mainFrame (includes viewFrame, xRangeBarFrame)
        # viewFrame
        self.mainFrame = Tkinter.Frame(master, bd=3, relief='groove')
        self.viewFrame = Tkinter.Frame(self.mainFrame)
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viewFrame)
        self.canvas._tkcanvas.config(background="#c0c0c0", borderwidth=0, highlightthickness=0)
        self.ax = self.fig.add_axes([0.1, 0.1, 0.8, 0.8])
        self.ax.axis(self.currentPlotArea)
        self.tkcanvas = self.canvas.get_tk_widget()
        self.tkcanvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)
        
        toolbar=NavigationToolbar2TkAgg(self.canvas, self.viewFrame)
        toolbar.pack(side=Tkinter.TOP)
        self.viewFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        
        self.newParamStringsDict = {}
        self.paramFrame = Tkinter.Frame(self.mainFrame, bd=3, relief='groove') #subFrame
        r=0
        Tkinter.Label(self.paramFrame, text='Original').grid(row=r,column=1)
        Tkinter.Label(self.paramFrame, text='New').grid(row=r,column=2)
        for key in GazeParser.Configuration.GazeParserOptions:
            r += 1
            Tkinter.Label(self.paramFrame, text=key).grid(row=r,column=0,sticky=Tkinter.W,)
            self.newParamStringsDict[key] = Tkinter.StringVar()
            if hasattr(self.D[self.tr].config,key):
                self.newParamStringsDict[key].set(getattr(self.D[self.tr].config,key))
                Tkinter.Label(self.paramFrame, text=str(getattr(self.D[self.tr].config,key))).grid(row=r,column=1,sticky=Tkinter.W,)
            else:
                Tkinter.Label(self.paramFrame, text='not available').grid(row=r,column=1,sticky=Tkinter.W,)
            Tkinter.Entry(self.paramFrame, textvariable=self.newParamStringsDict[key]).grid(row=r,column=2)
        r+=1
        Tkinter.Button(self.paramFrame, text='Update', command=self._updateParameters).grid(row=r,column=0,columnspan=3)
        self.paramFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        self.mainFrame.pack(side=Tkinter.TOP,fill=Tkinter.BOTH,expand=True)
        
        if self.D!=None:
            self._plotData()
    
    def _close(self,event=None):
        self.master.destroy()
        
    def _prevTrial(self, event=None):
        if self.D==None:
            tkMessageBox.showerror('Error','No Data')
            return
        if self.tr>0:
            self.tr -= 1
            if self.tr==0:
                self.menu_view.entryconfigure('Prev Trial', state = 'disabled')
            else:
                self.menu_view.entryconfigure('Prev Trial', state = 'normal')
            if self.tr==len(self.D)-1:
                self.menu_view.entryconfigure('Next Trial', state = 'disabled')
            else:
                self.menu_view.entryconfigure('Next Trial', state = 'normal')
        self._editParameters()
        
    def _nextTrial(self, event=None):
        if self.D==None:
            tkMessageBox.showerror('Error','No Data')
            return
        if self.tr<len(self.D)-1:
            self.tr += 1
            if self.tr==0:
                self.menu_view.entryconfigure('Prev Trial', state = 'disabled')
            else:
                self.menu_view.entryconfigure('Prev Trial', state = 'normal')
            if self.tr==len(self.D)-1:
                self.menu_view.entryconfigure('Next Trial', state = 'disabled')
            else:
                self.menu_view.entryconfigure('Next Trial', state = 'normal')
        self.updateAdjustResults1()
        self.updateAdjustResults2()
        
    def _plotData(self):
        self.ax.clear()
        
        tStart = self.D[self.tr].T[0]
        t = self.D[self.tr].T-tStart
        if self.newL != None:
            self.ax.plot(t,self.newL[:,0],':',color=self.conf.COLOR_TRAJECTORY_L_X)
            self.ax.plot(t,self.newL[:,1],':',color=self.conf.COLOR_TRAJECTORY_L_Y)
        if self.newR != None:
            self.ax.plot(t,self.newR[:,0],'.-',color=self.conf.COLOR_TRAJECTORY_R_X)
            self.ax.plot(t,self.newR[:,1],'.-',color=self.conf.COLOR_TRAJECTORY_R_Y)
        if self.D[self.tr].config.RECORDED_EYE != 'R':
            self.ax.plot(t,self.D[self.tr].L[:,0],'.-',color=self.conf.COLOR_TRAJECTORY_L_X)
            self.ax.plot(t,self.D[self.tr].L[:,1],'.-',color=self.conf.COLOR_TRAJECTORY_L_Y)
        if self.D[self.tr].config.RECORDED_EYE != 'L':
            self.ax.plot(t,self.D[self.tr].R[:,0],'.-',color=self.conf.COLOR_TRAJECTORY_R_X)
            self.ax.plot(t,self.D[self.tr].R[:,1],'.-',color=self.conf.COLOR_TRAJECTORY_R_Y)
        
        for f in range(self.D[self.tr].nFix):
            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart,self.D[self.tr].Fix[f].center[0],str(f),color=self.conf.COLOR_FIXATION_FC,
                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox), clip_on=True)
        
        for s in range(self.D[self.tr].nSac):
            self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000], self.D[self.tr].Sac[s].duration, 20000,
                              hatch='/', fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))
        
        if self.newSacList != None and self.newFixList != None:
            for f in range(len(self.newFixList)):
                #note: color is reversed
                self.ax.text(self.newFixList[f].startTime-tStart,self.newFixList[f].center[0]-50,str(f),color=self.conf.COLOR_FIXATION_BG,
                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_FC, clip_on=True, clip_box=self.ax.bbox), clip_on=True)
            
            hatchColor = getComplementaryColorStr(self.conf.COLOR_SACCADE_HATCH)
            for s in range(len(self.newSacList)):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.newSacList[s].startTime-tStart,-10000], self.newSacList[s].duration, 20000,
                                  hatch='\\', fc=hatchColor, alpha=0.3))
        
        self.ax.axis(self.currentPlotArea)
        
        self.fig.canvas.draw()
    
    def _updateParameters(self):
        if self.D == None:
            tkMessageBox.showerror('Error','No data!')
            return
            
        if self.newConfig==None:
            #self.newConfig = copy.deepcopy(self.D[self.tr].config)
            self.newConfig = self.D[self.tr].config
        
        self.StringVarDict = {}
        
        try:
            for key in GazeParser.Configuration.GazeParserOptions:
                value = self.newParamStringsDict[key].get()
                if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                    setattr(self.newConfig, key, int(value))
                elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                    setattr(self.newConfig, key, float(value))
                else:
                    setattr(self.newConfig, key, value)
        except:
            tkMessageBox.showerror('Error','Illeagal value in '+key)
            configStr = 'New Configuration\n\n'
            for key in GazeParser.Configuration.GazeParserOptions:
                configStr += '%s = %s\n' % (key, getattr(self.newConfig, key))
            self.param2Text.set(configStr)
            return
        
        offset = PLOT_OFFSET
        try:
            #from GazeParser.Converter.TrackerToGazeParser
            if self.newConfig.RECORDED_EYE=='B':
                self.newL = applyFilter(self.D[self.tr].T,self.D[self.tr].L, self.newConfig, decimals=8) + offset
                self.newR = applyFilter(self.D[self.tr].T,self.D[self.tr].R, self.newConfig, decimals=8) + offset
                (SacList,FixList,BlinkList) = buildEventListBinocular(self.D[self.tr].T,self.newL,self.newR,self.newConfig)
            else: #monocular
                if self.newConfig.RECORDED_EYE == 'L':
                    self.newL = applyFilter(self.D[self.tr].T,self.D[self.tr].L, self.newConfig, decimals=8) + offset
                    (SacList,FixList,BlinkList) = buildEventListMonocular(self.D[self.tr].T,self.newL,self.newConfig)
                    self.newR = None
                elif self.newConfig.RECORDED_EYE == 'R':
                    self.newR = applyFilter(self.D[self.tr].T,self.D[self.tr].R, self.newConfig, decimals=8) + offset
                    (SacList,FixList,BlinkList) = buildEventListMonocular(self.D[self.tr].T,self.newR,self.newConfig)
                    self.newR = None
            self.newSacList = SacList
            self.newFixList = FixList
        
        except:
            info = sys.exc_info()
            tbinfo = traceback.format_tb(info[2])
            errormsg = ''
            for tbi in tbinfo:
                errormsg += tbi
            errormsg += '  %s' % str(info[1])
            tkMessageBox.showerror('Error', errormsg)
            self.newSacList = None
            self.newFixList = None
        else:
            self._plotData()
    
    def _exportConfig(self):
        if self.newConfig == None:
            tkMessageBox.showerror('Error','New configuration is empty')
            return
        
        try:
            fname = tkFileDialog.asksaveasfilename(filetypes=self.configtypes, initialdir=GazeParser.configDir)
            self.newConfig.save(fname)
        except:
            tkMessageBox.showerror('Error','Could not write configuration to \'' + fname + '\'')

class mainWindow(Tkinter.Frame):
    def __init__(self,master=None):
        self.conf = ViewerOptions()
        
        self.ftypes = [('GazeParser/SimpleGazeTracker Datafile','*.db;*.csv')]
        #self.ftypes = [('GazeParser Datafile','*.db'),('SimpleGazeTracker CSV file','*.csv')]
        self.initialDataDir = GazeParser.homeDir
        self.D = None
        self.C = None
        self.tr = 0
        self.plotAreaXY = [0,1024,0,768]
        self.plotAreaTXY = [0,3000,0,1024]
        self.dataFileName = 'Please open data file.'
        if self.conf.CANVAS_DEFAULT_VIEW == 'TXY':
            self.plotStyle ='TXY'
            self.currentPlotArea = self.plotAreaTXY
        elif self.confCanvasDefaultView == 'XY':
            self.plotStyle ='XY'
            self.currentPlotArea = self.plotAreaXY
        else:
            raise ValueError, 'Default view must be XY or TXY.'
        self.selectionlist = {'Sac':[], 'Fix':[], 'Msg':[], 'Blink':[]}
        
        Tkinter.Frame.__init__(self,master)
        self.master.title('GazeParser Viewer')
        self.master.protocol('WM_DELETE_WINDOW', self._exit)
        self.menu_bar = Tkinter.Menu(tearoff=False)
        self.menu_file = Tkinter.Menu(tearoff=False)
        self.menu_view = Tkinter.Menu(tearoff=False)
        self.menu_convert = Tkinter.Menu(tearoff=False)
        self.menu_recent = Tkinter.Menu(tearoff=False)
        self.menu_config = Tkinter.Menu(tearoff=False)
        self.menu_analyse = Tkinter.Menu(tearoff=False)
        self.menu_bar.add_cascade(label='File',menu=self.menu_file,underline=0)
        self.menu_bar.add_cascade(label='View',menu=self.menu_view,underline=0)
        self.menu_bar.add_cascade(label='Convert',menu=self.menu_convert,underline=0)
        self.menu_bar.add_cascade(label='Analysis',menu=self.menu_analyse,underline=0)
        
        self.menu_file.add_command(label='Open',under=0,command=self._openfile)
        self.menu_file.add_cascade(label='Recent Dir',menu=self.menu_recent,underline=0)
        if self.conf.RecentDir == []:
            self.menu_recent.add_command(label='None',state=Tkinter.DISABLED)
        else:
            for i in range(len(self.conf.RecentDir)):
                self.menu_recent.add_command(label=self.conf.RecentDir[i],under=0,command=functools.partial(self._openRecent,d=i))
        self.menu_file.add_command(label='Export',under=0,command=self._exportfile)
        self.menu_file.add_command(label='Exit',under=0,command=self._exit)
        self.menu_view.add_command(label='Prev Trial',under=0,command=self._prevTrial)
        self.menu_view.add_command(label='Next Trial',under=0,command=self._nextTrial)
        self.menu_view.add_command(label='Jump to...',under=0,command=self._jumpToTrial)
        self.menu_view.add_separator()
        self.menu_view.add_command(label='Toggle Fixation Number',under=0,command=self._toggleFixNum)
        self.menu_view.add_command(label='Toggle View',under=0,command=self._toggleView)
        self.menu_view.add_separator()
        self.menu_view.add_command(label='Set grid',under=0,command=self._configGrid)
        self.menu_view.add_command(label='Config color', under=0, command=self._configColor)
        self.menu_convert.add_command(label='Convert SimpleGazeTracker CSV',under=0,command=self._convertGT)
        self.menu_convert.add_command(label='Convert Eyelink EDF',under=0,command=self._convertEL)
        self.menu_convert.add_command(label='Convert Tobii TSV',under=0,command=self._convertTSV)
        self.menu_convert.add_separator()
        self.menu_convert.add_command(label='Edit GazeParser.Configuration file',under=0,command=self._configEditor)
        self.menu_convert.add_command(label='Interactive configuration',under=0,command=self._interactive)
        self.menu_analyse.add_command(label='Saccade latency',under=0,command=self._getLatency)
        
        self.master.configure(menu = self.menu_bar)
        
        self.selectiontype = Tkinter.StringVar()
        self.selectiontype.set('Emphasize')
        
        # viewFrame
        self.viewFrame = Tkinter.Frame(master)
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viewFrame)
        self.canvas._tkcanvas.config(height=self.conf.CANVAS_HEIGHT,
                                     width=self.conf.CANVAS_WIDTH,
                                     background='#C0C0C0', borderwidth=0, highlightthickness=0)
        self.ax = self.fig.add_axes([80.0/self.conf.CANVAS_WIDTH, #80px
                                     60.0/self.conf.CANVAS_HEIGHT, #60px
                                     1.0-2*80.0/self.conf.CANVAS_WIDTH,
                                     1.0-2*60.0/self.conf.CANVAS_HEIGHT])
        self.ax.axis(self.currentPlotArea)
        self.canvas._tkcanvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)
        
        toolbar=NavigationToolbar2TkAgg(self.canvas, self.viewFrame)
        toolbar.pack(side=Tkinter.TOP,expand=False)
        self.viewFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        
        self.sideFrame = Tkinter.Frame(master)
        self.listboxFrame = Tkinter.Frame(self.sideFrame)
        Tkinter.Radiobutton(self.sideFrame,text='Emphasize',variable=self.selectiontype,value='Emphasize').pack(side=Tkinter.TOP)
        Tkinter.Radiobutton(self.sideFrame,text='Extract',variable=self.selectiontype,value='Extract').pack(side=Tkinter.TOP)
        buttonFrame = Tkinter.Frame(self.sideFrame)
        Tkinter.Button(buttonFrame,text='Ok',command=self._setmarker).pack(side=Tkinter.LEFT, padx=5)
        Tkinter.Button(buttonFrame,text='Clear',command=self._clearmarker).pack(side=Tkinter.LEFT, padx=5)
        buttonFrame.pack(side=Tkinter.TOP)
        self.yscroll = Tkinter.Scrollbar(self.listboxFrame, orient=Tkinter.VERTICAL)
        self.msglistbox = Tkinter.Listbox(master=self.listboxFrame,yscrollcommand=self.yscroll.set, selectmode=Tkinter.EXTENDED)
        self.msglistbox.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        self.yscroll.pack(side=Tkinter.LEFT, anchor=Tkinter.W, fill=Tkinter.Y, expand=False)
        self.yscroll['command'] = self.msglistbox.yview
        self.listboxFrame.pack(side=Tkinter.TOP,fill=Tkinter.BOTH, expand=True)
        self.sideFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        
        self.master.bind('<Control-KeyPress-o>', self._openfile)
        self.master.bind('<Control-KeyPress-q>', self._exit)
        self.master.bind('<Control-KeyPress-v>', self._toggleView)
        self.master.bind('<Left>', self._prevTrial)
        self.master.bind('<Right>', self._nextTrial)
        self.msglistbox.bind('<Double-Button-1>', self._jumpToTime)
        
        if self.conf.CANVAS_FONT_FILE != '':
            self.fontPlotText = matplotlib.font_manager.FontProperties(fname=self.conf.CANVAS_FONT_FILE)
        else:
            self.fontPlotText = matplotlib.font_manager.FontProperties()
    
    def _toggleView(self, event=None):
        if self.plotStyle == 'XY':
            self.plotStyle = 'TXY'
            self.currentPlotArea = self.plotAreaTXY
        else:
            self.plotStyle = 'XY'
            self.currentPlotArea = self.plotAreaXY
            
        self._plotData()
        
    def _toggleFixNum(self, event=None):
        if self.conf.CANVAS_SHOW_FIXNUMBER:
            self.conf.CANVAS_SHOW_FIXNUMBER = False
        else:
            self.conf.CANVAS_SHOW_FIXNUMBER = True
        
        self._plotData()
    
    def _openfile(self, event=None):
        self.dataFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes,initialdir=self.initialDataDir)
        if self.dataFileName=='':
            return
        self.initialDataDir = os.path.split(self.dataFileName)[0]
        #record recent dir
        if self.initialDataDir in self.conf.RecentDir:
            self.conf.RecentDir.remove(self.initialDataDir)
        self.conf.RecentDir.insert(0,self.initialDataDir)
        if len(self.conf.RecentDir)>MAX_RECENT:
            self.conf.RecentDir = self.conf.RecentDir[:MAX_RECENT]
        #update menu recent_dir
        self.menu_recent.delete(0,MAX_RECENT)
        for i in range(len(self.conf.RecentDir)):
            self.menu_recent.add_command(label=self.conf.RecentDir[i],under=0,command=functools.partial(self._openRecent,d=i))
        
        #if extension is .csv, try converting
        if os.path.splitext(self.dataFileName)[1].lower() == '.csv':
            dbFileName = os.path.splitext(self.dataFileName)[0]+'.db'
            print dbFileName
            if os.path.isfile(dbFileName):
                doOverwrite = tkMessageBox.askyesno('Overwrite?',dbFileName+' already exists. Overwrite?')
                if not doOverwrite:
                    tkMessageBox.showinfo('Info','Conversion canceled.')
                    return
            ret = GazeParser.Converter.TrackerToGazeParser(self.dataFileName, overwrite=True)
            if ret == 'SUCCESS':
                tkMessageBox.showinfo('Info','Conversion succeeded.\nOpen converted data file.')
                self.dataFileName = dbFileName
            else:
                tkMessageBox.showinfo('Conversion error','Failed to convert %s to GazeParser .db file' % (self.dataFileName))
                return
        
        [self.D,self.C] = GazeParser.load(self.dataFileName)
        if len(self.D)==0:
            tkMessageBox.showerror('Error','File contains no data. (%s)'%(self.dataFileName))
            self.D = None
            self.C = None
            return
        
        self.block = 0
        self.tr = 0
        self.plotAreaTXY[1] = 3000
        if self.D[self.tr].config.SCREEN_ORIGIN.lower() == 'topleft':
            self.plotAreaXY = [0, self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT, 0]
            self.plotAreaTXY[2] = 0
            self.plotAreaTXY[3] = max(self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT)
        elif self.D[self.tr].config.SCREEN_ORIGIN.lower() == 'center':
            self.plotAreaXY = [-self.D[self.tr].config.SCREEN_WIDTH/2.0, self.D[self.tr].config.SCREEN_WIDTH/2.0, -self.D[self.tr].config.SCREEN_HEIGHT/2.0, self.D[self.tr].config.SCREEN_HEIGHT/2.0]
            self.plotAreaTXY[2] = -max(self.D[self.tr].config.SCREEN_WIDTH/2.0, self.D[self.tr].config.SCREEN_HEIGHT/2.0)
            self.plotAreaTXY[3] = max(self.D[self.tr].config.SCREEN_WIDTH/2.0, self.D[self.tr].config.SCREEN_HEIGHT/2.0)
        else: #assume 'bottomleft'
            self.plotAreaXY = [0, self.D[self.tr].config.SCREEN_WIDTH, 0, self.D[self.tr].config.SCREEN_HEIGHT]
            self.plotAreaTXY[2] = 0
            self.plotAreaTXY[3] = max(self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT)
        if self.D[self.tr].L == None:
            self.hasLData = False
        else:
            self.hasLData = True
        
        if self.D[self.tr].R == None:
            self.hasRData = False
        else:
            self.hasRData = True
        
        #initialize current plot area
        if self.plotStyle == 'XY':
            self.currentPlotArea = self.plotAreaXY
        
        self.selectionlist = {'Sac':[], 'Fix':[], 'Msg':[], 'Blink':[]}
        self.selectiontype.set('Emphasize')
        self.menu_view.entryconfigure('Prev Trial', state = 'disabled')
        if len(self.D)<2:
            self.menu_view.entryconfigure('Next Trial', state = 'disabled')
        self._plotData()
        self._updateMsgBox()
    
    def _openRecent(self, d):
        self.initialDataDir = self.conf.RecentDir[d]
        self._openfile()
    
    def _exportfile(self,event=None):
        if self.D == None:
            tkMessageBox.showinfo('info','Data must be loaded before export')
            return
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        exportToFileWindow(master=dlg, data=self.D, additional=self.C, trial=self.tr)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
        
    
    def _configColor(self,event=None):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        configColorWindow(master=dlg,mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
    
    def _exit(self,event=None):
        self.conf._write()
        self.master.destroy()
        
    def _prevTrial(self, event=None):
        if self.D==None:
            tkMessageBox.showerror('Error','No Data')
            return
        if self.tr>0:
            self.tr -= 1
            if self.tr==0:
                self.menu_view.entryconfigure('Prev Trial', state = 'disabled')
            else:
                self.menu_view.entryconfigure('Prev Trial', state = 'normal')
            if self.tr==len(self.D)-1:
                self.menu_view.entryconfigure('Next Trial', state = 'disabled')
            else:
                self.menu_view.entryconfigure('Next Trial', state = 'normal')
        self.selectionlist = {'Sac':[], 'Fix':[], 'Msg':[], 'Blink':[]}
        self.selectiontype.set('Emphasize')
        self._plotData()
        self._updateMsgBox()
        
    def _nextTrial(self, event=None):
        if self.D==None:
            tkMessageBox.showerror('Error','No Data')
            return
        if self.tr<len(self.D)-1:
            self.tr += 1
            if self.tr==0:
                self.menu_view.entryconfigure('Prev Trial', state = 'disabled')
            else:
                self.menu_view.entryconfigure('Prev Trial', state = 'normal')
            if self.tr==len(self.D)-1:
                self.menu_view.entryconfigure('Next Trial', state = 'disabled')
            else:
                self.menu_view.entryconfigure('Next Trial', state = 'normal')
        self.selectionlist = {'Sac':[], 'Fix':[], 'Msg':[], 'Blink':[]}
        self.selectiontype.set('Emphasize')
        self._plotData()
        self._updateMsgBox()
    
    def _jumpToTrial(self, event=None):
        if self.D==None:
            tkMessageBox.showerror('Error','No Data')
            return
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        jumpToTrialWindow(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
    
    def _jumpToTime(self, event=None):
        if self.plotStyle == 'XY':
            i= self.msglistbox.index(Tkinter.ACTIVE)
            if isinstance(self.D[self.tr].EventList[i], GazeParser.Core.SaccadeData):
                pos = (self.D[self.tr].EventList[i].start + self.D[self.tr].EventList[i].end)/2.0
            elif isinstance(self.D[self.tr].EventList[i], GazeParser.Core.FixationData):
                pos = self.D[self.tr].EventList[i].center
            else:
                return
            
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            halfXrange = (xlim[1]-xlim[0])/2.0
            halfYrange = (ylim[1]-ylim[0])/2.0
            self.ax.set_xlim((pos[0]-halfXrange,pos[0]+halfXrange))
            self.ax.set_ylim((pos[1]-halfYrange,pos[1]+halfYrange))
            self.fig.canvas.draw()
            
        else:
            text=self.msglistbox.get(Tkinter.ACTIVE)
            time = float(text.split(':')[0]) #time
            xlim = self.ax.get_xlim()
            halfXrange = (xlim[1]-xlim[0])/2.0
            self.ax.set_xlim((time-halfXrange,time+halfXrange))
            self.fig.canvas.draw()
    
    def _modifyPlotRange(self):
        """
        .. deprecated:: 0.6.1
        """
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        plotRangeWindow(master=dlg,mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
    
    def _configGrid(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        configGridWindow(master=dlg,mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
    
    def _updateGrid(self):
        if self.plotStyle == 'XY':
            xattr = 'CANVAS_GRID_ABSCISSA_XY'
            yattr = 'CANVAS_GRID_ORDINATE_XY'
        else:
            xattr = 'CANVAS_GRID_ABSCISSA_XYT'
            yattr = 'CANVAS_GRID_ORDINATE_XYT'
        
        params = getattr(self.conf,xattr).split('#')
        if params[0] == 'NOGRID':
            self.ax.xaxis.grid(False)
        elif params[0] == 'CURRENT':
            self.ax.xaxis.grid(True)
        elif params[0] == 'INTERVAL':
            try:
                interval = float(params[1])
            except:
                tkMessageBox.showerror('Error','"%s" is not a float number.', (params[1]))
                return
            self.ax.xaxis.grid(True)
            self.ax.xaxis.set_major_locator(MultipleLocator(interval))
        elif params[0]=='CUSTOM':
            try:
                format = eval(params[1])
            except:
                tkMessageBox.showerror('Error','"%s" is not a python statement.'% (params[1]))
                return
            
            self.ax.xaxis.grid(True)
            self.ax.xaxis.set_ticks(format)
        else:
            raise ValueError, 'Unknown abscissa grid type (%s)' % (params[0])
        
        params = getattr(self.conf,yattr).split('#')
        if params[0] == 'NOGRID':
            self.ax.yaxis.grid(False)
        elif params[0] == 'CURRENT':
            self.ax.yaxis.grid(True)
        elif params[0] == 'INTERVAL':
            try:
                interval = float(params[1])
            except:
                tkMessageBox.showerror('Error','"%s" is not a float number.' % (params[1]))
                return
            self.ax.yaxis.grid(True)
            self.ax.yaxis.set_major_locator(MultipleLocator(interval))
        elif params[0]=='CUSTOM':
            try:
                format = eval(params[1])
            except:
                tkMessageBox.showerror('Error','"%s" is not a python statement.'%(params[1]))
                return
            self.ax.yaxis.grid(True)
            self.ax.yaxis.set_ticks(format)
        else:
            raise ValueError, 'Unknown ordinate grid type (%s)' % (params[0])
        
    
    def _plotData(self):
        if self.D == None:
            return
        
        self.ax.clear()
        
        if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
             sf = (1.0, 1.0)
        elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
             sf = self.D[self.tr]._pix2deg
        
        if self.plotStyle == 'XY':
            #plot fixations
            for f in range(self.D[self.tr].nFix):
                if self.hasLData:
                    ftraj = sf*self.D[self.tr].getFixTraj(f,'L')
                    col = self.conf.COLOR_TRAJECTORY_L_FIX
                    if self.selectiontype.get()=='Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0], ftraj[:,1], '.-', linewidth=4.0,color=col)
                            if self.conf.CANVAS_SHOW_FIXNUMBER:
                                self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.conf.COLOR_FIXATION_FC_E,
                                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG_E, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties = self.fontPlotText, clip_on=True)
                        else:
                            self.ax.plot(ftraj[:,0], ftraj[:,1],'.-',linewidth=1.0,color=col)
                            if self.conf.CANVAS_SHOW_FIXNUMBER:
                                self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.conf.COLOR_FIXATION_FC,
                                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties = self.fontPlotText, clip_on=True)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0], ftraj[:,1],'.-',linewidth=1.0,color=col)
                            if self.conf.CANVAS_SHOW_FIXNUMBER:
                                self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.conf.COLOR_FIXATION_FC,
                                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties = self.fontPlotText, clip_on=True)
                if self.hasRData:
                    ftraj = sf*self.D[self.tr].getFixTraj(f,'R')
                    col = self.conf.COLOR_TRAJECTORY_R_FIX
                    if self.selectiontype.get()=='Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0], ftraj[:,1], '.-', linewidth=4.0, color=col)
                        else:
                            self.ax.plot(ftraj[:,0], ftraj[:,1], '.-', linewidth=1.0, color=col)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0], ftraj[:,1], '.-', linewidth=1.0, color=col)
                
            #plot saccades
            for s in range(self.D[self.tr].nSac):
                if self.hasLData:
                    straj = sf*self.D[self.tr].getSacTraj(s,'L')
                    col = self.conf.COLOR_TRAJECTORY_L_SAC
                    if self.selectiontype.get()=='Emphasize':
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0], straj[:,1], '.-', linewidth=4.0, color=col)
                        else:
                            self.ax.plot(straj[:,0], straj[:,1], '.-', linewidth=1.0, color=col)
                    else:
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0], straj[:,1], '.-', linewidth=1.0, color=col)
                if self.hasRData:
                    straj = sf*self.D[self.tr].getSacTraj(s,'R')
                    col = self.conf.COLOR_TRAJECTORY_R_SAC
                    if self.selectiontype.get()=='Emphasize':
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0], straj[:,1], '.-', linewidth=4.0, color=col)
                        else:
                            self.ax.plot(straj[:,0], straj[:,1], '.-', linewidth=1.0, color=col)
                    else:
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0], straj[:,1], '.-', linewidth=1.0, color=col)
            
            if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
                self.ax.set_xlabel('Vertical gaze position (pix)')
                self.ax.set_ylabel('Horizontal gaze position (pix)')
            elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
                self.ax.set_xlabel('Vertical gaze position (deg)')
                self.ax.set_ylabel('Horizontal gaze position (deg)')
            
            self.ax.axis((sf[0]*self.currentPlotArea[0],sf[0]*self.currentPlotArea[1],
                          sf[1]*self.currentPlotArea[2],sf[1]*self.currentPlotArea[3]))
        
        else: #XY-T
            tStart = self.D[self.tr].T[0]
            t = self.D[self.tr].T-tStart
            if self.hasLData:
                self.ax.plot(t, sf[0]*self.D[self.tr].L[:,0], '.-', color=self.conf.COLOR_TRAJECTORY_L_X)
                self.ax.plot(t, sf[1]*self.D[self.tr].L[:,1], '.-', color=self.conf.COLOR_TRAJECTORY_L_Y)
            if self.hasRData:
                self.ax.plot(t, sf[0]*self.D[self.tr].R[:,0], '.-', color=self.conf.COLOR_TRAJECTORY_R_X)
                self.ax.plot(t, sf[1]*self.D[self.tr].R[:,1], '.-', color=self.conf.COLOR_TRAJECTORY_R_Y)
            
            if self.conf.CANVAS_SHOW_FIXNUMBER:
                for f in range(self.D[self.tr].nFix):
                    if self.selectiontype.get()=='Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, sf[0]*self.D[self.tr].Fix[f].center[0], str(f),
                                         color=self.conf.COLOR_FIXATION_FC_E,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG_E, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties = self.fontPlotText, clip_on=True)
                        else:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, sf[0]*self.D[self.tr].Fix[f].center[0], str(f),
                                         color=self.conf.COLOR_FIXATION_FC,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties = self.fontPlotText, clip_on=True)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, sf[0]*self.D[self.tr].Fix[f].center[0], str(f),
                                         color=self.conf.COLOR_FIXATION_FC,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties = self.fontPlotText, clip_on=True)
            
            for s in range(self.D[self.tr].nSac):
                if self.selectiontype.get()=='Emphasize':
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       hatch='/', fc=self.conf.COLOR_SACCADE_HATCH_E, alpha=0.8))
                    else:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       hatch='/', fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))
                else:
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       hatch='/', fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))
                
            for b in range(self.D[self.tr].nBlink):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Blink[b].startTime-tStart,-10000],
                                                               self.D[self.tr].Blink[b].duration, 20000,
                                                               hatch='\\', fc=self.conf.COLOR_BLINK_HATCH, alpha=0.3))
            
            for m in range(self.D[self.tr].nMsg):
                mObj = self.D[self.tr].Msg[m]
                if len(mObj.text)>10:
                    msgtext = str(m) + ':' + mObj.text[:7] + '...'
                else:
                    msgtext = str(m) + ':' + mObj.text
                self.ax.plot([mObj.time,mObj.time], [-10000,10000], '-', color=self.conf.COLOR_MESSAGE_CURSOR, linewidth=3.0)
                self.ax.text(mObj.time, 0, msgtext, color=self.conf.COLOR_MESSAGE_FC,
                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_MESSAGE_BG, clip_on=True, clip_box=self.ax.bbox),
                             fontproperties = self.fontPlotText, clip_on=True)
            
            if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
                self.ax.set_xlabel('Time (ms)')
                self.ax.set_ylabel('Gaze position (pix)')
            elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
                self.ax.set_xlabel('Time (ms)')
                self.ax.set_ylabel('Gaze position (deg)')
            
            self.ax.axis((self.currentPlotArea[0],self.currentPlotArea[1],
                          sf[0]*self.currentPlotArea[2],sf[0]*self.currentPlotArea[3]))
        
        
        self.ax.set_title('%s: Trial%d' % (os.path.basename(self.dataFileName), self.tr))
        self._updateGrid()
        self.fig.canvas.draw()
        
    def _updateMsgBox(self):
        self.msglistbox.delete(0,self.msglistbox.size())
        
        st=self.D[self.tr].T[0]
        et=self.D[self.tr].T[-1]
        
        for e in self.D[self.tr].EventList:
            if isinstance(e,GazeParser.SaccadeData):
                self.msglistbox.insert(Tkinter.END,str(e.startTime)+':Sac')
                #self.msglistbox.itemconfig(Tkinter.END, bg=self.conf.COLOR_TRAJECTORY_L_SAC)
            elif isinstance(e,GazeParser.FixationData):
                self.msglistbox.insert(Tkinter.END,str(e.startTime)+':Fix')
                #self.msglistbox.itemconfig(Tkinter.END, bg=self.conf.COLOR_TRAJECTORY_L_FIX)
            elif isinstance(e,GazeParser.MessageData):
                self.msglistbox.insert(Tkinter.END,str(e.time)+':'+e.text)
                self.msglistbox.itemconfig(Tkinter.END, bg=self.conf.COLOR_MESSAGE_BG, fg=self.conf.COLOR_MESSAGE_FC)
            elif isinstance(e,GazeParser.BlinkData):
                self.msglistbox.insert(Tkinter.END,str(e.startTime)+':Blk')
    
    def _setmarker(self):
        selected = self.msglistbox.curselection()
        self.selectionlist = {'Sac':[], 'Fix':[], 'Msg':[], 'Blink':[]}
        
        for s in selected:
            e = self.D[self.tr].EventList[int(s)]
            if isinstance(e,GazeParser.SaccadeData):
                self.selectionlist['Sac'].append(numpy.where(e==self.D[self.tr].Sac)[0][0])
            elif isinstance(e,GazeParser.FixationData):
                self.selectionlist['Fix'].append(numpy.where(e==self.D[self.tr].Fix)[0][0])
            elif isinstance(e,GazeParser.MessageData):
                self.selectionlist['Msg'].append(numpy.where(e==self.D[self.tr].Msg)[0][0])
            elif isinstance(e,GazeParser.BlinkData):
                self.selectionlist['Blink'].append(numpy.where(e==self.D[self.tr].Blink)[0][0])
            
        #self.currentPlotArea = self.ax.get_xlim()+self.ax.get_ylim()
        self._plotData()
        
    
    def _clearmarker(self):
        self.msglistbox.selection_clear(0,self.msglistbox.size())
        self.selectionlist = {'Sac':[], 'Fix':[], 'Msg':[], 'Blink':[]}
        self._plotData()
    
    def _configEditor(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GazeParser.app.ConfigEditor.ConfigEditor(master=dlg)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
        
    
    def _convertGT(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GazeParser.app.Converters.Converter(master=dlg)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
    
    def _convertEL(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GazeParser.app.Converters.EyelinkConverter(master=dlg)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
    
    def _convertTSV(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GazeParser.app.Converters.TobiiConverter(master=dlg)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
    
    def _interactive(self):
        if self.D == None:
            tkMessageBox.showinfo('info','Data must be loaded before\nusing interactive configuration.')
            return
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        InteractiveConfig(master=dlg, data=self.D, additional=self.C, conf=self.conf)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
    
    def _getLatency(self):
        if self.D == None:
            tkMessageBox.showinfo('info','Data must be loaded before\nmeasuring saccade latency')
            return
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GetSaccadeLatency(master=dlg, data=self.D, additional=self.C, conf=self.conf)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))

if __name__ == '__main__':
    w = mainWindow()
    w.mainloop()

