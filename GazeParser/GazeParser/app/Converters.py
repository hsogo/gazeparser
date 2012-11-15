"""
Part of GazeParser library.
Copyright (C) 2012 Hiroyuki Sogo.
Distributed under the terms of the GNU General Public License (GPL).

Convert gaze data files to GazeParser data file.
"""

import GazeParser
import GazeParser.Configuration
import os
import Tkinter
import tkFileDialog
import tkMessageBox
import sys
import traceback
import Image, ImageTk
import copy

from GazeParser.Converter import EyelinkToGazeParser, TrackerToGazeParser, TobiiToGazeParser
from GazeParser.Converter import buildEventListBinocular, buildEventListMonocular, applyFilter

import matplotlib,matplotlib.figure
import matplotlib.patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg

class Converter(Tkinter.Frame):
    def __init__(self, master=None):
        Tkinter.Frame.__init__(self, master, srctype=None)
        self.master.title('GazeParser Data Converter')
        
        self.useParameters = Tkinter.BooleanVar()
        self.useParameters.set(True)
        
        self.paramFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.configuration = GazeParser.Configuration.Config()
        
        self.stringVarDict = {}
        self.paramEntryDict = {}
        r = 0
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key] = Tkinter.StringVar()
            self.stringVarDict[key].set(getattr(self.configuration, key))
            Tkinter.Label(self.paramFrame, text=key).grid(row=r, column=0, sticky=Tkinter.W)
            self.paramEntryDict[key] = Tkinter.Entry(self.paramFrame, textvariable=self.stringVarDict[key])
            self.paramEntryDict[key].grid(row=r, column=1)
            r+=1
        self.sideFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        
        self.choiceFrame = Tkinter.Frame(self.sideFrame, bd=2, relief=Tkinter.GROOVE)
        self.usefileRadiobutton = Tkinter.Radiobutton(self.choiceFrame, text='Use parameters embedded in the data file', variable=self.useParameters, value=True, command=self._onClickChoiceFrame)
        self.overwriteRadiobutton = Tkinter.Radiobutton(self.choiceFrame, text='Use parameters shown in this dialog', variable=self.useParameters, value=False, command=self._onClickChoiceFrame)
        self.usefileRadiobutton.grid(row=0,column=0,sticky=Tkinter.W)
        Tkinter.Label(self.choiceFrame, text='(If parameters are not embedded in the\ndatafile, default configuration is used.)').grid(row=1,column=0,sticky=Tkinter.E)
        self.overwriteRadiobutton.grid(row=2,column=0,sticky=Tkinter.W)
        self.choiceFrame.pack(anchor=Tkinter.W,fill=Tkinter.X)
        
        self.filterFrame = Tkinter.Frame(self.sideFrame, bd=2, relief=Tkinter.GROOVE)
        self.stringVarDict['FILTER_TYPE'].set('identity')
        self.filterIdentityRB = Tkinter.Radiobutton(self.filterFrame,text='No Filter',variable=self.stringVarDict['FILTER_TYPE'],value='identity', command=self._onClickFilterFrame)
        self.filterMARB = Tkinter.Radiobutton(self.filterFrame,text='Moving Average',variable=self.stringVarDict['FILTER_TYPE'],value='ma', command=self._onClickFilterFrame)
        self.filterButterRB = Tkinter.Radiobutton(self.filterFrame,text='Butterworth',variable=self.stringVarDict['FILTER_TYPE'],value='butter', command=self._onClickFilterFrame)
        self.filterFiltFiltRB = Tkinter.Radiobutton(self.filterFrame,text='Forward-Backword Butterworth',variable=self.stringVarDict['FILTER_TYPE'],value='butter_filtfilt', command=self._onClickFilterFrame)
        self.filterIdentityRB.grid(row=0,column=0, sticky=Tkinter.W)
        self.filterMARB.grid(row=1,column=0, sticky=Tkinter.W)
        self.filterButterRB.grid(row=2,column=0, sticky=Tkinter.W)
        self.filterFiltFiltRB.grid(row=3,column=0, sticky=Tkinter.W)
        self.filterFrame.pack(fill=Tkinter.BOTH)
        self.checkOverwrite = Tkinter.IntVar()
        self.loadConfigButton = Tkinter.Button(self.sideFrame, text='Load Configuration File', command=self._loadConfig)
        self.loadConfigButton.pack(fill=Tkinter.X, padx=10, pady=2)
        Tkinter.Button(self.sideFrame,text='Convert Files',command=self._convertFiles).pack(fill=Tkinter.X, padx=10, pady=2)
        Tkinter.Checkbutton(self.sideFrame,text='Overwrite',variable=self.checkOverwrite).pack()
        
        self.sideFrame.pack(side=Tkinter.LEFT,anchor=Tkinter.W,fill=Tkinter.BOTH)
        self.paramFrame.pack(side=Tkinter.LEFT,fill=Tkinter.BOTH)
        
        self._onClickChoiceFrame()
    
    def _convertFiles(self):
        fnames = tkFileDialog.askopenfilenames(filetypes=[('SimpleGazeTracker CSV file','*.csv')],initialdir=GazeParser.homeDir)
        
        if fnames=='':
            tkMessageBox.showinfo('info', 'No files')
            return
        
        if isinstance(fnames, unicode):
            fnames = splitFilenames(fnames)
        
        if self.checkOverwrite.get()==1:
            overwrite = True
        else:
            overwrite = False
        
        usefileparameters = self.useParameters.get()
        
        self._updateParameters()
        
        donelist = []
        errorlist = []
        for f in fnames:
            try:
                res = GazeParser.Converter.TrackerToGazeParser(f,overwrite=overwrite,config=self.configuration,useFileParameters=usefileparameters)
            except:
                info = sys.exc_info()
                tbinfo = traceback.format_tb(info[2])
                errormsg = ''
                for tbi in tbinfo:
                    errormsg += tbi
                errormsg += '  %s' % str(info[1])
                tkMessageBox.showerror('Error', errormsg)
            else:
                if res == 'SUCCESS':
                    donelist.append(f)
                else:
                    tkMessageBox.showerror('Info', res)
                    errorlist.append(f)
        msg = 'Convertion done.\n'+'\n'.join(donelist)
        if len(errorlist) > 0:
            msg += '\n\nError.\n'+'\n'.join(errorlist)
        tkMessageBox.showinfo('info',msg)
    
    def _loadConfig(self):
        self.ftypes = [('GazeParser ConfigFile', '*.cfg')]
        if os.path.exists(GazeParser.configDir):
            initialdir = GazeParser.configDir
        else:
            initialdir = GazeParser.homeDir
        self.configFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes, initialdir=initialdir)
        try:
            self.configuration = GazeParser.Configuration.Config(self.configFileName)
        except:
            tkMessageBox.showerror('GazeParser.Configuration.GUI','Cannot read %s.\nThis file may not be a GazeParser ConfigFile' % self.configFileName)
        
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key].set(getattr(self.configuration,key))
        
    def _updateParameters(self):
        for key in GazeParser.Configuration.GazeParserOptions:
            value = self.stringVarDict[key].get()
            if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                setattr(self.configuration, key, int(value))
            elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                setattr(self.configuration, key, float(value))
            else:
                setattr(self.configuration, key, value)
    
    def _onClickChoiceFrame(self):
        if self.useParameters.get():
            state = 'disabled'
        else:
            state = 'normal'
            
        for key in self.paramEntryDict.keys():
            self.paramEntryDict[key].configure(state=state)
        self.loadConfigButton.configure(state=state)
        
        self.filterIdentityRB.configure(state=state)
        self.filterMARB.configure(state=state)
        self.filterButterRB.configure(state=state)
        self.filterFiltFiltRB.configure(state=state)
        
        if not self.useParameters.get():
            self._onClickFilterFrame()

    
    def _onClickFilterFrame(self):
        filter = self.stringVarDict['FILTER_TYPE'].get()
        if filter == 'ma':
            self.paramEntryDict['FILTER_SIZE'].configure(state='normal')
            self.paramEntryDict['FILTER_ORDER'].configure(state='disabled')
            self.paramEntryDict['FILTER_WN'].configure(state='disabled')
        elif filter == 'butter' or filter == 'butter_filtfilt':
            self.paramEntryDict['FILTER_SIZE'].configure(state='disabled')
            self.paramEntryDict['FILTER_ORDER'].configure(state='normal')
            self.paramEntryDict['FILTER_WN'].configure(state='normal')
        else:
            self.paramEntryDict['FILTER_SIZE'].configure(state='disabled')
            self.paramEntryDict['FILTER_ORDER'].configure(state='disabled')
            self.paramEntryDict['FILTER_WN'].configure(state='disabled')
        
    

