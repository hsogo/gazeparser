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
    okbutton = Tkinter.Button(mw, text='OK', command=ok)
    okbutton.pack()
    okbutton.focus_set()
    okbutton.bind("<Return>", ok)
    mw.pack()
    mw.mainloop()

