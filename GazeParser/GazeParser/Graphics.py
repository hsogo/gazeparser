"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2025 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import matplotlib.pyplot as pyplot
import numpy as np
import GazeParser
# from scipy import fftpack
# from scipy.stats import nanstd, nanmean

__version__ = GazeParser.release_name


def drawHeatMap(data, meshsize):
    """
    :param data: An instance of :class:`GazeParser.Core.GazeData` or a list of
        :class:`GazeParser.Core.FixationData` objects.
    :param meshsize: An array of 2x3 items.
    """
    xmesh, ymesh = np.meshgrid(np.arange(meshsize[0][0], meshsize[0][1], meshsize[0][2]),
                                  np.arange(meshsize[1][0], meshsize[1][1], meshsize[1][2]))
    heatmap = np.zeros(xmesh.shape)
    if isinstance(data, GazeParser.GazeData):
        xy = data.getFixCenter()
        dur = data.getFixDur()
    else:
        xy = np.zeros((2, len(data)))
        dur = np.zeros(len(data))
        for i in range(len(data)):
            xy[i, :] = data[i].center
            dur[i] = data[i].duration
    for idx in range(xy.shape[0]):
        if np.isnan(xy[idx, 0]) or np.isnan(xy[idx, 1]):
            continue
        heatmap = heatmap + dur[idx, 0]*np.exp(-((xmesh-xy[idx, 0])/50)**2-((ymesh-xy[idx, 1])/50)**2)
    pyplot.hot()
    pyplot.imshow(heatmap, extent=(meshsize[0][0], meshsize[0][1], meshsize[1][0], meshsize[1][1]), origin='lower')


def drawScatterPlot(data):
    """
    :param data: An instance of :class:`GazeParser.Core.GazeData`, a list of
        :class:`GazeParser.Core.FixationData` objects, or a list of fixation points.
    """
    if isinstance(data, GazeParser.GazeData):
        xy = data.getFixCenter()
        dur = data.getFixDur()
    else:
        xy = np.zeros((2, len(data)))
        dur = np.zeros(len(data))
        for i in range(len(data)):
            xy[i, :] = data[i].center
            dur[i] = data[i].duration
    pyplot.plot(xy[:, 0], xy[:, 1], 'k-')
    for idx in range(xy.shape[0]):
        pyplot.text(xy[idx, 0], xy[idx, 1], str(idx+1))
    pyplot.scatter(xy[:, 0], xy[:, 1], s=dur, c=dur, alpha=0.7)