class EyelinkConverter(Tkinter.Frame):
    def __init__(self, master=None):
        Tkinter.Frame.__init__(self, master, srctype=None)
        self.master.title('GazeParser Data Converter (Eyelink)')
        
        self.mainFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.configuration = GazeParser.Configuration.Config()
        
        self.stringVarDict = {}
        r = 0
        
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key] = Tkinter.StringVar()
            self.stringVarDict[key].set(getattr(self.configuration, key))
            Tkinter.Label(self.mainFrame, text=key).grid(row=r, column=0, sticky=Tkinter.W)
            Tkinter.Entry(self.mainFrame, textvariable=self.stringVarDict[key]).grid(row=r, column=1)
            r+=1
        Tkinter.Button(self.mainFrame, text='Load Configuration File', command=self._loadConfig).grid(row=r, column=0,columnspan=2, sticky=Tkinter.W+Tkinter.E, padx=10, ipady=2)
        self.mainFrame.pack()
        
        
        self.goFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.checkOverwrite = Tkinter.IntVar()
        Tkinter.Button(self.goFrame,text='Convert Files',command=self._convertFiles).pack(fill=Tkinter.X, padx=10, ipady=2)
        Tkinter.Checkbutton(self.goFrame,text='Overwrite',variable=self.checkOverwrite).pack()
        self.goFrame.pack(anchor=Tkinter.W,fill=Tkinter.X)
    
    def _convertFiles(self):
        fnames = tkFileDialog.askopenfilenames(filetypes=[('Eyelink EDF file','*.edf')],initialdir=GazeParser.homeDir)
        
        if fnames=='':
            tkMessageBox.showinfo('info', 'No files')
            return
        
        if isinstance(fnames, unicode):
            fnames = splitFilenames(fnames)
        
        if self.checkOverwrite.get()==1:
            overwrite = True
        else:
            overwrite = False
        
        self._updateParameters()
        
        donelist = []
        errorlist = []
        for f in fnames:
            try:
                res = GazeParser.Converter.EyelinkToGazeParser(f,'B',overwrite=overwrite,config=self.configuration)
            except:
                info = sys.exc_info()
                tbinfo = traceback.format_tb(info[2])
                errormsg = ''
                for tbi in tbinfo:
                    errormsg += tbi
                errormsg += '  %s' % str(info[1])
                tkMessageBox.showerror('Error', errormsg)
            else:
                if res == 'SUCCESS':
                    donelist.append(f)
                else:
                    tkMessageBox.showerror('Info', res)
                    errorlist.append(f)
        msg = 'Convertion done.\n'+'\n'.join(donelist)
        if len(errorlist) > 0:
            msg += '\n\nError.\n'+'\n'.join(errorlist)
        tkMessageBox.showinfo('info',msg)
        
    def _loadConfig(self):
        self.ftypes = [('GazeParser ConfigFile', '*.cfg')]
        self.configFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes, initialdir=GazeParser.configDir)
        self.configuration = GazeParser.Configuration.Config(self.configFileName)
        
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key].set(getattr(self.configuration,key))
        
    def _updateParameters(self):
        for key in GazeParser.Configuration.GazeParserOptions:
            value = self.stringVarDict[key].get()
            if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                setattr(self.configuration, key, int(value))
            elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                setattr(self.configuration, key, float(value))
            else:
                setattr(self.configuration, key, value)
    
