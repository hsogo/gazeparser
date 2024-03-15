"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2023 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import GazeParser
import GazeParser.Configuration
import os
import re
import sys
import codecs
import warnings
from datetime import datetime
from scipy.interpolate import interp1d
try:
    from numpy import nanmean
except:
    from scipy.stats import nanmean
from scipy.signal import butter, lfilter, lfilter_zi, filtfilt

try:
    import h5py
    has_h5py = True
except:
    has_h5py = False

try:
    import pathlib
    has_pathlib = True
except:
    has_pathlib = False

def parseBlinkCandidates(T, HVs, config):
    index = 0
    blinkCandIndex = []
    blinkCandDur = []
    isBlink = False
    blinkStart = None

    nanList = np.apply_along_axis(np.all, 1, np.isnan(HVs))
    lenNanList = len(nanList)

    while index < lenNanList-1:
        if isBlink:
            if not nanList[index]:
                dur = T[index]-T[blinkStart]
                blinkCandIndex.append([blinkStart, index])
                blinkCandDur.append(dur)
                isBlink = False
        else:
            if nanList[index]:
                isBlink = True
                blinkStart = index

        index += 1

    # check last blink
    if isBlink:
        dur = T[index]-T[blinkStart]
        blinkCandIndex.append([blinkStart, index])
        blinkCandDur.append(dur)

    return np.array(blinkCandIndex, dtype=np.int32), np.array(blinkCandDur)


def parseSaccadeCandidatesWithVACriteria(T, HV, config):
    cm2deg = 180/np.pi*np.arctan(1.0/config.VIEWING_DISTANCE)
    deg2pix = np.array([config.DOTS_PER_CENTIMETER_H, config.DOTS_PER_CENTIMETER_V])/cm2deg
    pix2deg = 1.0/deg2pix

    Tdiff = np.diff(T).reshape(-1, 1)
    HVdeg = np.zeros(HV.shape)
    HVdeg[:, 0] = HV[:, 0] * pix2deg[0]
    HVdeg[:, 1] = HV[:, 1] * pix2deg[1]

    velocity = np.diff(HVdeg, axis=0) / Tdiff * 1000   # millisecond to second
    acceleration = np.diff(velocity, axis=0) / Tdiff[:-1] * 1000
    absVelocity = np.apply_along_axis(np.linalg.norm, 1, velocity)
    absAcceleration = np.apply_along_axis(np.linalg.norm, 1, acceleration)

    index = 0
    isSaccade = False
    SacCandIndex = []
    SacCandDur = []
    saccadeStart = None
    while index < len(absAcceleration):
        if isSaccade:
            if np.isnan(absVelocity[index]) or absVelocity[index] <= config.SACCADE_VELOCITY_THRESHOLD:
                dur = T[index]-T[saccadeStart]
                # saccadeCandidates.append([saccadeStart, index, dur, absAcceleration[saccadeStart-1], absAcceleration[index-1]])
                SacCandIndex.append([saccadeStart, index])
                SacCandDur.append(dur)
                isSaccade = False
        else:
            if absVelocity[index] > config.SACCADE_VELOCITY_THRESHOLD and absAcceleration[index-1] > config.SACCADE_ACCELERATION_THRESHOLD:
                isSaccade = True
                saccadeStart = index

        index += 1

    # check last saccade
    if isSaccade:
        dur = T[index]-T[saccadeStart]
        # saccadeCandidates.append([saccadeStart, index-1, dur, absAcceleration[saccadeStart-1], absAcceleration[index-1]])
        SacCandIndex.append([saccadeStart, index-1])
        SacCandDur.append(dur)

    return np.array(SacCandIndex, dtype=np.int32), np.array(SacCandDur)


