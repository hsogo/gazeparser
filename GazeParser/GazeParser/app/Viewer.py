"""
Part of GazeParser library.
Copyright (C) 2012 Hiroyuki Sogo.
Distributed under the terms of the GNU General Public License (GPL).

Thanks to following page for embedded plot.

* http://www.mailinglistarchive.com/html/matplotlib-users@lists.sourceforge.net/2010-08/msg00148.html

"""

import Tkinter
import tkFileDialog
import tkMessageBox
import Image, ImageTk
import GazeParser
import GazeParser.Converter
import os
import numpy
import matplotlib,matplotlib.figure
import matplotlib.patches
import GazeParser.app.ConfigEditor
import GazeParser.app.Converters
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg

class mainWindow(Tkinter.Frame):
    def __init__(self,master=None):
        self.ftypes = [('GazeParser Datafile','*.db')]
        self.D = None
        self.C = None
        self.tr = 0
        self.plotAreaXY = [0,1024,0,768]
        self.plotAreaTXY = [0,3000,0,1024]
        self.dataFileName = 'Please open data file.'
        self.plotStyle ='XY'
        self.currentPlotArea = self.plotAreaXY
        self.relativeRangeX = 1.0
        self.relativeRangeY = 1.0
        self.selectionlist = {'Sac':[], 'Fix':[], 'Msg':[], 'Blink':[]}
        
        Tkinter.Frame.__init__(self,master)
        self.master.title('GazeParser Viewer')
        self.menu_bar = Tkinter.Menu(tearoff=False)
        self.menu_file = Tkinter.Menu(tearoff=False)
        self.menu_view = Tkinter.Menu(tearoff=False)
        self.menu_convert = Tkinter.Menu(tearoff=False)
        self.menu_bar.add_cascade(label='File',menu=self.menu_file,underline=0)
        self.menu_bar.add_cascade(label='View',menu=self.menu_view,underline=0)
        self.menu_bar.add_cascade(label='Convert',menu=self.menu_convert,underline=0)
        self.menu_file.add_command(label='Open',under=0,command=self._openfile)
        self.menu_file.add_command(label='Export',under=0,command=self._exportfile)
        self.menu_file.add_command(label='Exit',under=0,command=self._exit)
        self.menu_view.add_command(label='Toggle View',under=0,command=self._toggleView)
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
        
        #script_path = os.path.abspath(os.path.dirname(__file__))
        #self.img_zoomin = ImageTk.PhotoImage(Image.open(os.path.join(script_path,'img','zoomin.png')))
        #self.img_zoomout= ImageTk.PhotoImage(Image.open(os.path.join(script_path,'img','zoomout.png')))
        #self.img_cood = ImageTk.PhotoImage(Image.open(os.path.join(script_path,'img','cood.png')))
        
        # viewFrame
        self.viewFrame = Tkinter.Frame(master)
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viewFrame)
        self.canvas._tkcanvas.config(height=600, width=800, background="#c0c0c0", borderwidth=0, highlightthickness=0)
        self.ax = self.fig.add_axes([0.1, 0.1, 0.8, 0.8])
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
        
    def _toggleView(self, event=None):
        if self.plotStyle == 'XY':
            self.plotStyle = 'TXY'
            self.currentPlotArea = self.plotAreaTXY
        else:
            self.plotStyle = 'XY'
            self.currentPlotArea = self.plotAreaXY
            
        self._plotData()
        
    def _openfile(self, event=None):
        self.dataFileName = tkFileDialog.askopenfilename(filetypes=self.ftypes,initialdir=GazeParser.homeDir)
        if self.dataFileName=='':
            return
        [self.D,self.C] = GazeParser.load(self.dataFileName)
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
        
    def _exportfile(self,event=None):
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
        dlg.wait_window(dlg)
        
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
        
    def _modifyPlotRange(self):
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
        dlg.wait_window(dlg)
        
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
        self.ax.clear()
        
        if self.plotStyle == 'XY':
            for f in range(self.D[self.tr].nFix):
                if self.hasLData:
                    ftraj = self.D[self.tr].getFixTraj(f,'L')
                    col = (1,0,0)
                    if self.selectiontype.get()=='Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=4.0,color=col)
                            self.ax.text(self.D[self.tr].Fix[f].center[0],self.D[self.tr].Fix[f].center[1],str(f),color='w',bbox=dict(boxstyle="round", fc="0.2",clip_on=True,clip_box=self.ax.bbox),clip_on=True)
                        else:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=1.0,color=col)
                            self.ax.text(self.D[self.tr].Fix[f].center[0],self.D[self.tr].Fix[f].center[1],str(f),bbox=dict(boxstyle="round", fc="0.8",clip_on=True,clip_box=self.ax.bbox),clip_on=True)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=1.0,color=col)
                            self.ax.text(self.D[self.tr].Fix[f].center[0],self.D[self.tr].Fix[f].center[1],str(f),bbox=dict(boxstyle="round", fc="0.8",clip_on=True,clip_box=self.ax.bbox),clip_on=True)
                if self.hasRData:
                    ftraj = self.D[self.tr].getFixTraj(f,'R')
                    col = (0.6,0,0)
                    if self.selectiontype.get()=='Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=4.0,color=col)
                        else:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=1.0,color=col)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:,0],ftraj[:,1],'.-',linewidth=1.0,color=col)
                
            for s in range(self.D[self.tr].nSac):
                if self.hasLData:
                    straj = self.D[self.tr].getSacTraj(s,'L')
                    col = (0,0,1)
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
                    col = (0,0,0.6)
                    if self.selectiontype.get()=='Emphasize':
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=4.0,color=col)
                        else:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=1.0,color=col)
                    else:
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:,0],straj[:,1],'.-',linewidth=1.0,color=col)
                
            #self.ax.axis(self.plotAreaXY)
            
        else: #XY-T
            tStart = self.D[self.tr].T[0]
            t = self.D[self.tr].T-tStart
            if self.hasLData:
                self.ax.plot(t,self.D[self.tr].L[:,0],'.-',color=(1,0,1))
                self.ax.plot(t,self.D[self.tr].L[:,1],'.-',color=(0,0,1))
            if self.hasRData:
                self.ax.plot(t,self.D[self.tr].R[:,0],'.-',color=(1,0,0.5))
                self.ax.plot(t,self.D[self.tr].R[:,1],'.-',color=(0,0,0.5))
            
            for f in range(self.D[self.tr].nFix):
                if self.selectiontype.get()=='Emphasize':
                    if f in self.selectionlist['Fix']:
                        self.ax.text(self.D[self.tr].Fix[f].startTime-tStart,self.D[self.tr].Fix[f].center[0],str(f),color='w',bbox=dict(boxstyle="round", fc="0.2",clip_on=True,clip_box=self.ax.bbox),clip_on=True)
                    else:
                        self.ax.text(self.D[self.tr].Fix[f].startTime-tStart,self.D[self.tr].Fix[f].center[0],str(f),bbox=dict(boxstyle="round", fc="0.8",clip_on=True,clip_box=self.ax.bbox),clip_on=True)
                else:
                    if f in self.selectionlist['Fix']:
                        self.ax.text(self.D[self.tr].Fix[f].startTime-tStart,self.D[self.tr].Fix[f].center[0],str(f),bbox=dict(boxstyle="round", fc="0.8",clip_on=True,clip_box=self.ax.bbox),clip_on=True)
            
            for s in range(self.D[self.tr].nSac):
                if self.selectiontype.get()=='Emphasize':
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000], self.D[self.tr].Sac[s].duration,20000,ec=(0.0,0.0,0.6),hatch='/',fc=(0.3,0.3,1.0),alpha=0.8))
                    else:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000], self.D[self.tr].Sac[s].duration,20000,ec=(0.0,0.0,0.6),hatch='/',fc=(0.6,0.6,0.9),alpha=0.3))
                else:
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart,-10000], self.D[self.tr].Sac[s].duration,20000,ec=(0.0,0.0,0.6),hatch='/',fc=(0.6,0.6,0.9),alpha=0.3))
                
            for b in range(self.D[self.tr].nBlink):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Blink[b].startTime-tStart,-10000], self.D[self.tr].Blink[b].duration,20000,ec=(0.2,0.2,0.2),hatch='\\',fc=(0.8,0.8,0.8),alpha=0.3))
            
            for m in range(self.D[self.tr].nMsg):
                mObj = self.D[self.tr].Msg[m]
                if len(mObj.text)>10:
                    msgtext = str(m) + ':' + mObj.text[:7] + '...'
                else:
                    msgtext = str(m) + ':' + mObj.text
                self.ax.plot([mObj.time,mObj.time],[-10000,10000],'g-',linewidth=3.0)
                self.ax.text(mObj.time,0,msgtext,bbox=dict(boxstyle="round", fc=(0.8,1.0,0.9),clip_on=True,clip_box=self.ax.bbox),clip_on=True)
            
            #self.ax.axis(self.plotAreaTXY)
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
            elif isinstance(e,GazeParser.FixationData):
                self.msglistbox.insert(Tkinter.END,str(e.startTime)+':Fix')
            elif isinstance(e,GazeParser.MessageData):
                self.msglistbox.insert(Tkinter.END,str(e.time)+':'+e.text)
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
        w = Tkinter.Toplevel(self)
        GazeParser.app.ConfigEditor.ConfigEditor(master=w)
    
    def _convertGT(self):
        w = Tkinter.Toplevel(self)
        GazeParser.app.Converters.Converter(master=w)
    
    def _convertEL(self):
        w = Tkinter.Toplevel(self)
        GazeParser.app.Converters.EyelinkConverter(master=w)
    
    def _convertTSV(self):
        w = Tkinter.Toplevel(self)
        GazeParser.app.Converters.TobiiConverter(master=w)
    
    def _interactive(self):
        w = Tkinter.Toplevel(self)
        GazeParser.app.Converters.InteractiveConfig(master=w)
    

if __name__ == '__main__':
    w = mainWindow()
    w.mainloop()

