#!/usr/bin/env python
"""
Part of GazeParser library.
Copyright (C) 2012 Hiroyuki Sogo.
Distributed under the terms of the GNU General Public License (GPL).

Thanks to following page for embedded plot.

* http://www.mailinglistarchive.com/html/matplotlib-users@lists.sourceforge.net/2010-08/msg00148.html

"""

import ConfigParser
import shutil
import Tkinter
import tkFileDialog
import tkMessageBox
import Image
import ImageTk
import GazeParser
import GazeParser.Converter
import os
import sys
import re
import functools
import numpy
import matplotlib
import matplotlib.figure
import matplotlib.font_manager
import matplotlib.patches
import GazeParser.app.ConfigEditor
import GazeParser.app.Converters
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg

def parsegeometry(geometry):
    m = re.match("(\d+)x(\d+)([-+]\d+)([-+]\d+)", geometry)
    if not m:
        raise ValueError("failed to parse geometry string")
    return map(int, m.groups())

MAX_RECENT = 5

ViewerOptions = [
    ['Version',
     [['VIEWER_VERSION','confVersion',str]]],
    ['Appearance',
     [['CANVAS_WIDTH','confCanvasWidth',int],
      ['CANVAS_HEIGHT','confCanvasHeight',int],
      ['CANVAS_DEFAULT_VIEW','confCanvasDefaultView',str],
      ['CANVAS_SHOW_FIXNUMBER','confShowFixNum',bool],
      ['CANVAS_FONT_FILE','confFontPlot',str],
      ['COLOR_TRAJECTORY_L_SAC','confColorLS',str],
      ['COLOR_TRAJECTORY_R_SAC','confColorRS',str],
      ['COLOR_TRAJECTORY_L_FIX','confColorLF',str],
      ['COLOR_TRAJECTORY_R_FIX','confColorRF',str],
      ['COLOR_TRAJECTORY_L_X','confColorLX',str],
      ['COLOR_TRAJECTORY_L_Y','confColorLY',str],
      ['COLOR_TRAJECTORY_R_X','confColorRX',str],
      ['COLOR_TRAJECTORY_R_Y','confColorRY',str],
      ['COLOR_FIXATION_FC','confColorFixF',str],
      ['COLOR_FIXATION_BG','confColorFixB',str],
      ['COLOR_FIXATION_FC_E','confColorFixFE',str],
      ['COLOR_FIXATION_BG_E','confColorFixBE',str],
      ['COLOR_MESSAGE_CURSOR','confColorMsgCur',str],
      ['COLOR_MESSAGE_FC','confColorMsgF',str],
      ['COLOR_MESSAGE_BG','confColorMsgB',str]]],
    ['Recent',
     [['RECENT_DIR01','confRecentDir01',str],
      ['RECENT_DIR02','confRecentDir02',str],
      ['RECENT_DIR03','confRecentDir03',str],
      ['RECENT_DIR04','confRecentDir04',str],
      ['RECENT_DIR05','confRecentDir05',str]]]
]