def quickPlot(data, eye=None, period=(None, None), style='XY', xlim=None, ylim=None, units='pix'):
    """
    Plot gaze trajectory.

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
        data is plotted from the beginning. The second element is the end time
        of the period. I None is given as the second element, the data is
        plotted to the end. The unit of these values are millisecond.
        Default value is (None, None).
    :param str style:
        'XY', 'XYT', or 'TXY' is accepted ('XTY' and 'TXY' gives the same output).
        Default value is 'XY'.
    :param tuple xlim:
        If this value is not None, the value is passed tomatplotlib.pyplot.xlim().
        Default value is None.
    :param tuple ylim:
        If this value is not None, the value is passed to matplotlib.pyplot.ylim().
        Default value is None.
    :param units:
        Specify unit of the gaze position ('pix' or 'deg', case-insensitive).
        Default value is 'pix'.
    """

    if isinstance(data, GazeParser.Core.SaccadeData) or isinstance(data, GazeParser.Core.FixationData):
        if eye is None:
            eye = data.parent._recordedEye

        if units.lower() == 'pix':
            sf = (1.0, 1.0)
        elif units.lower() == 'deg':
            sf = data.parent._pix2deg

        traj = data.getTraj(eye)
        if eye != 'B':  # monocular
            traj = sf*traj
        else:  # binocular
            traj = [sf*traj[0], sf*traj[1]]

        if style == 'XY':
            if eye == 'B':  # binocular
                notNansL = np.where(np.logical_not(np.isnan(traj[0][:,0])))[0]
                if len(notNansL) > 0:
                    s = notNansL[0]
                    e = notNansL[-1]
                    pyplot.plot(traj[0][s:e+1, 0], traj[0][s:e+1, 1], '.-', label='L')
                    pyplot.text(traj[0][s, 0], traj[0][s, 1], 'S', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                    pyplot.text(traj[0][e, 0], traj[0][e, 1], 'E', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                notNansR = np.where(np.logical_not(np.isnan(traj[1][:,0])))[0]
                if len(notNansR) > 0:
                    s = notNansR[0]
                    e = notNansR[-1]
                    pyplot.plot(traj[1][s:e+1, 0], traj[1][s:e+1, 1], '.-', label='R')
                    pyplot.text(traj[1][s, 0], traj[1][s, 1], 'S', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                    pyplot.text(traj[1][e, 0], traj[1][e, 1], 'E', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.legend()
            else:  # monocular
                notNans = np.where(np.logical_not(np.isnan(traj[:,0])))[0]
                if len(notNans)>0:
                    s = notNans[0]
                    e = notNans[-1]
                    pyplot.plot(traj[s:e+1, 0], traj[s:e+1, 1], '.-')
                    pyplot.text(traj[s, 0], traj[s, 1], 'S', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                    pyplot.text(traj[e, 0], traj[e, 1], 'E', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
        elif style in ('XYT', 'TXY'):
            si = data.startIndex
            ei = data.endIndex+1
            t = data.parent._T
            if eye != 'B':  # monocular
                pyplot.plot(t[si:ei], traj[:, 0], '.-', label='X')
                pyplot.plot(t[si:ei], traj[:, 1], '.-', label='Y')
                pyplot.legend()
            else:  # binocular
                pyplot.plot(t[si:ei], traj[0][:, 0], '.-', label='LX')
                pyplot.plot(t[si:ei], traj[0][:, 1], '.-', label='LY')
                pyplot.plot(t[si:ei], traj[1][:, 0], '.-', label='RX')
                pyplot.plot(t[si:ei], traj[1][:, 1], '.-', label='RY')
                pyplot.legend()
        else:
            raise ValueError('style must be XY, XYT, or TXY.')

    elif isinstance(data, GazeParser.Core.GazeData):
        if eye is None:
            eye = data._recordedEye

        if eye not in ('L','R','B'):
            raise ValueError('eye must be \'L\', \'R\', or \'B\'.')

        if period[0] is None:
            si = 0
        else:
            si = np.where(data._T >= period[0])[0][0]
        if period[0] is None:
            ei = -1
        else:
            ei = np.where(data._T <= period[1])[0][-1]

        if units.lower() == 'pix':
            sf = (1.0, 1.0)
        elif units.lower() == 'deg':
            sf = data._pix2deg

        if style == 'XY':
            if eye == 'B':
                traj = (sf*data._L[si:ei, :], sf*data._R[si:ei, :])
                notNansL = np.where(np.logical_not(np.isnan(traj[0][:,0])))[0]
                if len(notNansL) > 0:
                    s = notNansL[0]
                    e = notNansL[-1]
                    pyplot.plot(traj[0][s:e+1, 0], traj[0][s:e+1, 1], '.-', label='L')
                    pyplot.text(traj[0][s, 0], traj[0][s, 1], 'S', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                    pyplot.text(traj[0][e, 0], traj[0][e, 1], 'E', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                notNansR = np.where(np.logical_not(np.isnan(traj[1][:,0])))[0]
                if len(notNansR) > 0:
                    s = notNansR[0]
                    e = notNansR[-1]
                    pyplot.plot(traj[1][s:e+1, 0], traj[1][s:e+1, 1], '.-', label='R')
                    pyplot.text(traj[1][s, 0], traj[1][s, 1], 'S', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                    pyplot.text(traj[1][e, 0], traj[1][e, 1], 'E', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                pyplot.legend()
            else:
                if eye == 'L':
                    traj = sf*data._L[si:ei, :]
                else: #R
                    traj = sf*data._R[si:ei, :]

                notNans = np.where(np.logical_not(np.isnan(traj[:,0])))[0]
                if len(notNans)>0:
                    s = notNans[0]
                    e = notNans[-1]
                    pyplot.plot(traj[s:e+1, 0], traj[s:e+1, 1], '.-')
                    pyplot.text(traj[s, 0], traj[s, 1], 'S', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))
                    pyplot.text(traj[e, 0], traj[e, 1], 'E', ha='center', va='center', bbox=dict(boxstyle="round", fc="0.8"))

        elif style in ('XYT', 'TXY'):
            if eye == 'L':
                L = sf*data._L
                pyplot.plot(data._T[si:ei], L[si:ei, 0], '.-', label='X')
                pyplot.plot(data._T[si:ei], L[si:ei, 1], '.-', label='Y')
                pyplot.legend()
            elif eye == 'R':
                R = sf*data._R
                pyplot.plot(data._T[si:ei], R[si:ei, 0], '.-', label='X')
                pyplot.plot(data._T[si:ei], R[si:ei, 1], '.-', label='Y')
                pyplot.legend()
            elif eye == 'B':
                L = sf*data._L
                R = sf*data._R
                pyplot.plot(data._T[si:ei], L[si:ei, 0], '.-', label='LX')
                pyplot.plot(data._T[si:ei], L[si:ei, 1], '.-', label='LY')
                pyplot.plot(data._T[si:ei], R[si:ei, 0], '.-', label='RX')
                pyplot.plot(data._T[si:ei], R[si:ei, 1], '.-', label='RY')
                pyplot.legend()
            else:
                raise ValueError('eye must be \'L\', \'R\', or \'B\'.')
        else:
            raise ValueError('style must be XY, XYT, or TXY.')

    if xlim is not None:
        pyplot.xlim(xlim)
    if ylim is not None:
        pyplot.ylim(ylim)