class TobiiConverter(Tkinter.Frame):
    def __init__(self, master=None):
        Tkinter.Frame.__init__(self, master, srctype=None)
        self.master.title('GazeParser Data Converter (Tobii)')
        
        self.mainFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.configuration = GazeParser.Configuration.Config()
        
        self.stringVarDict = {}
        r = 0
        
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key] = Tkinter.StringVar()
            self.stringVarDict[key].set(getattr(self.configuration, key))
            Tkinter.Label(self.mainFrame, text=key).grid(row=r, column=0, sticky=Tkinter.W)
            Tkinter.Entry(self.mainFrame, textvariable=self.stringVarDict[key]).grid(row=r, column=1)
            r+=1
        Tkinter.Button(self.mainFrame, text='Load Configuration File', command=self._loadConfig).grid(row=r, column=0,columnspan=2, sticky=Tkinter.W+Tkinter.E, padx=10, ipady=2)
        self.mainFrame.pack()
        
        self.goFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.checkOverwrite = Tkinter.IntVar()
        Tkinter.Button(self.goFrame,text='Convert Files',command=self._convertFiles).pack(fill=Tkinter.X, padx=10, ipady=2)
        Tkinter.Checkbutton(self.goFrame,text='Overwrite',variable=self.checkOverwrite).pack()
        self.goFrame.pack(anchor=Tkinter.W,fill=Tkinter.X)
    
    def _convertFiles(self):
        fnames = tkFileDialog.askopenfilenames(filetypes=[('Tobii TSV file','*.tsv')],initialdir=GazeParser.homeDir)
        
        if fnames=='':
            tkMessageBox.showinfo('info', 'No files')
            return
        
        if isinstance(fnames, unicode):
            fnames = splitFilenames(fnames)
        
        if self.checkOverwrite.get()==1:
            overwrite = True
        else:
            overwrite = False
        
        self._updateParameters()
        
        donelist = []
        errorlist = []
        for f in fnames:
            try:
                res = GazeParser.Converter.TobiiToGazeParser(f,overwrite=overwrite,config=self.configuration)
            except:
                info = sys.exc_info()
                tbinfo = traceback.format_tb(info[2])
                errormsg = ''
                for tbi in tbinfo:
                    errormsg += tbi
                errormsg += '  %s' % str(info[1])
                tkMessageBox.showerror('Error', errormsg)
            else:
                if res == 'SUCCESS':
                    donelist.append(f)
                else:
                    tkMessageBox.showerror('Info', res)
                    errorlist.append(f)
        msg = 'Convertion done.\n'+'\n'.join(donelist)
        if len(errorlist) > 0:
            msg += '\n\nError.\n'+'\n'.join(errorlist)
        tkMessageBox.showinfo('info',msg)
        
    def _loadConfig(self):
        self.ftypes = [('GazeParser ConfigFile', '*.cfg')]
        self.configFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes, initialdir=GazeParser.configDir)
        self.configuration = GazeParser.Configuration.Config(self.configFileName)
        
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key].set(getattr(self.configuration,key))
        
    def _updateParameters(self):
        for key in GazeParser.Configuration.GazeParserOptions:
            value = self.stringVarDict[key].get()
            if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                setattr(self.configuration, key, int(value))
            elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                setattr(self.configuration, key, float(value))
            else:
                setattr(self.configuration, key, value)
    