class mainWindow(Tkinter.Frame):
    def __init__(self,master=None):
        self.readApplicationConfig()
        
        #self.ftypes = [('GazeParser/SimpleGazeTracker Datafile','*.db;*.csv')]
        self.ftypes = [('GazeParser Datafile','*.db'),('SimpleGazeTracker CSV file','*.csv')]
        self.initialDataDir = GazeParser.homeDir
        self.D = None
        self.C = None
        self.tr = 0
        self.plotAreaXY = [0,1024,0,768]
        self.plotAreaTXY = [0,3000,0,1024]
        self.dataFileName = 'Please open data file.'
        if self.confCanvasDefaultView == 'TXY':
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
        self.menu_bar.add_cascade(label='File',menu=self.menu_file,underline=0)
        self.menu_bar.add_cascade(label='View',menu=self.menu_view,underline=0)
        self.menu_bar.add_cascade(label='Convert',menu=self.menu_convert,underline=0)
        self.menu_file.add_command(label='Open',under=0,command=self._openfile)
        self.menu_file.add_cascade(label='Recent Dir',menu=self.menu_recent,underline=0)
        if self.confRecentDir == []:
            self.menu_recent.add_command(label='None',state=Tkinter.DISABLED)
        else:
            for i in range(len(self.confRecentDir)):
                self.menu_recent.add_command(label=self.confRecentDir[i],under=0,command=functools.partial(self._openRecent,d=i))
        self.menu_file.add_command(label='Export',under=0,command=self._exportfile)
        self.menu_file.add_command(label='Exit',under=0,command=self._exit)
        self.menu_view.add_command(label='Toggle View',under=0,command=self._toggleView)
        self.menu_view.add_command(label='Toggle Fixation Number',under=0,command=self._toggleFixNum)
        self.menu_view.add_command(label='Modify Plot Range',under=0,command=self._modifyPlotRange)
        self.menu_view.add_command(label='Prev Trial',under=0,command=self._prevTrial)
        self.menu_view.add_command(label='Next Trial',under=0,command=self._nextTrial)
        self.menu_convert.add_command(label='Edit GazeParser.Configuration file',under=0,command=self._configEditor)
        self.menu_convert.add_command(label='Convert GazeTracker CSV',under=0,command=self._convertGT)
        self.menu_convert.add_command(label='Convert Eyelink EDF',under=0,command=self._convertEL)
        self.menu_convert.add_command(label='Convert Tobii TSV',under=0,command=self._convertTSV)
        self.menu_convert.add_command(label='Interactive config',under=0,command=self._interactive)
        self.master.configure(menu = self.menu_bar)
        
        self.selectiontype = Tkinter.StringVar()
        self.selectiontype.set('Emphasize')
        
        # viewFrame
        self.viewFrame = Tkinter.Frame(master)
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viewFrame)
        self.canvas._tkcanvas.config(height=self.confCanvasHeight,
                                     width=self.confCanvasWidth,
                                     background='#C0C0C0', borderwidth=0, highlightthickness=0)
        self.ax = self.fig.add_axes([80.0/self.confCanvasWidth, #80px
                                     60.0/self.confCanvasHeight, #60px
                                     1.0-2*80.0/self.confCanvasWidth,
                                     1.0-2*60.0/self.confCanvasHeight])
        self.ax.axis(self.currentPlotArea)
        self.canvas._tkcanvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)
        
        toolbar=NavigationToolbar2TkAgg(self.canvas, self.viewFrame)
        toolbar.pack(side=Tkinter.TOP,expand=False)
        self.viewFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        
        self.sideFrame = Tkinter.Frame(master)
        self.listboxFrame = Tkinter.Frame(self.sideFrame)
        Tkinter.Radiobutton(self.sideFrame,text='Emphasize',variable=self.selectiontype,value='Emphasize').pack(side=Tkinter.TOP)
        Tkinter.Radiobutton(self.sideFrame,text='Extract',variable=self.selectiontype,value='Extract').pack(side=Tkinter.TOP)
        Tkinter.Button(self.sideFrame,text='Ok',command=self._setmarker).pack(side=Tkinter.TOP)
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
        
        if self.confFontPlot != '':
            self.fontPlotText = matplotlib.font_manager.FontProperties(fname=self.confFontPlot)
        else:
            self.fontPlotText = matplotlib.font_manager.FontProperties()
    
    
    def readApplicationConfig(self):
        initialConfigFile = os.path.join(os.path.dirname(__file__),'viewer.cfg')
        appConfigDir = os.path.join(GazeParser.configDir, 'app')
        if not os.path.isdir(appConfigDir):
            os.mkdir(appConfigDir)
        
        self.viewerConfigFile = os.path.join(appConfigDir, 'viewer.cfg')
        if not os.path.isfile(self.viewerConfigFile):
            shutil.copyfile(initialConfigFile,self.viewerConfigFile)
        
        self.appConf = ConfigParser.SafeConfigParser()
        self.appConf.optionxform = str
        self.appConf.read(self.viewerConfigFile)
        
        try:
            self.confVersion = self.appConf.get('Version','VIEWER_VERSION')
        except:
            ans = tkMessageBox.askyesno('Error','No VIEWER_VERSION option in configuration file (%s). Backup current file and then initialize configuration file?\n' % (self.viewerConfigFile))
            if ans:
                shutil.copyfile(self.viewerConfigFile,self.viewerConfigFile+'.bak')
                shutil.copyfile(initialConfigFile,self.viewerConfigFile)
                self.appConf = ConfigParser.SafeConfigParser()
                self.appConf.optionxform = str
                self.appConf.read(self.viewerConfigFile)
                self.confVersion = self.appConf.get('Version','VIEWER_VERSION')
            else:
                tkMessageBox.showinfo('info','Please correct configuration file manually.')
                sys.exit()
        
        doMerge = False
        if self.confVersion != GazeParser.__version__:
            ans = tkMessageBox.askyesno('Warning','VIEWER_VERSION of configuration file (%s) disagree with GazeParser version (%s). Backup current configuration file and build new configuration file?'%(self.confVersion, GazeParser.__version__))
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
            for section,params in ViewerOptions:
                for optName, attrName, optType in params:
                    if section=='Version' and optName=='VIEWER_VERSION':
                        setattr(self,attrName,optType(appNewConf.get(section,optName)))
                        newOpts.append(' * '+optName)
                    elif self.appConf.has_option(section,optName):
                        setattr(self,attrName,optType(self.appConf.get(section,optName)))
                    else:
                        setattr(self,attrName,optType(appNewConf.get(section,optName)))
                        newOpts.append(' * '+optName)
            #new version number
            tkMessageBox.showinfo('info','Added:\n'+'\n'.join(newOpts))
        
        else:
            for section,params in ViewerOptions:
                for optName, attrName, optType in params:
                    setattr(self,attrName,optType(self.appConf.get(section,optName)))
        
        #set recent directories
        self.confRecentDir = []
        for i in range(5):
            d = getattr(self,'confRecentDir%02d' % (i+1))
            if d != '':
                self.confRecentDir.append(d)
    
    def _writeApplicationConfig(self):
        #set recent directories
        for i in range(5):
            if i<len(self.confRecentDir):
                setattr(self, 'confRecentDir%02d' % (i+1), self.confRecentDir[i])
            else:
                setattr(self, 'confRecentDir%02d' % (i+1), '')
        
        with open(self.viewerConfigFile, 'w') as fp:
            for section,params in ViewerOptions:
                fp.write('[%s]\n' % section)
                for optName, attrName, optType in params:
                    fp.write('%s = %s\n' % (optName, getattr(self,attrName)))
                fp.write('\n')
    
    def _toggleView(self, event=None):
        if self.plotStyle == 'XY':
            self.plotStyle = 'TXY'
            self.currentPlotArea = self.plotAreaTXY
        else:
            self.plotStyle = 'XY'
            self.currentPlotArea = self.plotAreaXY
            
        self._plotData()
        
    def _toggleFixNum(self, event=None):
        if self.confShowFixNum:
            self.confShowFixNum = False
        else:
            self.confShowFixNum = True
        
        self._plotData()
    
    def _openfile(self, event=None):
        self.dataFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes,initialdir=self.initialDataDir)
        if self.dataFileName=='':
            return
        self.initialDataDir = os.path.split(self.dataFileName)[0]
        #record recent dir
        if self.initialDataDir in self.confRecentDir:
            self.confRecentDir.remove(self.initialDataDir)
        self.confRecentDir.insert(0,self.initialDataDir)
        if len(self.confRecentDir)>MAX_RECENT:
            self.confRecentDir = self.confRecentDir[:MAX_RECENT]
        #update menu recent_dir
        self.menu_recent.delete(0,MAX_RECENT)
        for i in range(len(self.confRecentDir)):
            self.menu_recent.add_command(label=self.confRecentDir[i],under=0,command=functools.partial(self._openRecent,d=i))
        
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
        if self.D[self.tr].config.SCREEN_ORIGIN.lower() == 'topleft':
            self.plotAreaXY = [0, self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT, 0]
        elif self.D[self.tr].config.SCREEN_ORIGIN.lower() == 'center':
            self.plotAreaXY = [-1*self.D[self.tr].config.SCREEN_WIDTH/2.0, self.D[self.tr].config.SCREEN_WIDTH/2.0, -1*self.D[self.tr].config.SCREEN_HEIGHT/2.0, self.D[self.tr].config.SCREEN_HEIGHT/2.0]
        else: #assume 'bottomleft'
            self.plotAreaXY = [0, self.D[self.tr].config.SCREEN_WIDTH, 0, self.D[self.tr].config.SCREEN_HEIGHT]
        self.plotAreaTXY[1] = 3000
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
        self.initialDataDir = self.confRecentDir[d]
        self._openfile()
    
    def _exportfile(self,event=None):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        flgSac = Tkinter.BooleanVar()
        flgFix = Tkinter.BooleanVar()
        flgBlk = Tkinter.BooleanVar()
        flgMsg = Tkinter.BooleanVar()
        flgTrials = Tkinter.StringVar()
        flgOrder = Tkinter.StringVar()
        flgTrials.set('ThisTrial')
        flgOrder.set('ByTime')
        Tkinter.Label(dlg, text='Check items to export.').grid(row=0,column=0,columnspan=2)
        Tkinter.Checkbutton(dlg, text='Saccade', variable=flgSac).grid(row=1,column=0)
        Tkinter.Checkbutton(dlg, text='Fixation', variable=flgFix).grid(row=2,column=0)
        Tkinter.Checkbutton(dlg, text='Blink', variable=flgBlk).grid(row=1,column=1)
        Tkinter.Checkbutton(dlg, text='Message', variable=flgMsg).grid(row=2,column=1)
        Tkinter.Radiobutton(dlg, text='This trial', variable=flgTrials, value='ThisTrial').grid(row=3,column=0)
        Tkinter.Radiobutton(dlg, text='All trials', variable=flgTrials, value='AllTrials').grid(row=3,column=1)
        Tkinter.Radiobutton(dlg, text='By time', variable=flgOrder, value='ByTime').grid(row=4,column=0)
        Tkinter.Radiobutton(dlg, text='By events', variable=flgOrder, value='ByEvents').grid(row=4,column=1)
        Tkinter.Button(dlg, text='Ok', command=dlg.destroy).grid(row=5,column=0,columnspan=2)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
        
        if flgSac.get() or flgFix.get() or flgBlk.get() or flgMsg.get():
            exportFileName = tkFileDialog.asksaveasfilename(initialdir=GazeParser.homeDir)
            fp = open(exportFileName, 'w')
            
            if flgOrder.get()=='ByTime':
                if flgTrials.get()=='ThisTrial':
                    trlist = [self.tr]
                else: #AllTrials
                    trlist = range(len(self.D))
                for tr in trlist:
                    fp.write('TRIAL%d\n' % (tr+1))
                    for e in self.D[self.tr].EventList:
                        if isinstance(e,GazeParser.SaccadeData) and flgSac.get():
                            fp.write('SAC,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n' % 
                                     (e.startTime, e.endTime, e.Start[0], e.Start[1], e.End[0], e.End[1]))
                        elif isinstance(e,GazeParser.FixationData) and flgFix.get():
                            fp.write('FIX,%.1f,%.1f,%.1f,%.1f\n' % 
                                     (e.startTime, e.endTime, e.center[0],e.center[1]))
                        elif isinstance(e,GazeParser.MessageData) and flgMsg.get():
                            fp.write('MSG,%.1f,%.1f,%s\n' % (e.time, e.time, e.text))
                        elif isinstance(e,GazeParser.BlinkData) and flgBlk.get():
                            fp.write('BLK,%.1f,%.1f\n' % (e.startTime, e.endTime))
                
            else: #ByEvents
                if flgTrials.get()=='ThisTrial':
                    trlist = [self.tr]
                else: #AllTrials
                    trlist = range(len(self.D))
                for tr in trlist:
                    fp.write('TRIAL%d\n' % (tr+1))
                    if flgSac.get():
                        for e in self.D[tr].Sac:
                            fp.write('SAC,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n' % 
                                     (e.startTime, e.endTime, e.Start[0], e.Start[1], e.End[0], e.End[1]))
                    if flgFix.get():
                        for e in self.D[tr].Fix:
                            fp.write('FIX,%.1f,%.1f,%.1f,%.1f\n' % 
                                     (e.startTime, e.endTime, e.center[0],e.center[1]))
                    if flgMsg.get():
                        for e in self.D[tr].Msg:
                            fp.write('MSG,%.1f,%.1f,%s\n' % (e.time, e.time, e.text))
                    if flgBlk.get():
                        for e in self.D[tr].Blink:
                            fp.write('BLK,%.1f,%.1f\n' % (e.startTime, e.endTime))
            
            fp.close()
            
            tkMessageBox.showinfo('Info','Done.')
    
    def _exit(self,event=None):
        self._writeApplicationConfig()
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
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        strings = [Tkinter.StringVar() for i in range(4)]
        labels = ['Abcissa Min','Abcissa Max','Ordinate Min','Ordinate Max']
        Tkinter.Label(dlg, text='Current View: ').grid(row=0,column=0,columnspan=2)
        for i in range(4):
            strings[i].set(str(self.currentPlotArea[i]))
            Tkinter.Label(dlg, text=labels[i]).grid(row=i+1,column=0)
            Tkinter.Entry(dlg, textvariable=strings[i]).grid(row=i+1,column=1)
        Tkinter.Button(dlg, text='Ok', command=dlg.destroy).grid(row=5,column=0,columnspan=2)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d'%(geo[0],geo[1],geoMaster[2]+50,geoMaster[3]+50))
        
        tmpPlotArea = [0,0,0,0]
        try:
            for i in range(4):
                tmpPlotArea[i] = int(strings[i].get())
            
            for i in range(4):
                self.currentPlotArea[i] = tmpPlotArea[i]
            
            self.ax.axis(self.currentPlotArea)
            self.fig.canvas.draw()
        except:
            tkMessageBox.showinfo('Error','Values must be integer')
    
    def _plotData(self):
        if self.D == None:
            return
        
        self.ax.clear()
        
        if self.plotStyle == 'XY':
            #plot fixations
            for f in range(self.D[self.tr].nFix):
                if self.hasLData:
                    ftraj = self.D[self.tr].getFixTraj(f,'L')
                    col = self.confColorLF
                    if self.selectiontype.get()=='Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=4.0,color=col)
                            if self.confShowFixNum:
                                self.ax.text(self.D[self.tr].Fix[f].center[0], self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.confColorFixFE,
                                             bbox=dict(boxstyle="round", fc=self.confColorFixBE, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties = self.fontPlotText, clip_on=True)
                        else:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=1.0,color=col)
                            if self.confShowFixNum:
                                self.ax.text(self.D[self.tr].Fix[f].center[0], self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.confColorFixF,
                                             bbox=dict(boxstyle="round", fc=self.confColorFixB, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties = self.fontPlotText, clip_on=True)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=1.0,color=col)
                            if self.confShowFixNum:
                                self.ax.text(self.D[self.tr].Fix[f].center[0], self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.confColorFixF,
                                             bbox=dict(boxstyle="round", fc=self.confColorFixB, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties = self.fontPlotText, clip_on=True)
                if self.hasRData:
                    ftraj = self.D[self.tr].getFixTraj(f,'R')
                    col = self.confColorRF
                    if self.selectiontype.get()=='Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=4.0,color=col)
                        else:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=1.0,color=col)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=1.0,color=col)
                
            #plot saccades
            for s in range(self.D[self.tr].nSac):
                if self.hasLData:
                    straj = self.D[self.tr].getSacTraj(s,'L')
                    col = self.confColorLS
                    if self.selectiontype.get()=='Emphasize':
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=4.0,color=col)
                        else:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=1.0,color=col)
                    else:
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=1.0,color=col)
                if self.hasRData:
                    straj = self.D[self.tr].getSacTraj(s,'R')
                    col = self.confColorRS
                    if self.selectiontype.get()=='Emphasize':
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=4.0,color=col)
                        else:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=1.0,color=col)
                    else:
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=1.0,color=col)
            
        else: #XY-T
            tStart = self.D[self.tr].T[0]
            t = self.D[self.tr].T-tStart
            if self.hasLData:
                self.ax.plot(t,self.D[self.tr].L[:,0],'.-',color=self.confColorLX)
                self.ax.plot(t,self.D[self.tr].L[:,1],'.-',color=self.confColorLY)
            if self.hasRData:
                self.ax.plot(t,self.D[self.tr].R[:,0],'.-',color=self.confColorRX)
                self.ax.plot(t,self.D[self.tr].R[:,1],'.-',color=self.confColorRY)
            
            if self.confShowFixNum:
                for f in range(self.D[self.tr].nFix):
                    if self.selectiontype.get()=='Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, self.D[self.tr].Fix[f].center[0],str(f),
                                         color=self.confColorFixFE,
                                         bbox=dict(boxstyle="round", fc=self.confColorFixBE, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties = self.fontPlotText, clip_on=True)
                        else:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, self.D[self.tr].Fix[f].center[0],str(f),
                                         color=self.confColorFixF,
                                         bbox=dict(boxstyle="round", fc=self.confColorFixB, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties = self.fontPlotText, clip_on=True)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, self.D[self.tr].Fix[f].center[0], str(f),
                                         color=self.confColorFixF,
                                         bbox=dict(boxstyle="round", fc=self.confColorFixB, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties = self.fontPlotText, clip_on=True)
            
            for s in range(self.D[self.tr].nSac):
                if self.selectiontype.get()=='Emphasize':
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       ec=(0.0,0.0,0.6), hatch='/', fc=(0.3,0.3,1.0), alpha=0.8))
                    else:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       ec=(0.0,0.0,0.6), hatch='/', fc=(0.6,0.6,0.9), alpha=0.3))
                else:
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       ec=(0.0,0.0,0.6), hatch='/', fc=(0.6,0.6,0.9), alpha=0.3))
                
            for b in range(self.D[self.tr].nBlink):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Blink[b].startTime-tStart,-10000],
                                                               self.D[self.tr].Blink[b].duration, 20000,
                                                               ec=(0.2,0.2,0.2), hatch='\\', fc=(0.8,0.8,0.8), alpha=0.3))
            
            for m in range(self.D[self.tr].nMsg):
                mObj = self.D[self.tr].Msg[m]
                if len(mObj.text)>10:
                    msgtext = str(m) + ':' + mObj.text[:7] + '...'
                else:
                    msgtext = str(m) + ':' + mObj.text
                self.ax.plot([mObj.time,mObj.time], [-10000,10000], '-', color=self.confColorMsgCur, linewidth=3.0)
                self.ax.text(mObj.time, 0, msgtext, color=self.confColorMsgF,
                             bbox=dict(boxstyle="round", fc=self.confColorMsgB, clip_on=True, clip_box=self.ax.bbox),
                             fontproperties = self.fontPlotText, clip_on=True)
            
        self.ax.axis(self.currentPlotArea)
        
        self.ax.set_title('%s: Trial%d' % (os.path.basename(self.dataFileName), self.tr))
        self.fig.canvas.draw()
        
    def _updateMsgBox(self):
        self.msglistbox.delete(0,self.msglistbox.size())
        
        st=self.D[self.tr].T[0]
        et=self.D[self.tr].T[-1]
        
        for e in self.D[self.tr].EventList:
            if isinstance(e,GazeParser.SaccadeData):
                self.msglistbox.insert(Tkinter.END,str(e.startTime)+':Sac')
                #self.msglistbox.itemconfig(Tkinter.END, bg=self.confColorLS)
            elif isinstance(e,GazeParser.FixationData):
                self.msglistbox.insert(Tkinter.END,str(e.startTime)+':Fix')
                #self.msglistbox.itemconfig(Tkinter.END, bg=self.confColorLF)
            elif isinstance(e,GazeParser.MessageData):
                self.msglistbox.insert(Tkinter.END,str(e.time)+':'+e.text)
                self.msglistbox.itemconfig(Tkinter.END, bg=self.confColorMsgB, fg=self.confColorMsgF)
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
            
        self.currentPlotArea = self.ax.get_xlim()+self.ax.get_ylim()
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
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GazeParser.app.Converters.InteractiveConfig(master=dlg)
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

