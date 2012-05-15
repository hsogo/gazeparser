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

from GazeParser.Converter import EyelinkToGazeParser, TrackerToGazeParser

import matplotlib,matplotlib.figure
import matplotlib.patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg

class Converter(Tkinter.Frame):
    def __init__(self, master=None):
        Tkinter.Frame.__init__(self, master, srctype=None)
        self.master.title('GazeParser Data Converter')
        
        self.useParameters = Tkinter.StringVar()
        self.useParameters.set(True)
        
        self.mainFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.config = GazeParser.Configuration.Config()
        
        self.stringVarDict = {}
        r = 0
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key] = Tkinter.StringVar()
            self.stringVarDict[key].set(getattr(self.config, key))
            Tkinter.Label(self.mainFrame, text=key).grid(row=r, column=0, sticky=Tkinter.W)
            Tkinter.Entry(self.mainFrame, textvariable=self.stringVarDict[key]).grid(row=r, column=1)
            r+=1
        Tkinter.Button(self.mainFrame, text='Load Configuration File', command=self._loadConfig).grid(row=r, column=0,columnspan=2, padx=10, ipady=2)
        self.mainFrame.pack(side=Tkinter.LEFT,fill=Tkinter.BOTH)
        self.sideFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.choiceFrame = Tkinter.Frame(self.sideFrame, bd=2, relief=Tkinter.GROOVE)
        self.usefileRadiobutton = Tkinter.Radiobutton(self.choiceFrame, text='Use parameters embedded in the data file if available', variable=self.useParameters, value=True)
        self.overwriteRadiobutton = Tkinter.Radiobutton(self.choiceFrame, text='Use following parameters', variable=self.useParameters, value=False)
        self.usefileRadiobutton.grid(row=0,column=0,sticky=Tkinter.W)
        self.overwriteRadiobutton.grid(row=1,column=0,sticky=Tkinter.W)
        self.choiceFrame.pack(anchor=Tkinter.W,fill=Tkinter.X)
        #self.choiceFrame.grid(row=0,column=0,columnspan=2, sticky=Tkinter.W+Tkinter.E)
        self.filterFrame = Tkinter.Frame(self.sideFrame, bd=2, relief=Tkinter.GROOVE)
        self.stringVarDict['FILTER_TYPE'].set('butter_filtfilt')
        Tkinter.Radiobutton(self.filterFrame,text='No Filter',variable=self.stringVarDict['FILTER_TYPE'],value='identity').grid(row=0,column=0, sticky=Tkinter.W)
        Tkinter.Radiobutton(self.filterFrame,text='Moving Average',variable=self.stringVarDict['FILTER_TYPE'],value='ma').grid(row=1,column=0, sticky=Tkinter.W)
        Tkinter.Radiobutton(self.filterFrame,text='Butterworth',variable=self.stringVarDict['FILTER_TYPE'],value='butter').grid(row=2,column=0, sticky=Tkinter.W)
        Tkinter.Radiobutton(self.filterFrame,text='Forward-Backword Butterworth',variable=self.stringVarDict['FILTER_TYPE'],value='butter_filtfilt').grid(row=3,column=0, sticky=Tkinter.W)
        self.filterFrame.pack(fill=Tkinter.BOTH)
        self.checkOverwrite = Tkinter.IntVar()
        Tkinter.Button(self.sideFrame,text='Convert Single File',command=self._convertSingleFile).pack(fill=Tkinter.X, padx=10, ipady=2)
        Tkinter.Button(self.sideFrame,text='Convert Files in a Directory',command=self._convertDirectory).pack(fill=Tkinter.X, padx=10, ipady=2)
        Tkinter.Checkbutton(self.sideFrame,text='Overwrite',variable=self.checkOverwrite).pack()
        self.sideFrame.pack(side=Tkinter.LEFT,anchor=Tkinter.W,fill=Tkinter.BOTH)
        
    def _convertSingleFile(self):
        if self.checkOverwrite.get()==1:
            overwrite = True
        else:
            overwrite = False
        
        usefileparameters = self.useParameters.get()
        
        self._updateParameters()
        
        fname = tkFileDialog.askopenfilename(filetypes=[('GazeTracker CSV file','*.csv')],initialdir=GazeParser.homeDir)
        if fname=='':
            return
        try:
            res = GazeParser.Converter.TrackerToGazeParser(fname,overwrite=overwrite,config=self.config,useFileParameters=usefileparameters)
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
                tkMessageBox.showinfo('Info','Convertion done.')
            else:
                tkMessageBox.showerror('Info', res)
    
    def _convertDirectory(self):
        dname = tkFileDialog.askdirectory(initialdir=GazeParser.homeDir)
        if dname=='':
            return
        
        if self.checkOverwrite.get()==1:
            overwrite = True
        else:
            overwrite = False
        
        usefileparameters = self.useParameters.get()
        
        self._updateParameters()
        ext = '.csv'
        
        donelist = []
        errorlist = []
        for f in os.listdir(dname):
            if os.path.splitext(f)[1].lower() == ext:
                #res = GazeParser.Converter.TrackerToGazeParser(os.path.join(dname,f),overwrite=overwrite,config=self.config,useFileParameters=usefileparameters)
                try:
                    res = GazeParser.Converter.TrackerToGazeParser(os.path.join(dname,f),overwrite=overwrite,config=self.config,useFileParameters=usefileparameters)
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
                        #tkMessageBox.showerror('Info', res)
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
            self.config = GazeParser.Configuration.Config(self.configFileName)
        except:
            tkMessageBox.showerror('GazeParser.Configuration.GUI','Cannot read %s.\nThis file may not be a GazeParser ConfigFile' % self.configFileName)
        
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key].set(getattr(self.config,key))
        
    def _updateParameters(self):
        for key in GazeParser.Configuration.GazeParserOptions:
            value = self.stringVarDict[key].get()
            if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                setattr(self.config, key, int(value))
            elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                setattr(self.config, key, float(value))
            else:
                setattr(self.config, key, value)
    