def buildEventListBinocular(T, LHV, RHV, config):
    cm2deg = 180/np.pi*np.arctan(1.0/config.VIEWING_DISTANCE)
    deg2pix = np.array([config.DOTS_PER_CENTIMETER_H, config.DOTS_PER_CENTIMETER_V])/cm2deg
    pix2deg = 1.0/deg2pix

    sacCandL, sacCandDurL = parseSaccadeCandidatesWithVACriteria(T, LHV, config)
    sacCandR, sacCandDurR = parseSaccadeCandidatesWithVACriteria(T, RHV, config)
    blinkCand, blinkCandDur = parseBlinkCandidates(T, np.hstack((LHV, RHV)), config)

    # delete small saccade first, then check fixation
    # check saccade duration
    if len(sacCandL) > 0:
        idx = np.where(sacCandDurL > config.SACCADE_MINIMUM_DURATION)[0]
        if len(idx) > 0:
            sacCandL = sacCandL[idx, :]
            sacCandDurL = sacCandDurL[idx]
        else:
            sacCandL = []
            sacCandDurL = []
    if len(sacCandR) > 0:
        idx = np.where(sacCandDurR > config.SACCADE_MINIMUM_DURATION)[0]
        if len(idx) > 0:
            sacCandR = sacCandR[idx, :]
            sacCandDurR = sacCandDurR[idx]
        else:
            sacCandR = []
            sacCandDurR = []

    sacCand = []
    sacCandDur = []
    # check binocular coincidence
    if len(sacCandL)>0 and len(sacCandR)>0:
        for idx in range(len(sacCandL)):
            overlap = np.where((sacCandR[:, 1] >= sacCandL[idx, 0]) &
                                (sacCandR[:, 0] <= sacCandL[idx, 1]))[0]
            if len(overlap) > 0:
                startIndex = min(sacCandL[idx, 0], sacCandR[overlap[0], 0])
                endIndex = max(sacCandL[idx, 1], sacCandR[overlap[-1], 1])
                if len(sacCand) > 0 and sacCand[-1][1] > startIndex:
                    pass
                else:
                    sacCand.append([startIndex, endIndex])
                    sacCandDur.append(T[endIndex]-T[startIndex])
        sacCand = np.array(sacCand, dtype=np.int32)
        sacCandDur = np.array(sacCandDur)

    if len(sacCand) > 0:
        # amplitude
        amplitudeCheckList = []
        for idx in range(len(sacCand)):
            ampL = np.linalg.norm((LHV[sacCand[idx, 1], :]-LHV[sacCand[idx, 0], :])*pix2deg)
            ampR = np.linalg.norm((RHV[sacCand[idx, 1], :]-RHV[sacCand[idx, 0], :])*pix2deg)
            if (ampL+ampR)/2.0 >= config.SACCADE_MINIMUM_AMPLITUDE:
                amplitudeCheckList.append(idx)
        sacCand = sacCand[amplitudeCheckList, :]
        sacCandDur = sacCandDur[amplitudeCheckList]

    # find fixations
    if len(sacCand) > 0:
        # at first, check whether data starts with fixation or saccade.
        if sacCand[0, 0] > 0:
            dur = T[sacCand[0, 0]]-T[0]
            fixCand = [[0, sacCand[0, 0]]]
            fixCandDur = [dur]
        else:
            fixCand = []
            fixCandDur = []

        #
        for idx in range(sacCand.shape[0]-1):
            dur = T[sacCand[idx+1, 0]]-T[sacCand[idx, 1]]
            fixCand.append([sacCand[idx, 1], sacCand[idx+1, 0]])
            fixCandDur.append(dur)

        # check last fixation
        if sacCand[-1, 1] != len(T)-1:
            dur = T[-1] - T[sacCand[-1, 1]]
            fixCand.append([sacCand[-1, 1], len(T)-1])
            fixCandDur.append(dur)
        fixCand = np.array(fixCand)
        fixCandDur = np.array(fixCandDur)

        # merge small inter-saccadic fixation to saccade.
        tooShortFixation = np.where(fixCandDur <= config.FIXATION_MINIMUM_DURATION)[0]
        for idx in tooShortFixation:
            prevSaccadeIndex = np.where(sacCand[:, 1] == fixCand[idx, 0])[0]
            if len(prevSaccadeIndex) != 1:
                continue
            nextSaccadeIndex = prevSaccadeIndex+1
            if nextSaccadeIndex >= sacCand.shape[0]:  # there is no following saccade.
                continue
            sacCand[prevSaccadeIndex, 1] = sacCand[nextSaccadeIndex, 1]
            sacCandDur[prevSaccadeIndex] = T[sacCand[nextSaccadeIndex, 1]]-T[sacCand[prevSaccadeIndex, 0]]
            sacCand = np.delete(sacCand, nextSaccadeIndex, 0)
            sacCandDur = np.delete(sacCandDur, nextSaccadeIndex, 0)

        idx = fixCandDur > config.FIXATION_MINIMUM_DURATION
        fixCand = fixCand[idx, :]
        fixCandDur = fixCandDur[idx]

    else:  # no saccade candidate is found.
        fixCand = np.array([[0, len(T)-1]])
        fixCandDur = np.array([T[-1]-T[0]])

    # find blinks
    if len(blinkCandDur) > 0:
        idx = blinkCandDur > config.BLINK_MINIMUM_DURATION
        blinkCand = blinkCand[idx, :]
        blinkCandDur = blinkCandDur[idx]

    # bulild lists
    saccadeList = []
    fixationList = []
    blinkList = []

    for i, s in enumerate(sacCand):
        sx = (LHV[s[0], 0]+RHV[s[0], 0])/2.0
        sy = (LHV[s[0], 1]+RHV[s[0], 1])/2.0
        ex = (LHV[s[1], 0]+RHV[s[1], 0])/2.0
        ey = (LHV[s[1], 1]+RHV[s[1], 1])/2.0
        dur = sacCandDur[i]
        amp = np.linalg.norm((pix2deg[0]*(ex-sx), pix2deg[1]*(ey-sy)))
        saccadeList.append(GazeParser.SaccadeData((T[s[0]], T[s[1]]), (dur, sx, sy, ex, ey, amp), T))

    if not (np.isnan(LHV[:, 0]).all() and np.isnan(RHV[:, 0]).all()):  # Fixation is not appended if all values are none.
        for i, f in enumerate(fixCand):
            cx = nanmean(np.hstack((LHV[f[0]:f[1]+1, 0], RHV[f[0]:f[1]+1, 0])))
            cy = nanmean(np.hstack((LHV[f[0]:f[1]+1, 1], RHV[f[0]:f[1]+1, 1])))
            dur = fixCandDur[i]
            fixationList.append(GazeParser.FixationData((T[f[0]], T[f[1]]), (dur, cx, cy), T))

    for i, b in enumerate(blinkCand):
        blinkList.append(GazeParser.BlinkData((T[b[0]], T[b[1]]), blinkCandDur[i], T))

    return (saccadeList, fixationList, blinkList)


