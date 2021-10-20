"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy
import GazeParser
import GazeParser.Configuration
import os
import re
import sys
import codecs
from scipy.interpolate import interp1d
try:
    from numpy import nanmean
except:
    from scipy.stats import nanmean
from scipy.signal import butter, lfilter, lfilter_zi, filtfilt

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

    nanList = numpy.apply_along_axis(numpy.all, 1, numpy.isnan(HVs))
    lenNanList = len(nanList)

    while index < lenNanList-1:
        if isBlink:
            if not nanList[index]:
                dur = T[index-1]-T[blinkStart]
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

    return numpy.array(blinkCandIndex, dtype=numpy.int), numpy.array(blinkCandDur)


def parseSaccadeCandidatesWithVACriteria(T, HV, config):
    cm2deg = 180/numpy.pi*numpy.arctan(1.0/config.VIEWING_DISTANCE)
    deg2pix = numpy.array([config.DOTS_PER_CENTIMETER_H, config.DOTS_PER_CENTIMETER_V])/cm2deg
    pix2deg = 1.0/deg2pix

    Tdiff = numpy.diff(T).reshape(-1, 1)
    HVdeg = numpy.zeros(HV.shape)
    HVdeg[:, 0] = HV[:, 0] * pix2deg[0]
    HVdeg[:, 1] = HV[:, 1] * pix2deg[1]

    velocity = numpy.diff(HVdeg, axis=0) / Tdiff * 1000   # millisecond to second
    acceleration = numpy.diff(velocity, axis=0) / Tdiff[:-1] * 1000
    absVelocity = numpy.apply_along_axis(numpy.linalg.norm, 1, velocity)
    absAcceleration = numpy.apply_along_axis(numpy.linalg.norm, 1, acceleration)

    index = 0
    isSaccade = False
    SacCandIndex = []
    SacCandDur = []
    saccadeStart = None
    while index < len(absAcceleration):
        if isSaccade:
            if numpy.isnan(absVelocity[index]) or absVelocity[index] <= config.SACCADE_VELOCITY_THRESHOLD:
                dur = T[index-1]-T[saccadeStart]
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

    return numpy.array(SacCandIndex, dtype=numpy.int), numpy.array(SacCandDur)


