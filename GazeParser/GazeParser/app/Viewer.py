#!/usr/bin/env python
"""
Part of GazeParser library.
Copyright (C) 2012-2025 Hiroyuki Sogo.
Distributed under the terms of the GNU General Public License (GPL).

Thanks to following page for embedded plot.

* http://www.mailinglistarchive.com/html/matplotlib-users@lists.sourceforge.net/2010-08/msg00148.html

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
from configparser import ConfigParser
import shutil
import datetime
try:
    import Image
except ImportError:
    from PIL import Image
import GazeParser
import GazeParser.Converter
import GazeParser.Configuration
import GazeParser.Utility
import GazeParser.Region
import re
import codecs
import functools
import wx
if hasattr(wx, 'NewIdRef'):
    wx_NewIdRef = wx.NewIdRef
else:
    wx_NewIdRef = wx.NewId
import wx.aui
import matplotlib
#import functools
import traceback
import numpy as np
import matplotlib.figure
import matplotlib.font_manager
import matplotlib.patches
import matplotlib.cm
import matplotlib.animation
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg, NavigationToolbar2WxAgg
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from GazeParser.Converter import buildEventListBinocular, buildEventListMonocular, applyFilter

from packaging import version
from ._dialogs import (DlgAskyesno, DlgShowerror, DlgShowinfo, DlgAskopenfilename, 
                       DlgAskopenfilenames, DlgAsksaveasfilename, DlgAsk3buttonDialog)

matplotlib.interactive( True )
#matplotlib.use( 'WXAgg' )

matplotlib.rcParams['axes.xmargin'] = 0
matplotlib.rcParams['axes.ymargin'] = 0

MAX_RECENT = 5
PLOT_OFFSET = 10
XYPLOTMODES = ['XY', 'SCATTER', 'HEATMAP']
SELECTMODES = ['Emphasize', 'Extract']

ID_RECENT1 = wx_NewIdRef()
ID_RECENT2 = wx_NewIdRef()
ID_RECENT3 = wx_NewIdRef()
ID_RECENT4 = wx_NewIdRef()
ID_RECENT5 = wx_NewIdRef()
recentIDList = [ID_RECENT1, ID_RECENT2, ID_RECENT3, ID_RECENT4, ID_RECENT5]
ID_EXPORT = wx_NewIdRef()
ID_COMBINE = wx_NewIdRef()
ID_PREV_TR = wx_NewIdRef()
ID_NEXT_TR = wx_NewIdRef()
ID_VIEW_TXY = wx_NewIdRef()
ID_VIEW_XY = wx_NewIdRef()
ID_VIEW_SCATTER = wx_NewIdRef()
ID_VIEW_HEATMAP = wx_NewIdRef()
ID_SHOW_FIXNUM = wx_NewIdRef()
ID_SHOW_SELECTED_ONLY = wx_NewIdRef()
ID_SHOW_STIMIMAGE = wx_NewIdRef()
ID_CONF_GRID = wx_NewIdRef()
ID_CONF_COLOR = wx_NewIdRef()
ID_CONF_FONT = wx_NewIdRef()
ID_CONF_STIMIMAGE = wx_NewIdRef()
ID_TOOL_CONVERT = wx_NewIdRef()
ID_TOOL_EDITCONFIG = wx_NewIdRef()
ID_TOOL_GETLATENCY = wx_NewIdRef()
ID_TOOL_GETFIXREG = wx_NewIdRef()
ID_TOOL_ANIMATION = wx_NewIdRef()
ID_JUMPLIST_CURRENT = wx_NewIdRef()
ID_JUMPLIST_REGISTERED = wx_NewIdRef()
ID_JUMPLIST_EVENT = wx_NewIdRef()
ID_JUMP_TO = wx_NewIdRef()

def getComplementaryColorStr(col):
    """
    get complementary color (e.g. '#00FF88' -> '#FF0077'
    """
    return '#'+hex(16777215-int(col[1:], base=16))[2:].upper()

def findGazeParserObjectIndex(obj, objlist):
    idxs = []
    for i, o in enumerate(objlist):
        if obj == o:
            idxs.append(i)

    return idxs

def getTextColor(backgroundColor, thresh=0.3):
    g = int(backgroundColor[1:3], base=16)*0.298912 + int(backgroundColor[3:5], base=16)*0.586611 + int(backgroundColor[5:7], base=16)*0.114478
    if g < 127:
        return '#FFFFFF'
    else:
        return '#000000'


class animationDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(animationDialog, self).__init__(parent=parent, id=id, title='Animation')
        self.parent = parent
        self.D = parent.D
        self.tr = parent.tr
        self.stimImage = parent.stimImage
        self.stimImageExtent = parent.stimImageExtent
        self.conf = parent.conf
        self.plotAreaXY = parent.plotAreaXY
        self.fontPlotText = parent.fontPlotText
        self.dataFileName = parent.dataFileName
        self.hasLData = parent.hasLData
        self.hasRData = parent.hasRData

        if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
            self.sf = (1.0, 1.0)
        elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
            self.sf = self.D[self.tr]._pix2deg
        
        self.ID_STARTSLIDER = wx_NewIdRef()
        self.ID_STOPSLIDER = wx_NewIdRef()
        self.ID_STARTCTRL = wx_NewIdRef()
        self.ID_STOPCTRL = wx_NewIdRef()
        
        #TIMER_ID = wx_NewIdRef()
        #self.timer = wx.Timer(self, TIMER_ID)
        #wx.EVT_TIMER(self, TIMER_ID, self.onTimer)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer)
        
        self.saveMovie = False
        
        viewPanel = wx.Panel(self, wx.ID_ANY)
        self.fig = matplotlib.figure.Figure( figsize=(self.D[self.tr].config.SCREEN_WIDTH/200, self.D[self.tr].config.SCREEN_HEIGHT/200) ) # half of screen resolution
        self.canvas = FigureCanvasWxAgg( viewPanel, wx.ID_ANY, self.fig )
        self.ax = self.fig.add_axes([80.0/self.conf.CANVAS_WIDTH,  # 80px
                                     60.0/self.conf.CANVAS_HEIGHT,  # 60px
                                     1.0-2*80.0/self.conf.CANVAS_WIDTH,
                                     1.0-2*60.0/self.conf.CANVAS_HEIGHT])
        self.ax.axis(self.plotAreaXY)
        self.ax.set_aspect('equal')
        self.toolbar = NavigationToolbar2WxAgg(self.canvas)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, flag=wx.EXPAND, proportion=1)
        vbox.Add(self.toolbar, flag=wx.EXPAND, proportion=0)
        viewPanel.SetSizerAndFit(vbox)

        self.rangePanel = wx.Panel(self, wx.ID_ANY)
        self.startSlider = wx.Slider(self.rangePanel, self.ID_STARTSLIDER, style=wx.SL_HORIZONTAL, 
                                     value=1, minValue=1, maxValue=len(self.D[self.tr].T))
        self.stopSlider = wx.Slider(self.rangePanel, self.ID_STOPSLIDER, style=wx.SL_HORIZONTAL, 
                                     value=len(self.D[self.tr].T), minValue=1, maxValue=len(self.D[self.tr].T))
        self.tcStart = wx.TextCtrl(self.rangePanel, self.ID_STARTCTRL, '1', style=wx.TE_PROCESS_ENTER|wx.TE_RIGHT)
        self.tcStop = wx.TextCtrl(self.rangePanel, self.ID_STOPCTRL, str(len(self.D[self.tr].T)), style=wx.TE_PROCESS_ENTER|wx.TE_RIGHT)
        self.tcStartTime = wx.TextCtrl(self.rangePanel, wx.ID_ANY, '%.1f'%(self.D[self.tr].T[0]), style=wx.TE_RIGHT)
        self.tcStopTime = wx.TextCtrl(self.rangePanel, wx.ID_ANY, '%.1f'%(self.D[self.tr].T[-1]), style=wx.TE_RIGHT)
        self.startSlider.Bind(wx.EVT_SLIDER, self.updateRangeSlider)
        self.stopSlider.Bind(wx.EVT_SLIDER, self.updateRangeSlider)
        self.tcStart.Bind(wx.EVT_TEXT_ENTER, self.updateRangeCtrl)
        self.tcStop.Bind(wx.EVT_TEXT_ENTER, self.updateRangeCtrl)
        self.tcStartTime.Enable(False)
        self.tcStopTime.Enable(False)
        box = wx.FlexGridSizer(2, 3, 0, 0)
        box.Add(self.startSlider, flag=wx.EXPAND)
        box.Add(self.tcStart)
        box.Add(self.tcStartTime)
        box.Add(self.stopSlider, flag=wx.EXPAND)
        box.Add(self.tcStop)
        box.Add(self.tcStopTime)
        box.AddGrowableCol(0)
        self.rangePanel.SetSizerAndFit(box)

        self.fpsPanel = wx.Panel(self, wx.ID_ANY)
        stFPS = wx.StaticText(self.fpsPanel, wx.ID_ANY, 'FPS:')
        self.tcFPS = wx.TextCtrl(self.fpsPanel, wx.ID_ANY, '15', style=wx.TE_PROCESS_ENTER|wx.TE_RIGHT)
        stStep = wx.StaticText(self.fpsPanel, wx.ID_ANY, 'Step:')
        self.tcStep = wx.TextCtrl(self.fpsPanel, wx.ID_ANY, '1', style=wx.TE_PROCESS_ENTER|wx.TE_RIGHT)
        estimDur = float(len(self.D[self.tr].T))/(15*1)
        self.stEstimate = wx.StaticText(self.fpsPanel, wx.ID_ANY, 'Estimated movie duration: %.1f sec (%s)' % (estimDur, datetime.timedelta(seconds=estimDur)))
        self.stProgress = wx.StaticText(self.fpsPanel, wx.ID_ANY, '-/- (-%)')
        self.tcFPS.Bind(wx.EVT_TEXT_ENTER, self.updateEstimation)
        self.tcStep.Bind(wx.EVT_TEXT_ENTER, self.updateEstimation)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(stFPS, flag=wx.LEFT, border=5)
        box.Add(self.tcFPS)
        box.Add(stStep, flag=wx.LEFT, border=5)
        box.Add(self.tcStep)
        box.Add(self.stEstimate, flag=wx.LEFT, border=5)
        box.Add(self.stProgress, flag=wx.LEFT, border=5)
        self.fpsPanel.SetSizer(box)

        buttonPanel = wx.Panel(self, wx.ID_ANY)
        self.startButton = wx.Button(buttonPanel, wx.ID_ANY, 'Start animation')
        self.stopButton = wx.Button(buttonPanel, wx.ID_ANY, 'Stop animation')
        self.stopButton.Enable(False)
        self.cbShowAxes = wx.CheckBox(buttonPanel, wx.ID_ANY, 'Show axes')
        self.showAxes = True
        self.cbShowAxes.SetValue(self.showAxes)
        self.cbShowAxes.Bind(wx.EVT_CHECKBOX, self.plotData)
        self.cbSaveToFile = wx.CheckBox(buttonPanel, wx.ID_ANY, 'Save to file')
        self.cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Close')
        self.startButton.Bind(wx.EVT_BUTTON, self.startAnimation)
        self.stopButton.Bind(wx.EVT_BUTTON, self.stopAnimation)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.cancel)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.startButton)
        hbox.Add(self.stopButton)
        hbox.Add(self.cbShowAxes)
        hbox.Add(self.cbSaveToFile)
        hbox.Add(self.cancelButton)
        buttonPanel.SetSizerAndFit(hbox)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(viewPanel)
        vbox.Add(self.rangePanel, flag=wx.EXPAND)
        vbox.Add(self.fpsPanel, flag=wx.EXPAND)
        vbox.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(vbox)
        
        self.plotData()

        self.Show()
        
        #TODO: fps Step res *bitrate

    def updateRangeSlider(self, event=None):
        st = self.startSlider.GetValue()
        e = self.stopSlider.GetValue()
        if event.Id == self.ID_STARTSLIDER:
            if st>=e:
                st = e-1
                self.startSlider.SetValue(st)
            self.tcStart.SetValue(str(st))
            self.tcStartTime.SetValue('%.1f'%(self.D[self.tr].T[st-1]))
        elif event.Id == self.ID_STOPSLIDER:
            if st>=e:
                e = st+1
                self.stopSlider.SetValue(e)
            self.tcStop.SetValue(str(e))
            self.tcStopTime.SetValue('%.1f'%(self.D[self.tr].T[e-1]))

        self.plotData()
        self.updateEstimation()

    def updateRangeCtrl(self, event=None):
        try:
            st = int(self.tcStart.GetValue())
        except:
            self.tcStart.SetVaue(str(self.startSlider.GetValue()))
        try:
            e = int(self.tcStop.GetValue())
        except:
            self.tcStop.SetVaue(str(self.stopSlider.GetValue()))
        if event.Id == self.ID_STARTCTRL:
            if st>=e:
                st = e-1
                self.tcStart.SetValue(str(st))
            self.startSlider.SetValue(st)
            self.tcStartTime.SetValue('%.1f'%(self.D[self.tr].T[st-1]))
        elif event.Id == self.ID_STOPCTRL:
            if st>=e:
                e = st+1
                self.tcStop.SetValue(str(e))
            self.stopSlider.SetValue(e)
            self.tcStopTime.SetValue('%.1f'%(self.D[self.tr].T[e-1]))

        self.plotData()
        self.updateEstimation()

    def updateEstimation(self, event=None):
        try:
            fps = int(self.tcFPS.GetValue())
        except:
            self.tcFPS.SetValue('15')
            fps = 15
        try:
            step = int(self.tcStep.GetValue())
        except:
            self.tcStep.SetValue('1')
            step = 1
        if fps<=0:
            self.tcFPS.SetValue('15')
            fps = 15
        if step<=0:
            self.tcFPS.SetValue('1')
            step=1
        st = int(self.tcStart.GetValue())
        e = int(self.tcStop.GetValue())
        estimDur = float(e-st)/(fps*step)
        self.stEstimate.SetLabel('Estimated movie duration: %.1f sec (%s)' % (estimDur, datetime.timedelta(seconds=estimDur)))

    def startAnimation(self, event=None):
        self.saveMovie = self.cbSaveToFile.GetValue()
        self.step = int(self.tcStep.GetValue())
        if self.saveMovie:
            fps = int(self.tcFPS.GetValue())
            try:
                FFMpegWriter = matplotlib.animation.writers['ffmpeg']
            except:
                if sys.platform == 'win32':
                    try:
                        import imageio_ffmpeg
                        bindir = os.path.join(os.path.dirname(imageio_ffmpeg.__file__),'binaries')
                        for f in os.listdir(bindir):
                            m = re.match('ffmpeg.*\.exe', f)
                            if m is not None:
                                ffmpeg_path = os.path.join(bindir,f)
                                matplotlib.rcParams['animation.ffmpeg_path'] = ffmpeg_path
                                FFMpegWriter = matplotlib.animation.writers['ffmpeg']
                                break
                    except:
                        DlgShowinfo(self, 'Info', 'FFmpeg is not found. Add ffmpeg to PATH or install imageio_ffmpeg package.')
                        return
                else:
                    DlgShowinfo(self, 'Info', 'FFmpeg is not found. Add ffmpeg to PATH.')
                    return

            metadata = dict(title=self.parent.dataFileName, artist='GazeParser Data Viewer', comment='Trial %d' % (self.tr))
            self.writer = FFMpegWriter(fps=fps, bitrate=-1, metadata=metadata)
            fname = DlgAsksaveasfilename(self, initialdir=self.parent.initialDataDir, filetypes='mp4 file (*.mp4)|*.mp4')
            if fname == '':
                return
            self.writer.setup(self.fig, fname, dpi=100)
        self.index = self.startSlider.GetValue()-1
        self.startindex = self.index
        self.stopindex = self.stopSlider.GetValue()
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.clear()
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        # set plotrange and axis labels

        if self.showAxes:
            self.ax.set_position([80.0/self.conf.CANVAS_WIDTH, 60.0/self.conf.CANVAS_HEIGHT,
                1.0-2*80.0/self.conf.CANVAS_WIDTH, 1.0-2*60.0/self.conf.CANVAS_HEIGHT])
            if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
                self.ax.set_xlabel('Vertical gaze position (pix)', fontproperties=self.fontPlotText)
                self.ax.set_ylabel('Horizontal gaze position (pix)', fontproperties=self.fontPlotText)
            elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
                self.ax.set_xlabel('Vertical gaze position (deg)', fontproperties=self.fontPlotText)
                self.ax.set_ylabel('Horizontal gaze position (deg)', fontproperties=self.fontPlotText)
        else:
            self.ax.set_position([0.0, 0.0, 1.0, 1.0])
            self.ax.axis('off')


        if self.conf.CANVAS_SHOW_STIMIMAGE:
            self.ax.imshow(self.stimImage, extent=self.stimImageExtent, origin='upper')
        if self.hasLData:
            self.l, = self.ax.plot([],[],'-o', color=self.conf.COLOR_TRAJECTORY_L_X)
        if self.hasRData:
            self.r, = self.ax.plot([],[],'-o', color=self.conf.COLOR_TRAJECTORY_R_X)

        self.startButton.Enable(False)
        self.stopButton.Enable(True)
        self.cancelButton.Enable(False)
        self.rangePanel.Enable(False)
        self.cbShowAxes.Enable(False)
        self.cbSaveToFile.Enable(False)

        self.timer.Start(100)

    def stopAnimation(self, event=None):
        if self.saveMovie:
            self.writer.finish()
        self.timer.Stop()
        self.startButton.Enable(True)
        self.stopButton.Enable(False)
        self.cancelButton.Enable(True)
        self.rangePanel.Enable(True)
        self.cbShowAxes.Enable(True)
        self.cbSaveToFile.Enable(True)

        self.stProgress.SetLabelText('-/- (-%)')
        if event is None:
            DlgShowinfo(self, 'Info', 'Finished')

    def onTimer(self, event=None):
        if self.index < self.stopindex:
            total = self.stopindex-self.startindex
            current = self.index-self.startindex
            self.stProgress.SetLabelText('{}/{} ({:.1f}%)'.format(current,total,(current/total)*100))

            if self.showAxes:
                t = self.D[self.tr].T[self.index]
                self.ax.set_title('time: %.1f ms (%s)' % (t, datetime.timedelta(seconds=t/1000)))
            if self.hasLData:
                self.l.set_data(self.sf[0]*self.D[self.tr].L[self.index][0], self.sf[1]*self.D[self.tr].L[self.index][1])
            if self.hasRData:
                self.r.set_data(self.sf[0]*self.D[self.tr].R[self.index][0], self.sf[1]*self.D[self.tr].R[self.index][1])
            self.index += self.step
            self.canvas.draw()
            if self.saveMovie:
                self.writer.grab_frame()
        else:
            self.stopAnimation(event=None)

    def cancel(self, event=None):
        self.Close()

    def plotData(self, event=None):
        self.showAxes = self.cbShowAxes.GetValue()

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.clear()
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)

        # stimulus image
        if self.conf.CANVAS_SHOW_STIMIMAGE:
            self.ax.imshow(self.stimImage, extent=self.stimImageExtent, origin='upper')

        st = self.startSlider.GetValue()-1 # 1 must be subtracted
        e = self.stopSlider.GetValue()

        # ---- xy plot ----
        if self.hasLData:
            self.ax.plot(self.sf[0]*self.D[self.tr].L[st:e,0], self.sf[1]*self.D[self.tr].L[st:e,1], '-', color=self.conf.COLOR_TRAJECTORY_L_X)
        if self.hasRData:
            self.ax.plot(self.sf[0]*self.D[self.tr].R[st:e,0], self.sf[1]*self.D[self.tr].R[st:e,1], '-', color=self.conf.COLOR_TRAJECTORY_R_X)
        # ---- xy plot ----

        # set plotrange and axis labels
        if self.showAxes:
            self.ax.set_position([80.0/self.conf.CANVAS_WIDTH, 60.0/self.conf.CANVAS_HEIGHT,
                1.0-2*80.0/self.conf.CANVAS_WIDTH, 1.0-2*60.0/self.conf.CANVAS_HEIGHT])
            if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
                self.ax.set_xlabel('Vertical gaze position (pix)', fontproperties=self.fontPlotText)
                self.ax.set_ylabel('Horizontal gaze position (pix)', fontproperties=self.fontPlotText)
            elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
                self.ax.set_xlabel('Vertical gaze position (deg)', fontproperties=self.fontPlotText)
                self.ax.set_ylabel('Horizontal gaze position (deg)', fontproperties=self.fontPlotText)

            self.ax.set_title('%s: Trial %d / %d' % (os.path.basename(self.dataFileName), self.tr+1, len(self.D)), fontproperties=self.fontPlotText)
        else:
            self.ax.set_position([0.0, 0.0, 1.0, 1.0])
            self.ax.axis('off')
        
        self.fig.canvas.draw()


class convertDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(convertDialog, self).__init__(parent=parent, id=id, title='GazeParser datafile converter')

        self.mainWindow = parent
        if self.mainWindow is None:
            self.initialDataDir = GazeParser.homeDir
        else:
            self.initialDataDir = self.mainWindow.initialDataDir
        self.configuration = GazeParser.Configuration.Config()
        
        self.paramEntryDict = {}

        self.commandPanel = wx.Panel(self, wx.ID_ANY)

        self.datafileTypeChoices = ['SimpleGazeTracker CSV',
            'PsychoPy_Tobii_Controller TSV']
        self.datafileType = 'SimpleGazeTracker CSV'
        self.rbDatafileType = wx.RadioBox(self.commandPanel, wx.ID_ANY, 'Datafile Type', choices=self.datafileTypeChoices, style=wx.RA_VERTICAL)
        self.rbDatafileType.Bind(wx.EVT_RADIOBOX, self.onClickDatafileType)
        
        self.useEmbeddedChoices = ['Use parameters embedded in the data file',
            'Use parameters shown in this dialog']
        self.rbUseEmbedded = wx.RadioBox(self.commandPanel, wx.ID_ANY, 'Use embedded parameters', choices=self.useEmbeddedChoices, style=wx.RA_VERTICAL)
        self.rbUseEmbedded.Bind(wx.EVT_RADIOBOX, self.onClickUseEmbedded)

        self.tobiiOptionPanel = wx.StaticBox(self.commandPanel, wx.ID_ANY, 'Conversion options')
        tobiiOptionSizer = wx.StaticBoxSizer(self.tobiiOptionPanel, wx.VERTICAL)
        self.cbHeightToPix = wx.CheckBox(self.tobiiOptionPanel, wx.ID_ANY, 'Height to Pix')
        tobiiOptionSizer.Add(self.cbHeightToPix)
        self.tobiiOptionPanel.Hide()

        configFilePanel = wx.StaticBox(self.commandPanel, wx.ID_ANY, 'Configuration file')
        configFileSizer = wx.StaticBoxSizer(configFilePanel, wx.VERTICAL)
        loadConfigButton = wx.Button(configFilePanel, wx.ID_ANY, 'Load Configuration File')
        exportConfigButton = wx.Button(configFilePanel, wx.ID_ANY, 'Export current parameters')
        loadConfigButton.Bind(wx.EVT_BUTTON, self.loadConfig)
        exportConfigButton.Bind(wx.EVT_BUTTON, self.exportConfig)
        configFileSizer.Add(loadConfigButton, flag=wx.EXPAND)
        configFileSizer.Add(exportConfigButton, flag=wx.EXPAND)

        convertPanel = wx.StaticBox(self.commandPanel, wx.ID_ANY, 'Convert')
        convertSizer = wx.StaticBoxSizer(convertPanel, wx.VERTICAL)
        self.cbOverwrite = wx.CheckBox(convertPanel, wx.ID_ANY, 'Overwrite')
        convertButton = wx.Button(convertPanel, wx.ID_ANY, 'Convert Files')
        convertButton.Bind(wx.EVT_BUTTON, self.convertFiles)
        convertSizer.Add(convertButton, flag=wx.EXPAND)
        convertSizer.Add(self.cbOverwrite, flag=wx.EXPAND)

        cancelButton = wx.Button(self.commandPanel, wx.ID_ANY, 'Close')
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.rbDatafileType, flag=wx.EXPAND)
        box.Add(self.rbUseEmbedded, flag=wx.EXPAND)
        box.Add(tobiiOptionSizer, flag=wx.EXPAND)
        box.Add(configFileSizer, flag=wx.TOP|wx.EXPAND, border=30)
        box.Add(convertSizer, flag=wx.TOP|wx.EXPAND, border=10)
        box.Add(cancelButton, flag=wx.TOP|wx.ALIGN_CENTER, border=30)

        self.commandPanel.SetSizer(box)

        self.filterCommands = ['identity', 'ma', 'butter', 'butter_filtfilt']
        
        self.paramPanel = wx.Panel(self, wx.ID_ANY)
        box = wx.FlexGridSizer(len(GazeParser.Configuration.GazeParserOptions), 2, 0, 0)
        for key in GazeParser.Configuration.GazeParserOptions:
            box.Add(wx.StaticText(self.paramPanel, wx.ID_ANY, key))
            if key == 'FILTER_TYPE':
                self.paramEntryDict[key] = wx.ComboBox(self.paramPanel, wx.ID_ANY, choices=self.filterCommands, style=wx.CB_DROPDOWN)
                self.paramEntryDict[key].SetValue(getattr(self.configuration, key))
                self.paramEntryDict[key].Bind(wx.EVT_COMBOBOX, self.onClickUseEmbedded)
            else:
                self.paramEntryDict[key] = wx.TextCtrl(self.paramPanel, wx.ID_ANY, str(getattr(self.configuration, key)))
            box.Add(self.paramEntryDict[key])
        self.paramPanel.SetSizer(box)
        self.onClickUseEmbedded()
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.commandPanel, flag=wx.ALL, border=5)
        box.Add(self.paramPanel, flag=wx.ALL, border=5)
        self.SetSizerAndFit(box)
        
        self.Show()

    def convertFiles(self, event=None):
        datafileType = self.datafileTypeChoices[self.rbDatafileType.GetSelection()]
        if datafileType == 'SimpleGazeTracker CSV':
            fnames = DlgAskopenfilenames(self, filetypes='SimpleGazeTracker CSV file (*.csv)|*.csv', initialdir=self.initialDataDir)
        elif datafileType == 'PsychoPy_Tobii_Controller TSV':
            fnames = DlgAskopenfilenames(self, filetypes='PsychoPy_Tobii_Controller TSV file (*.tsv)|*.tsv', initialdir=self.initialDataDir)
        else:
            DlgShowerror(self, 'Error', 'Invalid datafile type ({})'.format(datafileType))
            return

        if fnames == []:
            DlgShowinfo(self, 'info', 'No files')
            return

        self.initialDataDir = os.path.split(fnames[0])[0]
        if self.mainWindow is not None:
            self.mainWindow.initialDataDir = self.initialDataDir

        if self.cbOverwrite.GetValue():
            overwrite = True
        else:
            overwrite = False

        if datafileType == 'SimpleGazeTracker CSV':
            usefileparameters = True if self.rbUseEmbedded.GetSelection()==0 else False

        if datafileType == 'PsychoPy_Tobii_Controller TSV':
            unitcnv = 'height2pix' if self.cbHeightToPix.GetValue() else None

        self.updateParameters()

        donelist = []
        errorlist = []
        nProcessed = 0
        with wx.ProgressDialog(title='Converting...',message='0/{}'.format(len(fnames)),maximum=len(fnames)) as progressDlg:
            for f in fnames:
                res = 'FAILED'
                try:
                    if datafileType == 'SimpleGazeTracker CSV':
                        res = GazeParser.Converter.TrackerToGazeParser(f, overwrite=overwrite, config=self.configuration, useFileParameters=usefileparameters)
                    elif datafileType == 'PsychoPy_Tobii_Controller TSV':
                        res = GazeParser.Converter.PTCToGazeParser(f, overwrite=overwrite, config=self.configuration, unitcnv=unitcnv)
                except:
                    info = sys.exc_info()
                    tbinfo = traceback.format_tb(info[2])
                    errormsg = ''
                    for tbi in tbinfo:
                        errormsg += tbi
                    errormsg += '  %s' % str(info[1])
                    errorlist.append(f)
                    if not DlgAskyesno(self, 'Error', errormsg + '\n\nConvert remaining files?'):
                        break
                else:
                    if res == 'SUCCESS':
                        donelist.append(f)
                    else:
                        errorlist.append(f)
                        if not DlgAskyesno(self, 'Error', res + '\n\nConvert remaining files?'):
                            break
                nProcessed += 1
                progressDlg.Update(value=nProcessed, newmsg='{}/{}'.format(nProcessed, len(fnames)))
        msg = 'Convertion done.\n'
        if len(donelist) <= 16:
            msg += '\n'.join(donelist)
        else:
            msg += '%d files were successfully converted.\n' % len(donelist)
        if 0 < len(errorlist) <= 16:
            msg += '\n\nError.\n'+'\n'.join(errorlist)
        elif len(errorlist) > 16:
            msg += '\n\nError.\n%d files were failed to convert.' % len(errorlist)
        DlgShowinfo(self, 'info', msg)

    def loadConfig(self, event=None):
        # self.ftypes = [('GazeParser ConfigFile', '*.cfg')]
        self.ftypes = 'GazeParser ConfigFile (*.cfg)|*.cfg'
        #if os.path.exists(GazeParser.configDir):
        #    initialdir = GazeParser.configDir
        #else:
        #    initialdir = GazeParser.homeDir
        self.configFileName = DlgAskopenfilename(self, filetypes=self.ftypes, initialdir=self.initialDataDir)
        if self.configFileName == '':
            return
        try:
            self.configuration = GazeParser.Configuration.Config(self.configFileName)
        except:
            DlgShowerror(self, 'GazeParser.Configuration.GUI', 'Cannot read %s.\nThis file may not be a GazeParser ConfigFile' % self.configFileName)
            return

        if self.mainWindow is not None:
            self.initialDataDir = os.path.split(self.configFileName)[0]
            self.mainWindow.initialDataDir = self.initialDataDir

        for key in GazeParser.Configuration.GazeParserOptions:
            self.paramEntryDict[key].SetValue(str(getattr(self.configuration, key)))

    def exportConfig(self, event=None):
        """
        Based on: Gazeparser.app.ConfigEditor._saveas()
        """
        # self.ftypes = [('GazeParser ConfigFile', '*.cfg')]
        self.ftypes = 'GazeParser ConfigFile (*.cfg)|*.cfg'
        for key in GazeParser.Configuration.GazeParserOptions:
            if self.paramEntryDict[key].GetValue() == '':
                DlgShowerror(self, 'GazeParser.Configuration.GUI', '\'%s\' is empty.\nConfiguration is not saved.' % key)
                return

        try:
            fdir = os.path.split(self.ConfigFileName)[0]
        except:
            if os.path.exists(GazeParser.configDir):
                fdir = GazeParser.configDir
            else:
                fdir = GazeParser.homeDir
        fname = DlgAsksaveasfilename(self, filetypes=self.ftypes, initialdir=fdir)

        if fname == '':
            return

        try:
            fp = open(fname, 'w')
        except:
            DlgShowerror(self, 'Error', 'Could not open \'%s\'' % fname)
            return

        fp.write('[GazeParser]\n')
        for key in GazeParser.Configuration.GazeParserOptions:
            fp.write('%s = %s\n' % (key, self.paramEntryDict[key].GetValue()))
        fp.close()

        DlgShowinfo(self, 'Info', 'Saved to \'%s\'' % fname)

    def updateParameters(self, event=None):
        for key in GazeParser.Configuration.GazeParserOptions:
            value = self.paramEntryDict[key].GetValue()
            if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                setattr(self.configuration, key, int(value))
            elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                setattr(self.configuration, key, float(value))
            else:
                setattr(self.configuration, key, value)

    def onClickDatafileType(self, event=None):
        if self.rbDatafileType.GetSelection()==0:
            self.datafileType = 'SimpleGazeTracker CSV'
            self.rbUseEmbedded.Show()
            #self.cbHeightToPix.Hide()
            self.tobiiOptionPanel.Hide()
        else:
            self.datafileType = 'PsychoPy_Tobii_Controller TSV'
            self.rbUseEmbedded.SetSelection(1) # Use parameters shown in this dialog
            self.rbUseEmbedded.Hide()
            #self.cbHeightToPix.Show()
            self.tobiiOptionPanel.Show()
        
        self.commandPanel.Layout()
        self.onClickUseEmbedded()

    def onClickUseEmbedded(self, event=None):
        if self.rbUseEmbedded.GetSelection()==0:
            self.paramPanel.Enable(False)
        else:
            self.paramPanel.Enable(True)
            
            filterStr = self.paramEntryDict['FILTER_TYPE'].GetValue()
            self.paramEntryDict['FILTER_TYPE'].SetValue(filterStr)
            if filterStr == 'ma':
                self.paramEntryDict['FILTER_SIZE'].Enable(True)
                self.paramEntryDict['FILTER_ORDER'].Enable(False)
                self.paramEntryDict['FILTER_WN'].Enable(False)
            elif filterStr in ['butter', 'butter_filtfilt']:
                self.paramEntryDict['FILTER_SIZE'].Enable(False)
                self.paramEntryDict['FILTER_ORDER'].Enable(True)
                self.paramEntryDict['FILTER_WN'].Enable(True)
            else:
                self.paramEntryDict['FILTER_SIZE'].Enable(False)
                self.paramEntryDict['FILTER_ORDER'].Enable(False)
                self.paramEntryDict['FILTER_WN'].Enable(False)

    def cancel(self, event=None):
        self.Close()


class interactiveConfigFrame(wx.Frame):
    def __init__(self, parent, id=wx.ID_ANY):
        super(interactiveConfigFrame, self).__init__(parent=parent, id=id, title='GazeParser configuration file editor')
        self.configtypes = 'GazeParser Configuration File (*.cfg)|*.cfg'
        if parent.D is None:
            DlgShowerror(self, 'Error', 'No data')
            return

        self.D = parent.D
        self.C = parent.C
        self.conf = parent.conf
        self.tr = 0
        self.dataFileName = parent.dataFileName
        self.fontPlotText = parent.fontPlotText
        self.newFixList = None
        self.newSacList = None
        self.newL = None
        self.newR = None
        self.newConfig = GazeParser.Configuration.Config()

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

        menu_bar = wx.MenuBar()
        menu_file = wx.Menu()
        self.menu_view = wx.Menu()
        menu_bar.Append(menu_file, 'File')
        menu_bar.Append(self.menu_view, 'View')
        menu_file.Append(ID_EXPORT, 'Export Config')
        menu_file.Append(wx.ID_CLOSE, 'Close')
        self.Bind(wx.EVT_MENU, self.exportConfig, id=ID_EXPORT)
        self.Bind(wx.EVT_MENU, self.cancel, id=wx.ID_CLOSE)
        self.menu_view.Append(ID_PREV_TR, 'Prev Trial')
        self.menu_view.Append(ID_NEXT_TR, 'Next Trial')
        self.Bind(wx.EVT_MENU, self.prevTrial, id=ID_PREV_TR)
        self.Bind(wx.EVT_MENU, self.nextTrial, id=ID_NEXT_TR)
        
        ac = []
        keys = ((wx.WXK_LEFT,self.prevTrial),
                (wx.WXK_RIGHT,self.nextTrial))
        for key in keys:
            _id = wx_NewIdRef()
            ac.append((wx.ACCEL_NORMAL, key[0], _id))
            self.Bind(wx.EVT_MENU, key[1], id=_id)
        tbl = wx.AcceleratorTable(ac)
        self.SetAcceleratorTable(tbl)

        self.SetMenuBar(menu_bar)

        ########
        # mainFrame (includes viewFrame, xRangeBarFrame)
        # viewFrame
        viewPanel = wx.Panel(self, wx.ID_ANY)
        self.fig = matplotlib.figure.Figure( None )
        self.canvas = FigureCanvasWxAgg( viewPanel, wx.ID_ANY, self.fig )
        self.ax = self.fig.add_axes([80.0/self.conf.CANVAS_WIDTH,  # 80px
                                     60.0/self.conf.CANVAS_HEIGHT,  # 60px
                                     1.0-2*80.0/self.conf.CANVAS_WIDTH,
                                     1.0-2*60.0/self.conf.CANVAS_HEIGHT])
        self.ax.axis(self.currentPlotArea)
        self.toolbar = NavigationToolbar2WxAgg(self.canvas)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, flag=wx.EXPAND, proportion=1)
        vbox.Add(self.toolbar, flag=wx.EXPAND, proportion=0)
        viewPanel.SetSizerAndFit(vbox)
        
        self.paramEntryDict = {}
        self.filterCommands = ['identity', 'ma', 'butter', 'butter_filtfilt']

        commandPanel = wx.Panel(self, wx.ID_ANY)
        paramPanel = wx.Panel(commandPanel, wx.ID_ANY)
        box = wx.FlexGridSizer(len(GazeParser.Configuration.GazeParserOptions)+1,3, 0, 0)
        box.Add(wx.StaticText(paramPanel, wx.ID_ANY, ''), flag=wx.ALL, border=5)
        box.Add(wx.StaticText(paramPanel, wx.ID_ANY, 'Original'), flag=wx.TOP|wx.RIGHT|wx.BOTTOM, border=5)
        box.Add(wx.StaticText(paramPanel, wx.ID_ANY, 'New'), flag=wx.TOP|wx.RIGHT|wx.BOTTOM, border=5)
        for key in GazeParser.Configuration.GazeParserOptions:
            box.Add(wx.StaticText(paramPanel, wx.ID_ANY, key), flag=wx.LEFT|wx.RIGHT, border=5)
            if hasattr(self.D[self.tr].config, key):
                # note: Value of GazeParser parameters are ASCII characters.
                box.Add(wx.StaticText(paramPanel, wx.ID_ANY, str(getattr(self.D[self.tr].config, key))), flag=wx.RIGHT, border=5)

                if key == 'FILTER_TYPE':
                    self.paramEntryDict[key] = wx.ComboBox(paramPanel, wx.ID_ANY, choices=self.filterCommands, style=wx.CB_DROPDOWN)
                    # note: Value of FILTER_TYPE is string, so str() is not necessary.
                    self.paramEntryDict[key].SetValue(getattr(self.D[self.tr].config, key))
                    self.paramEntryDict[key].Bind(wx.EVT_COMBOBOX, self.onClickCombobox)
                else:
                    # note: Value of GazeParser parameters are ASCII characters.
                    self.paramEntryDict[key] = wx.TextCtrl(paramPanel, wx.ID_ANY, str(getattr(self.D[self.tr].config, key)))
                box.Add(self.paramEntryDict[key], flag=wx.RIGHT, border=5)

            else:
                box.Add(wx.StaticText(paramPanel, wx.ID_ANY, 'not available'), flag=wx.RIGHT, border=5)
                
                if key == 'FILTER_TYPE':
                    self.paramEntryDict[key] = wx.ComboBox(paramPanel, wx.ID_ANY, choices=self.filterCommands, style=wx.CB_DROPDOWN)
                    self.paramEntryDict[key].SetValue(GazeParser.Configuration.GazeParserDefaults[key])
                    self.paramEntryDict[key].Bind(wx.EVT_COMBOBOX, self.onClickCombobox)
                else:
                    # note: Value of GazeParser parameters are ASCII characters.
                    self.paramEntryDict[key] = wx.TextCtrl(paramPanel, wx.ID_ANY, str(GazeParser.Configuration.GazeParserDefaults[key]))
                box.Add(self.paramEntryDict[key], flag=wx.RIGHT, border=5)


        paramPanel.SetSizer(box)

        updateButton = wx.Button(commandPanel, wx.ID_ANY, 'Update plot')
        updateButton.Bind(wx.EVT_BUTTON, self.updateParameters)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(paramPanel)
        vbox.Add(updateButton, flag=wx.EXPAND|wx.ALL, border=5)
        commandPanel.SetSizerAndFit(vbox)

        self.onClickCombobox()
        self.plotData()
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(viewPanel)
        hbox.Add(commandPanel, flag=wx.EXPAND)
        self.SetSizerAndFit(hbox)
        
        self.Bind(wx.EVT_CLOSE, self.onClose)
        
        # self.MakeModal(True)
        self.Show()
        self.eventLoop = wx.GUIEventLoop()
        self.eventLoop.Run()

    def onClose(self, event=None):
        # self.MakeModal(False)
        self.eventLoop.Exit()

    def onClickCombobox(self, event=None):
        filterStr = self.paramEntryDict['FILTER_TYPE'].GetValue()
        self.paramEntryDict['FILTER_TYPE'].SetValue(filterStr)
        if filterStr == 'ma':
            self.paramEntryDict['FILTER_SIZE'].Enable(True)
            self.paramEntryDict['FILTER_ORDER'].Enable(False)
            self.paramEntryDict['FILTER_WN'].Enable(False)
        elif filterStr in ['butter', 'butter_filtfilt']:
            self.paramEntryDict['FILTER_SIZE'].Enable(False)
            self.paramEntryDict['FILTER_ORDER'].Enable(True)
            self.paramEntryDict['FILTER_WN'].Enable(True)
        else:
            self.paramEntryDict['FILTER_SIZE'].Enable(False)
            self.paramEntryDict['FILTER_ORDER'].Enable(False)
            self.paramEntryDict['FILTER_WN'].Enable(False)

    def cancel(self, event=None):
        self.Close()

    def prevTrial(self, event=None):
        if self.D is None:
            DlgShowerror(self, 'Error', 'No Data')
            return
        if self.tr > 0:
            self.tr -= 1
            if self.tr == 0:
                self.menu_view.FindItemById(ID_PREV_TR).Enable(False)
            else:
                self.menu_view.FindItemById(ID_PREV_TR).Enable(True)
            if self.tr == len(self.D)-1:
                self.menu_view.FindItemById(ID_NEXT_TR).Enable(False)
            else:
                self.menu_view.FindItemById(ID_NEXT_TR).Enable(True)
        self.updateParameters()

    def nextTrial(self, event=None):
        if self.D is None:
            DlgShowerror(self, 'Error', 'No Data')
            return
        if self.tr < len(self.D)-1:
            self.tr += 1
            if self.tr == 0:
                self.menu_view.FindItemById(ID_PREV_TR).Enable(False)
            else:
                self.menu_view.FindItemById(ID_PREV_TR).Enable(True)
            if self.tr == len(self.D)-1:
                self.menu_view.FindItemById(ID_NEXT_TR).Enable(False)
            else:
                self.menu_view.FindItemById(ID_NEXT_TR).Enable(True)
        self.updateParameters()

    def plotData(self):
        self.ax.clear()

        tStart = self.D[self.tr].T[0]
        t = self.D[self.tr].T-tStart
        if self.newL is not None:
            self.ax.plot(t, self.newL[:, 0], ':', color=self.conf.COLOR_TRAJECTORY_L_X)
            self.ax.plot(t, self.newL[:, 1], ':', color=self.conf.COLOR_TRAJECTORY_L_Y)
        if self.newR is not None:
            self.ax.plot(t, self.newR[:, 0], ':', color=self.conf.COLOR_TRAJECTORY_R_X)
            self.ax.plot(t, self.newR[:, 1], ':', color=self.conf.COLOR_TRAJECTORY_R_Y)
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
                              fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))  # hatch='///', 

        if self.newSacList is not None and self.newFixList is not None:
            for f in range(len(self.newFixList)):
                # note: color is reversed
                self.ax.text(self.newFixList[f].startTime-tStart, self.newFixList[f].center[0]-50, str(f), color=self.conf.COLOR_FIXATION_BG,
                             bbox=dict(boxstyle="round", fc=self.conf.COLOR_FIXATION_FC, clip_on=True, clip_box=self.ax.bbox), clip_on=True)

            hatchColor = getComplementaryColorStr(self.conf.COLOR_SACCADE_HATCH)
            for s in range(len(self.newSacList)):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.newSacList[s].startTime-tStart, -10000], self.newSacList[s].duration, 20000,
                                  fc=hatchColor, alpha=0.3))  # hatch='\\\\\\', 

        self.ax.axis(self.currentPlotArea)
        self.ax.set_title('%s: Trial %d / %d' % (os.path.basename(self.dataFileName), self.tr+1, len(self.D)), fontproperties=self.fontPlotText)

        self.fig.canvas.draw()

    def updateParameters(self, event=None):
        if self.D is None:
            DlgShowerror(self, 'Error', 'No data!')
            return

        try:
            for key in GazeParser.Configuration.GazeParserOptions:
                value = self.paramEntryDict[key].GetValue()
                if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                    setattr(self.newConfig, key, int(value))
                elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                    setattr(self.newConfig, key, float(value))
                else:
                    setattr(self.newConfig, key, value)
        except:
            DlgShowerror(self, 'Error', 'Illeagal value in '+key)
            return

        offset = PLOT_OFFSET
        try:
            # from GazeParser.Converter.TrackerToGazeParser
            if self.newConfig.RECORDED_EYE == 'B':
                self.newL = applyFilter(self.D[self.tr].T, self.D[self.tr].L, self.newConfig, decimals=8) + offset
                self.newR = applyFilter(self.D[self.tr].T, self.D[self.tr].R, self.newConfig, decimals=8) + offset
                print(self.newConfig.AVERAGE_LR)
                if self.newConfig.AVERAGE_LR == 0:
                    (SacList, FixList, BlinkList) = buildEventListBinocular(self.D[self.tr].T, self.newL, self.newR, self.newConfig)
                elif self.newConfig.AVERAGE_LR == 1:
                    newB = np.nanmean([self.newL, self.newR], axis=0)
                    (SacList, FixList, BlinkList) = buildEventListMonocular(self.D[self.tr].T, newB, self.newConfig)
                else:
                    raise ValueError('AVERAGE_LR must be 0 or 1')
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
            DlgShowerror(self, 'Error', errormsg)
            self.newSacList = None
            self.newFixList = None
        else:
            self.plotData()

    def exportConfig(self, event=None):
        try:
            for key in GazeParser.Configuration.GazeParserOptions:
                value = self.paramEntryDict[key].GetValue()
                if isinstance(GazeParser.Configuration.GazeParserDefaults[key], int):
                    setattr(self.newConfig, key, int(value))
                elif isinstance(GazeParser.Configuration.GazeParserDefaults[key], float):
                    setattr(self.newConfig, key, float(value))
                else:
                    setattr(self.newConfig, key, value)
        except:
            DlgShowerror(self, 'Error', 'Illeagal value in '+key)
            return

        fname = ''
        try:
            fname = DlgAsksaveasfilename(self, filetypes=self.configtypes, initialdir=GazeParser.configDir)
            if fname == '':
                return
            self.newConfig.save(fname)
        except:
            if fname == '':
                DlgShowerror(self, 'Error', 'Could not get filename.')
            else:
                DlgShowerror(self, 'Error', 'Could not write configuration to \'' + fname + '\'')

class getFixationsInRegionDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(getFixationsInRegionDialog, self).__init__(parent=parent, id=id, title='Fxations in region')
        self.parent = parent
        self.D = parent.D
        self.C = parent.C
        self.conf = parent.conf
        self.initialDataDir = parent.initialDataDir
        
        self.commandChoices = ('Use commands embedded in the data file', 'Use commands defined here')
        self.commandCodes = ('embedded', 'dialog')
        self.rbCommandChoice = wx.RadioBox(self, wx.ID_ANY, 'Command', choices=self.commandChoices, style=wx.RA_VERTICAL)
        self.rbCommandChoice.SetSelection(0)
        self.rbCommandChoice.Bind(wx.EVT_RADIOBOX, self.onClickRadiobutton)

        self.customCommandPanel = wx.Panel(self, wx.ID_ANY)
        regionPanel = wx.Panel(self.customCommandPanel, wx.ID_ANY)
        regionPanelInside = wx.Panel(regionPanel, wx.ID_ANY)
        regionFrame = wx.StaticBox(regionPanel, wx.ID_ANY, 'Region')
        self.rbCircleRegion = wx.RadioButton(regionPanelInside, wx.ID_ANY, 'Circle')
        self.rbCircleRegion.SetValue(1)
        self.rbCircleRegion.Bind(wx.EVT_RADIOBUTTON, self.onClickRadiobutton)
        self.rbRectRegion = wx.RadioButton(regionPanelInside, wx.ID_ANY, 'Rect')
        self.rbRectRegion.SetValue(0)
        self.rbRectRegion.Bind(wx.EVT_RADIOBUTTON, self.onClickRadiobutton)
        self.tcCircleRegionX = wx.TextCtrl(regionPanelInside, wx.ID_ANY, size=(60,-1))
        self.tcCircleRegionY = wx.TextCtrl(regionPanelInside, wx.ID_ANY, size=(60,-1))
        self.tcCircleRegionR = wx.TextCtrl(regionPanelInside, wx.ID_ANY, size=(60,-1))
        self.tcRectRegionX1 = wx.TextCtrl(regionPanelInside, wx.ID_ANY, size=(60,-1))
        self.tcRectRegionY1 = wx.TextCtrl(regionPanelInside, wx.ID_ANY, size=(60,-1))
        self.tcRectRegionX2 = wx.TextCtrl(regionPanelInside, wx.ID_ANY, size=(60,-1))
        self.tcRectRegionY2 = wx.TextCtrl(regionPanelInside, wx.ID_ANY, size=(60,-1))
        box = wx.FlexGridSizer(2, 9, 0, 0)
        box.Add(self.rbCircleRegion, flag=wx.RIGHT, border=15)
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, 'x'))
        box.Add(self.tcCircleRegionX, flag=wx.RIGHT, border=10)
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, 'y'))
        box.Add(self.tcCircleRegionY, flag=wx.RIGHT, border=10)
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, 'r'))
        box.Add(self.tcCircleRegionR, flag=wx.RIGHT, border=10)
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, ''))
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, ''))
        box.Add(self.rbRectRegion, flag=wx.RIGHT, border=15)
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, 'x1'))
        box.Add(self.tcRectRegionX1, flag=wx.RIGHT, border=10)
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, 'y1'))
        box.Add(self.tcRectRegionY1, flag=wx.RIGHT, border=10)
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, 'x2'))
        box.Add(self.tcRectRegionX2, flag=wx.RIGHT, border=10)
        box.Add(wx.StaticText(regionPanelInside, wx.ID_ANY, 'y2'))
        box.Add(self.tcRectRegionY2, flag=wx.RIGHT, border=10)
        regionPanelInside.SetSizerAndFit(box)
        sbox = wx.StaticBoxSizer(regionFrame, wx.VERTICAL)
        sbox.Add(regionPanelInside)
        regionPanel.SetSizer(sbox)

        timePanel = wx.Panel(self.customCommandPanel, wx.ID_ANY)
        timeFrame = wx.StaticBox(timePanel, wx.ID_ANY, 'Time')
        self.tcFromTime = wx.TextCtrl(timePanel, wx.ID_ANY)
        self.tcToTime = wx.TextCtrl(timePanel, wx.ID_ANY)
        sbox = wx.StaticBoxSizer(timeFrame, wx.HORIZONTAL)
        sbox.Add(wx.StaticText(timePanel, wx.ID_ANY, 'From'))
        sbox.Add(self.tcFromTime, flag=wx.RIGHT, border=10)
        sbox.Add(wx.StaticText(timePanel, wx.ID_ANY, 'To'))
        sbox.Add(self.tcToTime, flag=wx.RIGHT, border=10)
        timePanel.SetSizer(sbox)
        
        self.spatialCriteriaChoices = ('The center of fixation is included in the region',
                                       'Whole trajectory of fixation is included in the region',
                                       'A part of trajectory of fixation is included in the region')
        self.spatialCriteriaCodes = ('center', 'all', 'any')
        self.rbSpatialCriteria = wx.RadioBox(self.customCommandPanel, wx.ID_ANY, 'Inclusion criteria (spatial)', choices=self.spatialCriteriaChoices, style=wx.RA_VERTICAL)

        temporalCriteriaPanel = wx.Panel(self.customCommandPanel, wx.ID_ANY)
        temporalCriteriaFrame = wx.StaticBox(temporalCriteriaPanel, wx.ID_ANY, 'Inclusion criteria (temporal)')
        self.cbTemporalCriterion = wx.CheckBox(temporalCriteriaPanel, wx.ID_ANY, 'Whole fixation must be included beween "From" and "To"')
        sbox = wx.StaticBoxSizer(temporalCriteriaFrame, wx.VERTICAL)
        sbox.Add(self.cbTemporalCriterion)
        temporalCriteriaPanel.SetSizer(sbox)

        messagePanel = wx.Panel(self.customCommandPanel, wx.ID_ANY)
        messageFrame = wx.StaticBox(messagePanel, wx.ID_ANY, 'Message')
        self.tcMessage = wx.TextCtrl(messagePanel, wx.ID_ANY)
        self.cbRegExp = wx.CheckBox(messagePanel, wx.ID_ANY, 'Regular expression')
        sbox = wx.StaticBoxSizer(messageFrame, wx.HORIZONTAL)
        sbox.Add(wx.StaticText(messagePanel, wx.ID_ANY, 'Only trials including this message:'), flag=wx.RIGHT, border=5)
        sbox.Add(self.tcMessage, flag=wx.RIGHT, border=15)
        sbox.Add(self.cbRegExp)
        messagePanel.SetSizer(sbox)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(regionPanel, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(timePanel, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(self.rbSpatialCriteria, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(temporalCriteriaPanel, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(messagePanel, flag=wx.EXPAND|wx.ALL, border=5)
        self.customCommandPanel.SetSizerAndFit(box)

        self.onClickRadiobutton()

        buttonPanel = wx.Panel(self, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Search')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Close')
        okButton.Bind(wx.EVT_BUTTON, self.calc)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.rbCommandChoice, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(self.customCommandPanel, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        
        self.SetSizerAndFit(box)
        self.Show()

    def onClickRadiobutton(self, event=None):
        if self.commandCodes[self.rbCommandChoice.GetSelection()] == 'embedded':
            self.customCommandPanel.Enable(False)
            self.rbSpatialCriteria.Enable(False)
        else:
            self.customCommandPanel.Enable(True)
            self.rbSpatialCriteria.Enable(True)
            if self.rbCircleRegion.GetValue()==1:
                self.tcCircleRegionX.Enable(True)
                self.tcCircleRegionY.Enable(True)
                self.tcCircleRegionR.Enable(True)
                self.tcRectRegionX1.Enable(False)
                self.tcRectRegionY1.Enable(False)
                self.tcRectRegionX2.Enable(False)
                self.tcRectRegionY2.Enable(False)
            else:
                self.tcCircleRegionX.Enable(False)
                self.tcCircleRegionY.Enable(False)
                self.tcCircleRegionR.Enable(False)
                self.tcRectRegionX1.Enable(True)
                self.tcRectRegionY1.Enable(True)
                self.tcRectRegionX2.Enable(True)
                self.tcRectRegionY2.Enable(True)

    def calc(self, event=None):
        if self.commandCodes[self.rbCommandChoice.GetSelection()] == 'embedded':
            sep = ' '

            data = []
            labels = []
            nFixList = []
            nTrial = 0
            for tr in range(len(self.D)):
                msglist = self.D[tr].findMessage('!REGION', useRegexp=False)
                if len(msglist) > 0:
                    fixlistTrial = []
                    labelsTrial = []
                    for msg in msglist:
                        commands = msg.text.split(sep)
                        period = [0, 0]
                        try:
                            label = commands[1]

                            regionparam = commands[3].split(',')
                            if commands[2] == 'CIRCLE':
                                region = GazeParser.Region.CircleRegion(float(regionparam[0]),
                                                                        float(regionparam[1]),
                                                                        float(regionparam[2]))
                            elif commands[2] == 'RECT':
                                region = GazeParser.Region.RectRegion(float(regionparam[0]),
                                                                      float(regionparam[1]),
                                                                      float(regionparam[2]),
                                                                      float(regionparam[3]))

                            try:
                                period[0] = float(commands[4])
                            except:  # label
                                if commands[4] == '!NONE':
                                    period[0] = None
                                else:
                                    from_msg = self.D[tr].findMessage(commands[4])
                                    if len(from_msg) == 1:
                                        period[0] = from_msg[0].time
                                    else:
                                        DlgShowerror(self, 'Error', 'Invalid FROM parameter in REGION.\n(Trial:{}, Message:{})'.format(tr+1, msg))
                                        return
                            try:
                                period[1] = float(commands[5])
                            except:  # label
                                if commands[5] == '!NONE':
                                    period[1] = None
                                else:
                                    to_msg = self.D[tr].findMessage(commands[5])
                                    if len(from_msg) == 1:
                                        period[1] = to_msg[0].time
                                    else:
                                        DlgShowerror(self, 'Error', 'Invalid TO parameter in REGION.\n(Trial:{}, Message:{})'.format(tr+1, msg))
                                        return

                            if len(commands) > 6:
                                val = commands[6].lower()
                                if not val in ('true', 'false'):
                                    DlgShowerror(self, 'Error', 'Invalid "useCenter" parameter in REGION.\n(Trial:{}, Message:{})'.format(tr+1, msg))
                                    return
                                useCenter = True if val == 'true' else False
                                val = commands[7].lower()
                                if not val in ('all', 'any'):
                                    DlgShowerror(self, 'Error', 'Invalid "containsTime" parameter in REGION.\n(Trial:{}, Message:{})'.format(tr+1, msg))
                                    return
                                containsTime = val
                                val = commands[8].lower()
                                if not val in ('all', 'any'):
                                    DlgShowerror(self, 'Error', 'Invalid "containsTraj" parameter in REGION.\n(Trial:{}, Message:{})'.format(tr+1, msg))
                                    return
                                containsTraj = val
                            else:
                                useCenter = True
                                containsTime = 'all'
                                containsTraj = 'all'

                            # print(region, period, useCenter, containsTime, containsTraj)

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
                            DlgShowerror(self, 'Error', msg.text+'\n\n'+errormsg)
                    data.append(fixlistTrial)
                    labels.append(labelsTrial)
                    nFixList.append(len(fixlistTrial))
                    nTrial += 1
                else:
                    data.append([])
                    labels.append([])
                    nFixList.append(0)

        else:  # use dialog parameters
            if self.rbCircleRegion.GetValue(): # circle
                try:
                    x = float(self.tcCircleRegionX.GetValue())
                    y = float(self.tcCircleRegionY.GetValue())
                    r = float(self.tcCircleRegionR.GetValue())
                except:
                    DlgShowerror(self, 'Error', 'non-float values in x, y, and/or r')
                    return
                region = GazeParser.Region.CircleRegion(x, y, r)

            else:  # rect
                try:
                    x1 = float(self.tcRectRegionX1.GetValue())
                    x2 = float(self.tcRectRegionY1.GetValue())
                    y1 = float(self.tcRectRegionX2.GetValue())
                    y2 = float(self.tcRectRegionY2.GetValue())
                except:
                    DlgShowerror(self, 'Error', 'non-float values in x1, x2, y1 and/or y2')
                    return

                region = GazeParser.Region.RectRegion(x1, x2, y1, y2)

            period = [None, None]

            fromStr = self.tcFromTime.GetValue()
            toStr = self.tcToTime.GetValue()
            try:
                if fromStr != '':
                    period[0] = float(fromStr)
                if toStr != '':
                    period[1] = float(toStr)
            except:
                DlgShowerror(self, 'Error', 'From and To must be empty or float value.')
                return

            if self.cbTemporalCriterion.GetValue():
                containsTime = 'all'
            else:
                containsTime = 'any'

            containsTraj = self.spatialCriteriaCodes[self.rbSpatialCriteria.GetSelection()]
            if containsTraj == 'center':
                useCenter = True
                containsTraj = 'all'  # any is also OK.
            else:
                useCenter = False

            msg = self.tcMessage.GetValue()
            useregexp = self.cbRegExp.GetValue()

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
        #ans = DlgAskyesno('Info', '%d fixations are found in %d trials.\nExport data?' % (np.sum(nFixList), nTrial))
        dlg = DlgAsk3buttonDialog(self, message='%d fixations are found in %d trials.\nExport data?' % (np.sum(nFixList), nTrial), buttons=['Export to file', 'Register on jump list', 'Cancel'])
        dlg.ShowModal()
        ans = dlg.GetSelection()
        dlg.Destroy()
        
        if ans == 0: # export to file
            fname = DlgAsksaveasfilename(self, initialdir=self.initialDataDir)
            if fname != '':
                fp = open(fname, 'w')
                fp.write('Trial\tLabel\tStart\tEnd\tDuration\tCenterX\tCenterY\n')
                for i in range(len(data)):
                    for fi in range(len(data[i])):
                        fp.write('%d\t%s\t%.1f\t%.1f\t%.1f\t%.2f\t%.2f\n' % (i, labels[i][fi],
                                                                             data[i][fi].startTime,
                                                                             data[i][fi].endTime,
                                                                             data[i][fi].duration,
                                                                             data[i][fi].center[0],
                                                                             data[i][fi].center[1]))
                fp.close()
                DlgShowinfo(self, 'Info', 'Done.')
            else:
                DlgShowinfo(self, 'Info', 'Canceled.')
        elif ans == 1: # register on jump list
                self.parent.jumplistbox.ClearAll()
                self.parent.jumplistbox.InsertColumn(0, 'Trial', width=40)
                self.parent.jumplistbox.InsertColumn(1, 'Time', width=wx.LIST_AUTOSIZE)
                self.parent.jumplistbox.InsertColumn(2, 'Label', width=wx.LIST_AUTOSIZE)
                self.parent.jumplistbox.InsertColumn(3, 'Center', width=wx.LIST_AUTOSIZE)
                self.parent.jumplistbox.InsertColumn(4, 'Duration', width=wx.LIST_AUTOSIZE)
                line = 0
                for i in range(len(data)):
                    for fi in range(len(data[i])):
                        self.parent.jumplistbox.InsertItem(line, str(i+1))
                        self.parent.jumplistbox.SetItem(line, 1, '%10.1f' % data[i][fi].startTime)
                        self.parent.jumplistbox.SetItem(line, 2, labels[i][fi])
                        self.parent.jumplistbox.SetItem(line, 3, '%.1f,%.1f' % tuple(data[i][fi].center))
                        self.parent.jumplistbox.SetItem(line, 4, '%10.1f' % data[i][fi].duration)
                        line += 1
                self.jumplistSortAscend = True
                self.jumplistSortColumn = 0
        
    def cancel(self, event=None):
        self.Close()

class getSaccadeLatencyDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(getSaccadeLatencyDialog, self).__init__(parent=parent, id=id, title='Saccade latency')
        self.parent = parent
        self.D = parent.D
        self.C = parent.C
        self.conf = parent.conf
        self.initialDataDir = parent.initialDataDir

        # plot frame
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvasWxAgg( self, wx.ID_ANY, self.fig )
        self.ax = self.fig.add_axes([0.1, 0.1, 0.8, 0.8])

        # parameter frame
        paramPanel = wx.Panel(self, wx.ID_ANY)

        messagePanel = wx.Panel(paramPanel, wx.ID_ANY)
        messageFrame = wx.StaticBox(messagePanel, wx.ID_ANY, 'Message')
        self.tcMessage = wx.TextCtrl(messagePanel, wx.ID_ANY)
        self.cbRegExp = wx.CheckBox(messagePanel, wx.ID_ANY, 'Regular expression')
        sbox = wx.StaticBoxSizer(messageFrame, wx.VERTICAL)
        sbox.Add(self.tcMessage, flag=wx.EXPAND|wx.ALL, border=5)
        sbox.Add(self.cbRegExp, flag=wx.EXPAND|wx.ALL, border=5)
        messagePanel.SetSizer(sbox)

        latencyPanel = wx.Panel(paramPanel, wx.ID_ANY)
        latencyFrame = wx.StaticBox(latencyPanel, wx.ID_ANY, 'Latency')
        latencyMinMaxPanel = wx.Panel(latencyPanel, wx.ID_ANY)
        self.tcMinLatency = wx.TextCtrl(latencyMinMaxPanel, wx.ID_ANY)
        self.tcMaxLatency = wx.TextCtrl(latencyMinMaxPanel, wx.ID_ANY)
        sbox = wx.FlexGridSizer(2, 2, 0, 0)
        sbox.Add(wx.StaticText(latencyMinMaxPanel, wx.ID_ANY, 'Min'))
        sbox.Add(self.tcMinLatency, flag=wx.EXPAND)
        sbox.Add(wx.StaticText(latencyMinMaxPanel, wx.ID_ANY, 'Max'))
        sbox.Add(self.tcMaxLatency, flag=wx.EXPAND)
        latencyMinMaxPanel.SetSizer(sbox)
        box = wx.StaticBoxSizer(latencyFrame, wx.VERTICAL)
        box.Add(latencyMinMaxPanel, flag=wx.EXPAND|wx.ALL, border=5)
        latencyPanel.SetSizer(box)

        amplitudePanel = wx.Panel(paramPanel, wx.ID_ANY)
        amplitudeFrame = wx.StaticBox(amplitudePanel, wx.ID_ANY, 'Amplitude')
        ampMinMaxPanel = wx.Panel(amplitudePanel, wx.ID_ANY)
        self.tcMinAmplitude = wx.TextCtrl(ampMinMaxPanel, wx.ID_ANY)
        self.tcMaxAmplitude = wx.TextCtrl(ampMinMaxPanel, wx.ID_ANY)
        sbox = wx.FlexGridSizer(2, 2, 0, 0)
        sbox.Add(wx.StaticText(ampMinMaxPanel, wx.ID_ANY, 'Min'))
        sbox.Add(self.tcMinAmplitude, flag=wx.EXPAND)
        sbox.Add(wx.StaticText(ampMinMaxPanel, wx.ID_ANY, 'Max'))
        sbox.Add(self.tcMaxAmplitude, flag=wx.EXPAND)
        ampMinMaxPanel.SetSizer(sbox)
        self.choices = ('deg','pix')
        self.rbAmpUnit = wx.RadioBox(amplitudePanel, wx.ID_ANY, 'unit', choices=self.choices)
        box = wx.StaticBoxSizer(amplitudeFrame, wx.VERTICAL)
        box.Add(ampMinMaxPanel, flag=wx.EXPAND)
        box.Add(self.rbAmpUnit, flag=wx.EXPAND)
        amplitudePanel.SetSizer(box)

        buttonPanel = wx.Panel(paramPanel, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Search')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Close')
        okButton.Bind(wx.EVT_BUTTON, self.calc)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)
        
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(messagePanel, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(latencyPanel, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(amplitudePanel, flag=wx.EXPAND|wx.ALL, border=5)
        box.Add(buttonPanel, flag=wx.ALIGN_RIGHT|wx.ALL)
        paramPanel.SetSizer(box)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.canvas)
        hbox.Add(paramPanel)
        self.SetSizerAndFit(hbox)
        
        self.Show()

    def calc(self, event=None):
        minamp = None
        maxamp = None
        minlat = None
        maxlat = None
        try:
            if self.tcMinAmplitude.GetValue() != '':
                minamp = float(self.tcMinAmplitude.GetValue())
            if self.tcMaxAmplitude.GetValue() != '':
                maxamp = float(self.tcMaxAmplitude.GetValue())
            if self.tcMinLatency.GetValue() != '':
                minlat = float(self.tcMinLatency.GetValue())
            if self.tcMaxLatency.GetValue() != '':
                maxlat = float(self.tcMaxLatency.GetValue())
        except:
            DlgShowerror(self, 'Error', 'Invalid values are found in amplitude/latency.')
        for value in (minamp, maxamp, minlat, maxlat):
            if value is not None and value < 0:
                DlgShowerror(self, 'Error', 'latency and amplitude must be zero or positive.')
                return

        nMsg = 0
        nSac = 0
        trdata = []
        sacdata = []
        for tr in range(len(self.D)):
            idxlist = self.D[tr].findMessage(self.tcMessage.GetValue(), byIndices=True, useRegexp=self.cbRegExp.GetValue())
            nMsg += len(idxlist)
            for msgidx in idxlist:
                isSaccadeFound = False
                sac = self.D[tr].Msg[msgidx].getNextEvent(eventType='saccade')
                if sac is not None:  # no saccade
                    while True:
                        tmplatency = sac.relativeStartTime(self.D[tr].Msg[msgidx])
                        if self.choices[self.rbAmpUnit.GetSelection()] == 'deg':
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
                    sacdata.append([tmplatency, tmpamplitude, sac.start[0], sac.start[1]])

        if nMsg > 0:
            if nSac > 0:
                self.ax.clear()
                latdata = np.array(sacdata)[:, 0]
                self.ax.hist(latdata)
                self.fig.canvas.draw()
                #ans = DlgAskyesno('Export', '%d saccades/%d messages(%.1f%%).\nExport data?' % (nSac, nMsg, (100.0*nSac)/nMsg))
                dlg = DlgAsk3buttonDialog(self, message='%d saccades/%d messages(%.1f%%).\nExport data?' % (nSac, nMsg, (100.0*nSac)/nMsg), buttons=['Export to file', 'Register on jump list', 'Cancel'])
                dlg.ShowModal()
                ans = dlg.GetSelection()
                dlg.Destroy()
                
                if ans==0: # export to file
                    fname = DlgAsksaveasfilename(self, initialdir=self.initialDataDir)
                    if fname != '':
                        fp = open(fname, 'w')
                        fp.write('Trial\tMessageTime\tMessageText\tLatency\tAmplitude\n')
                        for n in range(nSac):
                            fp.write('%d\t%.2f\t%s\t' % tuple(trdata[n]))
                            fp.write('%.2f\t%.2f\n' % tuple(sacdata[n][0:2]))
                        fp.close()
                        DlgShowinfo(self, 'Info', 'Done.')
                    else:
                        DlgShowinfo(self, 'Info', 'Canceled.')
                elif ans==1: # register with jump list
                    self.parent.jumplistbox.ClearAll()
                    self.parent.jumplistbox.InsertColumn(0, 'Trial', width=40)
                    self.parent.jumplistbox.InsertColumn(1, 'Time', width=wx.LIST_AUTOSIZE)
                    self.parent.jumplistbox.InsertColumn(2, 'Message', width=wx.LIST_AUTOSIZE)
                    self.parent.jumplistbox.InsertColumn(3, 'Start', width=wx.LIST_AUTOSIZE)
                    self.parent.jumplistbox.InsertColumn(4, 'Latency', width=wx.LIST_AUTOSIZE)
                    self.parent.jumplistbox.InsertColumn(5, 'Amplitude', width=wx.LIST_AUTOSIZE)
                    for n in range(nSac):
                        self.parent.jumplistbox.InsertItem(n, str(trdata[n][0]+1))
                        self.parent.jumplistbox.SetItem(n, 1, '%10.1f' % trdata[n][1])
                        self.parent.jumplistbox.SetItem(n, 2, trdata[n][2])
                        self.parent.jumplistbox.SetItem(n, 3, '%.1f,%.1f' % tuple(sacdata[n][2:4]))
                        self.parent.jumplistbox.SetItem(n, 4, '%10.1f' % sacdata[n][0])
                        self.parent.jumplistbox.SetItem(n, 5, '%.1f' % sacdata[n][1])
                    self.jumplistSortAscend = True
                    self.jumplistSortColumn = 0

            else:
                DlgShowinfo(self, 'Info', 'No saccades are detected')
        else:
            DlgShowinfo(self, 'Info', 'No messages are found')

    def cancel(self, event=None):
        self.Close()

class combineDataFileDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(combineDataFileDialog, self).__init__(parent=parent, id=id, title='Combining GazeParser datafiles')
        self.mainWindow = parent

        self.lbFileList = wx.ListBox(self, wx.ID_ANY, size=(600,-1))
        buttonPanel = wx.Panel(self, wx.ID_ANY)
        buttonUp = wx.Button(buttonPanel, wx.ID_ANY, 'Up')
        buttonDown = wx.Button(buttonPanel, wx.ID_ANY, 'Down')
        buttonAdd = wx.Button(buttonPanel, wx.ID_ANY, 'Add files')
        buttonRemove = wx.Button(buttonPanel, wx.ID_ANY, 'Remove selected')
        buttonRemoveAll = wx.Button(buttonPanel, wx.ID_ANY, 'Remove all')
        buttonCancel = wx.Button(buttonPanel, wx.ID_ANY, 'Cancel')
        buttonCombine = wx.Button(buttonPanel, wx.ID_ANY, 'Combine & Save')
        
        buttonUp.Bind(wx.EVT_BUTTON, self.up)
        buttonDown.Bind(wx.EVT_BUTTON, self.down)
        buttonAdd.Bind(wx.EVT_BUTTON, self.addFiles)
        buttonRemove.Bind(wx.EVT_BUTTON, self.removeFile)
        buttonRemoveAll.Bind(wx.EVT_BUTTON, self.removeAll)
        buttonCancel.Bind(wx.EVT_BUTTON, self.cancel)
        buttonCombine.Bind(wx.EVT_BUTTON, self.combine)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(buttonUp, flag=wx.EXPAND)
        vbox.Add(buttonDown, flag=wx.EXPAND)
        vbox.Add(buttonAdd, flag=wx.EXPAND)
        vbox.Add(buttonRemove, flag=wx.EXPAND)
        vbox.Add(buttonRemoveAll, flag=wx.EXPAND)
        vbox.Add(wx.StaticText(buttonPanel, wx.ID_ANY, ''))
        vbox.Add(buttonCancel, flag=wx.EXPAND)
        vbox.Add(buttonCombine, flag=wx.EXPAND)
        buttonPanel.SetSizerAndFit(vbox)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.lbFileList, flag=wx.EXPAND|wx.ALL, border=5)
        hbox.Add(buttonPanel, flag=wx.ALL, border=5)
        self.SetSizerAndFit(hbox)
        
        if self.mainWindow.D is not None:
            self.lbFileList.Append('* Current Data (' + self.mainWindow.dataFileName + ')')
        
        self.Show()

    def up(self, event=None):
        selected = self.lbFileList.GetSelection()
        if selected <= 0:
            return
        item = self.lbFileList.GetString(selected)
        self.lbFileList.Delete(selected)
        self.lbFileList.InsertItems([item], selected-1)
        self.lbFileList.SetSelection(selected-1)

    def down(self, event=None):
        selected = self.lbFileList.GetSelection()
        if selected < 0:
            return
        if selected >= self.lbFileList.GetCount()-1:
            return
        item = self.lbFileList.GetString(selected)
        self.lbFileList.Delete(selected)
        self.lbFileList.InsertItems([item], selected+1)
        self.lbFileList.SetSelection(selected+1)

    def addFiles(self, event=None):
        fnames = DlgAskopenfilenames(self, filetypes=self.mainWindow.datafiletype, initialdir=self.mainWindow.initialDataDir)
        if fnames == []:
            return

        self.mainWindow.initialDataDir = os.path.split(fnames[0])[0]

        for fname in fnames:
            self.lbFileList.Append(fname)

    def removeFile(self, event=None):
        selected = self.lbFileList.GetSelection()
        if selected >= 0:
            self.lbFileList.Delete(selected)
            if self.lbFileList.GetCount() <= selected:
                self.lbFileList.SetSelection(selected-1)
            else:
                self.lbFileList.SetSelection(selected)
        else:
            DlgShowinfo(self, 'Info', 'Select files to delete.')

    def removeAll(self, event=None):
        n = self.lbFileList.GetCount()
        for idx in range(n):
            self.lbFileList.Delete(n-1-idx)

    def combine(self, event=None):
        if self.lbFileList.GetCount() <= 1:
            DlgShowinfo(self, 'Info', 'At least two data files must be added.')
            return
        fnames = [self.lbFileList.GetString(idx) for idx in range(self.lbFileList.GetCount())]
        for index in range(len(fnames)):
            if fnames[index][:16] == '* Current Data (':
                fnames[index] = fnames[index][16:-1]

        combinedFilename = DlgAsksaveasfilename(self, filetypes=self.mainWindow.datafiletype, initialdir=self.mainWindow.initialDataDir)
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
            DlgShowerror(self, 'Error', errormsg)
        else:
            DlgShowinfo(self, 'Info', 'Done')
        self.Close()

    def cancel(self, event=None):
        self.Close()


class configStimImageDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(configStimImageDialog, self).__init__(parent=parent, id=id, title='Setting stimulus image directory')
        self.mainWindow = parent

        editPanel = wx.Panel(self, wx.ID_ANY)
        self.tcStimImagePrefix = wx.TextCtrl(editPanel, wx.ID_ANY, self.mainWindow.conf.COMMAND_STIMIMAGE_PATH)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.StaticText(editPanel, wx.ID_ANY, 'StimImage Prefix'), flag=wx.ALL, border=5)
        hbox.Add(self.tcStimImagePrefix, flag=wx.ALL, border=5)
        editPanel.SetSizerAndFit(hbox)

        self.cbEmbedded = wx.CheckBox(self, wx.ID_ANY, 'Use embedded images if available')
        self.cbEmbedded.SetValue(self.mainWindow.conf.COMMAND_USE_EMBEDDED_IMAGE)

        buttonPanel = wx.Panel(self, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Ok')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Cancel')
        okButton.Bind(wx.EVT_BUTTON, self.setValue)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(editPanel, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)
        vbox.Add(self.cbEmbedded, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=5)
        vbox.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(vbox)

        self.Show()

    def setValue(self, event=None):
        self.mainWindow.conf.COMMAND_STIMIMAGE_PATH = self.tcStimImagePrefix.GetValue()
        self.mainWindow.loadStimImage()
        self.mainWindow.loadRegion()
        self.mainWindow.plotData()

        self.Close()

    def cancel(self, event=None):
        self.Close()


class fontSelectDialog(wx.Dialog):
    def __init__(self, parent, id=None):
        super(fontSelectDialog, self).__init__(parent=parent, id=id, title='Fong settings')
        self.mainWindow = parent

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
        self.sortedIndex = np.argsort(self.fontnamelist)

        self.tcCurrentFontFile = wx.TextCtrl(self, wx.ID_ANY, 'Current font:'+self.mainWindow.conf.CANVAS_FONT_FILE)
        fontPanel = wx.Panel(self, id=wx.ID_ANY)
        self.lbFontList = wx.ListBox(fontPanel, wx.ID_ANY)
        for i in self.sortedIndex:
            self.lbFontList.Append(self.fontnamelist[i])
        self.lbFontList.Bind(wx.EVT_LISTBOX, self.updateSample)
        self.stSample= wx.StaticText(fontPanel, wx.ID_ANY, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789')
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.lbFontList)
        hbox.Add(self.stSample)
        fontPanel.SetSizerAndFit(hbox)

        buttonPanel = wx.Panel(self, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Select this font')
        defaultButton = wx.Button(buttonPanel, wx.ID_ANY, 'Use default')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Cancel')
        okButton.Bind(wx.EVT_BUTTON, self.setFont)
        defaultButton.Bind(wx.EVT_BUTTON, self.clearFont)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(defaultButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.tcCurrentFontFile, flag=wx.EXPAND)
        vbox.Add(fontPanel, flag=wx.EXPAND)
        vbox.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(vbox)

        self.Show()

    def updateSample(self, event=None):
        idx = self.lbFontList.GetSelection()
        self.tcCurrentFontFile.SetLabel('Current font:'+self.fontfilelist[self.sortedIndex[idx]])
        font = wx.Font(-1, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False, self.fontfilelist[self.sortedIndex[idx]])
        self.stSample.SetFont(font)

    def setFont(self, event=None):
        idx = self.lbFontList.GetSelection()
        if idx < 0:
            DlgShowerror(self, 'Error', 'No font is selected')
            return
        self.mainWindow.conf.CANVAS_FONT_FILE = self.fontfilelist[self.sortedIndex[idx]]
        self.mainWindow.fontPlotText = matplotlib.font_manager.FontProperties(fname=self.mainWindow.conf.CANVAS_FONT_FILE)
        self.tcCurrentFontFile.SetLabel('Current font:'+self.mainWindow.conf.CANVAS_FONT_FILE)
        if self.mainWindow.D is not None:
            self.mainWindow.plotData()

    def clearFont(self, event=None):
        self.mainWindow.conf.CANVAS_FONT_FILE = ''
        self.mainWindow.fontPlotText = matplotlib.font_manager.FontProperties()
        self.tcCurrentFontFile.SetLabel('Current font:')
        if self.mainWindow.D is not None:
            self.mainWindow.plotData()

    def cancel(self, event=None):
        self.Close()

class insertNewMessageDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(insertNewMessageDialog, self).__init__(parent=parent, id=id, title='Inserting new message')
        self.mainWindow = parent

        editPanel = wx.Panel(self, id=wx.ID_ANY)
        self.tcTime = wx.TextCtrl(editPanel, wx.ID_ANY, '', size=(360,-1))
        self.tcText = wx.TextCtrl(editPanel, wx.ID_ANY, '', size=(360,-1))
        box = wx.FlexGridSizer(2, 2, 0, 0)
        box.Add(wx.StaticText(editPanel, wx.ID_ANY, 'Time'), flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(self.tcTime, wx.LEFT|wx.RIGHT, border=5)
        box.Add(wx.StaticText(editPanel, wx.ID_ANY, 'Message'), flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(self.tcText, wx.LEFT|wx.RIGHT, border=5)
        editPanel.SetSizer(box)
        editPanel.SetAutoLayout(True)

        buttonPanel = wx.Panel(self, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Ok')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Cancel')
        okButton.Bind(wx.EVT_BUTTON, self.insert)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(editPanel, flag=wx.EXPAND|wx.ALL, border=5)
        vbox.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(vbox)

        self.Show()

    def insert(self, event=None):
        try:
            newTime = float(self.tcTime.GetValue())
        except:
            DlgShowerror(self, 'Error', 'Invalid time value')
            return

        newText = self.tcText.GetValue()

        try:
            self.mainWindow.D[self.mainWindow.tr].insertNewMessage(newTime, newText)
        except:
            DlgShowerror(self, 'Error', 'Invalid time value')
            return

        self.mainWindow.updateMsgBox()
        self.mainWindow.loadStimImage()
        self.loadRegion()
        self.mainWindow.plotData()

        self.mainWindow.dataModified = True
        self.Close()

    def cancel(self, event=None):
        self.Close()

class editMessageDialog(wx.Dialog):
    def __init__(self, parent, message, id=wx.ID_ANY):
        super(editMessageDialog, self).__init__(parent=parent, id=id, title='Editing message')
        self.mainWindow = parent

        self.message = message
        currentTime = '%10.1f' % (message.time)
        if len(message.text) > 30:
            currentMessage = message.text[:27]+'...'
        else:
            currentMessage = message.text

        editPanel = wx.Panel(self, id=wx.ID_ANY)
        tcCurrentTime = wx.TextCtrl(editPanel, wx.ID_ANY, currentTime, size=(200,-1))
        tcCurrentText = wx.TextCtrl(editPanel, wx.ID_ANY, currentMessage, size=(200,-1))
        self.tcTime = wx.TextCtrl(editPanel, wx.ID_ANY, str(message.time), size=(360,-1))
        self.tcText = wx.TextCtrl(editPanel, wx.ID_ANY, str(message.text), size=(360,-1))
        tcCurrentTime.Enable(False)
        tcCurrentText.Enable(False)
        box = wx.FlexGridSizer(3, 3, 0, 0)
        box.Add(wx.StaticText(editPanel, wx.ID_ANY, ''), flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(wx.StaticText(editPanel, wx.ID_ANY, 'Current'), flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(wx.StaticText(editPanel, wx.ID_ANY, 'New'), flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(wx.StaticText(editPanel, wx.ID_ANY, 'Time'), flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(tcCurrentTime, flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(self.tcTime, wx.LEFT|wx.RIGHT, border=5)
        box.Add(wx.StaticText(editPanel, wx.ID_ANY, 'Message'), flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(tcCurrentText, flag=wx.LEFT|wx.RIGHT, border=5)
        box.Add(self.tcText, wx.LEFT|wx.RIGHT, border=5)
        editPanel.SetSizer(box)
        editPanel.SetAutoLayout(True)

        buttonPanel = wx.Panel(self, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Ok')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Cancel')
        okButton.Bind(wx.EVT_BUTTON, self.update)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(editPanel, flag=wx.EXPAND|wx.ALL, border=5)
        vbox.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(vbox)

        self.Show()

    def update(self, event=None):
        try:
            newTime = float(self.tcTime.GetValue())
        except:
            DlgShowerror(self, 'Error', 'Invalid time value')
            return

        newText = self.tcText.GetValue()

        try:
            self.message.updateMessage(newTime, newText)
        except:
            DlgShowerror(self, 'Error', 'Message cannot be updated.\n\n'+str(newTime)+'\n'+newText)
            return

        self.mainWindow.updateMsgBox()
        self.mainWindow.loadStimImage()
        self.loadRegion()
        self.mainWindow.plotData()

        self.mainWindow.dataModified = True
        self.Close()

    def cancel(self, event=None):
        self.Close()


class exportToFileDialog(wx.Dialog):
    def __init__(self, parent, id, data, additional, trial, master=None, initialdir=None):
        super(exportToFileDialog, self).__init__(parent=parent, id=wx.ID_ANY, title='Select to export')
        self.D = data
        self.tr = trial
        if initialdir is None:
            self.initialDataDir = GazeParser.homeDir
        else:
            self.initialDataDir = initialdir

        itemPanel = wx.Panel(self, wx.ID_ANY)
        self.cbSaccade = wx.CheckBox(itemPanel,wx.ID_ANY, 'Saccade')
        self.cbFixation = wx.CheckBox(itemPanel,wx.ID_ANY, 'Fixation')
        self.cbBlink = wx.CheckBox(itemPanel,wx.ID_ANY, 'Blink')
        self.cbMessage = wx.CheckBox(itemPanel,wx.ID_ANY, 'Message')
        self.cbSaccade.SetValue(1)
        self.cbFixation.SetValue(1)
        self.cbBlink.SetValue(1)
        self.cbMessage.SetValue(1)
        box = wx.StaticBox(itemPanel, wx.ID_ANY, 'Check items to export')
        vbox = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        vbox.Add(self.cbSaccade)
        vbox.Add(self.cbFixation)
        vbox.Add(self.cbBlink)
        vbox.Add(self.cbMessage)
        itemPanel.SetSizer(vbox)

        self.rangeBox = wx.RadioBox(self, wx.ID_ANY, 'Range',
                                    choices=['All trials','This trial'],style=wx.RA_HORIZONTAL)
        self.rangeBox.SetSelection(0) # All trials

        self.orderBox = wx.RadioBox(self, wx.ID_ANY, 'Order',
                                    choices=['By time','By events'],style=wx.RA_HORIZONTAL)
        self.orderBox.SetSelection(0)
        
        buttonPanel = wx.Panel(self, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Ok')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Cancel')
        okButton.Bind(wx.EVT_BUTTON, self.export)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(itemPanel, flag=wx.EXPAND)
        vbox.Add(self.rangeBox, flag=wx.EXPAND)
        vbox.Add(self.orderBox, flag=wx.EXPAND)
        vbox.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(vbox)
        self.Show()

    def export(self, event=None):
        if self.cbSaccade.GetValue() or self.cbFixation.GetValue() or self.cbBlink.GetValue() or self.cbMessage.GetValue():
            exportFileName = DlgAsksaveasfilename(self, initialdir=self.initialDataDir)
            if exportFileName == '':
                return
            fp = open(exportFileName, 'w')

            if self.orderBox.GetStringSelection() == 'By time':
                if self.rangeBox.GetStringSelection() == 'This trial':
                    trlist = [self.tr]
                else:  # AllTrials
                    trlist = list(range(len(self.D)))
                for tr in trlist:
                    fp.write('TRIAL%d\n' % (tr+1))
                    for e in self.D[tr].EventList:
                        if isinstance(e, GazeParser.SaccadeData) and self.cbSaccade.GetValue():
                            fp.write('SAC,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n' %
                                     (e.startTime, e.endTime, e.start[0], e.start[1], e.end[0], e.end[1]))
                        elif isinstance(e, GazeParser.FixationData) and self.cbFixation.GetValue():
                            fp.write('FIX,%.1f,%.1f,%.1f,%.1f\n' %
                                     (e.startTime, e.endTime, e.center[0], e.center[1]))
                        elif isinstance(e, GazeParser.MessageData) and self.cbMessage.GetValue():
                            fp.write('MSG,%.1f,%.1f,%s\n' % (e.time, e.time, e.text))
                        elif isinstance(e, GazeParser.BlinkData) and self.cbBlink.GetValue():
                            fp.write('BLK,%.1f,%.1f\n' % (e.startTime, e.endTime))

            else:  # ByEvents
                if self.rangeBox.GetStringSelection() == 'This trial':
                    trlist = [self.tr]
                else:  # AllTrials
                    trlist = list(range(len(self.D)))
                for tr in trlist:
                    fp.write('TRIAL%d\n' % (tr+1))
                    if self.cbSaccade.GetValue():
                        for e in self.D[tr].Sac:
                            fp.write('SAC,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n' %
                                     (e.startTime, e.endTime, e.start[0], e.start[1], e.end[0], e.end[1]))
                    if self.cbFixation.GetValue():
                        for e in self.D[tr].Fix:
                            fp.write('FIX,%.1f,%.1f,%.1f,%.1f\n' %
                                     (e.startTime, e.endTime, e.center[0], e.center[1]))
                    if self.cbMessage.GetValue():
                        for e in self.D[tr].Msg:
                            fp.write('MSG,%.1f,%.1f,%s\n' % (e.time, e.time, e.text))
                    if self.cbBlink.GetValue():
                        for e in self.D[tr].Blink:
                            fp.write('BLK,%.1f,%.1f\n' % (e.startTime, e.endTime))

            fp.close()

            DlgShowinfo(self, 'Info', 'Done.')

        else:
            DlgShowinfo(self, 'Info', 'No items were selected.')
        
        self.Close()

    def cancel(self, event=None):
        self.Close()

class configColorDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(configColorDialog, self).__init__(parent=parent, id=id, title='Color settings')
        self.mainWindow = parent
        
        nParam = 0
        for section in self.mainWindow.conf.options:
            if section[0] == 'Appearance':
                for item in section[1]:
                    if item[0][0:5] == 'COLOR':
                        nParam += 1

        colorPanel = wx.Panel(self, wx.ID_ANY)
        box = wx.FlexGridSizer(nParam, 2, 0, 5)
        
        self.newColorDict = {}
        self.origColorDict = {}
        self.buttonDict = {}
        for section in self.mainWindow.conf.options:
            if section[0] == 'Appearance':
                for item in section[1]:
                    if item[0][0:5] != 'COLOR':
                        continue
                    name = item[0]
                    self.origColorDict[name] = getattr(self.mainWindow.conf, name)
                    self.newColorDict[name] = getattr(self.mainWindow.conf, name)
                    box.Add(wx.StaticText(colorPanel, wx.ID_ANY, name))
                    self.buttonDict[name] = wx.Button(colorPanel, wx.ID_ANY, self.newColorDict[name])
                    self.buttonDict[name].SetBackgroundColour(self.newColorDict[name])
                    self.buttonDict[name].SetForegroundColour(getTextColor(self.newColorDict[name]))
                    self.buttonDict[name].Bind(wx.EVT_BUTTON, functools.partial(self.chooseColor, name=name))
                    box.Add(self.buttonDict[name])
        
        colorPanel.SetSizerAndFit(box)
        
        buttonPanel = wx.Panel(self, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Update plot')
        resetButton = wx.Button(buttonPanel, wx.ID_ANY, 'Reset')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Close')
        okButton.Bind(wx.EVT_BUTTON, self.updatePlot)
        resetButton.Bind(wx.EVT_BUTTON, self.resetColor)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(resetButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(colorPanel, flag=wx.EXPAND|wx.ALL, border=5)
        vbox.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(vbox)

        self.Show()

    def chooseColor(self, event=None, name=''):
        dlg = wx.ColourDialog(self)
        dlg.GetColourData().SetChooseFull(True)
        if dlg.ShowModal() == wx.ID_OK:
            col = dlg.GetColourData().GetColour().Get()
            if len(col) == 3: #RGB
                self.newColorDict[name] = '#%02X%02X%02X' % col
            elif len(col) == 4: #RGBA
                self.newColorDict[name] = '#%02X%02X%02X' % col[0:3]
            else:
                DlgShowerror(None, 'Error', 'Invalid color code (%s)' % str(col))
            self.buttonDict[name].SetBackgroundColour(self.newColorDict[name])
            self.buttonDict[name].SetForegroundColour(getTextColor(self.newColorDict[name]))
            self.buttonDict[name].SetLabel(self.newColorDict[name])
        dlg.Destroy()

    def updatePlot(self, event=None):
        for name in self.newColorDict.keys():
            setattr(self.mainWindow.conf, name, self.newColorDict[name])
        self.mainWindow.plotData()

    def resetColor(self, event=None):
        for name in self.origColorDict.keys():
            setattr(self.mainWindow.conf, name, self.origColorDict[name])
            self.newColorDict[name] = self.origColorDict[name]
            self.buttonDict[name].SetBackgroundColour(self.newColorDict[name])
            self.buttonDict[name].SetForegroundColour(getTextColor(self.newColorDict[name]))
            self.buttonDict[name].SetLabel(self.newColorDict[name])

    def cancel(self, event=None):
        self.Close()


class configGridDialog(wx.Dialog):
    def __init__(self, parent, id=wx.ID_ANY):
        super(configGridDialog, self).__init__(parent=parent, id=id, title='Grid settings')
        self.mainWindow = parent
        
        self.choices = ['No grid', 'Show grid on current ticks', 'Set interval ticks', 'Set custom ticks']
        self.choiceCodes = ['NOGRID','CURRENT','INTERVAL','CUSTOM']
        
        gridPanel = wx.Panel(self, wx.ID_ANY)
        self.rbAbscissa = wx.RadioBox(gridPanel, wx.ID_ANY, 'Abscissa', choices = self.choices, style=wx.RA_VERTICAL)
        self.tcAbscissa = wx.TextCtrl(gridPanel, wx.ID_ANY)
        self.rbOrdinate = wx.RadioBox(gridPanel, wx.ID_ANY, 'Ordinate', choices = self.choices, style=wx.RA_VERTICAL)
        self.tcOrdinate = wx.TextCtrl(gridPanel, wx.ID_ANY)
        self.rbAbscissa.Bind(wx.EVT_RADIOBOX, self.onClickRadiobuttons)
        self.rbOrdinate.Bind(wx.EVT_RADIOBOX, self.onClickRadiobuttons)

        if self.mainWindow.plotStyle in XYPLOTMODES:
            xparams = self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XY.split('#')
            self.rbAbscissa.SetStringSelection(xparams[0])
            yparams = self.mainWindow.conf.CANVAS_GRID_ORDINATE_XY.split('#')
            self.rbOrdinate.SetStringSelection(yparams[0])
        else:
            xparams = self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XYT.split('#')
            self.rbAbscissa.SetStringSelection(xparams[0])
            yparams = self.mainWindow.conf.CANVAS_GRID_ORDINATE_XYT.split('#')
            self.rbOrdinate.SetStringSelection(yparams[0])

        if xparams[0] == 'INTERVAL' or xparams[0] == 'CUSTOM':
            self.tcAbscissa.SetValue(xparams[1])
        if yparams[0] == 'INTERVAL' or yparams[0] == 'CUSTOM':
            self.tcOrdinate.SetValue(yparams[1])

        box = wx.FlexGridSizer(2, 2, 0, 0)
        box.Add(self.rbAbscissa, flag=wx.EXPAND)
        box.Add(self.rbOrdinate, flag=wx.EXPAND)
        box.Add(self.tcAbscissa, flag=wx.EXPAND)
        box.Add(self.tcOrdinate, flag=wx.EXPAND)
        gridPanel.SetSizer(box)
        
        buttonPanel = wx.Panel(self, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Set')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Close')
        okButton.Bind(wx.EVT_BUTTON, self.updatePlot)
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)
        
        self.onClickRadiobuttons() #update TextCtrl status

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(gridPanel, flag=wx.EXPAND|wx.ALL, border=5)
        vbox.Add(buttonPanel, flag=wx.ALIGN_RIGHT)
        self.SetSizerAndFit(vbox)
        
        self.Show()

    def onClickRadiobuttons(self, event=None):
        gridtype = self.choiceCodes[self.rbAbscissa.GetSelection()]
        if gridtype == 'NOGRID' or gridtype == 'CURRENT':
            self.tcAbscissa.Enable(False)
        else:
            self.tcAbscissa.Enable(True)

        gridtype = self.choiceCodes[self.rbOrdinate.GetSelection()]
        if gridtype == 'NOGRID' or gridtype == 'CURRENT':
            self.tcOrdinate.Enable(False)
        else:
            self.tcOrdinate.Enable(True)

    def updatePlot(self, event=None):
        gridtypeX = self.choiceCodes[self.rbAbscissa.GetSelection()]
        gridtypeY = self.choiceCodes[self.rbOrdinate.GetSelection()]
        if gridtypeX == 'NOGRID':
            xstr = 'NOGRID'
        elif gridtypeX == 'CURRENT':
            xstr = 'CURRENT'
        elif gridtypeX == 'INTERVAL':
            xstr = 'INTERVAL#'+self.tcAbscissa.GetValue()
        elif gridtypeX == 'CUSTOM':
            xstr = 'CUSTOM#'+self.tcAbscissa.GetValue()
        else:
            raise ValueError('Unknown abscissa grid type (%s)' % (gridtypeX))

        if gridtypeY == 'NOGRID':
            ystr = 'NOGRID'
        elif gridtypeY == 'CURRENT':
            ystr = 'CURRENT'
        elif gridtypeY == 'INTERVAL':
            ystr = 'INTERVAL#'+self.tcOrdinate.GetValue()
        elif gridtypeY == 'CUSTOM':
            ystr = 'CUSTOM#'+self.tcOrdinate.GetValue()
        else:
            raise(ValueError, 'Unknown ordinate grid type (%s)' % (gridtypeY))

        if self.mainWindow.plotStyle in XYPLOTMODES:
            self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XY = xstr
            self.mainWindow.conf.CANVAS_GRID_ORDINATE_XY = ystr
        else:
            self.mainWindow.conf.CANVAS_GRID_ABSCISSA_XYT = xstr
            self.mainWindow.conf.CANVAS_GRID_ORDINATE_XYT = ystr

        self.mainWindow.updateGrid()
        self.mainWindow.fig.canvas.draw()

    def cancel(self, event=None):
        self.Close()


class ViewerOptions(object):
    options = [
        ['Version',
         [['VIEWER_VERSION', str]]],
        ['Appearance',
         [['CANVAS_WIDTH', int],
          ['CANVAS_HEIGHT', int],
          ['CANVAS_DEFAULT_VIEW', str],
          ['CANVAS_SHOW_FIXNUMBER', bool],
          ['CANVAS_SHOW_SELECTED_ONLY', bool],
          ['CANVAS_SHOW_STIMIMAGE', bool],
          ['CANVAS_SHOW_REGION', bool],
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
          ['COLOR_MESSAGE_BG', str],
          ['COLOR_REGION_EC', str]]],
        ['Command',
         [['COMMAND_SEPARATOR', str],
          ['COMMAND_STIMIMAGE_PATH', str],
          ['COMMAND_USE_EMBEDDED_IMAGE', bool]]],
        ['Recent',
         [['RECENT_DIR01', str],
          ['RECENT_DIR02', str],
          ['RECENT_DIR03', str],
          ['RECENT_DIR04', str],
          ['RECENT_DIR05', str]]]
    ]

    def __init__(self):
        initialConfigFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'viewer.cfg')
        appConfigDir = os.path.join(GazeParser.configDir, 'app')
        if not os.path.isdir(appConfigDir):
            os.mkdir(appConfigDir)

        self.viewerConfigFile = os.path.join(appConfigDir, 'viewer.cfg')
        if not os.path.isfile(self.viewerConfigFile):
            shutil.copyfile(initialConfigFile, self.viewerConfigFile)

        appConf = ConfigParser()
        appConf.optionxform = str
        try:
            if hasattr(appConf, 'read_file'):
                appConf.read_file(codecs.open(self.viewerConfigFile, 'r', 'utf8'))
            else: # Python2 ?
                appConf.readfp(codecs.open(self.viewerConfigFile, 'r', 'utf8'))
        except UnicodeDecodeError:
            DlgShowinfo(None, 'info', 'Could not open %s.\nCheck if the file is encoded in UTF-8.' % (self.viewerConfigFile))
            GazeParser.Utility.openLocation(appConfigDir)
            sys.exit()

        try:
            self.VIEWER_VERSION = appConf.get('Version', 'VIEWER_VERSION')
        except:
            ans = DlgAskyesno(None, 'Error', 'No VIEWER_VERSION option in configuration file (%s). Backup current file and then initialize configuration file?\n' % (self.viewerConfigFile))
            if ans:
                shutil.copyfile(self.viewerConfigFile, self.viewerConfigFile+'.bak')
                shutil.copyfile(initialConfigFile, self.viewerConfigFile)
                appConf = ConfigParser()
                appConf.optionxform = str
                if hasattr(appConf, 'read_file'):
                    appConf.read_file(codecs.open(self.viewerConfigFile, 'r', 'utf8'))
                else: # Python2 ?
                    appConf.readfp(codecs.open(self.viewerConfigFile, 'r', 'utf8'))
                self.VIEWER_VERSION = appConf.get('Version', 'VIEWER_VERSION')
            else:
                DlgShowinfo(None, 'info', 'Please correct configuration file ({}) manually.'.format(self.viewerConfigFile))
                GazeParser.Utility.openLocation(appConfigDir)
                sys.exit()

        doMerge = False
        if self.VIEWER_VERSION != GazeParser.__version__:
            ans = DlgAskyesno(None, 'Warning', 'VIEWER_VERSION of configuration file (%s) disagree with GazeParser version (%s). Backup current configuration file and build new configuration file?' % (self.VIEWER_VERSION, GazeParser.__version__))
            if ans:
                shutil.copyfile(self.viewerConfigFile, self.viewerConfigFile+'.bak')
                doMerge = True
            else:
                DlgShowinfo(None, 'info', 'Please update configuration file ({}) manually.'.format(self.viewerConfigFile))
                GazeParser.Utility.openLocation(appConfigDir)
                sys.exit()

        if doMerge:
            appNewConf = ConfigParser()
            appNewConf.optionxform = str
            if hasattr(appNewConf, 'read_file'):
                appNewConf.read_file(codecs.open(initialConfigFile, 'r', 'utf8'))
            else:
                appNewConf.readfp(codecs.open(initialConfigFile, 'r', 'utf8'))
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
            DlgShowinfo(None, 'info', 'Added:\n'+'\n'.join(newOpts))

        else:
            for section, params in self.options:
                for optName, optType in params:
                    try:
                        setattr(self, optName, optType(appConf.get(section, optName)))
                    except:
                        DlgShowerror(None, 'error', 'could not read option [%s]%s.\nConfiguration file (%s) may be corrupted. Please fix or remove this file and restart.' % (section, optName, self.viewerConfigFile))
                        GazeParser.Utility.openLocation(appConfigDir)
                        sys.exit()

        # set recent directories
        self.RecentDir = []
        for i in range(5):
            d = getattr(self, 'RECENT_DIR%02d' % (i+1))
            self.RecentDir.append(d)

    def _write(self):
        # set recent directories
        for i in range(5):
            setattr(self, 'RECENT_DIR%02d' % (i+1), self.RecentDir[i])

        # with codecs.open(self.viewerConfigFile, 'w', sys.getfilesystemencoding()) as fp:
        with codecs.open(self.viewerConfigFile, 'w', 'utf8') as fp:
            for section, params in self.options:
                fp.write('[%s]\n' % section)
                for optName, optType in params:
                    fp.write('%s = %s\n' % (optName, getattr(self, optName)))
                fp.write('\n')


class mainFrame(wx.Frame):
    def __init__(self, app):
        self.conf = ViewerOptions()
        
        #self.ftypes = [('GazeParser/SimpleGazeTracker Datafile', ('*.db', '*.csv'))]
        #self.datafiletype = [('GazeParser Datafile', '*.db')]
        self.ftypes = 'GazeParser/SimpleGazeTracker Datafile (*.db;*.csv)|*.db;*.csv'
        self.initialDataDir = GazeParser.homeDir
        self.datafiletype = 'GazeParser Datafile (*.db)|*.db'
        self.D = None
        self.C = None
        self.tr = 0
        self.plotAreaXY = [0, 1024, 0, 768]
        self.plotAreaTXY = [0, 3000, 0, 1024]
        # self.showStimImage = False
        self.stimImage = None
        self.region = []
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
        
        self.app = app
        super(mainFrame, self).__init__(parent=None, id=wx.ID_ANY, title='GazeParser Data Viewer')
        #SET ICON
        self.Bind(wx.EVT_CLOSE, self.exit)
        
        if self.conf.CANVAS_FONT_FILE != '':
            self.fontPlotText = matplotlib.font_manager.FontProperties(fname=self.conf.CANVAS_FONT_FILE)
        else:
            self.fontPlotText = matplotlib.font_manager.FontProperties()

        # main menu
        self.menu_bar = wx.MenuBar()
        self.menu_file = wx.Menu()
        self.menu_view = wx.Menu()
        self.menu_recent = wx.Menu()
        self.menu_tools = wx.Menu()
        self.menu_bar.Append(self.menu_file,'File')
        self.menu_bar.Append(self.menu_view,'View')
        self.menu_bar.Append(self.menu_tools,'Tools')

        self.menu_file.Append(wx.ID_OPEN,'Open')
        if hasattr(self.menu_file, 'AppendSubMenu'):
            self.menu_file.AppendSubMenu(self.menu_recent, 'Recent Dir')
        else:
            self.menu_file.Append(wx.ID_ANY, 'Recent Dir', self.menu_recent)
        for i in range(MAX_RECENT):
            item = self.menu_recent.Append(recentIDList[i], str(i+1)+'. '+self.conf.RecentDir[i])
            if self.conf.RecentDir[i] == '':
                item.Enable(False)
            self.Bind(wx.EVT_MENU, self.openrecent, id=recentIDList[i])
        self.menu_file.Append(wx.ID_SAVE, 'Save')
        self.menu_file.Append(ID_EXPORT, 'Export')
        self.menu_file.Append(ID_COMBINE, 'Combine data files')
        self.menu_file.Append(wx.ID_CLOSE, 'Exit')
        self.Bind(wx.EVT_MENU, self.openfile, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.savefile, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.exportfile, id=ID_EXPORT)
        self.Bind(wx.EVT_MENU, self.combinefiles, id=ID_COMBINE)
        self.Bind(wx.EVT_MENU, self.exit, id=wx.ID_CLOSE)
        self.menu_view.Append(ID_PREV_TR, 'Prev trial')
        self.menu_view.Append(ID_NEXT_TR, 'Next trial')
        self.Bind(wx.EVT_MENU, self.prevTrial, id=ID_PREV_TR)
        self.Bind(wx.EVT_MENU, self.nextTrial, id=ID_NEXT_TR)
        self.menu_view.AppendSeparator()
        self.menu_view.AppendRadioItem(ID_VIEW_TXY, 'T-XY plot')
        self.menu_view.AppendRadioItem(ID_VIEW_XY, 'XY plot')
        self.menu_view.AppendRadioItem(ID_VIEW_SCATTER, 'Scatter plot')
        self.menu_view.AppendRadioItem(ID_VIEW_HEATMAP, 'Heatmap plot')
        self.Bind(wx.EVT_MENU, self.toTXYView, id=ID_VIEW_TXY)
        self.Bind(wx.EVT_MENU, self.toXYView, id=ID_VIEW_XY)
        self.Bind(wx.EVT_MENU, self.toScatterView, id=ID_VIEW_SCATTER)
        self.Bind(wx.EVT_MENU, self.toHeatmapView, id=ID_VIEW_HEATMAP)
        self.menu_view.AppendSeparator()
        show_fix_num = self.menu_view.AppendCheckItem(ID_SHOW_FIXNUM, 'Show Fixation Number')
        if self.conf.CANVAS_SHOW_FIXNUMBER:
            show_fix_num.Check(True)
        else:
            show_fix_num.Check(False)
        show_selected_only = self.menu_view.AppendCheckItem(ID_SHOW_SELECTED_ONLY, 'Show selected only (Scatter, Heatmap)')
        if self.conf.CANVAS_SHOW_SELECTED_ONLY:
            show_selected_only.Check(True)
        else:
            show_selected_only.Check(False)
        show_stim_img = self.menu_view.AppendCheckItem(ID_SHOW_STIMIMAGE, 'Show Stimulus Image')
        if self.conf.CANVAS_SHOW_FIXNUMBER:
            show_stim_img.Check(True)
        else:
            show_stim_img.Check(False)
        self.Bind(wx.EVT_MENU, self.toggleFixNum, id=ID_SHOW_FIXNUM)
        self.Bind(wx.EVT_MENU, self.toggleSelectedOnly, id=ID_SHOW_SELECTED_ONLY)
        self.Bind(wx.EVT_MENU, self.toggleStimImage, id=ID_SHOW_STIMIMAGE)
        self.menu_view.AppendSeparator()
        self.menu_view.Append(ID_CONF_GRID, 'Config grid')
        self.menu_view.Append(ID_CONF_COLOR, 'Config color')
        self.menu_view.Append(ID_CONF_FONT, 'Config font')
        self.menu_view.Append(ID_CONF_STIMIMAGE, 'Config stimulus image')
        self.Bind(wx.EVT_MENU, self.configGrid, id=ID_CONF_GRID)
        self.Bind(wx.EVT_MENU, self.configColor, id=ID_CONF_COLOR)
        self.Bind(wx.EVT_MENU, self.configFont, id=ID_CONF_FONT)
        self.Bind(wx.EVT_MENU, self.configStimImage, id=ID_CONF_STIMIMAGE)
        self.menu_tools.Append(ID_TOOL_CONVERT, 'Convert Datafiles to GazeParser .db files')
        self.menu_tools.Append(ID_TOOL_EDITCONFIG, 'Edit GazeParser Configuration File')
        self.menu_tools.AppendSeparator()
        self.menu_tools.Append(ID_TOOL_GETLATENCY, 'Saccade latency')
        self.menu_tools.Append(ID_TOOL_GETFIXREG, 'Fixations in region')
        self.menu_tools.AppendSeparator()
        self.menu_tools.Append(ID_TOOL_ANIMATION, 'Animation')
        self.Bind(wx.EVT_MENU, self.convertDatafiles, id=ID_TOOL_CONVERT)
        self.Bind(wx.EVT_MENU, self.interactiveConfig, id=ID_TOOL_EDITCONFIG)
        self.Bind(wx.EVT_MENU, self.getLatency, id=ID_TOOL_GETLATENCY)
        self.Bind(wx.EVT_MENU, self.getFixationsInRegion, id=ID_TOOL_GETFIXREG)
        self.Bind(wx.EVT_MENU, self.animation, id=ID_TOOL_ANIMATION)
        
        # toolbar
        iconImgPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img')
        self.mainToolbar = self.CreateToolBar()
        self.mainToolbar.AddTool(wx.ID_OPEN, 'Open data file', wx.Bitmap(os.path.join(iconImgPath,'open.png')))
        self.mainToolbar.AddTool(wx.ID_SAVE, 'Save data file', wx.Bitmap(os.path.join(iconImgPath,'saveas.png')))
        self.mainToolbar.AddTool(ID_COMBINE, 'Combine data files', wx.Bitmap(os.path.join(iconImgPath,'combine.png')))
        self.mainToolbar.AddSeparator() 
        self.mainToolbar.AddTool(ID_PREV_TR, 'Prev', wx.Bitmap(os.path.join(iconImgPath,'previous.png')), wx.Bitmap(os.path.join(iconImgPath,'previous_disabled.png')))
        self.tcNTrials = wx.TextCtrl(self.mainToolbar, wx.ID_ANY, '(no data)', style=wx.TE_RIGHT)
        self.tcNTrials.Enable(False)
        self.tcJumpTo = wx.TextCtrl(self.mainToolbar, ID_JUMP_TO, style=wx.TE_RIGHT|wx.TE_PROCESS_ENTER)
        self.tcJumpTo.Bind(wx.EVT_TEXT_ENTER, self.jumpToTrial)
        self.mainToolbar.AddControl(self.tcNTrials)
        self.mainToolbar.AddControl(self.tcJumpTo)
        self.mainToolbar.AddTool(ID_NEXT_TR, 'Next', wx.Bitmap(os.path.join(iconImgPath,'next.png')), wx.Bitmap(os.path.join(iconImgPath,'next_disabled.png')))
        self.mainToolbar.EnableTool(ID_PREV_TR, False)
        self.mainToolbar.EnableTool(ID_NEXT_TR, False)
        self.mainToolbar.Realize()
        
        # viewFrame
        self.selectiontype = 'Emphasize'
        
        self.SetMenuBar(self.menu_bar)
        
        self.viewPanel = wx.Panel(self, wx.ID_ANY)
        self.fig = matplotlib.figure.Figure( None )
        self.canvas = FigureCanvasWxAgg( self.viewPanel, wx.ID_ANY, self.fig )
        self.ax = self.fig.add_axes([80.0/self.conf.CANVAS_WIDTH,  # 80px
                                     60.0/self.conf.CANVAS_HEIGHT,  # 60px
                                     1.0-2*80.0/self.conf.CANVAS_WIDTH,
                                     1.0-2*60.0/self.conf.CANVAS_HEIGHT])
        self.ax.axis(self.currentPlotArea)
        self.toolbar = NavigationToolbar2WxAgg(self.canvas)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, flag=wx.EXPAND, proportion=1)
        vbox.Add(self.toolbar, flag=wx.EXPAND, proportion=0)
        self.viewPanel.SetSizer(vbox)
        
        self.sidePane = wx.Notebook(self, wx.ID_ANY)
        
        self.eventPanel = wx.Panel(self.sidePane, wx.ID_ANY)
        self.selectradiobox = wx.RadioBox(self.eventPanel,wx.ID_ANY,'Selection',choices=SELECTMODES,style=wx.RA_HORIZONTAL)
        self.selectradiobox.SetSelection(SELECTMODES.index(self.selectiontype))
        self.msglistbox = wx.ListCtrl(self.eventPanel,ID_JUMPLIST_EVENT,style=wx.LC_REPORT)
        self.msglistbox.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.jumpToTime)
        self.msglistbox.Bind(wx.EVT_LIST_ITEM_SELECTED, self.updateInfo)
        self.msglistbox.InsertColumn(0, 'Time')
        self.msglistbox.InsertColumn(1, 'Event')
        
        buttonPanel = wx.Panel(self.eventPanel, wx.ID_ANY)
        okButton = wx.Button(buttonPanel, wx.ID_ANY, 'Set')
        cancelButton = wx.Button(buttonPanel, wx.ID_ANY, 'Clear')
        okButton.Bind(wx.EVT_BUTTON, self.setmarker)
        cancelButton.Bind(wx.EVT_BUTTON, self.clearmarker)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(okButton)
        hbox.Add(cancelButton)
        buttonPanel.SetSizer(hbox)
        
        self.infoTextCtrl = wx.TextCtrl(self.eventPanel, wx.ID_ANY, 
            '\n\n\n',
            style = wx.TE_MULTILINE|wx.TE_READONLY)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.selectradiobox, flag=wx.EXPAND, proportion=0)
        vbox.Add(buttonPanel, flag=wx.EXPAND, proportion=0)
        vbox.Add(self.msglistbox, flag=wx.EXPAND, proportion=1)
        vbox.Add(self.infoTextCtrl, flag=wx.EXPAND, proportion=0)
        self.eventPanel.SetSizerAndFit(vbox)

        self.trialPanel = wx.Panel(self.sidePane, wx.ID_ANY)
        self.jumplistbox = wx.ListCtrl(self.trialPanel,ID_JUMPLIST_REGISTERED,style=wx.LC_REPORT)
        self.jumplistbox.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.jumpToTrial)
        self.jumplistbox.Bind(wx.EVT_LIST_COL_CLICK, self.sortJumpList)
        self.jumplistSortAscend = True
        self.jumplistSortColumn = 0
        self.jumplistbox.InsertColumn(0, 'Trial')
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.jumplistbox, flag=wx.EXPAND, proportion=1)
        self.trialPanel.SetSizerAndFit(vbox)
        
        self.sidePane.InsertPage(0, self.eventPanel, 'Current Trial')
        self.sidePane.InsertPage(1, self.trialPanel, 'Registered')
        

        # popup menu
        menus = (('Edit selected message',self.editMessage),
                ('Insert new message',self.insertNewMessage),
                ('Delete selected message(s)',self.deleteMessages))
        self.popup_msglistbox = wx.Menu()
        for menu in menus:
            item = self.popup_msglistbox.Append(-1, menu[0])
            item.Enable(False)
            self.Bind(wx.EVT_MENU, menu[1], item)
        self.msglistbox.Bind(wx.EVT_CONTEXT_MENU, self.showPopupMsglistbox)

        menus = (('Delete selected jump point(s)',self.deleteJumplist),)
        self.popup_jumplistbox = wx.Menu()
        for menu in menus:
            item = self.popup_jumplistbox.Append(-1, menu[0])
            item.Enable(True)
            self.Bind(wx.EVT_MENU, menu[1], item)
        self.jumplistbox.Bind(wx.EVT_CONTEXT_MENU, self.showPopupJumplistbox)

        self._mgr = wx.aui.AuiManager(self)
        self._mgr.AddPane(self.viewPanel, wx.aui.AuiPaneInfo().Name("DataView").
            Caption("Data View").CenterPane().CloseButton(False).MaximizeButton(True))
        self._mgr.AddPane(self.sidePane, wx.aui.AuiPaneInfo().Name("JumpList").
            Caption("Jump List").RightDockable(True).LeftDockable(True).CloseButton(False).
            Right().MinSize(wx.Size(200,300)))
        self._mgr.Update()
        
        ac = []
        keys = ((wx.WXK_LEFT,self.prevTrial),
                (wx.WXK_RIGHT,self.nextTrial),
                (ord('v'),self.toggleView))
        for key in keys:
            _id = wx_NewIdRef()
            ac.append((wx.ACCEL_NORMAL, key[0], _id))
            self.Bind(wx.EVT_MENU, key[1], id=_id)
        tbl = wx.AcceleratorTable(ac)
        self.SetAcceleratorTable(tbl)
        
        self.SetSize(wx.Size(self.conf.CANVAS_WIDTH+220,self.conf.CANVAS_HEIGHT+64))
        self.SetAutoLayout(True)
        self.Show()

    def toggleView(self, event=None):
        if self.plotStyle == 'XY':
            self.plotStyle = 'SCATTER'
            self.currentPlotArea = self.plotAreaXY
            self.menu_view.Check(ID_VIEW_SCATTER, True)
        elif self.plotStyle == 'SCATTER':
            self.plotStyle = 'HEATMAP'
            self.currentPlotArea = self.plotAreaXY
            self.menu_view.Check(ID_VIEW_HEATMAP, True)
        elif self.plotStyle == 'HEATMAP':
            self.plotStyle = 'TXY'
            self.currentPlotArea = self.plotAreaTXY
            self.menu_view.Check(ID_VIEW_TXY, True)
        else:  # XYT
            self.plotStyle = 'XY'
            self.currentPlotArea = self.plotAreaXY
            self.menu_view.Check(ID_VIEW_XY, True)
        self.plotData()

    def toTXYView(self, event=None):
        self.plotStyle = 'TXY'
        self.currentPlotArea = self.plotAreaTXY
        self.plotData()

    def toXYView(self, event=None):
        self.plotStyle = 'XY'
        self.currentPlotArea = self.plotAreaXY
        self.plotData()

    def toScatterView(self, event=None):
        self.plotStyle = 'SCATTER'
        self.currentPlotArea = self.plotAreaXY
        self.plotData()

    def toHeatmapView(self, event=None):
        self.plotStyle = 'HEATMAP'
        self.currentPlotArea = self.plotAreaXY
        self.plotData()

    def toggleFixNum(self, event=None):
        if self.conf.CANVAS_SHOW_FIXNUMBER:
            self.conf.CANVAS_SHOW_FIXNUMBER = False
            #self.showFixationNumberItem.set(0)
        else:
            self.conf.CANVAS_SHOW_FIXNUMBER = True
            #self.showFixationNumberItem.set(1)

        self.plotData()

    def toggleSelectedOnly(self, event=None):
        if self.conf.CANVAS_SHOW_SELECTED_ONLY:
            self.conf.CANVAS_SHOW_SELECTED_ONLY = False
        else:
            self.conf.CANVAS_SHOW_SELECTED_ONLY = True

        if self.plotStyle in ['SCATTER','HEATMAP']:
            self.plotData()

    def toggleStimImage(self, event=None):
        if self.conf.CANVAS_SHOW_STIMIMAGE:
            self.conf.CANVAS_SHOW_STIMIMAGE = False
            # self.showStimulusImageItem.set(0)
        else:
            self.conf.CANVAS_SHOW_STIMIMAGE = True
            # self.showStimulusImageItem.set(1)

        self.plotData()

    def openfile(self, event=None):
        if self.dataModified:
            doSave = DlgAskyesno(self, 'Warning', 'Your changes have not been saved. Do you want to save the changes?')
            if doSave:
                self.savefile()

        fname = DlgAskopenfilename(self, filetypes=self.ftypes, initialdir=self.initialDataDir)
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
        for i in range(MAX_RECENT):
            self.menu_recent.SetLabel(recentIDList[i], str(i+1)+'. '+self.conf.RecentDir[i])
            if self.conf.RecentDir[i] == '':
                self.menu_recent.FindItemByPosition(i).Enable(False)
            else:
                self.menu_recent.FindItemByPosition(i).Enable(True)
        # if extension is .csv, try converting
        if os.path.splitext(self.dataFileName)[1].lower() == '.csv':
            dbFileName = os.path.splitext(self.dataFileName)[0]+'.db'
            print(dbFileName)
            if os.path.isfile(dbFileName):
                doOverwrite = DlgAskyesno(self, 'Overwrite?', dbFileName+' already exists. Overwrite?')
                if not doOverwrite:
                    DlgShowinfo(self, 'Info', 'Conversion canceled.')
                    return
            ret = GazeParser.Converter.TrackerToGazeParser(self.dataFileName, overwrite=True)
            if ret == 'SUCCESS':
                DlgShowinfo(self, 'Info', 'Conversion succeeded.\nOpen converted data file.')
                self.dataFileName = dbFileName
            else:
                DlgShowinfo(self, 'Conversion error', 'Failed to convert %s to GazeParser .db file' % (self.dataFileName))
                return

        [self.D, self.C] = GazeParser.load(self.dataFileName)
        if len(self.D) == 0:
            DlgShowerror(self, 'Error', 'File contains no data. (%s)' % (self.dataFileName))
            self.D = None
            self.C = None
            return

        self.dataModified = False

        if version.parse(self.D[0].__version__) < version.parse(GazeParser.__version__):
            lackingattributes = GazeParser.Utility.checkAttributes(self.D[0])
            if len(lackingattributes) > 0:
                ans = DlgAskyesno(self, 'Info', 'This data is generated by Version %s and lacks some data attributes newly appended in the later version. Try to append new attributes automatically? If you answered \'no\', some features may not work correctly.' % (self.D[0].__version__))
                if ans:
                    self.D = GazeParser.Utility.rebuildData(self.D)
                    self.dataModified = True
                    DlgShowinfo(self, 'Info', 'Automatic rebuild is finished.\nIf automatic rebuild seems to work as expected, please rebuild data from SimpleGazeTracker CSV file to add new attributes manually.')
                else:
                    DlgShowinfo(self, 'Info', 'Ok, Data file is opened without adding missing attributes.\nPlease rebuild data from SimpleGazeTracker CSV file to add new attributes manually.')

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
        self.selectradiobox.SetSelection(SELECTMODES.index('Emphasize'))
        self.menu_view.FindItemById(ID_PREV_TR).Enable(False)
        self.mainToolbar.EnableTool(ID_PREV_TR, False)
        if len(self.D) < 2:
            self.menu_view.FindItemById(ID_NEXT_TR).Enable(False)
            self.mainToolbar.EnableTool(ID_NEXT_TR, False)
        else:
            self.menu_view.FindItemById(ID_NEXT_TR).Enable(True)
            self.mainToolbar.EnableTool(ID_NEXT_TR, True)
        self.tcNTrials.SetValue('trials: 1-%d'%(len(self.D)))
        self.tcJumpTo.SetValue('1')

        self.loadStimImage()
        self.loadRegion()
        self.plotData()
        self.updateMsgBox()
        
        #clear jumplist
        self.jumplistbox.ClearAll()
        self.jumplistbox.InsertColumn(0, 'Trial', width=40)

        # enabel message-edit popup
        for item in self.popup_msglistbox.GetMenuItems():
            item.Enable(True)

    def openrecent(self, event=None):
        idx = recentIDList.index(event.Id)
        if not os.path.exists(self.conf.RecentDir[idx]):
            if DlgAskyesno(self, 'Info', self.conf.RecentDir[idx] + ' does not exist. Remove it from "Recent Dir"?'):
                self.conf.RecentDir.pop(idx)
                self.conf.RecentDir.append('')
                # update menu recent_dir
                for i in range(MAX_RECENT):
                    self.menu_recent.SetLabel(recentIDList[i], str(i+1)+'. '+self.conf.RecentDir[i])
                    if self.conf.RecentDir[i] == '':
                        self.menu_recent.FindItemByPosition(i).Enable(False)
                    else:
                        self.menu_recent.FindItemByPosition(i).Enable(True)
            return
        self.initialDataDir = self.conf.RecentDir[idx]
        self.openfile()

    def loadStimImage(self):
        msg = self.D[self.tr].findMessage('!STIMIMAGE', useRegexp=False)
        sep = ' '
        self.stimImage = None

        if len(msg) == 0:
            return False
        elif len(msg) > 1:
            DlgShowerror(self, 'Error', 'Multiple !STIMIMAGE commands in this trial.')
            return False

        found_embedded_image = False
        if self.conf.COMMAND_USE_EMBEDDED_IMAGE: # use embedded image
            try:
                img_names = self.C['EMBEDDED_IMAGES']['NAMES']
                img_list = self.C['EMBEDDED_IMAGES']['IMAGES']
                found_keys = True
            except:
                found_keys = False
            if found_keys:
                params = msg[0].text.split(sep)
                if params[0] != '!STIMIMAGE':
                    DlgShowerror(self, 'Error', '!STIMIMAGE command must be at the beginning of message text.')
                    return
                else:
                    if params[1] in img_names:
                        self.stimImage = img_list[img_names.index(params[1])]
                        found_embedded_image = True

        #else: # read from file
        if not found_embedded_image:
            if os.path.isabs(self.conf.COMMAND_STIMIMAGE_PATH):
                imagePath = self.conf.COMMAND_STIMIMAGE_PATH
            else:
                imagePath = os.path.join(os.path.split(self.dataFileName)[0], self.conf.COMMAND_STIMIMAGE_PATH)

            params = msg[0].text.split(sep)
            if params[0] != '!STIMIMAGE':
                DlgShowerror(self, 'Error', '!STIMIMAGE command must be at the beginning of message text.')
                return False
            try:
                imageFilename = os.path.join(imagePath, params[1])
                self.stimImage = Image.open(imageFilename)
            except:
                DlgShowerror(self, 'Error', 'Cannot open %s as StimImage.' % imageFilename)
                return False
        
        extent = params[2].split(',')

        # set extent [left, right, bottom, top] (See matplotlib.pyplot.imshow)
        if len(extent) == 2:
            # left and bottom are specified.
            try:
                self.stimImageExtent[0] = float(extent[0])
                self.stimImageExtent[2] = float(extent[1])
            except:
                DlgShowerror(self, 'Error', 'Invalid image extent: %s' % sep.join(params[2]))
                self.ImageExtent = [0, self.stimImage.size[0], 0, self.stimImage.size[1]]
                return False

            self.stimImageExtent[1] = self.stimImageExtent[0] + self.stimImage.size[0]
            self.stimImageExtent[3] = self.stimImageExtent[2] + self.stimImage.size[1]
        elif len(extent) == 4:
            # left, right, bottom and top are specified.
            try:
                self.stimImageExtent[0] = float(extent[0])
                self.stimImageExtent[1] = float(extent[1])
                self.stimImageExtent[2] = float(extent[2])
                self.stimImageExtent[3] = float(extent[3])
            except:
                DlgShowerror(self, 'Error', 'Invalid image extent: %s' % sep.join(params[2]))
                self.ImageExtent = [0, self.stimImage.size[0], 0, self.stimImage.size[1]]
                return False
        else:
                DlgShowerror(self, 'Warning', 'Invalid image extent: %s' % sep.join(params[2]))

        return True

    def loadRegion(self):
        msglist = self.D[self.tr].findMessage('!REGION', useRegexp=False)
        sep = ' '
        self.region = []

        for msg in msglist:
            commands = msg.text.split(sep)
            try:
                label = commands[1]

                regionparam = commands[3].split(',')

                if commands[2] == 'CIRCLE':
                    region = GazeParser.Region.CircleRegion(float(regionparam[0]),
                                                            float(regionparam[1]),
                                                            float(regionparam[2]))
                elif commands[2] == 'RECT':
                    region = GazeParser.Region.RectRegion(float(regionparam[0]),
                                                          float(regionparam[1]),
                                                          float(regionparam[2]),
                                                          float(regionparam[3]))
                else:
                    raise ValueError('Invalid REGION: {} {}'.format(commands[2],commands[3]))
            except:
                info = sys.exc_info()
                tbinfo = traceback.format_tb(info[2])
                errormsg = ''
                for tbi in tbinfo:
                    errormsg += tbi
                errormsg += '  %s' % str(info[1])
                DlgShowerror(self, 'Error', msg.text+'\n\n'+errormsg)
                continue
            
            self.region.append((label, region))


    def savefile(self, event=None):
        if self.D is None:
            DlgShowinfo(self, 'info', 'No data')
            return

        filename = DlgAsksaveasfilename(self, filetypes=self.datafiletype, initialfile=self.dataFileName, initialdir=self.initialDataDir)
        if filename == '':
            return

        try:
            GazeParser.save(filename, self.D, self.C)
        except:
            DlgShowinfo(self, 'Error', 'Cannot save data as %s' % (filename))
            return

        self.dataModified = False


    def exportfile(self, event=None):
        if self.D is None:
            DlgShowinfo(self, 'info', 'Data must be loaded before export')
            return
        dlg = exportToFileDialog(parent=self, id=wx.ID_ANY, data=self.D, additional=self.C, trial=self.tr, initialdir=self.initialDataDir)
        dlg.ShowModal()
        dlg.Destroy()

    def configColor(self, event=None):
        dlg = configColorDialog(parent=self)
        dlg.ShowModal()
        dlg.Destroy()

    def exit(self, event=None):
        if self.dataModified:
            doSave = DlgAskyesno(self, 'Warning', 'Your changes have not been saved. Do you want to save the changes?')
            if doSave:
                self.savefile()
        self.conf._write()
        self._mgr.UnInit()
        del self._mgr
        self.Destroy()

    def prevTrial(self, event=None):
        if self.D is None:
            DlgShowerror(self, 'Error', 'No Data')
            return
        if self.tr > 0:
            self.tr -= 1
            if self.tr == 0:
                self.menu_view.FindItemById(ID_PREV_TR).Enable(False)
                self.mainToolbar.EnableTool(ID_PREV_TR, False)
            else:
                self.menu_view.FindItemById(ID_PREV_TR).Enable(True)
                self.mainToolbar.EnableTool(ID_PREV_TR, True)
            if self.tr == len(self.D)-1:
                self.menu_view.FindItemById(ID_NEXT_TR).Enable(False)
                self.mainToolbar.EnableTool(ID_NEXT_TR, False)
            else:
                self.menu_view.FindItemById(ID_NEXT_TR).Enable(True)
                self.mainToolbar.EnableTool(ID_NEXT_TR, True)
        self.tcJumpTo.SetValue(str(self.tr+1))
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        self.selectiontype = 'Emphasize'
        self.loadStimImage()
        self.loadRegion()
        self.plotData()
        self.updateMsgBox()

    def nextTrial(self, event=None):
        if self.D is None:
            DlgShowerror(self, 'Error', 'No Data')
            return
        if self.tr < len(self.D)-1:
            self.tr += 1
            if self.tr == 0:
                self.menu_view.FindItemById(ID_PREV_TR).Enable(False)
                self.mainToolbar.EnableTool(ID_PREV_TR, False)
            else:
                self.menu_view.FindItemById(ID_PREV_TR).Enable(True)
                self.mainToolbar.EnableTool(ID_PREV_TR, True)
            if self.tr == len(self.D)-1:
                self.menu_view.FindItemById(ID_NEXT_TR).Enable(False)
                self.mainToolbar.EnableTool(ID_NEXT_TR, False)
            else:
                self.menu_view.FindItemById(ID_NEXT_TR).Enable(True)
                self.mainToolbar.EnableTool(ID_NEXT_TR, True)
        self.tcJumpTo.SetValue(str(self.tr+1))
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        self.selectiontype = 'Emphasize'
        self.loadStimImage()
        self.loadRegion()
        self.plotData()
        self.updateMsgBox()

    def jumpToTrial(self, event=None):
        if event.Id == ID_JUMPLIST_REGISTERED:
            newtr = int(event.GetText())-1
            self.tcJumpTo.SetValue(str(newtr+1))
        elif event.Id == ID_JUMP_TO:
            try:
                newtr = int(self.tcJumpTo.GetValue())-1
            except:
                DlgShowerror(self, 'Error', 'Value must be an integer')
                return

            if newtr < 0 or newtr >= len(self.D):
                DlgShowerror(self, 'Error', 'Invalid trial number')
                return
        else:
            DlgShowerror(self, 'Erro', 'Invalid event ID')
        
        if self.D is None:
            DlgShowerror(self, 'Error', 'No Data')
            return

        redraw_plot = True
        if self.tr == newtr:
            redraw_plot = False
        self.tr = newtr
        if self.tr == 0:
            self.menu_view.FindItemById(ID_PREV_TR).Enable(False)
            self.mainToolbar.EnableTool(ID_PREV_TR, False)
        else:
            self.menu_view.FindItemById(ID_PREV_TR).Enable(True)
            self.mainToolbar.EnableTool(ID_PREV_TR, True)
        if self.tr == len(self.D)-1:
            self.menu_view.FindItemById(ID_NEXT_TR).Enable(False)
            self.mainToolbar.EnableTool(ID_NEXT_TR, False)
        else:
            self.menu_view.FindItemById(ID_NEXT_TR).Enable(True)
            self.mainToolbar.EnableTool(ID_NEXT_TR, True)
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        self.selectiontype = 'Emphasize'
        self.updateMsgBox()
        
        if event.Id == ID_JUMPLIST_REGISTERED:
            # save current plot range before plotting new trial
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()

            if redraw_plot:
                self.loadStimImage()
                self.loadRegion()
            self.plotData(draw=redraw_plot)

            # restore plot range
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)

            # then jump to time
            self.jumpToTime(event)
        else:
            self.loadStimImage()
            self.loadRegion()
            self.plotData()
        
    def jumpToTime(self, event=None):
        if self.plotStyle in XYPLOTMODES:
            if event.Id == ID_JUMPLIST_EVENT:
                i = event.GetIndex()
                if isinstance(self.D[self.tr].EventList[i], GazeParser.Core.SaccadeData):
                    pos = (self.D[self.tr].EventList[i].start + self.D[self.tr].EventList[i].end)/2.0
                elif isinstance(self.D[self.tr].EventList[i], GazeParser.Core.FixationData):
                    pos = self.D[self.tr].EventList[i].center
                else:
                    return
            elif event.Id == ID_JUMPLIST_REGISTERED:
                posstr = self.jumplistbox.GetItem(event.GetIndex(),3).GetText()
                pos = list(map(float, posstr.split(',')))

            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            halfXrange = (xlim[1]-xlim[0])/2.0
            halfYrange = (ylim[1]-ylim[0])/2.0
            self.ax.set_xlim((pos[0]-halfXrange, pos[0]+halfXrange))
            self.ax.set_ylim((pos[1]-halfYrange, pos[1]+halfYrange))
            self.fig.canvas.draw()

        else:
            if event.Id == ID_JUMPLIST_EVENT:
                time = float(event.GetText())  # time
            elif event.Id == ID_JUMPLIST_REGISTERED:
                time = float(self.jumplistbox.GetItem(event.GetIndex(), 1).GetText())
            xlim = self.ax.get_xlim()
            halfXrange = (xlim[1]-xlim[0])/2.0
            self.ax.set_xlim((time-halfXrange, time+halfXrange))
            self.fig.canvas.draw()

    def sortJumpList(self, event=None):
        targetCol = event.GetColumn()
        if targetCol == self.jumplistSortColumn:
            self.jumplistSortAscend = not self.jumplistSortAscend
        else:
            self.jumplistSortColumn = targetCol
        
        items = []
        targetColItems = []
        rows = self.jumplistbox.GetItemCount()
        cols = self.jumplistbox.GetColumnCount()
        for row in range(rows):
            item = [self.jumplistbox.GetItem(row, col=col).GetText() for col in range(cols)]
            items.append(item)
            itemStr = self.jumplistbox.GetItem(row, col=targetCol).GetText()
            try:
                targetColItems.append(float(itemStr))
            except:
                targetColItems.append(itemStr)
        indexList = np.array(targetColItems).argsort(kind='mergesort')
        if not self.jumplistSortAscend:
            indexList = indexList[-1::-1] # reverse
        for row in range(rows):
            for col in range(cols):
                self.jumplistbox.SetItem(row, col, items[indexList[row]][col])

    def updateInfo(self, event=None):
        if event.Id == ID_JUMPLIST_EVENT:
            i = event.GetIndex()
            if isinstance(self.D[self.tr].EventList[i], GazeParser.Core.SaccadeData):
                msg = 'Amp:{:.2f} ({:.2f}pix)\nDur:{} ms\nFrom:{} To:{}'.format(
                    self.D[self.tr].EventList[i].amplitude,
                    self.D[self.tr].EventList[i].length,
                    self.D[self.tr].EventList[i].duration,
                    self.D[self.tr].EventList[i].start,
                    self.D[self.tr].EventList[i].end)
                pos = (self.D[self.tr].EventList[i].start + self.D[self.tr].EventList[i].end)/2.0
            elif isinstance(self.D[self.tr].EventList[i], GazeParser.Core.FixationData):
                pos = self.D[self.tr].EventList[i].center
                msg = 'Dur:{} ms\nCenter:({:.1f},{:.1f})'.format(
                    self.D[self.tr].EventList[i].duration,
                    self.D[self.tr].EventList[i].center[0],
                    self.D[self.tr].EventList[i].center[1])
            else:
                msg = ''
            
            self.infoTextCtrl.SetValue(msg)

    def showPopupMsglistbox(self, event=None):
        pos = event.GetPosition()
        pos = self.msglistbox.ScreenToClient(pos)
        self.msglistbox.PopupMenu(self.popup_msglistbox, pos)
        event.Skip()

    def showPopupJumplistbox(self, event=None):
        pos = event.GetPosition()
        pos = self.jumplistbox.ScreenToClient(pos)
        self.jumplistbox.PopupMenu(self.popup_jumplistbox, pos)
        event.Skip()

    def configGrid(self, event=None):
        dlg = configGridDialog(parent=self)
        dlg.ShowModal()
        dlg.Destroy()

    def updateGrid(self):
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
                DlgShowerror(self, 'Error', '"%s" is not a float number.', (params[1]))
                return
            self.ax.xaxis.grid(True)
            self.ax.xaxis.set_major_locator(MultipleLocator(interval))
        elif params[0] == 'CUSTOM':
            try:
                format = eval(params[1])
            except:
                DlgShowerror(self, 'Error', '"%s" is not a python statement.' % (params[1]))
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
                DlgShowerror(self, 'Error', '"%s" is not a float number.' % (params[1]))
                return
            self.ax.yaxis.grid(True)
            self.ax.yaxis.set_major_locator(MultipleLocator(interval))
        elif params[0] == 'CUSTOM':
            try:
                format = eval(params[1])
            except:
                DlgShowerror(self, 'Error', '"%s" is not a python statement.' % (params[1]))
                return
            self.ax.yaxis.grid(True)
            self.ax.yaxis.set_ticks(format)
        else:
            raise ValueError('Unknown ordinate grid type (%s)' % (params[0]))

    def plotData(self, draw=True):
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
                    if self.selectiontype == 'Emphasize':
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
                    if self.selectiontype == 'Emphasize':
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
                    if self.selectiontype == 'Emphasize':
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
                    if self.selectiontype == 'Emphasize':
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
            fixdur = self.D[self.tr].getFixDur().flatten()
            if self.conf.CANVAS_SHOW_SELECTED_ONLY and self.selectiontype == 'Extract':
                sidx = self.selectionlist['Fix']
                self.ax.plot(fixcenter[sidx, 0], fixcenter[sidx, 1], 'k-')
                self.ax.scatter(fixcenter[sidx, 0], fixcenter[sidx, 1], s=fixdur[sidx], c=fixdur[sidx], alpha=0.7)
            else:
                self.ax.plot(fixcenter[:, 0], fixcenter[:, 1], 'k-')
                self.ax.scatter(fixcenter[:, 0], fixcenter[:, 1], s=fixdur, c=fixdur, alpha=0.7)
            for f in range(self.D[self.tr].nFix):
                if self.selectiontype == 'Emphasize':
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
            xstep = (xmax-xmin)/512.0
            ystep = (ymax-ymin)/512.0
            xmesh, ymesh = np.meshgrid(np.arange(xmin, xmax, xstep),
                                          np.arange(ymin, ymax, ystep))
            heatmap = np.zeros(xmesh.shape)
            for idx in range(fixcenter.shape[0]):
                if np.isnan(fixcenter[idx, 0]) or np.isnan(fixcenter[idx, 1]):
                    continue
                if self.conf.CANVAS_SHOW_SELECTED_ONLY and self.selectiontype == 'Extract' and not idx in self.selectionlist['Fix']:
                    continue
                heatmap = heatmap + fixdur[idx, 0]*np.exp(-((xmesh-fixcenter[idx, 0])/50)**2-((ymesh-fixcenter[idx, 1])/50)**2)
            masked_heatmap = np.ma.masked_where(heatmap < 0.001, heatmap)
            cmap = matplotlib.cm.get_cmap('hot')
            cmap._init()
            alphas = np.linspace(0.0, 5.0, cmap.N)
            alphas[np.where(alphas > 0.8)[0]] = 0.8
            cmap._lut[:-3, -1] = alphas
            self.ax.imshow(masked_heatmap, extent=(xmin, xmax, ymin, ymax), origin='lower', cmap=cmap)

            for f in range(self.D[self.tr].nFix):
                if self.selectiontype == 'Emphasize':
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
                    if self.selectiontype == 'Emphasize':
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
                if self.selectiontype == 'Emphasize':
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart, -10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       fc=self.conf.COLOR_SACCADE_HATCH_E, alpha=0.8))  # hatch='///', 
                    else:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart, -10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))  # hatch='///', 
                else:
                    if s in self.selectionlist['Sac']:
                        self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Sac[s].startTime-tStart, -10000],
                                                                       self.D[self.tr].Sac[s].duration, 20000,
                                                                       fc=self.conf.COLOR_SACCADE_HATCH, alpha=0.3))  # hatch='///', 

            for b in range(self.D[self.tr].nBlink):
                self.ax.add_patch(matplotlib.patches.Rectangle([self.D[self.tr].Blink[b].startTime-tStart, -10000],
                                                               self.D[self.tr].Blink[b].duration, 20000,
                                                               fc=self.conf.COLOR_BLINK_HATCH, alpha=0.3))  # hatch='\\\\\\', 

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

        if self.plotStyle in XYPLOTMODES and self.conf.CANVAS_SHOW_REGION:
            for (label, region) in self.region:
                self.ax.add_patch(matplotlib.patches.Rectangle([region.x1, region.y1], region.x2-region.x1, region.y2-region.y1,
                                                               ec=self.conf.COLOR_REGION_EC, fill=False))
                self.ax.text(region.x1, region.y2, label, color=self.conf.COLOR_REGION_EC, fontproperties=self.fontPlotText)

        # set plotrange and axis labels
        if self.plotStyle in XYPLOTMODES:
            if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
                self.ax.set_xlabel('Vertical gaze position (pix)', fontproperties=self.fontPlotText)
                self.ax.set_ylabel('Horizontal gaze position (pix)', fontproperties=self.fontPlotText)
            elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
                self.ax.set_xlabel('Vertical gaze position (deg)', fontproperties=self.fontPlotText)
                self.ax.set_ylabel('Horizontal gaze position (deg)', fontproperties=self.fontPlotText)

            self.ax.axis((sf[0]*self.currentPlotArea[0], sf[0]*self.currentPlotArea[1],
                          sf[1]*self.currentPlotArea[2], sf[1]*self.currentPlotArea[3]))
            self.ax.set_aspect('equal')
        else:  # TXY
            if self.conf.CANVAS_XYAXES_UNIT.upper() == 'PIX':
                self.ax.set_xlabel('Time (ms)', fontproperties=self.fontPlotText)
                self.ax.set_ylabel('Gaze position (pix)', fontproperties=self.fontPlotText)
            elif self.conf.CANVAS_XYAXES_UNIT.upper() == 'DEG':
                self.ax.set_xlabel('Time (ms)', fontproperties=self.fontPlotText)
                self.ax.set_ylabel('Gaze position (deg)', fontproperties=self.fontPlotText)

            self.ax.axis((self.currentPlotArea[0], self.currentPlotArea[1],
                          sf[0]*self.currentPlotArea[2], sf[0]*self.currentPlotArea[3]))
            self.ax.set_aspect('auto')

        self.ax.set_title('%s: Trial %d / %d' % (os.path.basename(self.dataFileName), self.tr+1, len(self.D)), fontproperties=self.fontPlotText)
        self.updateGrid()
        if draw:
            self.fig.canvas.draw()

    def updateMsgBox(self):
        self.msglistbox.DeleteAllItems()

        st = self.D[self.tr].T[0]
        et = self.D[self.tr].T[-1]

        idx=0
        for e in self.D[self.tr].EventList:
            if isinstance(e, GazeParser.SaccadeData):
                self.msglistbox.InsertItem(idx, '%10.1f' % (e.startTime))
                self.msglistbox.SetItem(idx, 1, 'Sac')
                idx+=1
            elif isinstance(e, GazeParser.FixationData):
                self.msglistbox.InsertItem(idx, '%10.1f' % (e.startTime))
                self.msglistbox.SetItem(idx, 1, 'Fix')
                idx+=1
                # self.msglistbox.itemconfig(Tkinter.END, bg=self.conf.COLOR_TRAJECTORY_L_FIX)
            elif isinstance(e, GazeParser.MessageData):
                self.msglistbox.InsertItem(idx, '%10.1f' % (e.time))
                self.msglistbox.SetItem(idx, 1, e.text)
                self.msglistbox.SetItemBackgroundColour(idx, self.conf.COLOR_MESSAGE_BG)
                self.msglistbox.SetItemTextColour(idx, self.conf.COLOR_MESSAGE_FC)
                idx+=1
            elif isinstance(e, GazeParser.BlinkData):
                self.msglistbox.InsertItem(idx, '%10.1f' % (e.startTime))
                self.msglistbox.SetItem(idx, 1, 'Blk')
                idx+=1

    def setmarker(self, event=None):
        selected = []
        for idx in range(self.msglistbox.GetItemCount()):
            if self.msglistbox.GetItemState(idx, wx.LIST_STATE_SELECTED) != 0:
                selected.append(idx)
        
        self.selectiontype = SELECTMODES[self.selectradiobox.GetSelection()]
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        
        for s in selected:
            e = self.D[self.tr].EventList[int(s)]
            if isinstance(e, GazeParser.SaccadeData):
                self.selectionlist['Sac'].append(findGazeParserObjectIndex(e, self.D[self.tr].Sac)[0])
            elif isinstance(e, GazeParser.FixationData):
                self.selectionlist['Fix'].append(findGazeParserObjectIndex(e, self.D[self.tr].Fix)[0])
            elif isinstance(e, GazeParser.MessageData):
                self.selectionlist['Msg'].append(findGazeParserObjectIndex(e, self.D[self.tr].Msg)[0])
            elif isinstance(e, GazeParser.BlinkData):
                self.selectionlist['Blink'].append(findGazeParserObjectIndex(e, self.D[self.tr].Blink)[0])

        # self.currentPlotArea = self.ax.get_xlim()+self.ax.get_ylim()
        self.plotData()

    def clearmarker(self, event=None):
        for idx in range(self.msglistbox.GetItemCount()):
            self.msglistbox.SetItemState(idx, 0, wx.LIST_STATE_SELECTED)
        self.selectionlist = {'Sac': [], 'Fix': [], 'Msg': [], 'Blink': []}
        self.plotData()

    def convertDatafiles(self, event=None):
        dlg = convertDialog(parent=self)
        dlg.ShowModal()
        dlg.Destroy()

    def interactiveConfig(self, event=None):
        if self.D is None:
            DlgShowinfo(self, 'info', 'Data must be loaded before\nusing interactive configuration.')
            return
        frame = interactiveConfigFrame(parent=self)
        frame.Destroy()

    def getLatency(self, event=None):
        if self.D is None:
            DlgShowinfo(self, 'info', 'Data must be loaded before getting saccade latency')
            return
        dlg = getSaccadeLatencyDialog(parent=self)
        dlg.ShowModal()
        dlg.Destroy()

    def getFixationsInRegion(self, event=None):
        if self.D is None:
            DlgShowinfo(self, 'info', 'Data must be loaded before getting fixations in region')
            return
        dlg = getFixationsInRegionDialog(parent=self)
        dlg.ShowModal()
        dlg.Destroy()

    def editMessage(self, event=None):
        if self.D is None:
            DlgShowinfo(self, 'info', 'Data must be loaded before editing message')
            return

        selected = []
        for idx in range(self.msglistbox.GetItemCount()):
            if self.msglistbox.GetItemState(idx, wx.LIST_STATE_SELECTED) != 0:
                selected.append(idx)
        numSelectedMessages = 0
        for s in selected:
            e = self.D[self.tr].EventList[int(s)]
            if isinstance(e, GazeParser.MessageData):
                numSelectedMessages += 1
                if numSelectedMessages > 1:
                    DlgShowerror(self, 'Error', 'More than two messages are selected.')
                    return

        if numSelectedMessages == 0:
            DlgShowerror(self, 'Error', 'No messages are selected.')
            return

        dlg = editMessageDialog(parent=self, id=wx.ID_ANY, message=self.D[self.tr].EventList[int(selected[0])])
        dlg.ShowModal()
        dlg.Destroy()


    def insertNewMessage(self, event=None):
        if self.D is None:
            DlgShowinfo(self, 'info', 'Data must be loaded before inserting new message')
            return
            
        dlg = insertNewMessageDialog(parent=self, id=wx.ID_ANY)
        dlg.ShowModal()
        dlg.Destroy()

    def deleteMessages(self, event=None):
        selected = []
        for idx in range(self.msglistbox.GetItemCount()):
            if self.msglistbox.GetItemState(idx, wx.LIST_STATE_SELECTED) != 0:
                selected.append(idx)
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

        ans = DlgAskyesno(self, 'Warning', 'You cannot undo this operation. Are you sure to delete following message(s)?\n\n'+selectedMessagesText)
        if ans:
            for m in selectedMessages:
                m.delete()
            self.updateMsgBox()
            self.loadStimImage()
            self.loadRegion()
            self.plotData()

            self.dataModified = True

    def deleteJumplist(self, event=None):
        selected = []
        for idx in range(self.jumplistbox.GetItemCount()):
            if self.jumplistbox.GetItemState(idx, wx.LIST_STATE_SELECTED) != 0:
                selected.append(idx)

        ans = DlgAskyesno(self, 'Warning', 'You cannot undo this operation. Are you sure to delete selected jump points?')
        if ans:
            selected.reverse()
            for idx in selected:
                self.jumplistbox.DeleteItem(idx)

    def configFont(self, event=None):
        dlg = fontSelectDialog(parent=self, id=wx.ID_ANY)
        dlg.ShowModal()
        dlg.Destroy()

    def configStimImage(self, event=None):
        dlg = configStimImageDialog(parent=self, id=wx.ID_ANY)
        dlg.ShowModal()
        dlg.Destroy()

    def combinefiles(self, event=None):
        dlg = combineDataFileDialog(parent=self, id=wx.ID_ANY)
        dlg.ShowModal()
        dlg.Destroy()

    def animation(self, event=None):
        if self.D is None:
            DlgShowinfo(self, 'info', 'Data must be loaded before using this function')
            return
        dlg = animationDialog(parent=self, id=wx.ID_ANY)
        dlg.ShowModal()
        if dlg.timer.IsRunning():
            dlg.timer.Stop()
        dlg.Destroy()

class ViewerApp(wx.App):
    def __init__(self, arg=0, **kwargs):
        wx.App.__init__(self, arg)
        self.onInit()

    def onInit(self, showSplash=True, testMode=False):
        self.mainFrame = mainFrame(self)
        self.mainFrame.Show(True)
        return True

if __name__ == "__main__":

    application = ViewerApp()
    application.MainLoop()