def buildEventListMonocular(T, HV, config):
    cm2deg = 180/np.pi*np.arctan(1.0/config.VIEWING_DISTANCE)
    deg2pix = np.array([config.DOTS_PER_CENTIMETER_H, config.DOTS_PER_CENTIMETER_V])/cm2deg
    pix2deg = 1.0/deg2pix

    sacCand, sacCandDur = parseSaccadeCandidatesWithVACriteria(T, HV, config)
    blinkCand, blinkCandDur = parseBlinkCandidates(T, HV, config)

    # delete small saccade first, then check fixation
    if len(sacCand) > 0:
        # check saccade duration
        idx = np.where(sacCandDur > config.SACCADE_MINIMUM_DURATION)[0]
        sacCand = sacCand[idx, :]
        sacCandDur = sacCandDur[idx]

        # check saccade amplitude
        amplitudeCheckList = []
        for idx in range(len(sacCand)):
            if np.linalg.norm((HV[sacCand[idx, 1], :]-HV[sacCand[idx, 0], :])*pix2deg) >= config.SACCADE_MINIMUM_AMPLITUDE:
                amplitudeCheckList.append(idx)
        if len(amplitudeCheckList) > 0:
            sacCand = sacCand[amplitudeCheckList, :]
            sacCandDur = sacCandDur[amplitudeCheckList]
        else:
            sacCand = []
            sacCandDur = []

    # find fixations
    if len(sacCand) > 0:
        # check whether data starts with fixation or saccade.
        if sacCand[0, 0] > 0:
            dur = T[sacCand[0, 0]]-T[0]
            fixCand = [[0, sacCand[0, 0]]]
            fixCandDur = [dur]
        else:
            fixCand = []
            fixCandDur = []

        #
        for idx in range(sacCand.shape[0]-1):
            dur = T[sacCand[idx+1, 0]]-T[sacCand[idx, 1]]
            fixCand.append([sacCand[idx, 1], sacCand[idx+1, 0]])
            fixCandDur.append(dur)

        # check last fixation
        if sacCand[-1, 1] != len(T)-1:
            dur = T[-1] - T[sacCand[-1, 1]]
            fixCand.append([sacCand[-1, 1], len(T)-1])
            fixCandDur.append(dur)
        fixCand = np.array(fixCand, dtype=np.int32)
        fixCandDur = np.array(fixCandDur)


        # merge small inter-saccadic fixation to saccade.
        tooShortFixation = np.where(fixCandDur <= config.FIXATION_MINIMUM_DURATION)[0]
        for idx in tooShortFixation:
            prevSaccadeIndex = np.where(sacCand[:, 1] == fixCand[idx, 0])[0]
            if len(prevSaccadeIndex) != 1:
                continue
            nextSaccadeIndex = prevSaccadeIndex+1
            if nextSaccadeIndex >= sacCand.shape[0]:  # there is no following saccade.
                continue
            sacCand[prevSaccadeIndex, 1] = sacCand[nextSaccadeIndex, 1]
            # saccadeCandidates[prevSaccadeIndex, 4] = saccadeCandidates[nextSaccadeIndex, 4]
            sacCandDur[prevSaccadeIndex,] = T[sacCand[nextSaccadeIndex, 1]]-T[sacCand[prevSaccadeIndex, 0]]
            sacCand = np.delete(sacCand, nextSaccadeIndex, 0)
            sacCandDur = np.delete(sacCandDur, nextSaccadeIndex, 0)

        idx = fixCandDur > config.FIXATION_MINIMUM_DURATION
        fixCand = fixCand[idx, :]
        fixCandDur = fixCandDur[idx]

    else:  # no saccade candidate is found.
        fixCand = np.array([[0, len(T)-1]])
        fixCandDur = np.array([T[-1]-T[0]])

    # find blinks
    if len(blinkCandDur) > 0:
        idx = blinkCandDur > config.BLINK_MINIMUM_DURATION
        blinkCand = blinkCand[idx, :]
        blinkCandDur = blinkCandDur[idx]

    # bulild lists
    saccadeList = []
    fixationList = []
    blinkList = []

    for i, s in enumerate(sacCand):
        sx = HV[s[0], 0]
        sy = HV[s[0], 1]
        ex = HV[s[1], 0]
        ey = HV[s[1], 1]
        dur = sacCandDur[i]
        amp = np.linalg.norm((pix2deg[0]*(ex-sx), pix2deg[1]*(ey-sy)))
        saccadeList.append(GazeParser.SaccadeData((T[s[0]], T[s[1]]), (dur, sx, sy, ex, ey, amp), T))

    if not np.isnan(HV[:, 0]).all():  # Fixation is not appended if all values are none.
        for i, f in enumerate(fixCand):
            cx = nanmean(HV[f[0]:f[1]+1, 0])
            cy = nanmean(HV[f[0]:f[1]+1, 1])
            dur = fixCandDur[i]
            fixationList.append(GazeParser.FixationData((T[f[0]], T[f[1]]), (dur, cx, cy), T))

    for i, b in enumerate(blinkCand):
        blinkList.append(GazeParser.BlinkData((T[b[0]], T[b[1]]), blinkCandDur[i], T))

    return (saccadeList, fixationList, blinkList)


def buildMsgList(M):
    msglist = []
    for i in range(len(M)):
        msglist.append(GazeParser.MessageData(M[i]))

    return msglist


def resampleData(T, HV, frequency):
    """
    :param T: Timestamp (N x 1)
    :param HV: Horizontal and vertical gaze position (N x 2)
    :param frequency: sammpling frequency in Hz.
    """
    if frequency <= 0:
        raise ValueError('Frequency must be a positive number.')
    interval = 1000.0/frequency
    ti = np.arange(0, T[-1], interval)
    interpolaterH = interp1d(T, HV[:, 0])
    interpolaterV = interp1d(T, HV[:, 1])
    hi = interpolaterH(ti)
    vi = interpolaterV(ti)

    return [ti, np.vstack((hi, vi)).transpose()]


def resampleTimeStamp(t, threshold=None):
    """
    :param t: Timestamp (N x 1)
    :param threshold:

    .. note::

        This function is obsolete.
    """
    tdiff = np.diff(t)
    average = np.mean(tdiff)
    if threshold is None:
        threshold = average * 0.1  # 25%
    for i in range(len(tdiff)-1):
        d1 = tdiff[i]-average
        d2 = tdiff[i+1]-average
        if d1*d2 < 0 and np.abs(d1) > threshold and np.abs(d2) > threshold:
            t[i+1] -= tdiff[i]-average
            tdiff[i] = t[i+1]-t[i]
            tdiff[i+1] = t[i+2]-t[i+1]

    return t


def linearInterpolation(t, w):
    """
    Fill missing data by linear interpolation.

    :param t: Timestamp (N x 1)
    :param w: Data to be interpolated (N x 1)
    :return: Filled data.
    """
    # w[0] and w[-1] must not be np.nan.
    if np.isnan(w[0]):
        i = 0
        while(np.isnan(w[i])):
            i += 1
            if i >= len(w):  # all values are None.
                return w
        w[0] = w[i]
    if np.isnan(w[-1]):
        i = len(w)-1
        while(np.isnan(w[i])):
            i -= 1
        w[-1] = w[i]

    # nanIndex = np.where(np.isnan(w))[0]
    validIndex = np.where(w == w)[0]  # np.where(np.isnan(w) == False)[0]

    interpolater = interp1d(t[validIndex], w[validIndex])
    return interpolater(t)