def buildEventListBinocular(T, LHV, RHV, config):
    cm2deg = 180/numpy.pi*numpy.arctan(1.0/config.VIEWING_DISTANCE)
    deg2pix = numpy.array([config.DOTS_PER_CENTIMETER_H, config.DOTS_PER_CENTIMETER_V])/cm2deg
    pix2deg = 1.0/deg2pix

    sacCandL, sacCandDurL = parseSaccadeCandidatesWithVACriteria(T, LHV, config)
    sacCandR, sacCandDurR = parseSaccadeCandidatesWithVACriteria(T, RHV, config)
    blinkCand, blinkCandDur = parseBlinkCandidates(T, numpy.hstack((LHV, RHV)), config)

    # delete small saccade first, then check fixation
    # check saccade duration
    if len(sacCandL) > 0:
        idx = numpy.where(sacCandDurL > config.SACCADE_MINIMUM_DURATION)[0]
        if len(idx) > 0:
            sacCandL = sacCandL[idx, :]
            sacCandDurL = sacCandDurL[idx]
        else:
            sacCandL = []
            sacCandDurL = []
    if len(sacCandR) > 0:
        idx = numpy.where(sacCandDurR > config.SACCADE_MINIMUM_DURATION)[0]
        if len(idx) > 0:
            sacCandR = sacCandR[idx, :]
            sacCandDurR = sacCandDurR[idx]
        else:
            sacCandR = []
            sacCandDurR = []

    sacCand = []
    sacCandDur = []
    # check binocular coincidence
    for idx in range(len(sacCandL)):
        overlap = numpy.where((sacCandR[:, 1] >= sacCandL[idx, 0]) &
                              (sacCandR[:, 0] <= sacCandL[idx, 1]))[0]
        if len(overlap) > 0:
            startIndex = min(sacCandL[idx, 0], sacCandR[overlap[0], 0])
            endIndex = max(sacCandL[idx, 1], sacCandR[overlap[-1], 1])
            if len(sacCand) > 0 and sacCand[-1][1] > startIndex:
                pass
            else:
                sacCand.append([startIndex, endIndex])
                sacCandDur.append(T[endIndex]-T[startIndex])
    sacCand = numpy.array(sacCand, dtype=numpy.int)
    sacCandDur = numpy.array(sacCandDur)

    # amplitude
    amplitudeCheckList = []
    for idx in range(len(sacCand)):
        ampL = numpy.linalg.norm((LHV[sacCand[idx, 1], :]-LHV[sacCand[idx, 0], :])*pix2deg)
        ampR = numpy.linalg.norm((RHV[sacCand[idx, 1], :]-RHV[sacCand[idx, 0], :])*pix2deg)
        if (ampL+ampR)/2.0 >= config.SACCADE_MINIMUM_AMPLITUDE:
            amplitudeCheckList.append(idx)
    sacCand = sacCand[amplitudeCheckList, :]
    sacCandDur = sacCandDur[amplitudeCheckList]

    # find fixations
    # at first, check whether data starts with fixation or saccade.
    if sacCand[0, 0] > 0:
        dur = T[sacCand[0, 0]-1]-T[0]
        fixCand = [[0, sacCand[0, 0]-1]]
        fixCandDur = [dur]
    else:
        fixCand = []
        fixCandDur = []

    #
    for idx in range(sacCand.shape[0]-1):
        dur = T[sacCand[idx+1, 0]-1]-T[sacCand[idx, 1]-1]
        fixCand.append([sacCand[idx, 1], sacCand[idx+1, 0]])
        fixCandDur.append(dur)

    # check last fixation
    if sacCand[-1, 1] != len(T)-1:
        dur = T[-1] - T[sacCand[-1, 1]]
        fixCand.append([sacCand[-1, 1], len(T)-1])
        fixCandDur.append(dur)
    fixCand = numpy.array(fixCand)
    fixCandDur = numpy.array(fixCandDur)

    # merge small inter-saccadic fixation to saccade.
    tooShortFixation = numpy.where(fixCandDur <= config.FIXATION_MINIMUM_DURATION)[0]
    for idx in tooShortFixation:
        prevSaccadeIndex = numpy.where(sacCand[:, 1] == fixCand[idx, 0])[0]
        if len(prevSaccadeIndex) != 1:
            continue
        nextSaccadeIndex = prevSaccadeIndex+1
        if nextSaccadeIndex >= sacCand.shape[0]:  # there is no following saccade.
            continue
        sacCand[prevSaccadeIndex, 1] = sacCand[nextSaccadeIndex, 1]
        sacCandDur[prevSaccadeIndex] = T[sacCand[nextSaccadeIndex, 1]]-T[sacCand[prevSaccadeIndex, 0]]
        sacCand = numpy.delete(sacCand, nextSaccadeIndex, 0)
        sacCandDur = numpy.delete(sacCandDur, nextSaccadeIndex, 0)

    idx = fixCandDur > config.FIXATION_MINIMUM_DURATION
    fixCand = fixCand[idx, :]
    fixCandDur = fixCandDur[idx]

    # find blinks
    # TODO: check break of fixation and saccades by blink.
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
        amp = numpy.linalg.norm((pix2deg[0]*(ex-sx), pix2deg[1]*(ey-sy)))
        saccadeList.append(GazeParser.SaccadeData((T[s[0]], T[s[1]]), (dur, sx, sy, ex, ey, amp), T))

    if not (numpy.isnan(LHV[:, 0]).all() and numpy.isnan(RHV[:, 0]).all()):  # Fixation is not appended if all values are none.
        for i, f in enumerate(fixCand):
            cx = nanmean(numpy.hstack((LHV[f[0]:f[1]+1, 0], RHV[f[0]:f[1]+1, 0])))
            cy = nanmean(numpy.hstack((LHV[f[0]:f[1]+1, 1], RHV[f[0]:f[1]+1, 1])))
            dur = fixCandDur[i]
            fixationList.append(GazeParser.FixationData((T[f[0]], T[f[1]]), (dur, cx, cy), T))

    for i, b in enumerate(blinkCand):
        blinkList.append(GazeParser.BlinkData((T[b[0]], T[b[1]]), blinkCandDur[i], T))

    return (saccadeList, fixationList, blinkList)


