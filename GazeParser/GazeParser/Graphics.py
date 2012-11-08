"""
.. Part of GazeParser package.
.. Copyright (C) 2012 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""

import matplotlib.pyplot as pyplot
import numpy
import GazeParser
#from scipy import fftpack
#from scipy.stats import nanstd,nanmean

__version__ = GazeParser.release_name

def drawHeatMap(data,meshsize):
    """
    
    :param data: An instance of :class:`GazeParser.Core.GazeData` or a list of 
        :class:`GazeParser.Core.FixationData` objects.
    :param meshsize: An array of 2x3 items.
    """
    xmesh,ymesh = numpy.meshgrid(numpy.arange(meshsize[0][0],meshsize[0][1],meshsize[0][2]),
                                 numpy.arange(meshsize[1][0],meshsize[1][1],meshsize[1][2]))
    heatmap = numpy.zeros(xmesh.shape)
    if isinstance(data,GazeParser.GazeData):
        xy = data.getFixCenter()
        dur = data.getFixDur()
    else:
        xy = numpy.zeros((2,len(data)))
        dur = numpy.zeros(len(data))
        for i in range(len(data)):
            xy[i,:] = data[i].center
            dur[i] = data[i].duration
    for idx in range(xy.shape[0]):
        if numpy.isnan(xy[idx,0]) or numpy.isnan(xy[idx,1]):
            continue
        heatmap = heatmap + dur[idx,0]*numpy.exp(-((xmesh-xy[idx,0])/50)**2-((ymesh-xy[idx,1])/50)**2)
    pyplot.hot()
    pyplot.imshow(heatmap,extent=(meshsize[0][0],meshsize[0][1],meshsize[1][0],meshsize[1][1]),origin='lower')

def drawScatterPlot(data):
    """
    
    :param data: An instance of :class:`GazeParser.Core.GazeData`, a list of 
        :class:`GazeParser.Core.FixationData` objects, or a list of fixation points.
    """
    if isinstance(data,GazeParser.GazeData):
        xy = data.getFixCenter()
        dur = data.getFixDur()
    else:
        xy = numpy.zeros((2,len(data)))
        dur = numpy.zeros(len(data))
        for i in range(len(data)):
            xy[i,:] = data[i].center
            dur[i] = data[i].duration
    pyplot.plot(xy[:,0],xy[:,1],'k-')
    for idx in range(xy.shape[0]):
        pyplot.text(xy[idx,0],xy[idx,1],str(idx+1))
    pyplot.scatter(xy[:,0],xy[:,1],s=dur,c=dur,alpha=0.7)

def quickPlot(data,eye=None,period=(None,None),style='XY',xlim=None,ylim=None):
    """
    Plot gaze trajectory easily.
    
    :param data:
        If GazeParser.Core.SaccadeData or GazeParser.Core.FixationData instance
        is passed, Trajectory of the saccade or fixation is plotted.
        If GazeParser.Core.GazeData object is passed, whole gaze trajectory in 
        the trial is plotted.
    :param str eye:
        'L', 'R' or 'B' for left eye, right eye and both eyes.  If None,
        recorded eye is used.  Default value is None.
    :param tuple period:
        Specify the period for data plotting *when the data is an instance of 
        GazeParser.Core.GazeData*. The first element of the tuple specifies the 
        start time of the period. If None is given as the first element, the
        data is plotted from the begenning. The second element is the end time 
        of the period. I None is given as the second element, the data is 
        plotted to the end. The unit of these values are millisecond.
        Default value is (None, None).
    :param str style:
        'XY' or 'XYT' is accepted.  Default value is 'XY'.
    :param tuple xlim:
        If this value is not None, the value is passed tomatplotlib.pyplot.xlim().
        Default value is None.
    :param tuple ylim:
        If this value is not None, the value is passed to matplotlib.pyplot.ylim().
        Default value is None.
    """
    if isinstance(data,GazeParser.Core.SaccadeData) or isinstance(data,GazeParser.Core.FixationData):
        traj = data.getTraj(eye)
        if style=='XY':
            if traj.shape[1]==2:
                pyplot.plot(traj[:,0],traj[:,1],'.-')
                pyplot.text(traj[0,0],traj[0,1],'S',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(traj[-1,0],traj[-1,1],'E',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
            else:
                pyplot.plot(traj[:,0],traj[:,1],'.-',label='L')
                pyplot.plot(traj[:,2],traj[:,3],'.-',label='R')
                pyplot.text(traj[0,0],traj[0,1],'S',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(traj[-1,0],traj[-1,1],'E',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(traj[0,2],traj[0,3],'S',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(traj[-1,2],traj[-1,3],'E',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.legend()
        elif style=='XYT':
            si = data.startIndex
            ei = data.endIndex+1
            t = data.parent._T
            if traj.shape[1]==2:
                pyplot.plot(t[si:ei],traj[:,0],'.-',label='X')
                pyplot.plot(t[si:ei],traj[:,1],'.-',label='Y')
                pyplot.legend()
            else:
                pyplot.plot(t[si:ei],traj[:,0],'.-',label='LX')
                pyplot.plot(t[si:ei],traj[:,1],'.-',label='LY')
                pyplot.plot(t[si:ei],traj[:,2],'.-',label='RX')
                pyplot.plot(t[si:ei],traj[:,3],'.-',label='RY')
                pyplot.legend()
        else:
            raise ValueError, 'style must be XY or XYT.'
        
    elif isinstance(data,GazeParser.Core.GazeData):
        if eye==None:
            eye = data._recordedEye
        
        if period[0]==None:
            si = 0
        else:
            si = numpy.where(data._T>=period[0])[0][0]
        if period[0]==None:
            ei = -1
        else:
            ei = numpy.where(data._T<=period[1])[0][-1]
        
        if style=='XY':
            if eye=='L':
                pyplot.plot(data._L[si:ei,0],data._L[si:ei,1],'.-')
                pyplot.text(data._L[0,0],data._L[0,1],'S',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(data._L[-1,0],data._L[-1,1],'E',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
            elif eye=='R':
                pyplot.plot(data._R[si:ei,0],data._R[si:ei,1],'.-')
                pyplot.text(data._R[0,0],data._R[0,1],'S',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(data._R[-1,0],data._R[-1,1],'E',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
            elif eye=='B':
                pyplot.plot(data._L[si:ei,0],data._L[si:ei,1],'.-',label='L')
                pyplot.plot(data._R[si:ei,0],data._R[si:ei,1],'.-',label='R')
                pyplot.text(data._L[0,0],data._L[0,1],'S',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(data._L[-1,0],data._L[-1,1],'E',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(data._R[0,0],data._R[0,1],'S',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.text(data._R[-1,0],data._R[-1,1],'E',ha='center',va='center',bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.legend()
            else:
                raise ValueError, 'eye must be \'L\', \'R\', or \'B\'.'
        elif style=='XYT':
            if eye=='L':
                pyplot.plot(data._T[si:ei],data._L[si:ei,0],'.-',label='X')
                pyplot.plot(data._T[si:ei],data._L[si:ei,1],'.-',label='Y')
                pyplot.legend()
            elif eye=='R':
                pyplot.plot(data._T[si:ei],data._R[si:ei,0],'.-',label='X')
                pyplot.plot(data._T[si:ei],data._R[si:ei,1],'.-',label='Y')
                pyplot.legend()
            elif eye=='B':
                pyplot.plot(data._T[si:ei],data._L[si:ei,0],'.-',label='LX')
                pyplot.plot(data._T[si:ei],data._L[si:ei,1],'.-',label='LY')
                pyplot.plot(data._T[si:ei],data._R[si:ei,0],'.-',label='RX')
                pyplot.plot(data._T[si:ei],data._R[si:ei,1],'.-',label='RY')
                pyplot.legend()
            else:
                raise ValueError, 'eye must be \'L\', \'R\', or \'B\'.'
        else:
            raise ValueError, 'style must be XY or XYT.'
    
    if not xlim==None:
        pyplot.xlim(xlim)
    if not ylim==None:
        pyplot.ylim(ylim)
    