def applyFilter(T, HV, config, decimals=2):
    """
    Apply filter to gaze data. Filter type is specified by
    GazeParser.Configuration.Config object.

    :param T: Timestamp (N x 1)
    :param HV: Horizontal and vertical gaze position (N x 2)
    :param config: GazeParser.Configuration.Cofig object.
    :decimals: filtered data are rounded to the given number of
        this parameter. Default value is 2.
    :return: filtered data.
    """
    if config.FILTER_TYPE == 'identity':
        return HV
    elif config.FILTER_TYPE not in ('butter', 'butter_filtfilt', 'ma'):
        raise ValueError('Only butter, butter_filtfilt, ma and None are supported as Filter.')

    filter = config.FILTER_TYPE
    filterSize = config.FILTER_SIZE
    filterOrder = config.FILTER_ORDER
    filterWn = config.FILTER_WN

    nanListH = np.isnan(HV[:, 0])
    nanListV = np.isnan(HV[:, 1])
    H = linearInterpolation(T, HV[:, 0])
    V = linearInterpolation(T, HV[:, 1])

    # fill NaN with mean value of each edge
    if filter == 'butter' or filter == 'butter_filtfilt':
        (B, A) = butter(filterOrder, filterWn, btype='low', output='ba')
        zi = lfilter_zi(B, A)

        if filter == 'butter':
            (filteredH, zf) = lfilter(B, A, H, zi=zi*H[0])
            (filteredV, zf) = lfilter(B, A, V, zi=zi*V[0])

        else:  # butter_filtfilt
            filteredH = filtfilt(B, A, H)
            filteredV = filtfilt(B, A, V)

    elif filter == 'ma':
        weight = np.ones(filterSize)/filterSize
        filteredH = np.convolve(H, weight, 'same')
        filteredV = np.convolve(V, weight, 'same')

    filteredH = np.round(filteredH, decimals=decimals)
    filteredV = np.round(filteredV, decimals=decimals)

    filteredH[nanListH] = np.nan
    filteredV[nanListV] = np.nan

    return np.vstack((filteredH, filteredV)).transpose()