def buildEventListMonocular(T, HV, config):
    cm2deg = 180/numpy.pi*numpy.arctan(1.0/config.VIEWING_DISTANCE)
    deg2pix = numpy.array([config.DOTS_PER_CENTIMETER_H, config.DOTS_PER_CENTIMETER_V])/cm2deg
    pix2deg = 1.0/deg2pix

    sacCand, sacCandDur = parseSaccadeCandidatesWithVACriteria(T, HV, config)
    blinkCand, blinkCandDur = parseBlinkCandidates(T, HV, config)

    # delete small saccade first, then check fixation
    if len(sacCand) > 0:
        # check saccade duration
        idx = numpy.where(sacCandDur > config.SACCADE_MINIMUM_DURATION)[0]
        sacCand = sacCand[idx, :]
        sacCandDur = sacCandDur[idx]

        # check saccade amplitude
        amplitudeCheckList = []
        for idx in range(len(sacCand)):
            if numpy.linalg.norm((HV[sacCand[idx, 1], :]-HV[sacCand[idx, 0], :])*pix2deg) >= config.SACCADE_MINIMUM_AMPLITUDE:
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
            dur = T[sacCand[0, 0]-1]-T[0]
            fixCand = [[0, sacCand[0, 0]-1]]
            fixCandDur = [dur]
        else:
            fixCand = []
            fixCandDur = []

        #
        for idx in range(sacCand.shape[0]-1):
            dur = T[sacCand[idx+1, 0]-1]-T[sacCand[idx, 1]-1]
            fixCand.append([sacCand[idx, 1], sacCand[idx+1, 0]])
            fixCandDur.append(dur)

        # check last fixation
        if sacCand[-1, 1] != len(T)-1:
            dur = T[-1] - T[sacCand[-1, 1]]
            fixCand.append([sacCand[-1, 1], len(T)-1])
            fixCandDur.append(dur)
        fixCand = numpy.array(fixCand, dtype=numpy.int)
        fixCandDur = numpy.array(fixCandDur)


        # merge small inter-saccadic fixation to saccade.
        tooShortFixation = numpy.where(fixCandDur <= config.FIXATION_MINIMUM_DURATION)[0]
        for idx in tooShortFixation:
            prevSaccadeIndex = numpy.where(sacCand[:, 1] == fixCand[idx, 0])[0]
            if len(prevSaccadeIndex) != 1:
                continue
            nextSaccadeIndex = prevSaccadeIndex+1
            if nextSaccadeIndex >= sacCand.shape[0]:  # there is no following saccade.
                continue
            sacCand[prevSaccadeIndex, 1] = sacCand[nextSaccadeIndex, 1]
            # saccadeCandidates[prevSaccadeIndex, 4] = saccadeCandidates[nextSaccadeIndex, 4]
            sacCandDur[prevSaccadeIndex,] = T[sacCand[nextSaccadeIndex, 1]]-T[sacCand[prevSaccadeIndex, 0]]
            sacCand = numpy.delete(sacCand, nextSaccadeIndex, 0)
            sacCandDur = numpy.delete(sacCandDur, nextSaccadeIndex, 0)

        idx = fixCandDur > config.FIXATION_MINIMUM_DURATION
        fixCand = fixCand[idx, :]
        fixCandDur = fixCandDur[idx]

    else:  # no saccade candidate is found.
        fixCand = numpy.array([[0, len(T)-1]])
        fixCandDur = numpy.array([T[-1]-T[0]])

    # find blinks
    # TODO: check break of fixation and saccades by blink.
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
        amp = numpy.linalg.norm((pix2deg[0]*(ex-sx), pix2deg[1]*(ey-sy)))
        saccadeList.append(GazeParser.SaccadeData((T[s[0]], T[s[1]]), (dur, sx, sy, ex, ey, amp), T))

    if not numpy.isnan(HV[:, 0]).all():  # Fixation is not appended if all values are none.
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
    ti = numpy.arange(0, T[-1], interval)
    interpolaterH = interp1d(T, HV[:, 0])
    interpolaterV = interp1d(T, HV[:, 1])
    hi = interpolaterH(ti)
    vi = interpolaterV(ti)

    return [ti, numpy.vstack((hi, vi)).transpose()]