class InteractiveConfig(Tkinter.Frame):
    def __init__(self, master=None, data=None, additional=None):
        self.ftypes = [('GazeParser Datafile','*.db')]
        self.configtypes = [('GazeParser Configuration File','*.cfg')]
        if data==None:
            self.dataFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes,initialdir=GazeParser.homeDir)
            if self.dataFileName=='':
                return
            [self.D,self.C] = GazeParser.load(self.dataFileName)
        else:
            self.D = data
            self.C = additional
        self.tr = 0
        self.currentPlotArea = [0,3000,0,1024]
        self.relativeRangeX = 1.0
        self.relativeRangeY = 1.0
        self.dataFileName = 'Please open data file.'
        self.newFixList = None
        self.newSacList = None
        self.newL = None
        self.newR = None
        self.newConfig = None
        
        Tkinter.Frame.__init__(self,master)
        self.master.title('GazeParser Adjust-Parameters')
        menu_bar = Tkinter.Menu(tearoff=False)
        menu_file = Tkinter.Menu(tearoff=False)
        self.menu_view = Tkinter.Menu(tearoff=False)
        menu_bar.add_cascade(label='File',menu=menu_file,underline=0)
        menu_bar.add_cascade(label='View',menu=self.menu_view,underline=0)
        if self.D==None:
            menu_file.add_command(label='Open',under=0,command=self._openfile)
        menu_file.add_command(label='Export Config',under=0,command=self._exportConfig)
        menu_file.add_command(label='Exit',under=0,command=self._exit)
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
            self.newParamStringsDict[key].set(getattr(self.D[self.tr].config,key))
            Tkinter.Label(self.paramFrame, text=str(getattr(self.D[self.tr].config,key))).grid(row=r,column=1,sticky=Tkinter.W,)
            Tkinter.Entry(self.paramFrame, textvariable=self.newParamStringsDict[key]).grid(row=r,column=2)
        r+=1
        Tkinter.Button(self.paramFrame, text='Update', command=self._updateParameters).grid(row=r,column=0,columnspan=3)
        self.paramFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        self.mainFrame.pack(side=Tkinter.TOP,fill=Tkinter.BOTH,expand=True)
        
        if self.D!=None:
            self._plotData()
    
    """
    def _openfile(self, event=None):
        self.dataFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes,initialdir=GazeParser.homeDir)
        if self.dataFileName=='':
            return
        [self.D,self.C] = GazeParser.load(self.dataFileName)
        self.block = 0
        self.tr = 0
        self.newSacList = None
        self.newSacList = None
        self.newL = None
        self.newR = None
        configStr = 'Original Configuration\n\n'
        for key in GazeParser.Configuration.GazeParserOptions:
            configStr += '%s = %s\n' % (key, getattr(self.D[self.tr].config, key))
        self.param1Text.set(configStr)
        
        self.currentPlotArea[3] = max(self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT)
        
        self._plotData()
    """
    
    def _exit(self,event=None):
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
            self.ax.plot(t,self.newL[:,0],':',color=(1,0,1))
            self.ax.plot(t,self.newL[:,1],':',color=(0,0,1))
        if self.newR != None:
            self.ax.plot(t,self.newR[:,0],'.-',color=(1,0,0.5))
            self.ax.plot(t,self.newR[:,1],'.-',color=(0,0,0.5))
        if self.D[self.tr].config.RECORDED_EYE != 'R':
            self.ax.plot(t,self.D[self.tr].L[:,0],'.-',color=(1,0,1))
            self.ax.plot(t,self.D[self.tr].L[:,1],'.-',color=(0,0,1))
        if self.D[self.tr].config.RECORDED_EYE != 'L':
            self.ax.plot(t,self.D[self.tr].R[:,0],'.-',color=(1,0,0.5))
            self.ax.plot(t,self.D[self.tr].R[:,1],'.-',color=(0,0,0.5))
        
        for f in range(self.D[self.tr].nFix):
            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart,self.D[self.tr].Fix[f].center[0],str(f),color=(0.0,0.0,0.0),
                         bbox=dict(boxstyle="round", fc="0.8", clip_on=True, clip_box=self.ax.bbox), clip_on=True)
        
        for s in range(self.D[self.tr].nSac):
            self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000], self.D[self.tr].Sac[s].duration,20000,ec=(0.0,0.0,0.6),hatch='/',fc=(0.6,0.6,0.9),alpha=0.3))
        
        if self.newSacList != None and self.newFixList != None:
            for f in range(len(self.newFixList)):
                self.ax.text(self.newFixList[f].startTime-tStart,self.newFixList[f].center[0]-50,str(f),color=(0.5,0.0,0.0),
                             bbox=dict(boxstyle="round", fc=(1.0,0.8,0.8), clip_on=True, clip_box=self.ax.bbox), clip_on=True)
            
            for s in range(len(self.newSacList)):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.newSacList[s].startTime-tStart,-10000], self.newSacList[s].duration,20000,ec=(0.6,0.0,0.0),hatch='/',fc=(0.9,0.6,0.6),alpha=0.3))
        
        self.ax.axis(self.currentPlotArea)
        
        self.ax.set_title('%s: Trial%d' % (os.path.basename(self.dataFileName), self.tr))
        
        self.fig.canvas.draw()
    
    def _updateParameters(self):
        if self.D == None:
            tkMessageBox.showerror('Error','No data!')
            return
            
        if self.newConfig==None:
            self.newConfig = copy.deepcopy(self.D[self.tr].config)
        
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
        
        offset = 10
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
            fdir = os.path.split(self.dataFileName)[0]
        except:
            fdir = GazeParser.configDir
        
        try:
            fname = tkFileDialog.asksaveasfilename(filetypes=self.newConfigtypes, initialdir=fdir)
            self.newConfig.save(fname)
        except:
            tkMessageBox.showerror('Error','Could not write configuration to ' + fname)
    