def TrackerToGazeParser(inputfile, overwrite=False, config=None, useFileParameters=True, outputfile=None, verbose=False):
    """
    Convert an SimpleGazeTracker data file to a GazeParser file.
    If GazeTracker data file name is 'foo.csv', the output file name is 'foo.db'

    :param str inputfile:
        Name of SimpleGazeTracker CSV file to be converted.
    :param Boolean overwrite:
        If this parameter is true, output file is overwritten.
        The default value is False.
    :param GazeParser.Configuration, str config:
        An instance of GazeParser.Configuration that Specifies
        conversion configurations.  If value is a string, it is
        interpreted as a filename of GazeParser.configuration file.
        If value is none, default configuration is used.
        The default value is None.
    :param Boolean useFileParameters:
        If this parameter is true, conversion configurations are
        overwritten by parameters defined in the data file.
        The default value is True.
    :param str outputfile:
        Name of output file. If None, extension of input file name
        is replaced with '.db'.
    """
    (workDir, srcFilename) = os.path.split(os.path.abspath(inputfile))
    filenameRoot, ext = os.path.splitext(srcFilename)
    inputfileFullpath = os.path.join(workDir, srcFilename)
    additionalDataFileName = os.path.join(workDir, filenameRoot+'.txt')
    if outputfile is None:
        dstFileName = os.path.join(workDir, filenameRoot+'.db')
    else:
        dstFileName = os.path.join(workDir, outputfile)
    usbioFormat = None

    if verbose:
        print('------------------------------------------------------------')
        print('TrackerToGazeParser start.')
        print('source file: %s' % inputfile)
    if os.path.exists(dstFileName) and (not overwrite):
        if verbose:
            print('Target file (%s) already exist.' % dstFileName)
        return 'TARGET_FILE_ALREADY_EXISTS'

    if not isinstance(config, GazeParser.Configuration.Config):
        if isinstance(config, str):
            if verbose:
                print('Load configuration file: %s' % config)
            config = GazeParser.Configuration.Config(ConfigFile=config)
        elif has_pathlib and isinstance(config, pathlib.Path):
            if verbose:
                print('Load configuration file: %s' % str(config))
            config = GazeParser.Configuration.Config(ConfigFile=str(config))
        elif config is None:
            if verbose:
                print('Use default configuration.')
            config = GazeParser.Configuration.Config()
        else:
            raise ValueError('config must be GazeParser.Configuration.Config, str, unicode or None.')

    # default indices
    idxT = 0
    if config.RECORDED_EYE == 'B':
        idxLX = 1
        idxLY = 2
        idxRX = 3
        idxRY = 4
        idxLP = None
        idxRP = None
        idxC = None
        idxUSBIO = None
    else:
        idxX = 1
        idxY = 2
        idxP = None
        idxC = None
        idxUSBIO = None

    fid = codecs.open(inputfileFullpath, 'r', 'utf-8')

    Data = []

    T = []
    M = []
    B = []
    LHV = []
    RHV = []
    LP = []
    RP = []
    HV = []
    P = []
    C = []
    USBIO = []
    CALPOINT = []

    flgInBlock = False
    isCheckedEffectiveDigit = False
    effectiveDigit = 2
    if verbose:
        print('parsing...')
    
    line = fid.readline()
    if line.rstrip() != '#SimpleGazeTrackerDataFile':
        fid.close()
        if verbose:
            print('Not a SimpleGazeTracker data file.')
        return 'NOT_SIMPLEGAZETRACKER_FILE'

    for line in fid:
        itemList = line[:-1].rstrip().split(',')
        if itemList[0][0] == '#':  # Messages
            if itemList[0] == '#START_REC':
                startRec = list(map(int, itemList[1:]))
                flgInBlock = True

            elif itemList[0] == '#STOP_REC':
                if config.RECORDED_EYE == 'B':
                    if config.RESAMPLING > 0:
                        tmpT, tmpLHV = resampleData(np.array(T), np.array(LHV), config.RESAMPLING)
                        tmpT, tmpRHV = resampleData(np.array(T), np.array(LHV), config.RESAMPLING)

                        Llist = applyFilter(tmpT, tmpLHV, config, decimals=effectiveDigit)
                        Rlist = applyFilter(tmpT, tmpRHV, config, decimals=effectiveDigit)
                    else:
                        Tlist = np.array(T)
                        Llist = applyFilter(Tlist, np.array(LHV), config, decimals=effectiveDigit)
                        Rlist = applyFilter(Tlist, np.array(RHV), config, decimals=effectiveDigit)

                    if config.AVERAGE_LR == 0:
                        (SacList, FixList, BlinkList) = buildEventListBinocular(Tlist, Llist, Rlist, config)
                    elif config.AVERAGE_LR == 1:
                        Blist = np.nanmean([Llist,Rlist], axis=0)
                        (SacList, FixList, BlinkList) = buildEventListMonocular(Tlist, Blist, config)
                    else:
                        raise ValueError('AVERAGE_LR must be 0 or 1.')

                    if not (idxLP is None and idxRP is None):
                        Plist = np.array([LP, RP]).transpose()
                    else:
                        Plist = None
                else:  # monocular
                    if config.RECORDED_EYE == 'L':
                        if config.RESAMPLING > 0:
                            Tlist, tmpHV = resampleData(np.array(T), np.array(HV), config.RESAMPLING)
                            Llist = applyFilter(Tlist, tmpHV, config, decimals=effectiveDigit)
                        else:
                            Tlist = np.array(T)
                            Llist = applyFilter(Tlist, np.array(HV), config, decimals=effectiveDigit)
                        (SacList, FixList, BlinkList) = buildEventListMonocular(Tlist, Llist, config)
                        Rlist = None
                    elif config.RECORDED_EYE == 'R':
                        if config.RESAMPLING > 0:
                            Tlist, tmpHV = resampleData(np.array(T), np.array(HV), config.RESAMPLING)
                            Rlist = applyFilter(Tlist, tmpHV, config, decimals=effectiveDigit)
                        else:
                            Tlist = np.array(T)
                            Rlist = applyFilter(Tlist, np.array(HV), config, decimals=effectiveDigit)
                        (SacList, FixList, BlinkList) = buildEventListMonocular(Tlist, Rlist, config)
                        Llist = None
                    if idxP is not None:
                        Plist = np.array(P).transpose()
                    else:
                        Plist = None

                MsgList = buildMsgList(M)
                G = GazeParser.GazeData(Tlist, Llist, Rlist, SacList, FixList, MsgList, BlinkList, Plist, config.RECORDED_EYE, config=config, recordingDate=startRec)
                if idxC is not None:
                    G.setCameraSpecificData(np.array(C))
                if idxUSBIO is not None:
                    G.setUSBIOData(usbioFormat, np.array(USBIO))
                if len(CALPOINT)>0:
                    G.setCalPointData(CALPOINT)
                Data.append(G)

                # prepare for new block
                flgInBlock = False
                T = []
                M = []
                B = []
                LHV = []
                RHV = []
                LP = []
                RP = []
                HV = []
                P = []
                C = []
                USBIO = []
                CALPOINT = []

            elif itemList[0] == '#MESSAGE':
                try:
                    M.append([float(itemList[1]), ' '.join(itemList[2:])])
                except:
                    pass
            
            elif itemList[0] == '#CALPOINT':
                for idx in range(len(itemList)):
                    if idx==0:
                        continue
                    try:
                        itemList[idx] = float(itemList[idx])
                    except:
                        itemList[idx] = np.NaN
                if config.RECORDED_EYE == 'L':
                    accuracy = itemList[3:5]
                    precision = itemList[5:7]
                    accuracy.extend([np.NaN,np.NaN])
                    precision.extend([np.NaN,np.NaN])
                elif config.RECORDED_EYE == 'R':
                    accuracy = [np.NaN,np.NaN]
                    precision = [np.NaN,np.NaN]
                    accuracy.extend(itemList[3:5])
                    precision.extend(itemList[5:7])
                else:
                    accuracy = itemList[3:7]
                    precision = itemList[7:11]
                CALPOINT.append(GazeParser.CalPointData(itemList[1:3],accuracy,precision,config.RECORDED_EYE))
                
            elif itemList[0] == '#CALDATA':
                pass
            
            if not flgInBlock:
                # #DATAFORMAT must be loaded regardless of useFileParameters
                if itemList[0] == '#DATAFORMAT':
                    idxT = idxX = idxY = idxP = idxC = idxUSBIO = None
                    idxLX = idxLY = idxRX = idxRY = idxLP = idxRP = None
                    tmp = []
                    if verbose:
                        print(itemList)
                    for i in range(len(itemList)-1):
                        if itemList[i+1].find('USBIO;') == 0:  # support USBIO
                            idxUSBIO = i
                            cmd = 'USBIO={}'.format(i)
                            usbioFormat = itemList[i+1][6:].split(';')
                            if len(usbioFormat[-1]) == 0:  # remove last item if empty
                                usbioFormat.pop(-1)
                        else:
                            if itemList[i+1] == 'T':
                                idxT = i
                            elif itemList[i+1] == 'X':
                                idxX = i
                            elif itemList[i+1] == 'Y':
                                idxY = i
                            elif itemList[i+1] == 'P':
                                idxP = i
                            elif itemList[i+1] == 'C':
                                idxC = i
                            elif itemList[i+1] == 'LX':
                                idxLX = i
                            elif itemList[i+1] == 'LY':
                                idxLY = i
                            elif itemList[i+1] == 'RX':
                                idxRX = i
                            elif itemList[i+1] == 'RY':
                                idxRY = i
                            elif itemList[i+1] == 'LP':
                                idxLP = i
                            elif itemList[i+1] == 'RP':
                                idxRP = i
                            cmd = '{}={}'.format(itemList[i+1],i)
                        tmp.append(cmd)
                    if verbose:
                        print('DATAFORMAT: %s' % (','.join(tmp)))

                # Nothing to do against these options
                elif itemList[0] in ['#STOP_REC', '#TRACKER_VERSION']:
                    pass

                # load GazeParser options if useFileParameters is True
                elif useFileParameters:
                    optName = itemList[0][1:]
                    if optName in GazeParser.Configuration.GazeParserDefaults:
                        if isinstance(GazeParser.Configuration.GazeParserDefaults[optName], float):
                            setattr(config, optName, float(itemList[1]))
                            if verbose:
                                print('%s = %f' % (optName, getattr(config, optName)))
                        elif isinstance(GazeParser.Configuration.GazeParserDefaults[optName], int):
                            setattr(config, optName, int(itemList[1]))
                            if verbose:
                                print('%s = %d' % (optName, getattr(config, optName)))
                        else:  # str
                            setattr(config, optName, itemList[1])

                            if verbose:
                                print('%s = %s' % (optName, getattr(config, optName)))
                    else:
                        if verbose:
                            print('Warning: unknown option ({})'.format(optName))

                # output unprocessed parameters if verbose==True
                else:
                    if verbose:
                        print('Warning: ignored option ({})'.format(optName))
        else:  # gaze data
            if not isCheckedEffectiveDigit:
                if config.RECORDED_EYE == 'B':
                    periodPosition = itemList[idxLX].find('.')
                else:
                    periodPosition = itemList[idxX].find('.')
                if periodPosition == -1:
                    effectiveDigit = 0
                else:
                    effectiveDigit = len(itemList[1])-periodPosition-1
                isCheckedEffectiveDigit = True
            T.append(float(itemList[idxT]))
            if config.RECORDED_EYE == 'B':
                try:
                    xL = float(itemList[idxLX])
                    yL = float(itemList[idxLY])
                    xR = float(itemList[idxRX])
                    yR = float(itemList[idxRY])
                    if not (idxLP is None and idxRP is None):
                        lP = float(itemList[idxLP])
                        rP = float(itemList[idxRP])
                except:
                    if itemList[1] == 'NOPUPIL':  # NOPUPIL may be blink. todo: should other meassages be also treated as a blink?
                        B.append([len(T)-1, T[-1]])
                    xL = np.NaN
                    yL = np.NaN
                    xR = np.NaN
                    yR = np.NaN
                    if not (idxLP is None and idxRP is None):
                        lP = np.NaN
                        rP = np.NaN
                finally:
                    LHV.append([xL, yL])
                    RHV.append([xR, yR])
                    if not (idxLP is None and idxRP is None):
                        LP.append(lP)
                        RP.append(rP)
            else:  # Monocular
                try:
                    x = float(itemList[idxX])
                    y = float(itemList[idxY])
                    if idxP is not None:
                        p = float(itemList[idxP])
                except:
                    if itemList[1] == 'NOPUPIL':  # NOPUPIL may be blink. todo: should other meassages be also treated as a blink?
                        B.append([len(T)-1, T[-1]])
                    x = np.NaN
                    y = np.NaN
                    if idxP is not None:
                        p = np.NaN
                finally:
                    HV.append([x, y])
                    if idxP is not None:
                        P.append(p)
            if idxC is not None:  # datafile has camera-specific data
                try:
                    C.append(int(itemList[idxC]))
                except:
                    C.append(itemList[idxC])
            if idxUSBIO is not None:  # datafile has USBIO data
                try:
                    tmp = itemList[idxUSBIO].split(';')
                    if len(tmp[-1]) == 0:
                        tmp.pop(-1)
                    tmp = list(map(int, tmp))
                    USBIO.append(tmp)
                except:
                    C.append(itemList[idxUSBIO])

    if verbose:
        print('saving...')
    if os.path.exists(additionalDataFileName):
        adfp = codecs.open(additionalDataFileName, 'r', 'utf-8')
        ad = []
        for line in adfp:
            data = line.split('\t')
            for di in range(len(data)):
                try:
                    data[di] = int(data[di])
                except:
                    try:
                        data[di] = float(data[di])
                    except:
                        pass
            ad.append(data)
        GazeParser.save(dstFileName, Data, additionalData=ad)
    else:
        GazeParser.save(dstFileName, Data)

    if verbose:
        print('done.')
    return 'SUCCESS'