def resampleTimeStamp(t, threshold=None):
    """
    :param t: Timestamp (N x 1)
    :param threshold:

    .. note::

        This function is obsolete.
    """
    tdiff = numpy.diff(t)
    average = numpy.mean(tdiff)
    if threshold is None:
        threshold = average * 0.1  # 25%
    for i in range(len(tdiff)-1):
        d1 = tdiff[i]-average
        d2 = tdiff[i+1]-average
        if d1*d2 < 0 and numpy.abs(d1) > threshold and numpy.abs(d2) > threshold:
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
    # w[0] and w[-1] must not be numpy.nan.
    if numpy.isnan(w[0]):
        i = 0
        while(numpy.isnan(w[i])):
            i += 1
            if i >= len(w):  # all values are None.
                return w
        w[0] = w[i]
    if numpy.isnan(w[-1]):
        i = len(w)-1
        while(numpy.isnan(w[i])):
            i -= 1
        w[-1] = w[i]

    # nanIndex = numpy.where(numpy.isnan(w))[0]
    validIndex = numpy.where(w == w)[0]  # numpy.where(numpy.isnan(w) == False)[0]

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

    nanListH = numpy.isnan(HV[:, 0])
    nanListV = numpy.isnan(HV[:, 1])
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
        weight = numpy.ones(filterSize)/filterSize
        filteredH = numpy.convolve(H, weight, 'same')
        filteredV = numpy.convolve(V, weight, 'same')

    filteredH = numpy.round(filteredH, decimals=decimals)
    filteredV = numpy.round(filteredV, decimals=decimals)

    filteredH[nanListH] = numpy.nan
    filteredV[nanListV] = numpy.nan

    return numpy.vstack((filteredH, filteredV)).transpose()


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
        if verbose: print('Target file (%s) already exist.' % dstFileName)
        return 'TARGET_FILE_ALREADY_EXISTS'

    if not isinstance(config, GazeParser.Configuration.Config):
        if isinstance(config, str):
            if verbose: print('Load configuration file: %s' % config)
            config = GazeParser.Configuration.Config(ConfigFile=config)
        elif sys.version_info[0] == 2 and isinstance(config, unicode):
            if verbose: print('Load configuration file: %s' % config)
            config = GazeParser.Configuration.Config(ConfigFile=config)
        elif has_pathlib and isinstance(config, pathlib.Path):
            if verbose: print('Load configuration file: %s' % str(config))
            config = GazeParser.Configuration.Config(ConfigFile=str(config))
        elif config is None:
            if verbose: print('Use default configuration.')
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
    if verbose: print('parsing...')
    
    line = fid.readline()
    if line.rstrip() != '#SimpleGazeTrackerDataFile':
        fid.close()
        if verbose: print('Not a SimpleGazeTracker data file.')
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
                        tmpT, tmpLHV = resampleData(numpy.array(T), numpy.array(LHV), config.RESAMPLING)
                        tmpT, tmpRHV = resampleData(numpy.array(T), numpy.array(LHV), config.RESAMPLING)

                        Llist = applyFilter(tmpT, tmpLHV, config, decimals=effectiveDigit)
                        Rlist = applyFilter(tmpT, tmpRHV, config, decimals=effectiveDigit)
                    else:
                        Tlist = numpy.array(T)
                        Llist = applyFilter(Tlist, numpy.array(LHV), config, decimals=effectiveDigit)
                        Rlist = applyFilter(Tlist, numpy.array(RHV), config, decimals=effectiveDigit)

                    (SacList, FixList, BlinkList) = buildEventListBinocular(Tlist, Llist, Rlist, config)
                    if not (idxLP is None and idxRP is None):
                        Plist = numpy.array([LP, RP]).transpose()
                    else:
                        Plist = None
                else:  # monocular
                    if config.RECORDED_EYE == 'L':
                        if config.RESAMPLING > 0:
                            Tlist, tmpHV = resampleData(numpy.array(T), numpy.array(HV), config.RESAMPLING)
                            Llist = applyFilter(Tlist, tmpHV, config, decimals=effectiveDigit)
                        else:
                            Tlist = numpy.array(T)
                            Llist = applyFilter(Tlist, numpy.array(HV), config, decimals=effectiveDigit)
                        (SacList, FixList, BlinkList) = buildEventListMonocular(Tlist, Llist, config)
                        Rlist = None
                    elif config.RECORDED_EYE == 'R':
                        if config.RESAMPLING > 0:
                            Tlist, tmpHV = resampleData(numpy.array(T), numpy.array(HV), config.RESAMPLING)
                            Rlist = applyFilter(Tlist, tmpHV, config, decimals=effectiveDigit)
                        else:
                            Tlist = numpy.array(T)
                            Rlist = applyFilter(Tlist, numpy.array(HV), config, decimals=effectiveDigit)
                        (SacList, FixList, BlinkList) = buildEventListMonocular(Tlist, Rlist, config)
                        Llist = None
                    if idxP is not None:
                        Plist = numpy.array(P).transpose()
                    else:
                        Plist = None

                MsgList = buildMsgList(M)
                G = GazeParser.GazeData(Tlist, Llist, Rlist, SacList, FixList, MsgList, BlinkList, Plist, config.RECORDED_EYE, config=config, recordingDate=startRec)
                if idxC is not None:
                    G.setCameraSpecificData(numpy.array(C))
                if idxUSBIO is not None:
                    G.setUSBIOData(usbioFormat, numpy.array(USBIO))
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
                        itemList[idx] = numpy.NaN
                if config.RECORDED_EYE == 'L':
                    accuracy = itemList[3:5]
                    precision = itemList[5:7]
                    accuracy.extend([numpy.NaN,numpy.NaN])
                    precision.extend([numpy.NaN,numpy.NaN])
                elif config.RECORDED_EYE == 'R':
                    accuracy = [numpy.NaN,numpy.NaN]
                    precision = [numpy.NaN,numpy.NaN]
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
                    if verbose: print(itemList)
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
                    if verbose: print('DATAFORMAT: %s' % (','.join(tmp)))

                # Nothing to do against these options
                elif itemList[0] in ['#STOP_REC', '#TRACKER_VERSION']:
                    pass

                # load GazeParser options if useFileParameters is True
                elif useFileParameters:
                    optName = itemList[0][1:]
                    if optName in GazeParser.Configuration.GazeParserDefaults:
                        if type(GazeParser.Configuration.GazeParserDefaults[optName]) == float:
                            setattr(config, optName, float(itemList[1]))
                            if verbose: print('%s = %f' % (optName, getattr(config, optName)))
                        elif type(GazeParser.Configuration.GazeParserDefaults[optName]) == int:
                            setattr(config, optName, int(itemList[1]))
                            if verbose: print('%s = %d' % (optName, getattr(config, optName)))
                        else:  # str
                            setattr(config, optName, itemList[1])

                            if verbose: print('%s = %s' % (optName, getattr(config, optName)))
                    else:
                        if verbose: print('Warning: unknown option ({})'.format(optName))

                # output unprocessed parameters if verbose==True
                else:
                    if verbose: print('Warning: ignored option ({})'.format(optName))
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
                    xL = numpy.NaN
                    yL = numpy.NaN
                    xR = numpy.NaN
                    yR = numpy.NaN
                    if not (idxLP is None and idxRP is None):
                        lP = numpy.NaN
                        rP = numpy.NaN
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
                    x = numpy.NaN
                    y = numpy.NaN
                    if idxP is not None:
                        p = numpy.NaN
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

    if verbose: print('saving...')
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

    if verbose: print('done.')
    return 'SUCCESS'