class EyelinkConverter(Tkinter.Frame):
    def __init__(self, master=None):
        Tkinter.Frame.__init__(self, master, srctype=None)
        self.master.title('GazeParser Data Converter (Eyelink)')
        
        self.mainFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.config = GazeParser.Configuration.Config()
        
        self.stringVarDict = {}
        r = 0
        
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key] = Tkinter.StringVar()
            self.stringVarDict[key].set(getattr(self.config, key))
            Tkinter.Label(self.mainFrame, text=key).grid(row=r, column=0, sticky=Tkinter.W)
            Tkinter.Entry(self.mainFrame, textvariable=self.stringVarDict[key]).grid(row=r, column=1)
            r+=1
        Tkinter.Button(self.mainFrame, text='Load Configuration File', command=self._loadConfig).grid(row=r, column=0,columnspan=2, sticky=Tkinter.W+Tkinter.E, padx=10, ipady=2)
        self.mainFrame.pack()
        
        self.goFrame = Tkinter.Frame(master, bd=2, relief=Tkinter.GROOVE)
        self.checkOverwrite = Tkinter.IntVar()
        Tkinter.Button(self.goFrame,text='Convert Single File',command=self._convertSingleFile).pack(fill=Tkinter.X, padx=10, ipady=2)
        Tkinter.Button(self.goFrame,text='Convert Files in a Directory',command=self._convertDirectory).pack(fill=Tkinter.X, padx=10, ipady=2)
        Tkinter.Checkbutton(self.goFrame,text='Overwrite',variable=self.checkOverwrite).pack()
        self.goFrame.pack(anchor=Tkinter.W,fill=Tkinter.X)
        
    def _convertSingleFile(self):
        if self.checkOverwrite.get()==1:
            overwrite = True
        else:
            overwrite = False
        
        self._updateParameters()
        
        fname = tkFileDialog.askopenfilename(filetypes=[('Eyelink EDF file','*.edf')],initialdir=GazeParser.homeDir)
        if fname=='':
            return
        try:
            res = GazeParser.Converter.EyelinkToGazeParser(fname,'B',overwrite=overwrite,config=self.config)
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
                tkMessageBox.showinfo('Info','Convertion done.')
            else:
                tkMessageBox.showerror('Info', res)
    
    def _convertDirectory(self):
        if self.checkOverwrite.get()==1:
            overwrite = True
        else:
            overwrite = False
        
        dname = tkFileDialog.askdirectory(initialdir=GazeParser.homeDir)
        if dname=='':
            return
        
        self._updateParameters()
        ext = '.edf'
        
        donelist = []
        errorlist = []
        for f in os.listdir(dname):
            if os.path.splitext(f)[1].lower() == ext:
                try:
                    res = GazeParser.Converter.EyelinkToGazeParser(os.path.join(dname,f),'B',overwrite=overwrite,config=self.config)
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
                        #tkMessageBox.showerror('Info', res)
                        errorlist.append(f)
        msg = 'Convertion done.\n'+'\n'.join(donelist)
        if len(errorlist) > 0:
            msg += '\n\nError.\n'+'\n'.join(errorlist)
        tkMessageBox.showinfo('info',msg)
        
    def _loadConfig(self):
        self.ftypes = [('GazeParser ConfigFile', '*.cfg')]
        self.configFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes, initialdir=GazeParser.configDir)
        self.config = GazeParser.Configuration.Config(self.configFileName)
        
        for key in GazeParser.Configuration.GazeParserOptions:
            self.stringVarDict[key].set(getattr(self.config,key))
        
    def _updateParameters(self):
        for key in GazeParser.Configuration.GazeParserOptions:
            value = self.stringVarDict[key].get()
            if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                setattr(self.config, key, int(value))
            elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                setattr(self.config, key, float(value))
            else:
                setattr(self.config, key, value)
    