def PTCToGazeParser(inputfile, overwrite=False, config=None, outputfile=None, unitcnv=None, verbose=False):
    """
    Convert a PsychoPy-Tobii-Controller TSV file to a GazeParser file.
    If TSV file name is 'foo.tsv', the output file name is 'foo.db'

    :param str inputfile:
        name of PsychoPy-Tobii-Controller TSV file to be converted.
    :param Boolean overwrite:
        If this parameter is true, output file is overwritten.
        The default value is False.
    :param GazeParser.Configuration, str config:
        An instance of GazeParser.Configuration that Specifies
        conversion configurations.  If value is a string, it is
        interpreted as a filename of GazeParser.configuration file.
        If value is none, default configuration is used.
        The default value is None.
    :param str outputfile:
        Name of output file. If None, extension of input file name
        is replaced with '.db'.
    :param str unitcnv:
        Covert unit. Currently, only 'height2pix' is supported.
        Default value is None (no conversion).
    """
    effectiveDigit = 2

    if unitcnv is not None:
        if unitcnv not in ('height2pix',):
            if verbose:
                print('Invalid unit conversion (%s).' % unitcnv)
            return 'INVALID_UNIT_CONVERSION'

    (workDir, srcFilename) = os.path.split(os.path.abspath(inputfile))
    filenameRoot, ext = os.path.splitext(srcFilename)
    inputfileFullpath = os.path.join(workDir, srcFilename)
    additionalDataFileName = os.path.join(workDir, filenameRoot+'.txt')
    if outputfile is None:
        dstFileName = os.path.join(workDir, filenameRoot+'.db')
    else:
        dstFileName = os.path.join(workDir, outputfile)

    if verbose:
        print('TobiiToGazeParser start.')
    if os.path.exists(dstFileName) and (not overwrite):
        if verbose:
            print('Can not open %s.' % dstFileName)
        return 'CANNOT_OPEN_OUTPUT_FILE'

    if not isinstance(config, GazeParser.Configuration.Config):
        if isinstance(config, str):
            if verbose:
                print('Load configuration file: %s' % config)
            config = GazeParser.Configuration.Config(ConfigFile=config)
        elif has_pathlib and isinstance(config, pathlib.Path):
            if verbose:
                print('Load configuration file: %s' % str(config))
            config = GazeParser.Configuration.Config(ConfigFile=str(config))
        elif config is None:
            if verbose:
                print('Use default configuration.')
            config = GazeParser.Configuration.Config()
        else:
            raise ValueError('config must be GazeParser.Configuration.Config, str, unicode or None.')

    fid = codecs.open(inputfileFullpath, "r", 'utf-8')

    Data = []
    field = {}
    EventRecMode = 'Separated'
    RecordingDate = '1970/01/01'
    RecordingTime = '00:00:00'

    flgInBlock = False

    for line in fid:
        itemList = line.rstrip().split('\t')
        if not flgInBlock:
            if itemList[0] == 'Recording resolution:':
                config.SCREEN_WIDTH = int(itemList[1].split('x')[0])
                config.SCREEN_HEIGHT = int(itemList[1].split('x')[1])
                if verbose: 
                    print('SCREEN_WIDTH: %d' % config.SCREEN_WIDTH)
                    print('SCREEN_HEIGHT: %d' % config.SCREEN_HEIGHT)
            elif itemList[0] == 'Recording date:':
                RecordingDate = itemList[1]
            elif itemList[0] == 'Recording time:':
                RecordingTime = itemList[1]
            elif itemList[0] == 'Event recording mode:':
                EventRecMode = itemList[1]

            elif itemList[0] == 'Session Start':
                flgInBlock = True
                T = []
                P = []
                LHV = []
                RHV = []
                M = []

        else:
            if itemList[0] == 'TimeStamp':
                field = {}
                for i in range(len(itemList)):
                    field[itemList[i]] = i

            elif itemList[0] == 'Session End':
                # convert to np.ndarray
                Tlist = np.array(T)
                Plist = np.array(P)
                LHV = np.array(LHV)
                RHV = np.array(RHV)
                if unitcnv == 'height2pix':
                    LHV *= config.SCREEN_HEIGHT
                    RHV *= config.SCREEN_HEIGHT
                Llist = applyFilter(Tlist, LHV, config, decimals=effectiveDigit)
                Rlist = applyFilter(Tlist, RHV, config, decimals=effectiveDigit)

                # build MessageData
                MsgList = []
                for msg in range(len(M)):
                    MsgList.append(GazeParser.MessageData(M[msg]))

                # build GazeData
                recdatestr = list(map(int, RecordingDate.split('/') + RecordingTime.split(':')))
                if config.AVERAGE_LR == 0:
                    (SacList, FixList, BlinkList) = buildEventListBinocular(Tlist, Llist, Rlist, config)
                elif config.AVERAGE_LR == 1:
                    #suppress "RuntimeWarning: Mean of empty slice" when both L and R are NaN
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=RuntimeWarning)
                        Blist = np.nanmean([Llist,Rlist], axis=0)
                    (SacList, FixList, BlinkList) = buildEventListMonocular(Tlist, Blist, config)

                G = GazeParser.GazeData(Tlist, Llist, Rlist, SacList, FixList, MsgList, BlinkList, Plist, 'B', config=config, recordingDate=recdatestr)

                Data.append(G)

                flgInBlock = False

            else:
                if EventRecMode == 'Embedded' or ('Event' not in field):
                    isGazeDataAvailable = False
                    # record gaze position
                    if itemList[field['GazePointXLeft']] != '':
                        isGazeDataAvailable = True
                        if itemList[field['ValidityLeft']] != '4':
                            LHV.append((float(itemList[field['GazePointXLeft']]), float(itemList[field['GazePointYLeft']])))
                        else:  # pupil was not found
                            LHV.append((np.NaN, np.NaN))

                    if itemList[field['GazePointXRight']] != '':
                        isGazeDataAvailable = True
                        if itemList[field['ValidityRight']] != '4':
                            RHV.append((float(itemList[field['GazePointXRight']]), float(itemList[field['GazePointYRight']])))
                        else:  # pupil was not found
                            RHV.append((np.NaN, np.NaN))

                    # record timeStamp if gaze data is available
                    if isGazeDataAvailable:
                        T.append(float(itemList[field['TimeStamp']]))
                        P.append((float(itemList[field['PupilLeft']]), float(itemList[field['PupilRight']])))
                
                elif EventRecMode == 'Embedded' or ('Event' in field):
                    # record event
                    if itemList[field['Event']] != '':
                        M.append((float(itemList[field['TimeStamp']]), itemList[field['Event']]))

    # last fixation ... check exact format of Tobii data later.
    # FIX.append(int(itemList[field['TimeStamp']]))

    if verbose:
        print('saving...')
    if os.path.exists(additionalDataFileName):
        if verbose:
            print('Additional data file is found.')
        adfp = open(additionalDataFileName)
        ad = []
        for line in adfp:
            data = line.split('\t')
            for di in range(len(data)):
                try:
                    data[di] = int(data[di])
                except:
                    try:
                        data[di] = float(data[di])
                    except:
                        pass
            ad.append(data)
        GazeParser.save(dstFileName, Data, additionalData=ad)
    else:
        GazeParser.save(dstFileName, Data)

    if verbose:
        print('done.')
    return 'SUCCESS'