def splitFilenames(filenames):
    tmplist = filenames.split(' ')
    newFilenames = []
    i = 0
    while i<len(tmplist):
        if tmplist[i][0] == '{': #space is included
            s = i
            while tmplist[i][-1] != '}':
                i+=1
            fname = ' '.join(tmplist[s:i+1])
            newFilenames.append(fname[1:-1])
        elif tmplist[i][-1] == '\\':
            s = i
            while tmplist[i][-1] == '\\':
                i+=1
            fname = ' '.join(tmplist[s:i+1])
            newFilenames.append(fname.replace('\\',''))
        else:
            newFilenames.append(tmplist[i].replace('\\',''))
        i+=1
    return newFilenames

if (__name__ == '__main__'):
    def ok(event=None):
        c = choice.get()
        dw = Tkinter.Toplevel()
        if c==0:
            Converter(master=dw)
        elif c==1:
            EyelinkConverter(master=dw)
        elif c==2:
            TobiiConverter(master=dw)
        elif c==3:
            InteractiveConfig(master=dw)
        dw.focus_set()
        dw.grab_set()
        #w.transient(mw)
        #w.resizable(0, 0)
        dw.wait_window(dw)
    
    mw = Tkinter.Frame()
    choice = Tkinter.IntVar()
    Tkinter.Radiobutton(mw, text='Converter', variable=choice, value=0).pack()
    Tkinter.Radiobutton(mw, text='Eyelink Converter', variable=choice, value=1).pack()
    Tkinter.Radiobutton(mw, text='Tobii Converter', variable=choice, value=2).pack()
    Tkinter.Radiobutton(mw, text='Interactive Configuration', variable=choice, value=3).pack()
    okbutton = Tkinter.Button(mw, text='OK', command=ok)
    okbutton.pack()
    okbutton.focus_set()
    okbutton.bind("<Return>", ok)
    mw.pack()
    mw.mainloop()