class InteractiveConfig(Tkinter.Frame):
    """
    .. todo:: Support new converter.
    
    .. warning:: Currently this tool doesn't work.
    """
    def __init__(self, master = None):
        self.ftypes = [('GazeParser Datafile','*.db')]
        self.configtypes = [('GazeParser Configuration File','*.cfg')]
        self.D = None
        self.C = None
        self.tr = 0
        self.currentPlotArea = [0,3000,0,1024]
        self.relativeRangeX = 1.0
        self.relativeRangeY = 1.0
        self.dataFileName = 'Please open data file.'
        self.newFixList = None
        self.newSacList = None
        
        self.config = GazeParser.Configuration.Config()
        
        Tkinter.Frame.__init__(self,master)
        self.master.title('GazeParser Adjust-Parameters')
        menu_bar = Tkinter.Menu(tearoff=False)
        menu_file = Tkinter.Menu(tearoff=False)
        self.menu_view = Tkinter.Menu(tearoff=False)
        menu_bar.add_cascade(label='File',menu=menu_file,underline=0)
        menu_bar.add_cascade(label='View',menu=self.menu_view,underline=0)
        menu_file.add_command(label='Open',under=0,command=self._openfile)
        menu_file.add_command(label='Export Config1',under=0,command=self._exportConfig1)
        menu_file.add_command(label='Export Config2',under=0,command=self._exportConfig2)
        menu_file.add_command(label='Exit',under=0,command=self._exit)
        self.menu_view.add_command(label='Prev Trial',under=0,command=self._prevTrial)
        self.menu_view.add_command(label='Next Trial',under=0,command=self._nextTrial)
        self.master.configure(menu = menu_bar)
        
        """
        script_path = os.path.abspath(os.path.dirname(__file__))
        self.img_zoomin = ImageTk.PhotoImage(Image.open(os.path.join(script_path,'img','zoomin.png')))
        self.img_zoomout= ImageTk.PhotoImage(Image.open(os.path.join(script_path,'img','zoomout.png')))
        self.img_cood = ImageTk.PhotoImage(Image.open(os.path.join(script_path,'img','cood.png')))
        """
        
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
        
        
        #self.subFrame1 = Tkinter.Frame(self.mainFrame, bd=3, relief='groove')
        self.paramFrame1 = Tkinter.Frame(self.mainFrame, bd=3, relief='groove') #subFrame1
        self.velThresholdEntry1 = Tkinter.StringVar()
        self.minDurationEntry1 = Tkinter.StringVar()
        Tkinter.Label(self.paramFrame1, text='Saccade Velocity Threshold').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame1, textvariable=self.velThresholdEntry1).pack(side=Tkinter.TOP)
        Tkinter.Label(self.paramFrame1, text='Saccade Minimum Duration').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame1, textvariable=self.minDurationEntry1).pack(side=Tkinter.TOP)
        Tkinter.Button(self.paramFrame1, text='Update', command=self._updateAdjustResults1).pack(side=Tkinter.TOP)
        self.paramFrame1.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        
        #self.subFrame2 = Tkinter.Frame(self.mainFrame, bd=3, relief='groove')
        self.paramFrame2 = Tkinter.Frame(self.mainFrame, bd=3, relief='groove') #subFrame2
        self.velThresholdEntry2 = Tkinter.StringVar()
        self.minDurationEntry2 = Tkinter.StringVar()
        Tkinter.Label(self.paramFrame2, text='Saccade Velocity Threshold').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame2, textvariable=self.velThresholdEntry2).pack(side=Tkinter.TOP)
        Tkinter.Label(self.paramFrame2, text='Saccade Minimum Duration').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame2, textvariable=self.minDurationEntry2).pack(side=Tkinter.TOP)
        Tkinter.Button(self.paramFrame2, text='Update', command=self._updateAdjustResults2).pack(side=Tkinter.TOP)
        self.paramFrame2.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        
        self.paramFrame3 = Tkinter.Frame(self.mainFrame, bd=3, relief='groove') #apparatus
        self.screenWidthEntry = Tkinter.StringVar()
        self.screenHeightEntry = Tkinter.StringVar()
        self.viewingDistanceEntry = Tkinter.StringVar()
        self.dotsPerCentiWEntry = Tkinter.StringVar()
        self.dotsPerCentiHEntry = Tkinter.StringVar()
        Tkinter.Label(self.paramFrame3, text='Screen Width').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame3, textvariable=self.screenWidthEntry).pack(side=Tkinter.TOP)
        Tkinter.Label(self.paramFrame3, text='Screen Height').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame3, textvariable=self.screenHeightEntry).pack(side=Tkinter.TOP)
        Tkinter.Label(self.paramFrame3, text='Viewing Distance').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame3, textvariable=self.viewingDistanceEntry).pack(side=Tkinter.TOP)
        Tkinter.Label(self.paramFrame3, text='Dots per Centimeter (W)').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame3, textvariable=self.dotsPerCentiWEntry).pack(side=Tkinter.TOP)
        Tkinter.Label(self.paramFrame3, text='Dots per Centimener (H)').pack(side=Tkinter.TOP)
        Tkinter.Entry(self.paramFrame3, textvariable=self.dotsPerCentiHEntry).pack(side=Tkinter.TOP)
        self.paramFrame3.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        
        self.mainFrame.pack(side=Tkinter.TOP,fill=Tkinter.BOTH,expand=True)
        
        
    def _openfile(self, event=None):
        self.dataFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes,initialdir=GazeParser.homeDir)
        if self.dataFileName=='':
            return
        [self.D,self.C] = GazeParser.load(self.dataFileName)
        self.block = 0
        self.tr = 0
        self.newSacList1 = self.D[self.tr].Sac[:]
        self.newFixList1 = self.D[self.tr].Fix[:]
        self.newSacList2 = None
        self.newSacList2 = None
        self.velThresholdEntry1.set(str(self.D[self.tr].config.SACCADE_VELOCITY_THRESHOLD))
        self.minDurationEntry1.set(str(self.D[self.tr].config.SACCADE_MINIMUM_DURATION))
        self.screenWidthEntry.set(str(self.D[self.tr].config.SCREEN_WIDTH))
        self.screenHeightEntry.set(str(self.D[self.tr].config.SCREEN_HEIGHT))
        self.viewingDistanceEntry.set(str(self.D[self.tr].config.VIEWING_DISTANCE))
        self.dotsPerCentiWEntry.set(str(self.D[self.tr].config.DOTS_PER_CENTIMETER_H))
        self.dotsPerCentiHEntry.set(str(self.D[self.tr].config.DOTS_PER_CENTIMETER_V))
        
        self.currentPlotArea[3] = max(self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT)
        
        self._plotData()
        
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
        self.updateAdjustResults1()
        self.updateAdjustResults2()
        
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
        self.ax.plot(t,self.D[self.tr].L[:,0],'g.-')
        self.ax.plot(t,self.D[self.tr].L[:,1],'m.-')
        
        if self.newSacList1 != None and self.newFixList1 != None:
            for f in range(len(self.newFixList1)):
                self.ax.text(self.newFixList1[f].startTime-tStart,self.newFixList1[f].center[0],str(f),color=(0.0,0.0,0.0))
            
            for s in range(len(self.newSacList1)):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.newSacList1[s].startTime-tStart,-10000], self.newSacList1[s].duration,20000,ec=(0.0,0.0,0.6),hatch='/',fc=(0.6,0.6,0.9),alpha=0.3))
            
            #for b in range(self.D[self.tr].nBlink):
            #    self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Blink[b].startTime-tStart,-10000], self.D[self.tr].Blink[b].duration,20000,ec='none',fc=(0.8,0.8,0.8)))
        
        if self.newSacList2 != None and self.newFixList2 != None:
            for f in range(len(self.newFixList2)):
                self.ax.text(self.newFixList2[f].startTime-tStart,self.newFixList2[f].center[0]-50,str(f),color=(0.6,0.0,0.0))
            
            for s in range(len(self.newSacList2)):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.newSacList2[s].startTime-tStart,-10000], self.newSacList2[s].duration,20000,ec=(0.6,0.0,0.0),hatch='/',fc=(0.9,0.6,0.6),alpha=0.3))
        
        self.ax.axis(self.currentPlotArea)
        
        self.ax.set_title('%s: Trial%d' % (os.path.basename(self.dataFileName), self.tr))
        
        self.fig.canvas.draw()
    
    def _updateAdjustResults1(self):
        if self.D == None:
            tkMessageBox.showerror('Error','No data!')
            return
        
        velthresh = self.velThresholdEntry1.get()
        mindur = self.minDurationEntry1.get()
        vdist = self.viewingDistanceEntry.get()
        dpcW = self.dotsPerCentiWEntry.get()
        dpcH = self.dotsPerCentiHEntry.get()
        if '' in (velthresh, mindur, vdist, dpcW, dpcH):
            return
        
        try:
            (self.newSacList1,self.newFixList1) = BuildSacFixList(self.D[self.tr].T,self.D[self.tr].L,
                            float(velthresh), float(mindur), float(vdist), (float(dpcW), float(dpcH)))
        except:
            info = sys.exc_info()
            tbinfo = traceback.format_tb(info[2])
            errormsg = ''
            for tbi in tbinfo:
                errormsg += tbi
            errormsg += '  %s' % str(info[1])
            tkMessageBox.showerror('Error', errormsg)
            self.newSacList1 = None
            self.newFixList1 = None
        
        self._plotData()
    
    def _updateAdjustResults2(self):
        if self.D == None:
            tkMessageBox.showerror('Error','No data!')
            return
        
        velthresh = self.velThresholdEntry2.get()
        mindur = self.minDurationEntry2.get()
        vdist = self.viewingDistanceEntry.get()
        dpcW = self.dotsPerCentiWEntry.get()
        dpcH = self.dotsPerCentiHEntry.get()
        if '' in (velthresh, mindur, vdist, dpcW, dpcH):
            return
       
        try:
            (self.newSacList2,self.newFixList2) = BuildSacFixList(self.D[self.tr].T,self.D[self.tr].L,
                            float(velthresh), float(mindur), float(vdist), (float(dpcW), float(dpcH)))
        except:
            info = sys.exc_info()
            tbinfo = traceback.format_tb(info[2])
            errormsg = ''
            for tbi in tbinfo:
                errormsg += tbi
            errormsg += '  %s' % str(info[1])
            tkMessageBox.showerror('Error', errormsg)
            self.newSacList2 = None
            self.newFixList2 = None
        
        self._plotData()
    
    def _exportConfig1(self):
        try:
            vth = float(self.velThresholdEntry1.get())
            dth = float(self.minDurationEntry1.get())
            sw = float(self.screenWidthEntry.get())
            sh = float(self.screenHeightEntry.get())
            vd = float(self.viewingDistanceEntry.get())
            dpcw = float(self.dotsPerCentiWEntry.get())
            dpch = float(self.dotsPerCentiHEntry.get())
        except:
            tkMessageBox.showerror('Error','Invalid values')
            return
        self.config.SACCADE_VELOCITY_THRESHOLD = vth
        self.config.SACCADE_MINIMUM_DURATION = dth
        self.config.SCREEN_WIDTH = sw
        self.config.SCREEN_HEIGHT = sh
        self.config.VIEWING_DISTANCE = vd
        self.config.DOTS_PER_CENTIMETER_H = dpcw
        self.config.DOTS_PER_CENTIMETER_V = dpch
        
        try:
            fdir = os.path.split(self.configFileName)[0]
        except:
            fdir = GazeParser.configDir
        
        try:
            fname = tkFileDialog.asksaveasfilename(filetypes=self.configtypes, initialdir=fdir)
            self.config.save(fname)
        except:
            tkMessageBox.showerror('Error','Could not write configuration to ' + fname)
    
    def _exportConfig2(self):
        try:
            vth = float(self.velThresholdEntry1.get())
            dth = float(self.minDurationEntry1.get())
            sw = float(self.screenWidthEntry.get())
            sh = float(self.screenHeightEntry.get())
            vd = float(self.viewingDistanceEntry.get())
            dpcw = float(self.dotsPerCentiWEntry.get())
            dpch = float(self.dotsPerCentiHEntry.get())
        except:
            tkMessageBox.showerror('Error','Invalid values')
            return
        self.config.SACCADE_VELOCITY_THRESHOLD = vth
        self.config.SACCADE_MINIMUM_DURATION = dth
        self.config.SCREEN_WIDTH = sw
        self.config.SCREEN_HEIGHT = sh
        self.config.VIEWING_DISTANCE = vd
        self.config.DOTS_PER_CENTIMETER_H = dpcw
        self.config.DOTS_PER_CENTIMETER_V = dpch
        
        try:
            fdir = os.path.split(self.configFileName)[0]
        except:
            fdir = GazeParser.configDir
        
        try:
            fname = tkFileDialog.asksaveasfilename(filetypes=self.configtypes, initialdir=fdir)
            self.config.save(fname)
        except:
            tkMessageBox.showerror('Error','Could not write configuration to ' + fname)


if (__name__ == '__main__'):
    mw = Tkinter.Frame()
    choice = Tkinter.IntVar()
    Tkinter.Radiobutton(mw, text='Converter', variable=choice, value=0).pack()
    Tkinter.Radiobutton(mw, text='Eyelink Converter', variable=choice, value=1).pack()
    Tkinter.Radiobutton(mw, text='Interactive Configuration', variable=choice, value=2).pack()
    Tkinter.Button(mw, text='OK', command=mw.quit).pack()
    mw.pack()
    mw.mainloop()
    c = choice.get()
    mw.destroy()
    
    if c==0:
        w = Converter()
    elif c==1:
        w = EyelinkConverter()
    elif c==2:
        w = InteractiveConfig()
    w.mainloop()