def PPHDF5ToGazeParser(inputfile, overwrite=False, config=None, outputfile=None, 
    startMsg='RecStart .*', stopMsg='RecStop .*', 
    recdate=None, unitcnv=None, verbose=False):
    """
    Convert a PsychoPy HDF5 file to a GazeParser file.

    :param str inputfile:
        name of PsychoPy HDF5 file to be converted.
    :param Boolean overwrite:
        If this parameter is true, output file is overwritten.
        The default value is False.
    :param GazeParser.Configuration, str config:
        An instance of GazeParser.Configuration that Specifies
        conversion configurations.  If value is a string, it is
        interpreted as a filename of GazeParser.configuration file.
        If value is none, default configuration is used.
        The default value is None.
    :param str outputfile:
        Name of output file. If None, extension of input file name
        is replaced with '.db'.
    :param str startMsg:
        Message string for 'start recording'.  Default is 'RecStart .*'
        re.match() is used to match to event texts.
    :param str stopMsg:
        Message string for 'stop recording'.  Default is 'RecStop .*'
        re.match() is used to match to event texts.
    :param str recdate:
        Specify recording date in 'YYYY/mm/dd-HH:MM:SS'.
        If None, timestamp of HDF5 file is used.
    :param str unitcnv:
        Covert unit. Currently, only 'height2pix' is supported.
        Default value is None (no conversion).
    """
    if not has_h5py:
        if verbose:
            print('h5py package is required for PPHDF5ToGazeParser.')
        return 'NO_H5PY'

    effectiveDigit = 2

    if unitcnv is not None:
        if unitcnv not in ('height2pix',):
            if verbose:
                print('Invalid unit conversion (%s).' % unitcnv)
            return 'INVALID_UNIT_CONVERSION'

    (workDir, srcFilename) = os.path.split(os.path.abspath(inputfile))
    filenameRoot, ext = os.path.splitext(srcFilename)
    inputfileFullpath = os.path.join(workDir, srcFilename)
    additionalDataFileName = os.path.join(workDir, filenameRoot+'.txt')
    if outputfile is None:
        dstFileName = os.path.join(workDir, filenameRoot+'.db')
    else:
        dstFileName = os.path.join(workDir, outputfile)

    if verbose:
        print('PsychoPyHDF5ToGazeParser start.')
    if os.path.exists(dstFileName) and (not overwrite):
        if verbose:
            print('Can not open %s.' % dstFileName)
        return 'CANNOT_OPEN_OUTPUT_FILE'

    if not isinstance(config, GazeParser.Configuration.Config):
        if isinstance(config, str):
            if verbose:
                print('Load configuration file: %s' % config)
            config = GazeParser.Configuration.Config(ConfigFile=config)
        elif has_pathlib and isinstance(config, pathlib.Path):
            if verbose:
                print('Load configuration file: %s' % str(config))
            config = GazeParser.Configuration.Config(ConfigFile=str(config))
        elif config is None:
            if verbose:
                print('Use default configuration.')
            config = GazeParser.Configuration.Config()
        else:
            raise ValueError('config must be GazeParser.Configuration.Config, str, unicode or None.')



    Data = []
    field = {}
    EventRecMode = 'Separated'
    RecordingDate = '1970/01/01'
    RecordingTime = '00:00:00'

    if recdate is None:
        file_stat = os.stat(inputfileFullpath)
        ctime = datetime.fromtimestamp(file_stat.st_ctime)
        RecordingDate = ctime.strftime('%Y/%m/%d')
        RecordingTime = ctime.strftime('%H:%M:%S')
    else:
        RecordingDate, RecordingTime = recdate.split('-')

    # PsychoPy coordinate system is 'center'
    config.SCREEN_ORIGIN = 'center'
    config.TRACKER_ORIGIN = 'center'

    # config.RECORDED_EYE = 'B'

    hdf = h5py.File(inputfileFullpath)
    startMatch = re.compile(startMsg)
    stopMatch = re.compile(stopMsg)

    start_time_list = []
    stop_time_list = []
    start_time_msg = []
    stop_time_msg = []

    msgdata = hdf['/data_collection/events/experiment/MessageEvent']
    for i in range(len(msgdata)):
        msg_text = msgdata[i]['text'].decode('UTF-8')
        if startMatch.match(msg_text):
            start_time_list.append(msgdata[i]['time'])
            start_time_msg.append(msgdata[i]['text'])
        elif stopMatch.match(msg_text):
            stop_time_list.append(msgdata[i]['time'])
            stop_time_msg.append(msgdata[i]['text'])
    
    if len(start_time_list) != len(stop_time_list):
        print('Numbers of RecStart and RecStop messages are not equal')
        return 'INVALID_RECSTART_RECSTOP_MESSAGES'
    for i in range(len(start_time_list)):
        if start_time_list[i] >= stop_time_list[i]:
            print('Time of RecStop is earlier than that of RecStart')
            return 'INVALID_RECSTART_RECSTOP_MESSAGES'

    bindata = hdf['/data_collection/events/eyetracker/BinocularEyeSampleEvent']

    left_invalid = bindata['status'] < 20  # left is invalid = 20, both are invalid = 22
    right_invalid = bindata['status'] % 20 != 2  # right is invalid = 2, both are invalid = 22
    bindata[left_invalid]['left_gaze_x'] = np.NaN
    bindata[left_invalid]['left_gaze_y'] = np.NaN
    bindata[right_invalid]['right_gaze_x'] = np.NaN
    bindata[right_invalid]['right_gaze_y'] = np.NaN


    for block in range(len(start_time_list)):
        block_idx = (start_time_list[block] <= bindata['time']) & (bindata['time'] <= stop_time_list[block])

        T = np.array(bindata[block_idx]['time'])
        start_time_sec = T[0]
        Tlist = 1000*(np.array(T)-start_time_sec)

        LHV = np.vstack([bindata[block_idx]['left_gaze_x'], bindata[block_idx]['left_gaze_y']]).T
        RHV = np.vstack([bindata[block_idx]['right_gaze_x'], bindata[block_idx]['right_gaze_y']]).T
        if unitcnv == 'height2pix':
            LHV *= config.SCREEN_HEIGHT
            RHV *= config.SCREEN_HEIGHT
        Llist = applyFilter(Tlist, LHV, config, decimals=effectiveDigit)
        Rlist = applyFilter(Tlist, RHV, config, decimals=effectiveDigit)
        print(bindata[block_idx]['left_gaze_x'].shape, LHV.shape)

        Plist = np.vstack([bindata[block_idx]['left_pupil_measure1'], bindata[block_idx]['right_pupil_measure1']]).T

        msg_idx = (start_time_list[block] <= msgdata['time']) & (msgdata['time'] <= stop_time_list[block])
        msg_time = 1000*(msgdata[msg_idx]['time']-start_time_sec)
        msg_text = msgdata[msg_idx]['text']
        MsgList = []
        for i in range(len(msg_time)):
            MsgList.append(GazeParser.MessageData((msg_time[i], msg_text[i].decode('UTF-8'))))

        # build GazeData
        recdatestr = list(map(int, RecordingDate.split('/') + RecordingTime.split(':')))
        if config.AVERAGE_LR == 0:
            (SacList, FixList, BlinkList) = buildEventListBinocular(Tlist, Llist, Rlist, config)
        elif config.AVERAGE_LR == 1:
            #suppress "RuntimeWarning: Mean of empty slice" when both L and R are NaN
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                Blist = np.nanmean([Llist,Rlist], axis=0)
            (SacList, FixList, BlinkList) = buildEventListMonocular(Tlist, Blist, config)

        G = GazeParser.GazeData(Tlist, Llist, Rlist, SacList, FixList, MsgList, BlinkList, Plist, 'B', config=config, recordingDate=recdatestr)

        Data.append(G)


    if verbose:
        print('saving...')
    if os.path.exists(additionalDataFileName):
        if verbose:
            print('Additional data file is found.')
        adfp = open(additionalDataFileName)
        ad = []
        for line in adfp:
            data = line.split('\t')
            for di in range(len(data)):
                try:
                    data[di] = int(data[di])
                except:
                    try:
                        data[di] = float(data[di])
                    except:
                        pass
            ad.append(data)
        GazeParser.save(dstFileName, Data, additionalData=ad)
    else:
        GazeParser.save(dstFileName, Data)

    if verbose:
        print('done.')
    return 'SUCCESS'
