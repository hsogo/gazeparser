#!/usr/bin/env python
"""
Part of GazeParser library.
Copyright (C) 2012-2015 Hiroyuki Sogo.
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
try:
    import Image
    import ImageTk
except ImportError:
    from PIL import Image
    from PIL import ImageTk
import GazeParser
import GazeParser.Converter
import GazeParser.Utility
import GazeParser.Region
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
import matplotlib.cm
import GazeParser.app.ConfigEditor
import GazeParser.app.Converters
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from GazeParser.Converter import buildEventListBinocular, buildEventListMonocular, applyFilter

MAX_RECENT = 5
PLOT_OFFSET = 10
XYPLOTMODES = ['XY', 'SCATTER', 'HEATMAP']


class getFixationsInRegionWindow(Tkinter.Frame):
    def __init__(self, data, additional, conf, master=None, initialdir=None):
        Tkinter.Frame.__init__(self, master)
        self.D = data
        self.C = additional
        self.conf = conf
        if initialdir is None:
            self.initialDataDir = GazeParser.homeDir
        else:
            self.initialDataDir = initialdir

        self.commandChoice = Tkinter.StringVar()
        self.commandChoice.set('embedded')

        self.regionType = Tkinter.StringVar()
        self.regionType.set('circle')
        self.x = Tkinter.StringVar()
        self.y = Tkinter.StringVar()
        self.r = Tkinter.StringVar()
        self.x1 = Tkinter.StringVar()
        self.x2 = Tkinter.StringVar()
        self.y1 = Tkinter.StringVar()
        self.y2 = Tkinter.StringVar()
        self.regionEntryCircle = []
        self.regionEntryRect = []

        self.fromStr = Tkinter.StringVar()
        self.toStr = Tkinter.StringVar()

        self.containsMode = Tkinter.StringVar()
        self.containsMode.set('center')
        self.containsTimeMode = Tkinter.BooleanVar()

        self.messageStr = Tkinter.StringVar()
        self.useregexp = Tkinter.BooleanVar()

        choiceFrame = Tkinter.Frame(self)
        Tkinter.Radiobutton(choiceFrame, text='Use commands inserted in the data', variable=self.commandChoice, value='embedded', command=self.onClickChoiceRadiobutton).grid(row=0, column=0)
        Tkinter.Radiobutton(choiceFrame, text='Use following commands', variable=self.commandChoice, value='dialog', command=self.onClickChoiceRadiobutton).grid(row=0, column=1)
        choiceFrame.pack(fill=Tkinter.X)

        paramFrame = Tkinter.Frame(self)
        regionShapeFrame = Tkinter.LabelFrame(paramFrame, text='Region')
        r = 0
        Tkinter.Radiobutton(regionShapeFrame, text='Circle', variable=self.regionType, value='circle', command=self.onClickRegionRadiobutton).grid(row=r, column=0, columnspan=2, sticky=Tkinter.W)
        r += 1
        Tkinter.Label(regionShapeFrame, text='x').grid(row=r, column=0)
        Tkinter.Label(regionShapeFrame, text='y').grid(row=r, column=2)
        Tkinter.Label(regionShapeFrame, text='r').grid(row=r, column=4)
        self.regionEntryCircle.append(Tkinter.Entry(regionShapeFrame, textvariable=self.x, width=6))
        self.regionEntryCircle.append(Tkinter.Entry(regionShapeFrame, textvariable=self.y, width=6))
        self.regionEntryCircle.append(Tkinter.Entry(regionShapeFrame, textvariable=self.r, width=6))
        for i in range(3):
            self.regionEntryCircle[i].grid(row=r, column=2*i+1)
        r += 1
        Tkinter.Radiobutton(regionShapeFrame, text='Rectangle', variable=self.regionType, value='rect', command=self.onClickRegionRadiobutton).grid(row=r, column=0, columnspan=2, sticky=Tkinter.W)
        r += 1
        Tkinter.Label(regionShapeFrame, text='x1').grid(row=r, column=0)
        Tkinter.Label(regionShapeFrame, text='x2').grid(row=r, column=2)
        Tkinter.Label(regionShapeFrame, text='y1').grid(row=r, column=4)
        Tkinter.Label(regionShapeFrame, text='y2').grid(row=r, column=6)
        self.regionEntryRect.append(Tkinter.Entry(regionShapeFrame, textvariable=self.x1, width=6))
        self.regionEntryRect.append(Tkinter.Entry(regionShapeFrame, textvariable=self.x2, width=6))
        self.regionEntryRect.append(Tkinter.Entry(regionShapeFrame, textvariable=self.y1, width=6))
        self.regionEntryRect.append(Tkinter.Entry(regionShapeFrame, textvariable=self.y2, width=6))
        for i in range(4):
            self.regionEntryRect[i].grid(row=r, column=2*i+1)
        regionShapeFrame.pack(fill=Tkinter.X)

        timeFrame = Tkinter.LabelFrame(paramFrame, text='Time')
        r = 0
        Tkinter.Label(timeFrame, text='From (empty=beginning of trial)').grid(row=r, column=0)
        Tkinter.Entry(timeFrame, textvariable=self.fromStr).grid(row=r, column=1)
        r += 1
        Tkinter.Label(timeFrame, text='To (empty=end of trial)').grid(row=r, column=0)
        Tkinter.Entry(timeFrame, textvariable=self.toStr).grid(row=r, column=1)
        timeFrame.pack(fill=Tkinter.X)

        optspatialFrame = Tkinter.LabelFrame(paramFrame, text='Inclusion criteria (spatial)')
        r = 0
        Tkinter.Radiobutton(optspatialFrame, text='The center of fixation is included in the region', variable=self.containsMode, value='center').grid(row=r, column=0, sticky=Tkinter.W)
        r += 1
        Tkinter.Radiobutton(optspatialFrame, text='Whole trajectory of fixation is included in the region', variable=self.containsMode, value='all').grid(row=r, column=0, sticky=Tkinter.W)
        r += 1
        Tkinter.Radiobutton(optspatialFrame, text='A part of trajectory of fixation is included in the region', variable=self.containsMode, value='any').grid(row=r, column=0, sticky=Tkinter.W)
        optspatialFrame.pack(fill=Tkinter.X)

        opttimeFrame = Tkinter.LabelFrame(paramFrame, text='Inclusion criteria (temporal)')
        Tkinter.Checkbutton(opttimeFrame, text='Whole fixation must be included beween "From" and "To"', variable=self.containsTimeMode).grid(row=r, column=0)
        opttimeFrame.pack(fill=Tkinter.X)

        messageFrame = Tkinter.Frame(paramFrame)
        Tkinter.Label(messageFrame, text='Only trials including this message:').grid(row=0, column=0)
        Tkinter.Entry(messageFrame, textvariable=self.messageStr).grid(row=0, column=1)
        Tkinter.Checkbutton(messageFrame, text='Regular expression', variable=self.useregexp).grid(row=0, column=2)
        messageFrame.pack(fill=Tkinter.X)

        paramFrame.pack()
        self.paramFrameList = [regionShapeFrame, timeFrame, optspatialFrame, opttimeFrame, messageFrame]

        self.onClickChoiceRadiobutton()

        Tkinter.Button(self, text='Search', command=self.calc).pack()

        self.pack()

    def onClickChoiceRadiobutton(self, event=None):
        if self.commandChoice.get() == 'embedded':
            for childFrame in self.paramFrameList:
                for child in childFrame.winfo_children():
                    try:
                        child.configure(state='disabled')
                    except:
                        pass
        else:
            for childFrame in self.paramFrameList:
                for child in childFrame.winfo_children():
                    try:
                        child.configure(state='normal')
                    except:
                        pass
            self.onClickRegionRadiobutton()

    def onClickRegionRadiobutton(self, event=None):
        if self.regionType.get() == 'circle':
            for e in self.regionEntryCircle:
                e.configure(state='normal')
            for e in self.regionEntryRect:
                e.configure(state='disabled')
        else:
            for e in self.regionEntryCircle:
                e.configure(state='disabled')
            for e in self.regionEntryRect:
                e.configure(state='normal')

    def calc(self, event=None):
        if self.commandChoice.get() == 'embedded':
            sep = ' '

            data = []
            labels = []
            nFixList = []
            nTrial = 0
            for tr in range(len(self.D)):
                msglist = self.D[tr].findMessage('!FIXINREGION', useRegexp=False)
                if len(msglist) > 0:
                    fixlistTrial = []
                    labelsTrial = []
                    for msg in msglist:
                        commands = msg.text.split(sep)
                        period = [0, 0]
                        try:
                            label = commands[1]
                            try:
                                period[0] = float(commands[2])
                            except:  # label
                                if commands[2] == '!BEGINNING':
                                    period[0] = None
                                else:
                                    period[0] = self.D[tr].findMessage(commands[2])[0].time
                            try:
                                period[1] = float(commands[3])
                            except:  # label
                                if commands[3] == '!END':
                                    period[1] = None
                                else:
                                    period[1] = self.D[tr].findMessage(commands[3])[0].time
                            regiontype = commands[4]
                            if regiontype == 'CIRCLE':
                                region = GazeParser.Region.CircleRegion(float(commands[5]),
                                                                        float(commands[6]),
                                                                        float(commands[7]))
                                pi = 8
                            elif regiontype == 'RECT':
                                region = GazeParser.Region.RectRegion(float(commands[5]),
                                                                      float(commands[6]),
                                                                      float(commands[7]),
                                                                      float(commands[8]))
                                pi = 9

                            if len(commands) > pi:
                                useCenter = True if commands[pi].lower() == 'true' else False
                                containsTime = commands[pi+1]
                                containsTraj = commands[pi+2]
                            else:
                                useCenter = True
                                containsTime = 'all'
                                containsTraj = 'all'

                            # print region, period, useCenter, containsTime, containsTraj

                            fixlist = GazeParser.Region.getFixationsInRegion(self.D[tr], region, period, useCenter, containsTime, containsTraj)
                            fixlistTrial.extend(fixlist)
                            labelsTrial.extend([label]*len(fixlist))
                        except:
                            info = sys.exc_info()
                            tbinfo = traceback.format_tb(info[2])
                            errormsg = ''
                            for tbi in tbinfo:
                                errormsg += tbi
                            errormsg += '  %s' % str(info[1])
                            tkMessageBox.showerror('Error', msg.text+'\n\n'+errormsg)
                    data.append(fixlistTrial)
                    labels.append(labelsTrial)
                    nFixList.append(len(fixlistTrial))
                    nTrial += 1
                else:
                    data.append([])
                    labels.append([])
                    nFixList.append(0)

        else:  # use dualog parameters
            if self.regionType.get() == 'circle':
                try:
                    x = float(self.x.get())
                    y = float(self.y.get())
                    r = float(self.r.get())
                except:
                    tkMessageBox.showerror('Error', 'non-float values in x, y, and/or r')
                    return

                region = GazeParser.Region.CircleRegion(x, y, r)

            else:  # rect
                try:
                    x1 = float(self.x1.get())
                    x2 = float(self.x2.get())
                    y1 = float(self.y1.get())
                    y2 = float(self.y2.get())
                except:
                    tkMessageBox.showerror('Error', 'non-float values in x1, x2, y1 and/or y2')
                    return

                region = GazeParser.Region.RectRegion(x1, x2, y1, y2)

            period = [None, None]

            fromStr = self.fromStr.get()
            toStr = self.toStr.get()
            try:
                if fromStr != '':
                    period[0] = float(fromStr)
                if toStr != '':
                    period[1] = float(toStr)
            except:
                tkMessageBox.showerror('Error', 'From and To must be empty or float value.')
                return

            if self.containsTimeMode.get():
                containsTime = 'all'
            else:
                containsTime = 'any'

            containsTraj = self.containsMode.get()
            if containsTraj == 'center':
                useCenter = True
                containsTraj = 'all'  # any is also OK.
            else:
                useCenter = False

            msg = self.messageStr.get()
            useregexp = self.useregexp.get()

            data = []
            labels = []
            nFixList = []
            nTrial = 0
            for tr in range(len(self.D)):
                if msg != '' and self.D[tr].findMessage(msg, useRegexp=useregexp) == []:
                    data.append([])
                    labels.append([])
                    nFixList.append(0)
                    continue
                fixlist = GazeParser.Region.getFixationsInRegion(self.D[tr], region, period, useCenter, containsTime, containsTraj)
                data.append(fixlist)
                labels.append([msg]*len(fixlist))  # generate a list of msg
                nFixList.append(len(fixlist))
                nTrial += 1

        # output data
        ans = tkMessageBox.askyesno('Info', '%d fixations are found in %d trials.\nExport data?' % (numpy.sum(nFixList), nTrial))
        if ans:
            fname = tkFileDialog.asksaveasfilename(initialdir=self.initialDataDir)
            if fname != '':
                fp = open(fname, 'w')
                fp.write('Trial\tLabel\tStarting\tFinish\tDuration\tCenterX\tCenterY\n')
                for i in range(len(data)):
                    for fi in range(len(data[i])):
                        fp.write('%d\t%s\t%.1f\t%.1f\t%.1f\t%.2f\t%.2f\n' % (i, labels[i][fi],
                                                                             data[i][fi].startTime,
                                                                             data[i][fi].endTime,
                                                                             data[i][fi].duration,
                                                                             data[i][fi].center[0],
                                                                             data[i][fi].center[1]))
                fp.close()
                tkMessageBox.showinfo('Info', 'Done.')
            else:
                tkMessageBox.showinfo('Info', 'Canceled.')


class combineDataFileWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
        self.mainWindow = mainWindow

        listboxFrame = Tkinter.Frame(self)
        self.yscroll = Tkinter.Scrollbar(listboxFrame, orient=Tkinter.VERTICAL)
        self.filelistbox = Tkinter.Listbox(master=listboxFrame, yscrollcommand=self.yscroll.set, width=96)
        self.filelistbox.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        self.yscroll.pack(side=Tkinter.LEFT, anchor=Tkinter.W, fill=Tkinter.Y, expand=False)
        self.yscroll['command'] = self.filelistbox.yview
        updownButtonFrame = Tkinter.Frame(listboxFrame)
        Tkinter.Button(updownButtonFrame, text='up', command=self.up).pack(side=Tkinter.TOP, fill=Tkinter.BOTH)
        Tkinter.Button(updownButtonFrame, text='down', command=self.down).pack(side=Tkinter.TOP, fill=Tkinter.BOTH)
        Tkinter.Button(updownButtonFrame, text='add files', command=self.addfiles).pack(side=Tkinter.TOP, fill=Tkinter.BOTH, pady=3)
        Tkinter.Button(updownButtonFrame, text='remove selected', command=self.removefiles).pack(side=Tkinter.TOP, fill=Tkinter.BOTH, pady=3)
        Tkinter.Button(updownButtonFrame, text='remove all', command=self.removeAll).pack(side=Tkinter.TOP, fill=Tkinter.BOTH, pady=3)
        Tkinter.Button(updownButtonFrame, text='combine & save', command=self.combine).pack(side=Tkinter.TOP, fill=Tkinter.BOTH)
        updownButtonFrame.pack(side=Tkinter.LEFT, fill=Tkinter.Y)
        listboxFrame.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)

        if self.mainWindow.D is not None:
            self.filelistbox.insert(Tkinter.END, 'Current Data (' + self.mainWindow.dataFileName + ')')

        self.pack()

    def up(self, event=None):
        selected = self.filelistbox.curselection()
        if len(selected) > 0:
            index = int(selected[0])
            if index == 0:
                return
            item = self.filelistbox.get(index)
            self.filelistbox.delete(index)
            self.filelistbox.insert(index-1, item)
            self.filelistbox.selection_set(index-1)

    def down(self, event=None):
        selected = self.filelistbox.curselection()
        if len(selected) > 0:
            index = int(selected[0])
            if index >= self.filelistbox.size()-1:
                return
            item = self.filelistbox.get(index)
            self.filelistbox.delete(index)
            self.filelistbox.insert(index+1, item)
            self.filelistbox.selection_set(index+1)

    def addfiles(self, event=None):
        fnames = tkFileDialog.askopenfilenames(filetypes=self.mainWindow.datafiletype, initialdir=self.mainWindow.initialDataDir)
        if fnames == '':
            return

        if isinstance(fnames, unicode):
            fnames = GazeParser.Utility.splitFilenames(fnames)

        self.mainWindow.initialDataDir = os.path.split(fnames[0])[0]

        for fname in fnames:
            self.filelistbox.insert(Tkinter.END, fname)

    def removefiles(self, event=None):
        selected = self.filelistbox.curselection()
        # print self.filelistbox.size(), selected[0]
        if len(selected) > 0:
            self.filelistbox.delete(selected)
            # print self.filelistbox.size(), selected[0]
            if self.filelistbox.size() <= int(selected[0]):
                # print 'select '+selected[0]+'-1'
                self.filelistbox.selection_set(int(selected[0])-1)
            else:
                # print 'select '+selected[0]
                self.filelistbox.selection_set(selected)
        else:
            tkMessageBox.showinfo('Info', 'Select files to delete.')

    def removeAll(self, event=None):
        if self.filelistbox.size() > 0:
            self.filelistbox.delete(0, Tkinter.END)

    def combine(self, event=None):
        if self.filelistbox.size() <= 1:
            tkMessageBox.showinfo('Info', 'At least two data files must be added.')
            return
        fnames = list(self.filelistbox.get(0, Tkinter.END))
        for index in range(len(fnames)):
            if fnames[index][:14] == 'Current Data (':
                fnames[index] = fnames[index][14:-1]

        combinedFilename = tkFileDialog.asksaveasfilename(filetypes=self.mainWindow.datafiletype, initialdir=self.mainWindow.initialDataDir)
        if combinedFilename == '':
            return

        self.mainWindow.initialDataDir = os.path.split(combinedFilename)[0]

        try:
            GazeParser.Utility.join(combinedFilename, fnames)
        except:
            info = sys.exc_info()
            tbinfo = traceback.format_tb(info[2])
            errormsg = ''
            for tbi in tbinfo:
                errormsg += tbi
            errormsg += '  %s' % str(info[1])
            tkMessageBox.showerror('Error', errormsg)
        else:
            tkMessageBox.showinfo('Info', 'Done')


class configStimImageWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
        self.mainWindow = mainWindow

        self.stimImagePrefix = Tkinter.StringVar()
        self.stimImagePrefix.set(self.mainWindow.conf.COMMAND_STIMIMAGE_PATH)

        r = 0
        Tkinter.Label(self, text='StimImage Prefix').grid(row=r, column=0)
        Tkinter.Entry(self, textvariable=self.stimImagePrefix).grid(row=r, column=1)

        r += 1
        Tkinter.Button(self, text='OK', command=self.setValues).grid(row=r, column=0, columnspan=2)

        self.pack()

    def setValues(self, event=None):
        self.mainWindow.conf.COMMAND_STIMIMAGE_PATH = self.stimImagePrefix.get()
        self.mainWindow._loadStimImage()
        self.mainWindow._plotData()

        self.master.destroy()


class fontSelectWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
        self.mainWindow = mainWindow

        self.fontnamelist = []
        self.fontfilelist = []

        if sys.platform == 'win32':
            fontdir = matplotlib.font_manager.win32FontDirectory()
            for fname in os.listdir(fontdir):
                if os.path.splitext(fname)[1].lower() in ['.ttc', '.ttf']:
                    fontprop = matplotlib.font_manager.FontProperties(fname=os.path.join(fontdir, fname))
                    fontname = fontprop.get_name()
                    if fontname not in self.fontnamelist:
                        self.fontnamelist.append(fontname)
                        self.fontfilelist.append(os.path.join(fontdir, fname))
        else:  # linux(?)
            if sys.platform == 'darwin':
                fontdirs = matplotlib.font_manager.OSXFontDirectories
            else:
                fontdirs = matplotlib.font_manager.X11FontDirectories
            for fontdir in fontdirs:
                for dpath, dnames, fnames in os.walk(fontdir):
                    for fname in fnames:
                        if os.path.splitext(fname)[1].lower() in ['.ttc', '.ttf']:
                            fontprop = matplotlib.font_manager.FontProperties(fname=os.path.join(dpath, fname))
                            fontname = fontprop.get_name()
                            if fontname not in self.fontnamelist:
                                self.fontnamelist.append(fontname)
                                self.fontfilelist.append(os.path.join(dpath, fname))
        self.sortedIndex = numpy.argsort(self.fontnamelist)

        self.currentFontfile = Tkinter.Label(self, text='Current font:'+self.mainWindow.conf.CANVAS_FONT_FILE, anchor=Tkinter.W, width=96)
        listframe = Tkinter.Frame(self, bg='yellow')
        self.yscroll = Tkinter.Scrollbar(listframe, orient=Tkinter.VERTICAL)
        self.fontlistbox = Tkinter.Listbox(listframe, yscrollcommand=self.yscroll.set)
        self.yscroll['command'] = self.fontlistbox.yview
        self.sample = Tkinter.Label(listframe, text='ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789')
        self.fontlistbox.bind('<Button-1>', self.updateSample)

        for i in self.sortedIndex:
            self.fontlistbox.insert(Tkinter.END, self.fontnamelist[i])

        self.currentFontfile.pack(anchor=Tkinter.W, fill=Tkinter.X)
        self.fontlistbox.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH)
        self.yscroll.pack(side=Tkinter.LEFT, anchor=Tkinter.W, fill=Tkinter.Y)
        self.sample.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        listframe.pack(anchor=Tkinter.W, fill=Tkinter.BOTH, expand=True)

        buttonframe = Tkinter.Frame(self)
        Tkinter.Button(buttonframe, text='Use this font', command=self.setFont).grid(row=0, column=0)
        Tkinter.Button(buttonframe, text='Use default font', command=self.clearFont).grid(row=0, column=1)
        buttonframe.pack(anchor=Tkinter.W, fill=Tkinter.X, expand=True)

        self.pack()

    def updateSample(self, event=None):
        selected = self.fontlistbox.curselection()
        if len(selected) == 0:
            return
        i = int(selected[0])
        self.sample.configure(font=(self.fontnamelist[self.sortedIndex[i]], '12'))

    def setFont(self, event=None):
        selected = self.fontlistbox.curselection()
        if len(selected) == 0:
            tkMessageBox.showerror('Error', 'No font is selected')
            return
        i = int(selected[0])
        self.mainWindow.conf.CANVAS_FONT_FILE = self.fontfilelist[self.sortedIndex[i]]
        self.mainWindow.fontPlotText = matplotlib.font_manager.FontProperties(fname=self.mainWindow.conf.CANVAS_FONT_FILE)
        self.currentFontfile.configure(text='Current font:'+self.mainWindow.conf.CANVAS_FONT_FILE)
        if self.mainWindow.D is not None:
            self.mainWindow._plotData()

    def clearFont(self, event=None):
        self.mainWindow.conf.CANVAS_FONT_FILE = ''
        self.mainWindow.fontPlotText = matplotlib.font_manager.FontProperties()
        self.currentFontfile.configure(text='Current font:'+self.mainWindow.conf.CANVAS_FONT_FILE)
        if self.mainWindow.D is not None:
            self.mainWindow._plotData()


class insertNewMessageWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
        self.mainWindow = mainWindow

        self.time = Tkinter.StringVar()
        self.text = Tkinter.StringVar()

        r = 0
        Tkinter.Label(self, text='Time').grid(row=r, column=0)
        Tkinter.Entry(self, textvariable=self.time).grid(row=r, column=1)
        r += 1
        Tkinter.Label(self, text='Message').grid(row=r, column=0)
        Tkinter.Entry(self, textvariable=self.text).grid(row=r, column=1)
        r += 1
        Tkinter.Button(self, text='Insert', command=self.insert).grid(row=r, column=0, columnspan=2)

        self.pack()

    def insert(self, event=None):
        try:
            newTime = float(self.time.get())
        except:
            tkMessageBox.showerror('Error', 'Invalid time value')
            return

        newText = self.text.get()

        try:
            self.mainWindow.D[self.mainWindow.tr].insertNewMessage(newTime, newText)
        except:
            tkMessageBox.showerror('Error', 'Invalid time value')
            return

        self.mainWindow._updateMsgBox()
        self.mainWindow._loadStimImage()
        self.mainWindow._plotData()

        self.mainWindow.dataModified = True
        self.master.destroy()

        # tkMessageBox.showinfo('Info', 'Message is inserted.')


class editMessageWindow(Tkinter.Frame):
    def __init__(self, message, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
        self.mainWindow = mainWindow

        self.message = message
        currentTime = '%10.1f' % (message.time)
        if len(message.text) > 30:
            currentMessage = message.text[:27]+'...'
        else:
            currentMessage = message.text

        self.time = Tkinter.StringVar()
        self.text = Tkinter.StringVar()

        self.time.set(str(message.time))
        self.text.set(str(message.text))

        r = 0
        Tkinter.Label(self, text='Current').grid(row=r, column=1)
        Tkinter.Label(self, text='New').grid(row=r, column=2)
        r += 1
        Tkinter.Label(self, text='Time').grid(row=r, column=0)
        Tkinter.Label(self, text=currentTime, relief=Tkinter.RIDGE).grid(row=r, column=1, sticky=Tkinter.W+Tkinter.E)
        Tkinter.Entry(self, textvariable=self.time).grid(row=r, column=2)
        r += 1
        Tkinter.Label(self, text='Message').grid(row=r, column=0)
        Tkinter.Label(self, text=currentMessage, relief=Tkinter.RIDGE).grid(row=r, column=1, sticky=Tkinter.W+Tkinter.E)
        Tkinter.Entry(self, textvariable=self.text).grid(row=r, column=2)
        r += 1
        Tkinter.Button(self, text='Update', command=self.update).grid(row=r, column=0, columnspan=3)

        self.pack()

    def update(self, event=None):
        try:
            newTime = float(self.time.get())
        except:
            tkMessageBox.showerror('Error', 'Invalid time value')
            return

        newText = self.text.get()

        try:
            self.message.updateMessage(newTime, newText)
        except:
            tkMessageBox.showerror('Error', 'Message cannot be updated.\n\n'+str(newTime)+'\n'+newText)
            return

        self.mainWindow._updateMsgBox()
        self.mainWindow._loadStimImage()
        self.mainWindow._plotData()

        self.mainWindow.dataModified = True
        self.master.destroy()

        # tkMessageBox.showinfo('Info', 'Message is updated.')


class jumpToTrialWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
        self.mainWindow = mainWindow

        self.newtrStr = Tkinter.StringVar()
        Tkinter.Label(self, text='Jump to... (0-%s)' % (len(mainWindow.D)-1)).grid(row=0, column=0)
        Tkinter.Entry(self, textvariable=self.newtrStr).grid(row=0, column=1)

        Tkinter.Button(self, text='OK', command=self.jump).grid(row=1, column=0, columnspan=2)
        self.pack()

    def jump(self, event=None):
        try:
            newtr = int(self.newtrStr.get())
        except:
            tkMessageBox.showerror('Error', 'Value must be an integer')
            return

        if newtr < 0 or newtr >= len(self.mainWindow.D):
            tkMessageBox.showerror('Error', 'Invalid trial number')
            return

        self.mainWindow.tr = newtr
        if self.mainWindow.tr == 0:
            self.mainWindow.menu_view.entryconfigure('Prev Trial', state='disabled')
        else:
            self.mainWindow.menu_view.entryconfigure('Prev Trial', state='normal')
        if self.mainWindow.tr == len(self.mainWindow.D)-1:
            self.mainWindow.menu_view.entryconfigure('Next Trial', state='disabled')
        else:
            self.mainWindow.menu_view.entryconfigure('Next Trial', state='normal')
        self.mainWindow.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        self.mainWindow.selectiontype.set('Emphasize')
        self.mainWindow._plotData()
        self.mainWindow._updateMsgBox()


class exportToFileWindow(Tkinter.Frame):
    def __init__(self, data, additional, trial, master=None, initialdir=None):
        Tkinter.Frame.__init__(self, master)
        self.D = data
        self.tr = trial
        if initialdir is None:
            self.initialDataDir = GazeParser.homeDir
        else:
            self.initialDataDir = initialdir

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
        self.flgTrials.set('AllTrials')
        self.flgOrder.set('ByTime')

        itemFrame = Tkinter.LabelFrame(self, text='Check items to export.')
        itemFrame.grid(row=0, column=0)
        Tkinter.Checkbutton(itemFrame, text='Saccade', variable=self.flgSac).grid(row=0, column=0)
        Tkinter.Checkbutton(itemFrame, text='Fixation', variable=self.flgFix).grid(row=1, column=0)
        Tkinter.Checkbutton(itemFrame, text='Blink', variable=self.flgBlk).grid(row=0, column=1)
        Tkinter.Checkbutton(itemFrame, text='Message', variable=self.flgMsg).grid(row=1, column=1)

        trialFrame = Tkinter.LabelFrame(self, text='Range')
        trialFrame.grid(row=1, column=0)
        Tkinter.Radiobutton(trialFrame, text='This trial', variable=self.flgTrials, value='ThisTrial').grid(row=0, column=0)
        Tkinter.Radiobutton(trialFrame, text='All trials', variable=self.flgTrials, value='AllTrials').grid(row=0, column=1)

        groupFrame = Tkinter.LabelFrame(self, text='Grouping')
        groupFrame.grid(row=2, column=0)
        Tkinter.Radiobutton(groupFrame, text='By time', variable=self.flgOrder, value='ByTime').grid(row=0, column=0)
        Tkinter.Radiobutton(groupFrame, text='By events', variable=self.flgOrder, value='ByEvents').grid(row=0, column=1)

        Tkinter.Button(self, text='Export', command=self.export).grid(row=3, column=0)
        self.pack()

    def export(self, event=None):
        if self.flgSac.get() or self.flgFix.get() or self.flgBlk.get() or self.flgMsg.get():
            exportFileName = tkFileDialog.asksaveasfilename(initialdir=self.initialDataDir)
            fp = open(exportFileName, 'w')

            if self.flgOrder.get() == 'ByTime':
                if self.flgTrials.get() == 'ThisTrial':
                    trlist = [self.tr]
                else:  # AllTrials
                    trlist = range(len(self.D))
                for tr in trlist:
                    fp.write('TRIAL%d\n' % (tr+1))
                    for e in self.D[tr].EventList:
                        if isinstance(e, GazeParser.SaccadeData) and self.flgSac.get():
                            fp.write('SAC,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n' %
                                     (e.startTime, e.endTime, e.start[0], e.start[1], e.end[0], e.end[1]))
                        elif isinstance(e, GazeParser.FixationData) and self.flgFix.get():
                            fp.write('FIX,%.1f,%.1f,%.1f,%.1f\n' %
                                     (e.startTime, e.endTime, e.center[0], e.center[1]))
                        elif isinstance(e, GazeParser.MessageData) and self.flgMsg.get():
                            fp.write('MSG,%.1f,%.1f,%s\n' % (e.time, e.time, e.text))
                        elif isinstance(e, GazeParser.BlinkData) and self.flgBlk.get():
                            fp.write('BLK,%.1f,%.1f\n' % (e.startTime, e.endTime))

            else:  # ByEvents
                if self.flgTrials.get() == 'ThisTrial':
                    trlist = [self.tr]
                else:  # AllTrials
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
                                     (e.startTime, e.endTime, e.center[0], e.center[1]))
                    if self.flgMsg.get():
                        for e in self.D[tr].Msg:
                            fp.write('MSG,%.1f,%.1f,%s\n' % (e.time, e.time, e.text))
                    if self.flgBlk.get():
                        for e in self.D[tr].Blink:
                            fp.write('BLK,%.1f,%.1f\n' % (e.startTime, e.endTime))

            fp.close()

            tkMessageBox.showinfo('Info', 'Done.')

        else:
            tkMessageBox.showinfo('Info', 'No items were selected.')


class getSaccadeLatencyWindow(Tkinter.Frame):
    def __init__(self, data, additional, conf, master=None, initialdir=None):
        Tkinter.Frame.__init__(self, master)
        self.D = data
        self.C = additional
        self.conf = conf
        if initialdir is None:
            self.initialDataDir = GazeParser.homeDir
        else:
            self.initialDataDir = initialdir

        self.messageStr = Tkinter.StringVar()
        self.useRegexp = Tkinter.BooleanVar()
        self.minLatencyStr = Tkinter.StringVar()
        self.maxLatencyStr = Tkinter.StringVar()
        self.minAmplitudeStr = Tkinter.StringVar()
        self.maxAmplitudeStr = Tkinter.StringVar()
        self.amplitudeUnit = Tkinter.StringVar()
        self.amplitudeUnit.set('pix')

        # plot frame
        plotFrame = Tkinter.Frame(self)
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, master=plotFrame)
        self.ax = self.fig.add_axes([0.1, 0.1, 0.8, 0.8])
        self.canvas._tkcanvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)
        plotFrame.pack(side=Tkinter.LEFT)

        # parameter frame
        paramFrame = Tkinter.Frame(self)

        messageFrame = Tkinter.LabelFrame(paramFrame, text='Message')
        Tkinter.Entry(messageFrame, textvariable=self.messageStr).pack()
        Tkinter.Checkbutton(messageFrame, text='Regular expression', variable=self.useRegexp).pack()
        messageFrame.pack(fill=Tkinter.X)

        latencyFrame = Tkinter.LabelFrame(paramFrame, text='Latency')
        Tkinter.Label(latencyFrame, text='Min').grid(row=0, column=0)
        Tkinter.Entry(latencyFrame, textvariable=self.minLatencyStr).grid(row=0, column=1)
        Tkinter.Label(latencyFrame, text='Max').grid(row=1, column=0)
        Tkinter.Entry(latencyFrame, textvariable=self.maxLatencyStr).grid(row=1, column=1)
        latencyFrame.pack(fill=Tkinter.X)

        amplitudeFrame = Tkinter.LabelFrame(paramFrame, text='Amplitude')
        Tkinter.Label(amplitudeFrame, text='Min').grid(row=0, column=0)
        Tkinter.Entry(amplitudeFrame, textvariable=self.minAmplitudeStr).grid(row=0, column=1)
        Tkinter.Label(amplitudeFrame, text='Max').grid(row=1, column=0)
        Tkinter.Entry(amplitudeFrame, textvariable=self.maxAmplitudeStr).grid(row=1, column=1)
        Tkinter.Radiobutton(amplitudeFrame, text='deg', variable=self.amplitudeUnit, value='deg').grid(row=2, column=1)
        Tkinter.Radiobutton(amplitudeFrame, text='pix', variable=self.amplitudeUnit, value='pix').grid(row=3, column=1)
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
            tkMessageBox.showerror('Error', 'Invalid values are found in amplitude/latency.')
        for value in (minamp, maxamp, minlat, maxlat):
            if value is not None and value < 0:
                tkMessageBox.showerror('Error', 'latency and amplitude must be zero or positive.')
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
                if sac is not None:  # no saccade
                    while True:
                        tmplatency = sac.relativeStartTime(self.D[tr].Msg[msgidx])
                        if self.amplitudeUnit.get() == 'deg':
                            tmpamplitude = sac.amplitude
                        else:
                            tmpamplitude = sac.length
                        if (minamp is None or minamp <= tmpamplitude) and (maxamp is None or maxamp >= tmpamplitude) and \
                           (minlat is None or minlat <= tmplatency) and (maxlat is None or maxlat >= tmplatency):
                            isSaccadeFound = True
                            break
                        sac = sac.getNextEvent(eventType='saccade')
                        if sac is None:
                            break
                if isSaccadeFound:
                    nSac += 1
                    trdata.append([tr, self.D[tr].Msg[msgidx].time, self.D[tr].Msg[msgidx].text])
                    sacdata.append([tmplatency, tmpamplitude])

        if nMsg > 0:
            if nSac > 0:
                self.ax.clear()
                latdata = numpy.array(sacdata)[:, 0]
                self.ax.hist(latdata)
                self.fig.canvas.draw()
                ans = tkMessageBox.askyesno('Export', '%d saccades/%d messages(%.1f%%).\nExport data?' % (nSac, nMsg, (100.0*nSac)/nMsg))
                if ans:
                    fname = tkFileDialog.asksaveasfilename(initialdir=self.initialDataDir)
                    if fname != '':
                        fp = open(fname, 'w')
                        fp.write('Trial\tMessageTime\tMessageText\tLatency\tAmplitude\n')
                        for n in range(nSac):
                            fp.write('%d\t%.2f\t%s\t' % tuple(trdata[n]))
                            fp.write('%.2f\t%.2f\n' % tuple(sacdata[n]))
                        fp.close()
                        tkMessageBox.showinfo('Info', 'Done.')
                    else:
                        tkMessageBox.showinfo('Info', 'Canceled.')
            else:
                tkMessageBox.showinfo('Info', 'No saccades are detected')
        else:
            tkMessageBox.showinfo('Info', 'No messages are found')


def getComplementaryColorStr(col):
    """
    get complementary color (e.g. '#00FF88' -> '#FF0077'
    """
    return '#'+hex(16777215-int(col[1:], base=16))[2:].upper()


def getTextColor(backgroundColor, thresh=0.3):
    minc = min(int(backgroundColor[1:3], base=16), int(backgroundColor[3:5], base=16), int(backgroundColor[5:7], base=16))
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
         [['VIEWER_VERSION', str]]],
        ['Appearance',
         [['CANVAS_WIDTH', int],
          ['CANVAS_HEIGHT', int],
          ['CANVAS_DEFAULT_VIEW', str],
          ['CANVAS_SHOW_FIXNUMBER', bool],
          ['CANVAS_SHOW_STIMIMAGE', bool],
          ['CANVAS_FONT_FILE', str],
          ['CANVAS_XYAXES_UNIT', str],
          ['CANVAS_GRID_ABSCISSA_XY', str],
          ['CANVAS_GRID_ORDINATE_XY', str],
          ['CANVAS_GRID_ABSCISSA_XYT', str],
          ['CANVAS_GRID_ORDINATE_XYT', str],
          ['COLOR_TRAJECTORY_L_SAC', str],
          ['COLOR_TRAJECTORY_R_SAC', str],
          ['COLOR_TRAJECTORY_L_FIX', str],
          ['COLOR_TRAJECTORY_R_FIX', str],
          ['COLOR_TRAJECTORY_L_X', str],
          ['COLOR_TRAJECTORY_L_Y', str],
          ['COLOR_TRAJECTORY_R_X', str],
          ['COLOR_TRAJECTORY_R_Y', str],
          ['COLOR_FIXATION_FC', str],
          ['COLOR_FIXATION_BG', str],
          ['COLOR_FIXATION_FC_E', str],
          ['COLOR_FIXATION_BG_E', str],
          ['COLOR_SACCADE_HATCH', str],
          ['COLOR_SACCADE_HATCH_E', str],
          ['COLOR_BLINK_HATCH', str],
          ['COLOR_MESSAGE_CURSOR', str],
          ['COLOR_MESSAGE_FC', str],
          ['COLOR_MESSAGE_BG', str]]],
        ['Command',
         [['COMMAND_SEPARATOR', str],
          ['COMMAND_STIMIMAGE_PATH', str]]],
        ['Recent',
         [['RECENT_DIR01', str],
          ['RECENT_DIR02', str],
          ['RECENT_DIR03', str],
          ['RECENT_DIR04', str],
          ['RECENT_DIR05', str]]]
    ]

    def __init__(self):
        initialConfigFile = os.path.join(os.path.dirname(__file__), 'viewer.cfg')
        appConfigDir = os.path.join(GazeParser.configDir, 'app')
        if not os.path.isdir(appConfigDir):
            os.mkdir(appConfigDir)

        self.viewerConfigFile = os.path.join(appConfigDir, 'viewer.cfg')
        if not os.path.isfile(self.viewerConfigFile):
            shutil.copyfile(initialConfigFile, self.viewerConfigFile)

        appConf = ConfigParser.SafeConfigParser()
        appConf.optionxform = str
        appConf.read(self.viewerConfigFile)

        try:
            self.VIEWER_VERSION = appConf.get('Version', 'VIEWER_VERSION')
        except:
            ans = tkMessageBox.askyesno('Error', 'No VIEWER_VERSION option in configuration file (%s). Backup current file and then initialize configuration file?\n' % (self.viewerConfigFile))
            if ans:
                shutil.copyfile(self.viewerConfigFile, self.viewerConfigFile+'.bak')
                shutil.copyfile(initialConfigFile, self.viewerConfigFile)
                appConf = ConfigParser.SafeConfigParser()
                appConf.optionxform = str
                appConf.read(self.viewerConfigFile)
                self.VIEWER_VERSION = appConf.get('Version', 'VIEWER_VERSION')
            else:
                tkMessageBox.showinfo('info', 'Please correct configuration file manually.')
                sys.exit()

        doMerge = False
        if self.VIEWER_VERSION != GazeParser.__version__:
            ans = tkMessageBox.askyesno('Warning', 'VIEWER_VERSION of configuration file (%s) disagree with GazeParser version (%s). Backup current configuration file and build new configuration file?' % (self.VIEWER_VERSION, GazeParser.__version__))
            if ans:
                shutil.copyfile(self.viewerConfigFile, self.viewerConfigFile+'.bak')
                doMerge = True
            else:
                tkMessageBox.showinfo('info', 'Please update configuration file manually.')
                sys.exit()

        if doMerge:
            appNewConf = ConfigParser.SafeConfigParser()
            appNewConf.optionxform = str
            appNewConf.read(initialConfigFile)
            newOpts = []
            for section, params in self.options:
                for optName, optType in params:
                    if section == 'Version' and optName == 'VIEWER_VERSION':
                        setattr(self, optName, optType(appNewConf.get(section, optName)))
                        newOpts.append(' * '+optName)
                    elif appConf.has_option(section, optName):
                        setattr(self, optName, optType(appConf.get(section, optName)))
                    else:
                        setattr(self, optName, optType(appNewConf.get(section, optName)))
                        newOpts.append(' * '+optName)
            # new version number
            tkMessageBox.showinfo('info', 'Added:\n'+'\n'.join(newOpts))

        else:
            for section, params in self.options:
                for optName, optType in params:
                    setattr(self, optName, optType(appConf.get(section, optName)))

        # set recent directories
        self.RecentDir = []
        for i in range(5):
            d = getattr(self, 'RECENT_DIR%02d' % (i+1))
            if d != '':
                self.RecentDir.append(d)

    def _write(self):
        # set recent directories
        for i in range(5):
            if i < len(self.RecentDir):
                setattr(self, 'RECENT_DIR%02d' % (i+1), self.RecentDir[i])
            else:
                setattr(self, 'RECENT_DIR%02d' % (i+1), '')

        with open(self.viewerConfigFile, 'w') as fp:
            for section, params in self.options:
                fp.write('[%s]\n' % section)
                for optName, optType in params:
                    fp.write('%s = %s\n' % (optName, getattr(self, optName)))
                fp.write('\n')


class configColorWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
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
                    self.origColorDict[name] = getattr(mainWindow.conf, name)
                    self.newColorDict[name] = getattr(mainWindow.conf, name)
                    Tkinter.Label(self, text=name).grid(row=r, column=0)
                    self.buttonDict[name] = Tkinter.Button(self, text=self.newColorDict[name],
                                                           command=functools.partial(self._chooseColor, name=name),
                                                           bg=self.newColorDict[name], fg=getTextColor(self.newColorDict[name]))
                    self.buttonDict[name].grid(row=r, column=1, sticky=Tkinter.W + Tkinter.E)
                    r += 1
        Tkinter.Button(self, text='Update plot', command=self._updatePlot).grid(row=r, column=0)
        Tkinter.Button(self, text='Reset', command=self._resetColor).grid(row=r, column=1)
        self.pack()

    def _chooseColor(self, name):
        ret = tkColorChooser.askcolor()
        if ret[1] is not None:
            self.newColorDict[name] = ret[1].upper()
            self.buttonDict[name].config(text=self.newColorDict[name], bg=self.newColorDict[name], fg=getTextColor(self.newColorDict[name]))

    def _updatePlot(self, event=None):
        for name in self.newColorDict.keys():
            setattr(self.mainWindow.conf, name, self.newColorDict[name])
        self.mainWindow._plotData()

    def _resetColor(self, event=None):
        for name in self.origColorDict.keys():
            setattr(self.mainWindow.conf, name, self.origColorDict[name])
            self.newColorDict[name] = self.origColorDict[name]
            self.buttonDict[name].config(text=self.origColorDict[name], bg=self.origColorDict[name])


class plotRangeWindow(Tkinter.Frame):
    """
    .. deprecated:: 0.6.1
    """
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
        self.currentPlotArea = mainWindow.currentPlotArea
        self.ax = mainWindow.ax
        self.fig = mainWindow.fig

        self.strings = [Tkinter.StringVar() for i in range(4)]
        labels = ['Abcissa Min', 'Abcissa Max', 'Ordinate Min', 'Ordinate Max']
        Tkinter.Label(self, text='Current View (unit=pix)').grid(row=0, column=0, columnspan=2)
        for i in range(4):
            self.strings[i].set(str(self.currentPlotArea[i]))
            Tkinter.Label(self, text=labels[i]).grid(row=i+1, column=0)
            Tkinter.Entry(self, textvariable=self.strings[i]).grid(row=i+1, column=1)
        Tkinter.Button(self, text='Update plot', command=self._updatePlot).grid(row=5, column=0, columnspan=2)
        self.pack()

    def _updatePlot(self, event=None):
        tmpPlotArea = [0, 0, 0, 0]
        try:
            for i in range(4):
                tmpPlotArea[i] = float(self.strings[i].get())

            for i in range(4):
                self.currentPlotArea[i] = tmpPlotArea[i]

            self.ax.axis(self.currentPlotArea)
            self.fig.canvas.draw()
        except:
            tkMessageBox.showinfo('Error', 'Illeagal values')


class configGridWindow(Tkinter.Frame):
    def __init__(self, mainWindow, master=None):
        Tkinter.Frame.__init__(self, master)
        self.mainWindow = mainWindow
        self.choiceAbscissa = Tkinter.StringVar()
        self.choiceOrdinate = Tkinter.StringVar()
        self.strAbscissa = Tkinter.StringVar()
        self.strOrdinate = Tkinter.StringVar()

        if self.mainWindow.plotStyle in XYPLOTMODES:
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
        Tkinter.Radiobutton(xframe, text='No grid', variable=self.choiceAbscissa, value='NOGRID', command=self._onClickRadiobuttons).grid(row=0, column=0)
        Tkinter.Radiobutton(xframe, text='Show grid on current ticks', variable=self.choiceAbscissa, value='CURRENT', command=self._onClickRadiobuttons).grid(row=0, column=1)
        Tkinter.Radiobutton(xframe, text='Set interval ticks', variable=self.choiceAbscissa, value='INTERVAL', command=self._onClickRadiobuttons).grid(row=0, column=2)
        Tkinter.Radiobutton(xframe, text='Set custom ticks', variable=self.choiceAbscissa, value='CUSTOM', command=self._onClickRadiobuttons).grid(row=0, column=3)
        self.abscissaEntry = Tkinter.Entry(xframe, textvariable=self.strAbscissa)
        self.abscissaEntry.grid(row=1, column=0, columnspan=4, sticky=Tkinter.W+Tkinter.E)
        xframe.pack()

        yframe = Tkinter.LabelFrame(self, text='Ordinate')
        Tkinter.Radiobutton(yframe, text='No grid', variable=self.choiceOrdinate, value='NOGRID', command=self._onClickRadiobuttons).grid(row=0, column=0)
        Tkinter.Radiobutton(yframe, text='Show grid on current ticks', variable=self.choiceOrdinate, value='CURRENT', command=self._onClickRadiobuttons).grid(row=0, column=1)
        Tkinter.Radiobutton(yframe, text='Set interval ticks', variable=self.choiceOrdinate, value='INTERVAL', command=self._onClickRadiobuttons).grid(row=0, column=2)
        Tkinter.Radiobutton(yframe, text='Set custom ticks', variable=self.choiceOrdinate, value='CUSTOM', command=self._onClickRadiobuttons).grid(row=0, column=3)
        self.ordinateEntry = Tkinter.Entry(yframe, textvariable=self.strOrdinate)
        self.ordinateEntry.grid(row=1, column=0, columnspan=4, sticky=Tkinter.W+Tkinter.E)
        yframe.pack()

        Tkinter.Button(self, text='Update plot', command=self._updatePlot).pack()

        self._onClickRadiobuttons()

        self.pack()

    def _onClickRadiobuttons(self, event=None):
        gridtype = self.choiceAbscissa.get()
        if gridtype == 'NOGRID' or gridtype == 'CURRENT':
            self.abscissaEntry.configure(state='disabled')
        else:
            self.abscissaEntry.configure(state='normal')

        gridtype = self.choiceOrdinate.get()
        if gridtype == 'NOGRID' or gridtype == 'CURRENT':
            self.ordinateEntry.configure(state='disabled')
        else:
            self.ordinateEntry.configure(state='normal')

    def _updatePlot(self, event=None):
        gridtypeX = self.choiceAbscissa.get()
        gridtypeY = self.choiceOrdinate.get()
        if gridtypeX == 'NOGRID':
            xstr = 'NOGRID'
        elif gridtypeX == 'CURRENT':
            xstr = 'CURRENT'
        elif gridtypeX == 'INTERVAL':
            xstr = 'INTERVAL#'+self.abscissaEntry.get()
        elif gridtypeX == 'CUSTOM':
            xstr = 'CUSTOM#'+self.abscissaEntry.get()
        else:
            raise ValueError('Unknown abscissa grid type (%s)' % (gridtypeX))

        if gridtypeY == 'NOGRID':
            ystr = 'NOGRID'
        elif gridtypeY == 'CURRENT':
            ystr = 'CURRENT'
        elif gridtypeY == 'INTERVAL':
            ystr = 'INTERVAL#'+self.ordinateEntry.get()
        elif gridtypeY == 'CUSTOM':
            ystr = 'CUSTOM#'+self.ordinateEntry.get()
        else:
            raise(ValueError, 'Unknown ordinate grid type (%s)' % (gridtypeY))

        if self.mainWindow.plotStyle in XYPLOTMODES:
            self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XY = xstr
            self.mainWindow.conf.CANVAS_GRID_ORDINATE_XY = ystr
        else:
            self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XYT = xstr
            self.mainWindow.conf.CANVAS_GRID_ORDINATE_XYT = ystr

        self.mainWindow._updateGrid()
        self.mainWindow.fig.canvas.draw()


class InteractiveConfig(Tkinter.Frame):
    def __init__(self, data, additional, conf, master=None):
        self.configtypes = [('GazeParser Configuration File', '*.cfg')]
        if data is None:
            tkMessageBox.showerror('Error', 'No data')
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
        else:  # assume 'bottomleft'
            ymin = 0
            ymax = max(self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT)

        self.currentPlotArea = [0, 3000, ymin, ymax]

        Tkinter.Frame.__init__(self, master)
        self.master.title('Interactive configuration')
        menu_bar = Tkinter.Menu(tearoff=False)
        menu_file = Tkinter.Menu(tearoff=False)
        self.menu_view = Tkinter.Menu(tearoff=False)
        menu_bar.add_cascade(label='File', menu=menu_file, underline=0)
        menu_bar.add_cascade(label='View', menu=self.menu_view, underline=0)
        menu_file.add_command(label='Export Config', under=0, command=self._exportConfig)
        menu_file.add_command(label='Close', under=0, command=self._close)
        self.menu_view.add_command(label='Prev Trial', under=0, command=self._prevTrial)
        self.menu_view.add_command(label='Next Trial', under=0, command=self._nextTrial)
        self.master.configure(menu=menu_bar)

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

        toolbar = NavigationToolbar2TkAgg(self.canvas, self.viewFrame)
        toolbar.pack(side=Tkinter.TOP)
        self.viewFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)

        self.newParamStringsDict = {}
        self.paramFrame = Tkinter.Frame(self.mainFrame, bd=3, relief='groove')  # subFrame
        r = 0
        Tkinter.Label(self.paramFrame, text='Original').grid(row=r, column=1)
        Tkinter.Label(self.paramFrame, text='New').grid(row=r, column=2)
        for key in GazeParser.Configuration.GazeParserOptions:
            r += 1
            Tkinter.Label(self.paramFrame, text=key).grid(row=r, column=0, sticky=Tkinter.W)
            self.newParamStringsDict[key] = Tkinter.StringVar()
            if hasattr(self.D[self.tr].config, key):
                self.newParamStringsDict[key].set(getattr(self.D[self.tr].config, key))
                Tkinter.Label(self.paramFrame, text=str(getattr(self.D[self.tr].config, key))).grid(row=r, column=1, sticky=Tkinter.W)
            else:
                Tkinter.Label(self.paramFrame, text='not available').grid(row=r, column=1, sticky=Tkinter.W)
            Tkinter.Entry(self.paramFrame, textvariable=self.newParamStringsDict[key]).grid(row=r, column=2)
        r += 1
        Tkinter.Button(self.paramFrame, text='Update', command=self._updateParameters).grid(row=r, column=0, columnspan=3)
        self.paramFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        self.mainFrame.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)

        if self.D is not None:
            self._plotData()

    def _close(self, event=None):
        self.master.destroy()

    def _prevTrial(self, event=None):
        if self.D is None:
            tkMessageBox.showerror('Error', 'No Data')
            return
        if self.tr > 0:
            self.tr -= 1
            if self.tr == 0:
                self.menu_view.entryconfigure('Prev Trial', state='disabled')
            else:
                self.menu_view.entryconfigure('Prev Trial', state='normal')
            if self.tr == len(self.D)-1:
                self.menu_view.entryconfigure('Next Trial', state='disabled')
            else:
                self.menu_view.entryconfigure('Next Trial', state='normal')
        self._updateParameters()

    def _nextTrial(self, event=None):
        if self.D is None:
            tkMessageBox.showerror('Error', 'No Data')
            return
        if self.tr < len(self.D)-1:
            self.tr += 1
            if self.tr == 0:
                self.menu_view.entryconfigure('Prev Trial', state='disabled')
            else:
                self.menu_view.entryconfigure('Prev Trial', state='normal')
            if self.tr == len(self.D)-1:
                self.menu_view.entryconfigure('Next Trial', state='disabled')
            else:
                self.menu_view.entryconfigure('Next Trial', state='normal')
        self._updateParameters()

    def _plotData(self):
        self.ax.clear()

        tStart = self.D[self.tr].T[0]
        t = self.D[self.tr].T-tStart
        if self.newL is not None:
            self.ax.plot(t, self.newL[:, 0], ':', color=self.conf.COLOR_TRAJECTORY_L_X)
            self.ax.plot(t, self.newL[:, 1], ':', color=self.conf.COLOR_TRAJECTORY_L_Y)
        if self.newR is not None:
            self.ax.plot(t, self.newR[:, 0], '.-', color=self.conf.COLOR_TRAJECTORY_R_X)
            self.ax.plot(t, self.newR[:, 1], '.-', color=self.conf.COLOR_TRAJECTORY_R_Y)
        if self.D[self.tr].config.RECORDED_EYE != 'R':
            self.ax.plot(t, self.D[self.tr].L[:, 0], '.-', color=self.conf.COLOR_TRAJECTORY_L_X)
            self.ax.plot(t, self.D[self.tr].L[:, 1], '.-', color=self.conf.COLOR_TRAJECTORY_L_Y)
        if self.D[self.tr].config.RECORDED_EYE != 'L':
            self.ax.plot(t, self.D[self.tr].R[:, 0], '.-', color=self.conf.COLOR_TRAJECTORY_R_X)
            self.ax.plot(t, self.D[self.tr].R[:, 1], '.-', color=self.conf.COLOR_TRAJECTORY_R_Y)

        for f in range(self.D[self.tr].nFix):
            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, self.D[self.tr].Fix[f].center[0], str(f), color=self.conf.COLOR_FIXATION_FC,
                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox), clip_on=True)

        for s in range(self.D[self.tr].nSac):
            self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart, -10000], self.D[self.tr].Sac[s].duration, 20000,
                              hatch='/', fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))

        if self.newSacList is not None and self.newFixList is not None:
            for f in range(len(self.newFixList)):
                # note: color is reversed
                self.ax.text(self.newFixList[f].startTime-tStart, self.newFixList[f].center[0]-50, str(f), color=self.conf.COLOR_FIXATION_BG,
                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_FC, clip_on=True, clip_box=self.ax.bbox), clip_on=True)

            hatchColor = getComplementaryColorStr(self.conf.COLOR_SACCADE_HATCH)
            for s in range(len(self.newSacList)):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.newSacList[s].startTime-tStart, -10000], self.newSacList[s].duration, 20000,
                                  hatch='\\', fc=hatchColor, alpha=0.3))

        self.ax.axis(self.currentPlotArea)

        self.fig.canvas.draw()

    def _updateParameters(self):
        if self.D is None:
            tkMessageBox.showerror('Error', 'No data!')
            return

        if self.newConfig is None:
            # self.newConfig = copy.deepcopy(self.D[self.tr].config)
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
            tkMessageBox.showerror('Error', 'Illeagal value in '+key)
            configStr = 'New Configuration\n\n'
            for key in GazeParser.Configuration.GazeParserOptions:
                configStr += '%s = %s\n' % (key, getattr(self.newConfig, key))
            self.param2Text.set(configStr)
            return

        offset = PLOT_OFFSET
        try:
            # from GazeParser.Converter.TrackerToGazeParser
            if self.newConfig.RECORDED_EYE == 'B':
                self.newL = applyFilter(self.D[self.tr].T, self.D[self.tr].L, self.newConfig, decimals=8) + offset
                self.newR = applyFilter(self.D[self.tr].T, self.D[self.tr].R, self.newConfig, decimals=8) + offset
                (SacList, FixList, BlinkList) = buildEventListBinocular(self.D[self.tr].T, self.newL, self.newR, self.newConfig)
            else:  # monocular
                if self.newConfig.RECORDED_EYE == 'L':
                    self.newL = applyFilter(self.D[self.tr].T, self.D[self.tr].L, self.newConfig, decimals=8) + offset
                    (SacList, FixList, BlinkList) = buildEventListMonocular(self.D[self.tr].T, self.newL, self.newConfig)
                    self.newR = None
                elif self.newConfig.RECORDED_EYE == 'R':
                    self.newR = applyFilter(self.D[self.tr].T, self.D[self.tr].R, self.newConfig, decimals=8) + offset
                    (SacList, FixList, BlinkList) = buildEventListMonocular(self.D[self.tr].T, self.newR, self.newConfig)
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
        if self.newConfig is None:
            tkMessageBox.showerror('Error', 'New configuration is empty')
            return

        try:
            fname = tkFileDialog.asksaveasfilename(filetypes=self.configtypes, initialdir=GazeParser.configDir)
            self.newConfig.save(fname)
        except:
            tkMessageBox.showerror('Error', 'Could not write configuration to \'' + fname + '\'')


class mainWindow(Tkinter.Frame):
    def __init__(self, master=None):
        self.conf = ViewerOptions()

        self.ftypes = [('GazeParser/SimpleGazeTracker Datafile', ('*.db', '*.csv'))]
        self.datafiletype = [('GazeParser Datafile', '*.db')]
        self.initialDataDir = GazeParser.homeDir
        self.D = None
        self.C = None
        self.tr = 0
        self.plotAreaXY = [0, 1024, 0, 768]
        self.plotAreaTXY = [0, 3000, 0, 1024]
        self.showStimImage = False
        self.stimImage = None
        self.stimImageExtent = [0, 1024, 0, 768]
        self.dataFileName = 'Please open data file.'
        self.dataModified = False
        if self.conf.CANVAS_DEFAULT_VIEW == 'TXY':
            self.plotStyle = 'TXY'
            self.currentPlotArea = self.plotAreaTXY
        elif self.confCanvasDefaultView == 'XY':
            self.plotStyle = 'XY'
            self.currentPlotArea = self.plotAreaXY
        elif self.confCanvasDefaultView == 'SCATTER':
            self.plotStyle = 'SCATTER'
            self.currentPlotArea = self.plotAreaXY
        elif self.confCanvasDefaultView == 'HEATMAP':
            self.plotStyle = 'HEATMAP'
            self.currentPlotArea = self.plotAreaXY
        else:
            raise ValueError('Default view must be ' + ', '.join(XYPLOTMODES) + ' or TXY.')
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}

        Tkinter.Frame.__init__(self, master)
        self.master.title('GazeParser Viewer')
        self.master.protocol('WM_DELETE_WINDOW', self._exit)
        icon = Tkinter.PhotoImage(file=os.path.join(os.path.dirname(__file__), 'img', 'gazeparser_viewer.gif'))
        self.winfo_toplevel().call('wm', 'iconphoto', self.winfo_toplevel(), icon)

        # main menu
        self.menu_bar = Tkinter.Menu(tearoff=False)
        self.menu_file = Tkinter.Menu(tearoff=False)
        self.menu_view = Tkinter.Menu(tearoff=False)
        self.menu_convert = Tkinter.Menu(tearoff=False)
        self.menu_recent = Tkinter.Menu(tearoff=False)
        self.menu_config = Tkinter.Menu(tearoff=False)
        self.menu_analyse = Tkinter.Menu(tearoff=False)
        self.menu_bar.add_cascade(label='File', menu=self.menu_file, underline=0)
        self.menu_bar.add_cascade(label='View', menu=self.menu_view, underline=0)
        self.menu_bar.add_cascade(label='Convert', menu=self.menu_convert, underline=0)
        self.menu_bar.add_cascade(label='Analysis', menu=self.menu_analyse, underline=0)

        self.menu_file.add_command(label='Open', under=0, command=self._openfile)
        self.menu_file.add_cascade(label='Recent Dir', menu=self.menu_recent, underline=0)
        if self.conf.RecentDir == []:
            self.menu_recent.add_command(label='None', state=Tkinter.DISABLED)
        else:
            for i in range(len(self.conf.RecentDir)):
                self.menu_recent.add_command(label=str(i+1)+'. '+self.conf.RecentDir[i], under=0, command=functools.partial(self._openRecent, d=i))
        self.menu_file.add_command(label='Save', under=0, command=self._savefile)
        self.menu_file.add_command(label='Export', under=0, command=self._exportfile)
        self.menu_file.add_command(label='Combine data files', under=0, command=self._combinefiles)
        self.menu_file.add_command(label='Exit', under=1, command=self._exit)
        self.menu_view.add_command(label='Prev Trial', under=0, command=self._prevTrial)
        self.menu_view.add_command(label='Next Trial', under=0, command=self._nextTrial)
        self.menu_view.add_command(label='Jump to...', under=0, command=self._jumpToTrial)
        self.menu_view.add_separator()
        self.plotStyleMenuItem = Tkinter.StringVar()
        self.plotStyleMenuItem.set(self.plotStyle)
        self.menu_view.add_radiobutton(label='T-XY plot', under=0, command=self._toTXYView, variable=self.plotStyleMenuItem, value='TXY')
        self.menu_view.add_radiobutton(label='XY plot', under=0, command=self._toXYView, variable=self.plotStyleMenuItem, value='XY')
        self.menu_view.add_radiobutton(label='Scatter plot', under=0, command=self._toScatterView, variable=self.plotStyleMenuItem, value='SCATTER')
        self.menu_view.add_radiobutton(label='Heatmap plot', under=0, command=self._toHeatmapView, variable=self.plotStyleMenuItem, value='HEATMAP')
        self.menu_view.add_separator()
        self.showFixationNumberItem = Tkinter.IntVar()
        if self.conf.CANVAS_SHOW_FIXNUMBER:
            self.showFixationNumberItem.set(1)
        else:
            self.showFixationNumberItem.set(0)
        self.showStimulusImageItem = Tkinter.IntVar()
        if self.conf.CANVAS_SHOW_STIMIMAGE:
            self.showStimulusImageItem.set(1)
        else:
            self.showStimulusImageItem.set(0)
        self.menu_view.add_radiobutton(label='Show Fixation Number', under=7, command=self._toggleFixNum, variable=self.showFixationNumberItem, value=1)
        self.menu_view.add_radiobutton(label='Show Stimulus Image', under=7, command=self._toggleStimImage, variable=self.showStimulusImageItem, value=1)
        self.menu_view.add_separator()
        self.menu_view.add_command(label='Config grid', command=self._configGrid)
        self.menu_view.add_command(label='Config color', command=self._configColor)
        self.menu_view.add_command(label='Config font', command=self._configFont)
        self.menu_view.add_command(label='Config Stimulus Image', command=self._configStimImage)
        self.menu_convert.add_command(label='Convert SimpleGazeTracker CSV', under=8, command=self._convertGT)
        self.menu_convert.add_command(label='Convert Eyelink EDF', under=8, command=self._convertEL)
        self.menu_convert.add_command(label='Convert Tobii TSV', under=8, command=self._convertTSV)
        self.menu_convert.add_separator()
        self.menu_convert.add_command(label='Edit GazeParser.Configuration file', command=self._configEditor)
        self.menu_convert.add_command(label='Interactive configuration', command=self._interactive)
        self.menu_analyse.add_command(label='Saccade latency', under=0, command=self._getLatency)
        self.menu_analyse.add_command(label='Fixations in region', under=0, command=self._getFixationsInRegion)

        self.master.configure(menu=self.menu_bar)

        # popup menu
        self.popup_msglistbox = Tkinter.Menu(tearoff=False)
        self.popup_msglistbox.add_command(label='Edit selected message', command=self._editMessage, state='disabled')
        self.popup_msglistbox.add_command(label='Insert new message', command=self._insertNewMessage, state='disabled')
        self.popup_msglistbox.add_command(label='Delete selected message(s)', command=self._deleteMessages, state='disabled')

        # viewFrame
        self.selectiontype = Tkinter.StringVar()
        self.selectiontype.set('Emphasize')

        self.viewFrame = Tkinter.Frame(master)
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viewFrame)
        self.canvas._tkcanvas.config(height=self.conf.CANVAS_HEIGHT,
                                     width=self.conf.CANVAS_WIDTH,
                                     background='#C0C0C0', borderwidth=0, highlightthickness=0)
        self.ax = self.fig.add_axes([80.0/self.conf.CANVAS_WIDTH,  # 80px
                                     60.0/self.conf.CANVAS_HEIGHT,  # 60px
                                     1.0-2*80.0/self.conf.CANVAS_WIDTH,
                                     1.0-2*60.0/self.conf.CANVAS_HEIGHT])
        self.ax.axis(self.currentPlotArea)
        self.canvas._tkcanvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)

        toolbar = NavigationToolbar2TkAgg(self.canvas, self.viewFrame)
        toolbar.pack(side=Tkinter.TOP, expand=False)
        self.viewFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)

        self.sideFrame = Tkinter.Frame(master)
        self.listboxFrame = Tkinter.Frame(self.sideFrame)
        Tkinter.Radiobutton(self.sideFrame, text='Emphasize', variable=self.selectiontype, value='Emphasize').pack(side=Tkinter.TOP)
        Tkinter.Radiobutton(self.sideFrame, text='Extract', variable=self.selectiontype, value='Extract').pack(side=Tkinter.TOP)
        buttonFrame = Tkinter.Frame(self.sideFrame)
        Tkinter.Button(buttonFrame, text='Ok', command=self._setmarker).pack(side=Tkinter.LEFT, padx=5)
        Tkinter.Button(buttonFrame, text='Clear', command=self._clearmarker).pack(side=Tkinter.LEFT, padx=5)
        buttonFrame.pack(side=Tkinter.TOP)
        self.yscroll = Tkinter.Scrollbar(self.listboxFrame, orient=Tkinter.VERTICAL)
        self.msglistbox = Tkinter.Listbox(master=self.listboxFrame, yscrollcommand=self.yscroll.set, selectmode=Tkinter.EXTENDED)
        self.msglistbox.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        self.yscroll.pack(side=Tkinter.LEFT, anchor=Tkinter.W, fill=Tkinter.Y, expand=False)
        self.yscroll['command'] = self.msglistbox.yview
        self.listboxFrame.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=True)
        self.sideFrame.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)

        self.master.bind('<Control-KeyPress-o>', self._openfile)
        self.master.bind('<Control-KeyPress-q>', self._exit)
        self.master.bind('<Control-KeyPress-v>', self._toggleView)
        self.master.bind('<Left>', self._prevTrial)
        self.master.bind('<Right>', self._nextTrial)
        self.msglistbox.bind('<Double-Button-1>', self._jumpToTime)
        self.msglistbox.bind('<Button-3>', self._showPopupMsglistbox)

        if self.conf.CANVAS_FONT_FILE != '':
            self.fontPlotText = matplotlib.font_manager.FontProperties(fname=self.conf.CANVAS_FONT_FILE)
        else:
            self.fontPlotText = matplotlib.font_manager.FontProperties()

    def _toggleView(self, event=None):

        if self.plotStyle == 'XY':
            self.plotStyle = 'SCATTER'
            self.currentPlotArea = self.plotAreaXY
        elif self.plotStyle == 'SCATTER':
            self.plotStyle = 'HEATMAP'
            self.currentPlotArea = self.plotAreaXY
        elif self.plotStyle == 'HEATMAP':
            self.plotStyle = 'TXY'
            self.currentPlotArea = self.plotAreaTXY
        else:  # XYT
            self.plotStyle = 'XY'
            self.currentPlotArea = self.plotAreaXY
        self.plotStyleMenuItem.set(self.plotStyle)
        self._plotData()

    def _toTXYView(self):
        self.plotStyle = 'TXY'
        self.currentPlotArea = self.plotAreaTXY
        self._plotData()

    def _toXYView(self):
        self.plotStyle = 'XY'
        self.currentPlotArea = self.plotAreaXY
        self._plotData()

    def _toScatterView(self):
        self.plotStyle = 'SCATTER'
        self.currentPlotArea = self.plotAreaXY
        self._plotData()

    def _toHeatmapView(self):
        self.plotStyle = 'HEATMAP'
        self.currentPlotArea = self.plotAreaXY
        self._plotData()

    def _toggleFixNum(self, event=None):
        if self.conf.CANVAS_SHOW_FIXNUMBER:
            self.conf.CANVAS_SHOW_FIXNUMBER = False
            self.showFixationNumberItem.set(0)
        else:
            self.conf.CANVAS_SHOW_FIXNUMBER = True
            self.showFixationNumberItem.set(1)

        self._plotData()

    def _toggleStimImage(self, event=None):
        if self.conf.CANVAS_SHOW_STIMIMAGE:
            self.conf.CANVAS_SHOW_STIMIMAGE = False
            self.showStimulusImageItem.set(0)
        else:
            self.conf.CANVAS_SHOW_STIMIMAGE = True
            self.showStimulusImageItem.set(1)

        self._plotData()

    def _openfile(self, event=None):
        if self.dataModified:
            doSave = tkMessageBox.askyesno('Warning', 'Your changes have not been saved. Do you want to save the changes?')
            if doSave:
                self._savefile()

        fname = tkFileDialog.askopenfilename(filetypes=self.ftypes, initialdir=self.initialDataDir)
        if fname == '':
            return
        self.dataFileName = fname
        self.initialDataDir = os.path.split(self.dataFileName)[0]
        # record recent dir
        if self.initialDataDir in self.conf.RecentDir:
            self.conf.RecentDir.remove(self.initialDataDir)
        self.conf.RecentDir.insert(0, self.initialDataDir)
        if len(self.conf.RecentDir) > MAX_RECENT:
            self.conf.RecentDir = self.conf.RecentDir[:MAX_RECENT]
        # update menu recent_dir
        self.menu_recent.delete(0, MAX_RECENT)
        for i in range(len(self.conf.RecentDir)):
            self.menu_recent.add_command(label=str(i+1)+'. '+self.conf.RecentDir[i], under=0, command=functools.partial(self._openRecent, d=i))

        # if extension is .csv, try converting
        if os.path.splitext(self.dataFileName)[1].lower() == '.csv':
            dbFileName = os.path.splitext(self.dataFileName)[0]+'.db'
            print dbFileName
            if os.path.isfile(dbFileName):
                doOverwrite = tkMessageBox.askyesno('Overwrite?', dbFileName+' already exists. Overwrite?')
                if not doOverwrite:
                    tkMessageBox.showinfo('Info', 'Conversion canceled.')
                    return
            ret = GazeParser.Converter.TrackerToGazeParser(self.dataFileName, overwrite=True)
            if ret == 'SUCCESS':
                tkMessageBox.showinfo('Info', 'Conversion succeeded.\nOpen converted data file.')
                self.dataFileName = dbFileName
            else:
                tkMessageBox.showinfo('Conversion error', 'Failed to convert %s to GazeParser .db file' % (self.dataFileName))
                return

        [self.D, self.C] = GazeParser.load(self.dataFileName)
        if len(self.D) == 0:
            tkMessageBox.showerror('Error', 'File contains no data. (%s)' % (self.dataFileName))
            self.D = None
            self.C = None
            return

        self.dataModified = False

        if GazeParser.Utility.compareVersion(self.D[0].__version__, GazeParser.__version__) < 0:
            lackingattributes = GazeParser.Utility.checkAttributes(self.D[0])
            if len(lackingattributes) > 0:
                ans = tkMessageBox.askyesno('Info', 'This data is generated by Version %s and lacks some data attributes newly appended in the later version. Try to append new attributes automatically? If you answered \'no\', some features may not work correctly.' % (self.D[0].__version__))
                if ans:
                    self.D = GazeParser.Utility.rebuildData(self.D)
                    self.dataModified = True
                    tkMessageBox.showinfo('Info', 'Automatic rebuild is finished.\nIf automatic rebuild seems to work as expected, please rebuild data from SimpleGazeTracker CSV file to add new attributes manually.')
                else:
                    tkMessageBox.showinfo('Info', 'Ok, Data file is opened without adding missing attributes.\nPlease rebuild data from SimpleGazeTracker CSV file to add new attributes manually.')

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
        else:  # assume 'bottomleft'
            self.plotAreaXY = [0, self.D[self.tr].config.SCREEN_WIDTH, 0, self.D[self.tr].config.SCREEN_HEIGHT]
            self.plotAreaTXY[2] = 0
            self.plotAreaTXY[3] = max(self.D[self.tr].config.SCREEN_WIDTH, self.D[self.tr].config.SCREEN_HEIGHT)
        if self.D[self.tr].L is None:
            self.hasLData = False
        else:
            self.hasLData = True

        if self.D[self.tr].R is None:
            self.hasRData = False
        else:
            self.hasRData = True

        # initialize current plot area
        if self.plotStyle in XYPLOTMODES:
            self.currentPlotArea = self.plotAreaXY

        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        self.selectiontype.set('Emphasize')
        self.menu_view.entryconfigure('Prev Trial', state='disabled')
        if len(self.D) < 2:
            self.menu_view.entryconfigure('Next Trial', state='disabled')

        self._loadStimImage()

        self._plotData()
        self._updateMsgBox()

        # enabel message-edit popup
        self.popup_msglistbox.entryconfigure('Edit selected message', state='normal')
        self.popup_msglistbox.entryconfigure('Insert new message', state='normal')
        self.popup_msglistbox.entryconfigure('Delete selected message(s)', state='normal')

    def _openRecent(self, d):
        self.initialDataDir = self.conf.RecentDir[d]
        self._openfile()

    def _loadStimImage(self):
        msg = self.D[self.tr].findMessage('!STIMIMAGE', useRegexp=False)
        sep = ' '
        if os.path.isabs(self.conf.COMMAND_STIMIMAGE_PATH):
            imagePath = self.conf.COMMAND_STIMIMAGE_PATH
        else:
            imagePath = os.path.join(os.path.split(self.dataFileName)[0], self.conf.COMMAND_STIMIMAGE_PATH)
        self.stimImage = None
        if len(msg) == 0:
            return False
        elif len(msg) > 1:
            tkMessageBox.showerror('Error', 'Multiple !STIMIMAGE commands in this trial.')
            return False
        else:
            params = msg[0].text.split(sep)
            if params[0] != '!STIMIMAGE':
                tkMessageBox.showerror('Error', '!STIMIMAGE command must be at the beginning of message text.')
                return False
            try:
                imageFilename = os.path.join(imagePath, params[1])
                self.stimImage = Image.open(imageFilename)
            except:
                tkMessageBox.showerror('Error', 'Cannot open %s as StimImage.' % imageFilename)
                return

            # set extent [left, right, bottom, top] (See matplotlib.pyplot.imshow)
            if len(params) == 4:
                # left and bottom are specified.
                try:
                    self.stimImageExtent[0] = float(params[2])
                    self.stimImageExtent[2] = float(params[3])
                except:
                    tkMessageBox.showerror('Error', 'Invalid extent: %s' % sep.join(params[2:]))
                    self.ImageExtent = [0, self.stimImage.size[0], 0, self.stimImage.size[1]]
                    return False

                self.stimImageExtent[1] = self.stimImageExtent[0] + self.stimImage.size[0]
                self.stimImageExtent[3] = self.stimImageExtent[2] + self.stimImage.size[1]
            if len(params) == 6:
                # left, right, bottom and top are specified.
                try:
                    self.stimImageExtent[0] = float(params[2])
                    self.stimImageExtent[1] = float(params[3])
                    self.stimImageExtent[2] = float(params[4])
                    self.stimImageExtent[3] = float(params[5])
                except:
                    tkMessageBox.showerror('Error', 'Invalid extent: %s' % sep.join(params[2:]))
                    self.ImageExtent = [0, self.stimImage.size[0], 0, self.stimImage.size[1]]
                    return False

            return True

    def _savefile(self, event=None):
        if self.D is None:
            tkMessageBox.showinfo('info', 'No data')
            return

        filename = tkFileDialog.asksaveasfilename(filetypes=self.datafiletype, initialfile=self.dataFileName, initialdir=self.initialDataDir)
        if filename == '':
            return

        try:
            GazeParser.save(filename, self.D, self.C)
        except:
            tkMessageBox.showinfo('Error', 'Cannot save data as %s' % (filename))
            return

        self.dataModified = False

    def _exportfile(self, event=None):
        if self.D is None:
            tkMessageBox.showinfo('info', 'Data must be loaded before export')
            return
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        exportToFileWindow(master=dlg, data=self.D, additional=self.C, trial=self.tr, initialdir=self.initialDataDir)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _configColor(self, event=None):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        configColorWindow(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _exit(self, event=None):
        if self.dataModified:
            doSave = tkMessageBox.askyesno('Warning', 'Your changes have not been saved. Do you want to save the changes?')
            if doSave:
                self._savefile()
        self.conf._write()
        self.master.destroy()

    def _prevTrial(self, event=None):
        if self.D is None:
            tkMessageBox.showerror('Error', 'No Data')
            return
        if self.tr > 0:
            self.tr -= 1
            if self.tr == 0:
                self.menu_view.entryconfigure('Prev Trial', state='disabled')
            else:
                self.menu_view.entryconfigure('Prev Trial', state='normal')
            if self.tr == len(self.D)-1:
                self.menu_view.entryconfigure('Next Trial', state='disabled')
            else:
                self.menu_view.entryconfigure('Next Trial', state='normal')
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        self.selectiontype.set('Emphasize')
        self._loadStimImage()
        self._plotData()
        self._updateMsgBox()

    def _nextTrial(self, event=None):
        if self.D is None:
            tkMessageBox.showerror('Error', 'No Data')
            return
        if self.tr < len(self.D)-1:
            self.tr += 1
            if self.tr == 0:
                self.menu_view.entryconfigure('Prev Trial', state='disabled')
            else:
                self.menu_view.entryconfigure('Prev Trial', state='normal')
            if self.tr == len(self.D)-1:
                self.menu_view.entryconfigure('Next Trial', state='disabled')
            else:
                self.menu_view.entryconfigure('Next Trial', state='normal')
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        self.selectiontype.set('Emphasize')
        self._loadStimImage()
        self._plotData()
        self._updateMsgBox()

    def _jumpToTrial(self, event=None):
        if self.D is None:
            tkMessageBox.showerror('Error', 'No Data')
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
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _jumpToTime(self, event=None):
        if self.plotStyle in XYPLOTMODES:
            i = self.msglistbox.index(Tkinter.ACTIVE)
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
            self.ax.set_xlim((pos[0]-halfXrange, pos[0]+halfXrange))
            self.ax.set_ylim((pos[1]-halfYrange, pos[1]+halfYrange))
            self.fig.canvas.draw()

        else:
            text = self.msglistbox.get(Tkinter.ACTIVE)
            time = float(text.split(':')[0])  # time
            xlim = self.ax.get_xlim()
            halfXrange = (xlim[1]-xlim[0])/2.0
            self.ax.set_xlim((time-halfXrange, time+halfXrange))
            self.fig.canvas.draw()

    def _showPopupMsglistbox(self, event=None):
        self.popup_msglistbox.post(event.x_root, event.y_root)

    def _modifyPlotRange(self):
        """
        .. deprecated:: 0.6.1
        """
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        plotRangeWindow(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _configGrid(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        configGridWindow(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _updateGrid(self):
        if self.plotStyle in XYPLOTMODES:
            xattr = 'CANVAS_GRID_ABSCISSA_XY'
            yattr = 'CANVAS_GRID_ORDINATE_XY'
        else:
            xattr = 'CANVAS_GRID_ABSCISSA_XYT'
            yattr = 'CANVAS_GRID_ORDINATE_XYT'

        params = getattr(self.conf, xattr).split('#')
        if params[0] == 'NOGRID':
            self.ax.xaxis.grid(False)
        elif params[0] == 'CURRENT':
            self.ax.xaxis.grid(True)
        elif params[0] == 'INTERVAL':
            try:
                interval = float(params[1])
            except:
                tkMessageBox.showerror('Error', '"%s" is not a float number.', (params[1]))
                return
            self.ax.xaxis.grid(True)
            self.ax.xaxis.set_major_locator(MultipleLocator(interval))
        elif params[0] == 'CUSTOM':
            try:
                format = eval(params[1])
            except:
                tkMessageBox.showerror('Error', '"%s" is not a python statement.' % (params[1]))
                return

            self.ax.xaxis.grid(True)
            self.ax.xaxis.set_ticks(format)
        else:
            raise ValueError('Unknown abscissa grid type (%s)' % (params[0]))

        params = getattr(self.conf, yattr).split('#')
        if params[0] == 'NOGRID':
            self.ax.yaxis.grid(False)
        elif params[0] == 'CURRENT':
            self.ax.yaxis.grid(True)
        elif params[0] == 'INTERVAL':
            try:
                interval = float(params[1])
            except:
                tkMessageBox.showerror('Error', '"%s" is not a float number.' % (params[1]))
                return
            self.ax.yaxis.grid(True)
            self.ax.yaxis.set_major_locator(MultipleLocator(interval))
        elif params[0] == 'CUSTOM':
            try:
                format = eval(params[1])
            except:
                tkMessageBox.showerror('Error', '"%s" is not a python statement.' % (params[1]))
                return
            self.ax.yaxis.grid(True)
            self.ax.yaxis.set_ticks(format)
        else:
            raise ValueError('Unknown ordinate grid type (%s)' % (params[0]))

    def _plotData(self):
        if self.D is None:
            return

        self.ax.clear()

        if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
            sf = (1.0, 1.0)
        elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
            sf = self.D[self.tr]._pix2deg

        if self.plotStyle in XYPLOTMODES and self.stimImage is not None and self.conf.CANVAS_SHOW_STIMIMAGE:
            self.ax.imshow(self.stimImage, extent=self.stimImageExtent, origin='upper')

        if self.plotStyle == 'XY':
            # plot fixations
            for f in range(self.D[self.tr].nFix):
                if self.hasLData:
                    ftraj = sf*self.D[self.tr].getFixTraj(f, 'L')
                    col = self.conf.COLOR_TRAJECTORY_L_FIX
                    if self.selectiontype.get() == 'Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:, 0], ftraj[:, 1], '.-', linewidth=4.0, color=col)
                            if self.conf.CANVAS_SHOW_FIXNUMBER:
                                self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.conf.COLOR_FIXATION_FC_E,
                                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG_E, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties=self.fontPlotText, clip_on=True)
                        else:
                            self.ax.plot(ftraj[:, 0], ftraj[:, 1], '.-', linewidth=1.0, color=col)
                            if self.conf.CANVAS_SHOW_FIXNUMBER:
                                self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.conf.COLOR_FIXATION_FC,
                                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties=self.fontPlotText, clip_on=True)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:, 0], ftraj[:, 1], '.-', linewidth=1.0, color=col)
                            if self.conf.CANVAS_SHOW_FIXNUMBER:
                                self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                             color=self.conf.COLOR_FIXATION_FC,
                                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                             fontproperties=self.fontPlotText, clip_on=True)
                if self.hasRData:
                    ftraj = sf*self.D[self.tr].getFixTraj(f, 'R')
                    col = self.conf.COLOR_TRAJECTORY_R_FIX
                    if self.selectiontype.get() == 'Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:, 0], ftraj[:, 1], '.-', linewidth=4.0, color=col)
                        else:
                            self.ax.plot(ftraj[:, 0], ftraj[:, 1], '.-', linewidth=1.0, color=col)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.plot(ftraj[:, 0], ftraj[:, 1], '.-', linewidth=1.0, color=col)

            # plot saccades
            for s in range(self.D[self.tr].nSac):
                if self.hasLData:
                    straj = sf*self.D[self.tr].getSacTraj(s, 'L')
                    col = self.conf.COLOR_TRAJECTORY_L_SAC
                    if self.selectiontype.get() == 'Emphasize':
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:, 0], straj[:, 1], '.-', linewidth=4.0, color=col)
                        else:
                            self.ax.plot(straj[:, 0], straj[:, 1], '.-', linewidth=1.0, color=col)
                    else:
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:, 0], straj[:, 1], '.-', linewidth=1.0, color=col)
                if self.hasRData:
                    straj = sf*self.D[self.tr].getSacTraj(s, 'R')
                    col = self.conf.COLOR_TRAJECTORY_R_SAC
                    if self.selectiontype.get() == 'Emphasize':
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:, 0], straj[:, 1], '.-', linewidth=4.0, color=col)
                        else:
                            self.ax.plot(straj[:, 0], straj[:, 1], '.-', linewidth=1.0, color=col)
                    else:
                        if s in self.selectionlist['Sac']:
                            self.ax.plot(straj[:, 0], straj[:, 1], '.-', linewidth=1.0, color=col)

        elif self.plotStyle == 'SCATTER':
            # plot fixations
            fixcenter = self.D[self.tr].getFixCenter()
            fixdur = self.D[self.tr].getFixDur()
            self.ax.plot(fixcenter[:, 0], fixcenter[:, 1], 'k-')
            self.ax.scatter(fixcenter[:, 0], fixcenter[:, 1], s=fixdur, c=fixdur, alpha=0.7)
            for f in range(self.D[self.tr].nFix):
                if self.selectiontype.get() == 'Emphasize':
                    if f in self.selectionlist['Fix']:
                        if self.conf.CANVAS_SHOW_FIXNUMBER:
                            self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                         color=self.conf.COLOR_FIXATION_FC_E,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG_E, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)
                    else:
                        if self.conf.CANVAS_SHOW_FIXNUMBER:
                            self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                         color=self.conf.COLOR_FIXATION_FC,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)
                else:
                    if f in self.selectionlist['Fix']:
                        if self.conf.CANVAS_SHOW_FIXNUMBER:
                            self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                         color=self.conf.COLOR_FIXATION_FC,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)

        elif self.plotStyle == 'HEATMAP':
            fixcenter = self.D[self.tr].getFixCenter()
            fixdur = self.D[self.tr].getFixDur()
            xmin = sf[0]*self.currentPlotArea[0]
            xmax = sf[0]*self.currentPlotArea[1]
            ymin = sf[1]*self.currentPlotArea[2]
            ymax = sf[1]*self.currentPlotArea[3]
            xstep = (xmax-xmin)/128.0
            ystep = (ymax-ymin)/128.0
            xmesh, ymesh = numpy.meshgrid(numpy.arange(xmin, xmax, xstep),
                                          numpy.arange(ymin, ymax, ystep))
            heatmap = numpy.zeros(xmesh.shape)
            for idx in range(fixcenter.shape[0]):
                if numpy.isnan(fixcenter[idx, 0]) or numpy.isnan(fixcenter[idx, 1]):
                    continue
                heatmap = heatmap + fixdur[idx, 0]*numpy.exp(-((xmesh-fixcenter[idx, 0])/50)**2-((ymesh-fixcenter[idx, 1])/50)**2)
            cmap = matplotlib.cm.get_cmap('hot')
            cmap._init()
            alphas = numpy.linspace(0.0, 5.0, cmap.N)
            alphas[numpy.where(alphas > 0.8)[0]] = 0.8
            cmap._lut[:-3, -1] = alphas
            self.ax.imshow(heatmap, extent=(xmin, xmax, ymin, ymax), origin='lower', cmap=cmap)

            for f in range(self.D[self.tr].nFix):
                if self.selectiontype.get() == 'Emphasize':
                    if f in self.selectionlist['Fix']:
                        if self.conf.CANVAS_SHOW_FIXNUMBER:
                            self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                         color=self.conf.COLOR_FIXATION_FC_E,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG_E, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)
                    else:
                        if self.conf.CANVAS_SHOW_FIXNUMBER:
                            self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                         color=self.conf.COLOR_FIXATION_FC,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)
                else:
                    if f in self.selectionlist['Fix']:
                        if self.conf.CANVAS_SHOW_FIXNUMBER:
                            self.ax.text(sf[0]*self.D[self.tr].Fix[f].center[0], sf[1]*self.D[self.tr].Fix[f].center[1], str(f),
                                         color=self.conf.COLOR_FIXATION_FC,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)

        else:  # XY-T
            tStart = self.D[self.tr].T[0]
            t = self.D[self.tr].T-tStart
            if self.hasLData:
                self.ax.plot(t, sf[0]*self.D[self.tr].L[:, 0], '.-', color=self.conf.COLOR_TRAJECTORY_L_X)
                self.ax.plot(t, sf[1]*self.D[self.tr].L[:, 1], '.-', color=self.conf.COLOR_TRAJECTORY_L_Y)
            if self.hasRData:
                self.ax.plot(t, sf[0]*self.D[self.tr].R[:, 0], '.-', color=self.conf.COLOR_TRAJECTORY_R_X)
                self.ax.plot(t, sf[1]*self.D[self.tr].R[:, 1], '.-', color=self.conf.COLOR_TRAJECTORY_R_Y)

            if self.conf.CANVAS_SHOW_FIXNUMBER:
                for f in range(self.D[self.tr].nFix):
                    if self.selectiontype.get() == 'Emphasize':
                        if f in self.selectionlist['Fix']:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, sf[0]*self.D[self.tr].Fix[f].center[0], str(f),
                                         color=self.conf.COLOR_FIXATION_FC_E,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG_E, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)
                        else:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, sf[0]*self.D[self.tr].Fix[f].center[0], str(f),
                                         color=self.conf.COLOR_FIXATION_FC,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)
                    else:
                        if f in self.selectionlist['Fix']:
                            self.ax.text(self.D[self.tr].Fix[f].startTime-tStart, sf[0]*self.D[self.tr].Fix[f].center[0], str(f),
                                         color=self.conf.COLOR_FIXATION_FC,
                                         bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_BG, clip_on=True, clip_box=self.ax.bbox),
                                         fontproperties=self.fontPlotText, clip_on=True)

            for s in range(self.D[self.tr].nSac):
                if self.selectiontype.get() == 'Emphasize':
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart, -10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       hatch='/', fc=self.conf.COLOR_SACCADE_HATCH_E, alpha=0.8))
                    else:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart, -10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       hatch='/', fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))
                else:
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart, -10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       hatch='/', fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))

            for b in range(self.D[self.tr].nBlink):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Blink[b].startTime-tStart, -10000],
                                                               self.D[self.tr].Blink[b].duration, 20000,
                                                               hatch='\\', fc=self.conf.COLOR_BLINK_HATCH, alpha=0.3))

            for m in range(self.D[self.tr].nMsg):
                mObj = self.D[self.tr].Msg[m]
                if len(mObj.text) > 10:
                    msgtext = str(m) + ':' + mObj.text[:7] + '...'
                else:
                    msgtext = str(m) + ':' + mObj.text
                self.ax.plot([mObj.time, mObj.time], [-10000, 10000], '-', color=self.conf.COLOR_MESSAGE_CURSOR, linewidth=3.0)
                self.ax.text(mObj.time, 0, msgtext, color=self.conf.COLOR_MESSAGE_FC,
                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_MESSAGE_BG, clip_on=True, clip_box=self.ax.bbox),
                             fontproperties=self.fontPlotText, clip_on=True)

        # set plotrange and axis labels
        if self.plotStyle in XYPLOTMODES:
            if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
                self.ax.set_xlabel('Vertical gaze position (pix)')
                self.ax.set_ylabel('Horizontal gaze position (pix)')
            elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
                self.ax.set_xlabel('Vertical gaze position (deg)')
                self.ax.set_ylabel('Horizontal gaze position (deg)')

            self.ax.axis((sf[0]*self.currentPlotArea[0], sf[0]*self.currentPlotArea[1],
                          sf[1]*self.currentPlotArea[2], sf[1]*self.currentPlotArea[3]))
            self.ax.set_aspect('equal')
        else:  # TXY
            if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
                self.ax.set_xlabel('Time (ms)')
                self.ax.set_ylabel('Gaze position (pix)')
            elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
                self.ax.set_xlabel('Time (ms)')
                self.ax.set_ylabel('Gaze position (deg)')

            self.ax.axis((self.currentPlotArea[0], self.currentPlotArea[1],
                          sf[0]*self.currentPlotArea[2], sf[0]*self.currentPlotArea[3]))
            self.ax.set_aspect('auto')

        self.ax.set_title('%s: Trial%d' % (os.path.basename(self.dataFileName), self.tr))
        self._updateGrid()
        self.fig.canvas.draw()

    def _updateMsgBox(self):
        self.msglistbox.delete(0, self.msglistbox.size())

        st = self.D[self.tr].T[0]
        et = self.D[self.tr].T[-1]

        for e in self.D[self.tr].EventList:
            if isinstance(e, GazeParser.SaccadeData):
                self.msglistbox.insert(Tkinter.END, '%10.1f' % (e.startTime)+':Sac')
                # self.msglistbox.itemconfig(Tkinter.END, bg=self.conf.COLOR_TRAJECTORY_L_SAC)
            elif isinstance(e, GazeParser.FixationData):
                self.msglistbox.insert(Tkinter.END, '%10.1f' % (e.startTime)+':Fix')
                # self.msglistbox.itemconfig(Tkinter.END, bg=self.conf.COLOR_TRAJECTORY_L_FIX)
            elif isinstance(e, GazeParser.MessageData):
                self.msglistbox.insert(Tkinter.END, '%10.1f' % (e.time)+':'+e.text)
                self.msglistbox.itemconfig(Tkinter.END, bg=self.conf.COLOR_MESSAGE_BG, fg=self.conf.COLOR_MESSAGE_FC)
            elif isinstance(e, GazeParser.BlinkData):
                self.msglistbox.insert(Tkinter.END, '%10.1f' % (e.startTime)+':Blk')

    def _setmarker(self):
        selected = self.msglistbox.curselection()
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}

        for s in selected:
            e = self.D[self.tr].EventList[int(s)]
            if isinstance(e, GazeParser.SaccadeData):
                self.selectionlist['Sac'].append(numpy.where(e == self.D[self.tr].Sac)[0][0])
            elif isinstance(e, GazeParser.FixationData):
                self.selectionlist['Fix'].append(numpy.where(e == self.D[self.tr].Fix)[0][0])
            elif isinstance(e, GazeParser.MessageData):
                self.selectionlist['Msg'].append(numpy.where(e == self.D[self.tr].Msg)[0][0])
            elif isinstance(e, GazeParser.BlinkData):
                self.selectionlist['Blink'].append(numpy.where(e == self.D[self.tr].Blink)[0][0])

        # self.currentPlotArea = self.ax.get_xlim()+self.ax.get_ylim()
        self._plotData()

    def _clearmarker(self):
        self.msglistbox.selection_clear(0, self.msglistbox.size())
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        if self.selectiontype.get() == 'Extract':
            self.selectiontype.set('Emphasize')
        self._plotData()

    def _configEditor(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GazeParser.app.ConfigEditor.ConfigEditor(master=dlg, showExit=False)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _convertGT(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        obj = GazeParser.app.Converters.Converter(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _convertEL(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GazeParser.app.Converters.EyelinkConverter(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _convertTSV(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        GazeParser.app.Converters.TobiiConverter(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _interactive(self):
        if self.D is None:
            tkMessageBox.showinfo('info', 'Data must be loaded before\nusing interactive configuration.')
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
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _getLatency(self):
        if self.D is None:
            tkMessageBox.showinfo('info', 'Data must be loaded before getting saccade latency')
            return
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        getSaccadeLatencyWindow(master=dlg, data=self.D, additional=self.C, conf=self.conf, initialdir=self.initialDataDir)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _getFixationsInRegion(self):
        if self.D is None:
            tkMessageBox.showinfo('info', 'Data must be loaded before getting fixations in region')
            return
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        getFixationsInRegionWindow(master=dlg, data=self.D, additional=self.C, conf=self.conf, initialdir=self.initialDataDir)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _editMessage(self):
        if self.D is None:
            tkMessageBox.showinfo('info', 'Data must be loaded before editing message')
            return

        selected = self.msglistbox.curselection()
        numSelectedMessages = 0
        for s in selected:
            e = self.D[self.tr].EventList[int(s)]
            if isinstance(e, GazeParser.MessageData):
                numSelectedMessages += 1
                if numSelectedMessages > 1:
                    tkMessageBox.showerror('Error', 'More than two messages are selected.')
                    return

        if numSelectedMessages == 0:
            tkMessageBox.showerror('Error', 'No messages are selected.')
            return

        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        editMessageWindow(master=dlg, mainWindow=self, message=self.D[self.tr].EventList[int(selected[0])])
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _insertNewMessage(self):
        if self.D is None:
            tkMessageBox.showinfo('info', 'Data must be loaded before inserting new message')
            return
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        insertNewMessageWindow(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _deleteMessages(self):
        selected = self.msglistbox.curselection()
        selectedMessages = []
        selectedMessagesText = ''
        for s in selected:
            e = self.D[self.tr].EventList[int(s)]
            if isinstance(e, GazeParser.MessageData):
                selectedMessages.append(e)
                msgtext = e.text
                if len(msgtext) > 30:
                    msgtext = msgtext[:27]+'...'
                selectedMessagesText += '%10.1f, %s\n' % (e.time, msgtext)

        ans = tkMessageBox.askokcancel('Warning', 'You cannot undo this operation. Are you sure to delete following message(s)?\n\n'+selectedMessagesText)
        if ans:
            for m in selectedMessages:
                m.delete()
            self._updateMsgBox()
            self._loadStimImage()
            self._plotData()

            self.dataModified = True

    def _configFont(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        fontSelectWindow(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _configStimImage(self):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        configStimImageWindow(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

    def _combinefiles(self, event=None):
        geoMaster = parsegeometry(self.master.winfo_geometry())
        dlg = Tkinter.Toplevel(self)
        combineDataFileWindow(master=dlg, mainWindow=self)
        dlg.focus_set()
        dlg.grab_set()
        dlg.transient(self)
        dlg.resizable(0, 0)
        dlg.update_idletasks()
        geo = parsegeometry(dlg.winfo_geometry())
        dlg.geometry('%dx%d+%d+%d' % (geo[0], geo[1], geoMaster[2]+50, geoMaster[3]+50))

if __name__ == '__main__':
    w = mainWindow()
    w.mainloop()
