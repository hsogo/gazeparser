"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""

import numpy
import GazeParser
import GazeParser.Configuration
import os
import re
import codecs
from scipy.interpolate import interp1d
from scipy.stats import nanmean
from scipy.signal import butter, lfilter, lfilter_zi, filtfilt


def EyelinkToGazeParser(EDFfile, eye, overwrite=False, config=None):
    """
    Convert an Eyelink EDF file to a GazeParser file.
    'edf2asc.exe' must be in a directory that is in your PATH.
    If EDF file name is 'foo.edf', the output file name is 'foo.db'

    :param str inputfile:
        name of EDF file to be converted.
    :param str eye:
        Output both-eye ('B'), left-eye ('L') or right-eye ('R') data.
    :param Boolean overwrite:
        If this parameter is true, output file is overwritten.
        The default value is False.
    :param GazeParser.Configuration, str config:
        An instance of GazeParser.Configuration that Specifies
        conversion configurations.  If value is a string, it is
        interpreted as a filename of GazeParser.configuration file.
        If value is none, default configuration is used.
        The default value is None.
    """
    (workDir, srcFilename) = os.path.split(os.path.abspath(EDFfile))
    filenameRoot, ext = os.path.splitext(srcFilename)
    EDFfileFullpath = os.path.join(workDir, srcFilename)
    dstFileName = os.path.join(workDir, filenameRoot + '.db')
    additionalDataFileName = os.path.join(workDir, filenameRoot + '.txt')

    print 'EyelinkToGazeParser start.'
    if os.path.exists(dstFileName) and (not overwrite):
        print 'Can not open %s.' % dstFileName
        return 'CANNOT_OPEN_OUTPUT_FILE'

    if not isinstance(config, GazeParser.Configuration.Config):
        if isinstance(config, str) or isinstance(config, unicode):
            print 'Load configuration file: %s' % config
            config = GazeParser.Configuration.Config(ConfigFile=config)
        elif config is None:
            print 'Use default configuration.'
            config = GazeParser.Configuration.Config()
        else:
            raise ValueError('config must be GazeParser.Configuration.Config, str, unicode or None.')

    if eye == 'L':
        flgL = True
        flgR = False
    elif eye == 'R':
        flgL = False
        flgR = True
    elif eye == 'B':
        flgL = True
        flgR = True
    else:
        raise ValueError('Second argument must be L/R/B.')

    T = []
    RH = []
    RV = []
    Rp = []
    LH = []
    LV = []
    Lp = []

    if flgL:
        tmpFile = os.path.join(workDir, '__left__.asc')
        os.system('edf2asc.exe ' + EDFfileFullpath + ' -sg -s -miss 9999 -nflags -l ' + tmpFile)
        fidLeft = open(tmpFile, 'r')
        for line in fidLeft.readlines():
            itemList = line[:-1].split('\t')
            try:
                T.append(int(itemList[0]))
                if float(itemList[1]) == 9999.0:
                    LH.append(numpy.NaN)
                    LV.append(numpy.NaN)
                    Lp.append(float(itemList[3]))
                else:
                    LH.append(float(itemList[1]))
                    LV.append(float(itemList[2]))
                    Lp.append(float(itemList[3]))
            except:
                continue
        fidLeft.close()
        os.remove(tmpFile)

    if flgR:
        tmpFile = os.path.join(workDir, '__right__.asc')
        os.system('edf2asc.exe ' + EDFfileFullpath + ' -sg -s -miss 9999 -nflags -r ' + tmpFile)
        fidRight = open(tmpFile, 'r')
        for line in fidRight.readlines():
            itemList = line[:-1].split('\t')
            try:
                if not flgL:  # if flgL is true, T has already bean built.
                    T.append(int(itemList[0]))
                if float(itemList[1]) == 9999.0:
                    RH.append(numpy.NaN)
                    RV.append(numpy.NaN)
                    Rp.append(float(itemList[3]))
                else:
                    RH.append(float(itemList[1]))
                    RV.append(float(itemList[2]))
                    Rp.append(float(itemList[3]))
            except:
                continue
        fidRight.close()
        os.remove(tmpFile)

    """
    if len(LH)>0 and len(RH) == 0:
        RH = LH
        RV = LV
        Rp = Lp

    if len(LH) == 0 and len(RH)>0:
        LH = RH
        LV = RV
        Lp = Rp
    """

    tmpFile = os.path.join(workDir, '__event__.asc')
    os.system('edf2asc.exe ' + EDFfileFullpath + ' -e -miss 9999 ' + tmpFile)
    fidEvent = open(tmpFile, 'r')

    listBlock = []
    listSaccadeTime = []
    listFixationTime = []
    listBlinkTime = []
    listMessage = []

    listSaccadeData = []
    listFixationData = []
    listBlinkData = []

    flgInBlock = False

    # Detect blocks, saccades, fixations, blinks, and messages

    for line in fidEvent.readlines():
        itemList = re.split('\s*', line[:-1])

        if itemList[0] == "START" and not flgInBlock:  # Beginning of a block
            flgInBlock = True
            timeBlockStart = int(itemList[1])

        elif itemList[0] == "END" and flgInBlock:  # End of a block
            flgInBlock = False
            listBlock.append([timeBlockStart, int(itemList[1])])

        elif itemList[0] == "ESACC" and flgInBlock:  # End of a saccade
            listSaccadeTime.append([int(itemList[2]), int(itemList[3])])
            listSaccadeData.append([int(itemList[4]), float(itemList[5]), float(itemList[6]), float(itemList[7]), float(itemList[8]), float(itemList[9])])
            # (Duration, start_X, start_Y, end_X, end_Y, amplitude)

        elif itemList[0] == "EFIX" and flgInBlock:  # End of a fixation
            listFixationTime.append([int(itemList[2]), int(itemList[3])])
            listFixationData.append([int(itemList[4]), float(itemList[5]), float(itemList[6])])
            # (Duration, COG_x, COG_Y)

        elif itemList[0] == "MSG" and flgInBlock:
            listMessage.append([int(itemList[1]), ' '.join(itemList[2:])])

        elif itemList[0] == "EBLINK" and flgInBlock:  # End of a blink
            listBlinkTime.append([int(itemList[2]), int(itemList[3])])
            listBlinkData.append(int(itemList[4]))
            # (Duration)

    fidEvent.close()
    os.remove(tmpFile)

    # Generating a instance of GazeData

    T = numpy.array(T)
    Data = []

    for blk in range(len(listBlock)):
        idx = numpy.where((T >= listBlock[blk][0]) & (T <= listBlock[blk][1]))[0]
        Tlist = T[idx[0]:idx[-1]+1]
        if LH != []:
            Llist = (numpy.array([LH[idx[0]:idx[-1]+1], LV[idx[0]:idx[-1]+1]])).transpose()
        else:
            Llist = []
        if RH != []:
            Rlist = (numpy.array([RH[idx[0]:idx[-1]+1], RV[idx[0]:idx[-1]+1]])).transpose()
        else:
            Rlist = []

        SacList = []
        for sac in range(len(listSaccadeTime)):
            if listSaccadeTime[sac][0] >= listBlock[blk][0] and listSaccadeTime[sac][1] <= listBlock[blk][1]:
                SacList.append(GazeParser.SaccadeData(listSaccadeTime[sac], listSaccadeData[sac], Tlist))

        FixList = []
        for fix in range(len(listFixationTime)):
            if listFixationTime[fix][0] >= listBlock[blk][0] and listFixationTime[fix][1] <= listBlock[blk][1]:
                FixList.append(GazeParser.FixationData(listFixationTime[fix], listFixationData[fix], Tlist))

        MsgList = []
        for msg in range(len(listMessage)):
            if listBlock[blk][0] <= listMessage[msg][0] <= listBlock[blk][1]:
                MsgList.append(GazeParser.MessageData(listMessage[msg]))

        BlinkList = []
        for b in range(len(listBlinkTime)):
            if listBlinkTime[b][0] >= listBlock[blk][0] and listBlinkTime[b][1] <= listBlock[blk][1]:
                BlinkList.append(GazeParser.BlinkData(listBlinkTime[b], listBlinkData[b], Tlist))

        G = GazeParser.GazeData(Tlist, Llist, Rlist, SacList, FixList, MsgList, BlinkList, eye, config=config)

        Data.append(G)

    if os.path.exists(additionalDataFileName):
        print 'Additional data file is found.'
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

    return 'SUCCESS'


def parseBlinkCandidates(T, HVs, config):
    index = 0
    blinkCandidates = []
    isBlink = False
    blinkStart = None

    nanList = numpy.apply_along_axis(numpy.all, 1, numpy.isnan(HVs))
    lenNanList = len(nanList)

    while index < lenNanList-1:
        if isBlink:
            if not nanList[index]:
                dur = T[index-1]-T[blinkStart]
                blinkCandidates.append([blinkStart, index, dur])
                isBlink = False
        else:
            if nanList[index]:
                isBlink = True
                blinkStart = index

        index += 1

    # check last blink
    if isBlink:
        dur = T[index]-T[blinkStart]
        blinkCandidates.append([blinkStart, index, dur])
    blinkCandidates = numpy.array(blinkCandidates)

    return blinkCandidates


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
    saccadeCandidates = []
    saccadeStart = None
    while index < len(absAcceleration):
        if isSaccade:
            if numpy.isnan(absVelocity[index]) or absVelocity[index] <= config.SACCADE_VELOCITY_THRESHOLD:
                dur = T[index-1]-T[saccadeStart]
                # saccadeCandidates.append([saccadeStart, index, dur, absAcceleration[saccadeStart-1], absAcceleration[index-1]])
                saccadeCandidates.append([saccadeStart, index, dur])
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
        saccadeCandidates.append([saccadeStart, index-1, dur])
    saccadeCandidates = numpy.array(saccadeCandidates)

    return saccadeCandidates


def buildEventListBinocular(T, LHV, RHV, config):
    cm2deg = 180/numpy.pi*numpy.arctan(1.0/config.VIEWING_DISTANCE)
    deg2pix = numpy.array([config.DOTS_PER_CENTIMETER_H, config.DOTS_PER_CENTIMETER_V])/cm2deg
    pix2deg = 1.0/deg2pix

    saccadeCandidatesL = parseSaccadeCandidatesWithVACriteria(T, LHV, config)
    saccadeCandidatesR = parseSaccadeCandidatesWithVACriteria(T, RHV, config)
    blinkCandidates = parseBlinkCandidates(T, numpy.hstack((LHV, RHV)), config)

    # delete small saccade first, then check fixation
    # check saccade duration
    if len(saccadeCandidatesL) > 0:
        idx = numpy.where(saccadeCandidatesL[:, 2] > config.SACCADE_MINIMUM_DURATION)[0]
        if len(idx) > 0:
            saccadeCandidatesL = saccadeCandidatesL[idx, :]
        else:
            saccadeCandidatesL = []
    if len(saccadeCandidatesR) > 0:
        idx = numpy.where(saccadeCandidatesR[:, 2] > config.SACCADE_MINIMUM_DURATION)[0]
        if len(idx) > 0:
            saccadeCandidatesR = saccadeCandidatesR[idx, :]
        else:
            saccadeCandidatesR = []

    saccadeCandidates = []
    # check binocular coincidence
    for index in range(len(saccadeCandidatesL)):
        overlap = numpy.where((saccadeCandidatesR[:, 1] >= saccadeCandidatesL[index, 0]) &
                              (saccadeCandidatesR[:, 0] <= saccadeCandidatesL[index, 1]))[0]
        if len(overlap) > 0:
            startIndex = min(saccadeCandidatesL[index, 0], saccadeCandidatesR[overlap[0], 0])
            endIndex = max(saccadeCandidatesL[index, 1], saccadeCandidatesR[overlap[-1], 1])
            if len(saccadeCandidates) > 0 and saccadeCandidates[-1][1] > startIndex:
                pass
            else:
                saccadeCandidates.append([startIndex, endIndex, T[endIndex]-T[startIndex]])
    saccadeCandidates = numpy.array(saccadeCandidates)

    # amplitude
    amplitudeCheckList = []
    for idx in range(len(saccadeCandidates)):
        ampL = numpy.linalg.norm((LHV[saccadeCandidates[idx, 1], :]-LHV[saccadeCandidates[idx, 0], :])*pix2deg)
        ampR = numpy.linalg.norm((RHV[saccadeCandidates[idx, 1], :]-RHV[saccadeCandidates[idx, 0], :])*pix2deg)
        if (ampL+ampR)/2.0 >= config.SACCADE_MINIMUM_AMPLITUDE:
            amplitudeCheckList.append(idx)
    saccadeCandidates = saccadeCandidates[amplitudeCheckList, :]

    # find fixations
    # at first, check whether data starts with fixation or saccade.
    if saccadeCandidates[0, 0] > 0:
        dur = T[saccadeCandidates[0, 0]-1]-T[0]
        fixationCandidates = [[0, saccadeCandidates[0, 0]-1, dur]]
    else:
        fixationCandidates = []

    #
    for index in range(saccadeCandidates.shape[0]-1):
        dur = T[saccadeCandidates[index+1, 0]-1]-T[saccadeCandidates[index, 1]-1]
        fixationCandidates.append([saccadeCandidates[index, 1], saccadeCandidates[index+1, 0], dur])

    # check last fixation
    if saccadeCandidates[-1, 1] != len(T)-1:
        dur = T[-1] - T[saccadeCandidates[-1, 1]]
        fixationCandidates.append([saccadeCandidates[-1, 1], len(T)-1, dur])
    fixationCandidates = numpy.array(fixationCandidates)

    # merge small inter-saccadic fixation to saccade.
    tooShortFixation = numpy.where(fixationCandidates[:, 2] <= config.FIXATION_MINIMUM_DURATION)[0]
    for index in tooShortFixation:
        prevSaccadeIndex = numpy.where(saccadeCandidates[:, 1] == fixationCandidates[index, 0])[0]
        if len(prevSaccadeIndex) != 1:
            continue
        nextSaccadeIndex = prevSaccadeIndex+1
        if nextSaccadeIndex >= saccadeCandidates.shape[0]:  # there is no following saccade.
            continue
        saccadeCandidates[prevSaccadeIndex, 1] = saccadeCandidates[nextSaccadeIndex, 1]
        saccadeCandidates[prevSaccadeIndex, 2] = T[int(saccadeCandidates[nextSaccadeIndex, 1])]-T[int(saccadeCandidates[prevSaccadeIndex, 0])]
        saccadeCandidates = numpy.delete(saccadeCandidates, nextSaccadeIndex, 0)

    fixationCandidates = fixationCandidates[fixationCandidates[:, 2] > config.FIXATION_MINIMUM_DURATION, :]

    # find blinks
    # TODO: check break of fixation and saccades by blink.
    if len(blinkCandidates) > 0:
        blinkCandidates = blinkCandidates[blinkCandidates[:, 2] > config.BLINK_MINIMUM_DURATION]

    # bulild lists
    saccadeList = []
    fixationList = []
    blinkList = []

    for s in saccadeCandidates:
        sx = (LHV[s[0], 0]+RHV[s[0], 0])/2.0
        sy = (LHV[s[0], 1]+RHV[s[0], 1])/2.0
        ex = (LHV[s[1], 0]+RHV[s[1], 0])/2.0
        ey = (LHV[s[1], 1]+RHV[s[1], 1])/2.0
        amp = numpy.linalg.norm((pix2deg[0]*(ex-sx), pix2deg[1]*(ey-sy)))
        saccadeList.append(GazeParser.SaccadeData((T[s[0]], T[s[1]]), (s[2], sx, sy, ex, ey, amp), T))

    if not (numpy.isnan(LHV[:, 0]).all() and numpy.isnan(RHV[:, 0]).all()):  # Fixation is not appended if all values are none.
        for f in fixationCandidates:
            cx = nanmean(numpy.hstack((LHV[f[0]:f[1]+1, 0], RHV[f[0]:f[1]+1, 0])))
            cy = nanmean(numpy.hstack((LHV[f[0]:f[1]+1, 1], RHV[f[0]:f[1]+1, 1])))
            fixationList.append(GazeParser.FixationData((T[f[0]], T[f[1]]), (f[2], cx, cy), T))

    for b in blinkCandidates:
        blinkList.append(GazeParser.BlinkData((T[b[0]], T[b[1]]), b[2], T))

    return (saccadeList, fixationList, blinkList)


def buildEventListMonocular(T, HV, config):
    cm2deg = 180/numpy.pi*numpy.arctan(1.0/config.VIEWING_DISTANCE)
    deg2pix = numpy.array([config.DOTS_PER_CENTIMETER_H, config.DOTS_PER_CENTIMETER_V])/cm2deg
    pix2deg = 1.0/deg2pix

    saccadeCandidates = parseSaccadeCandidatesWithVACriteria(T, HV, config)
    blinkCandidates = parseBlinkCandidates(T, HV, config)

    # delete small saccade first, then check fixation
    if len(saccadeCandidates) > 0:
        # check saccade duration
        idx = numpy.where(saccadeCandidates[:, 2] > config.SACCADE_MINIMUM_DURATION)[0]
        saccadeCandidates = saccadeCandidates[idx, :]

        # check saccade amplitude
        amplitudeCheckList = []
        for idx in range(len(saccadeCandidates)):
            if numpy.linalg.norm((HV[saccadeCandidates[idx, 1], :]-HV[saccadeCandidates[idx, 0], :])*pix2deg) >= config.SACCADE_MINIMUM_AMPLITUDE:
                amplitudeCheckList.append(idx)
        if len(amplitudeCheckList) > 0:
            saccadeCandidates = saccadeCandidates[amplitudeCheckList, :]
        else:
            saccadeCandidates = []

    # find fixations
    if len(saccadeCandidates) > 0:
        # check whether data starts with fixation or saccade.
        if saccadeCandidates[0, 0] > 0:
            dur = T[saccadeCandidates[0, 0]-1]-T[0]
            fixationCandidates = [[0, saccadeCandidates[0, 0]-1, dur]]
        else:
            fixationCandidates = []

        #
        for index in range(saccadeCandidates.shape[0]-1):
            dur = T[saccadeCandidates[index+1, 0]-1]-T[saccadeCandidates[index, 1]-1]
            fixationCandidates.append([saccadeCandidates[index, 1], saccadeCandidates[index+1, 0], dur])

        # check last fixation
        if saccadeCandidates[-1, 1] != len(T)-1:
            dur = T[-1] - T[saccadeCandidates[-1, 1]]
            fixationCandidates.append([saccadeCandidates[-1, 1], len(T)-1, dur])
        fixationCandidates = numpy.array(fixationCandidates)

        # merge small inter-saccadic fixation to saccade.
        tooShortFixation = numpy.where(fixationCandidates[:, 2] <= config.FIXATION_MINIMUM_DURATION)[0]
        for index in tooShortFixation:
            prevSaccadeIndex = numpy.where(saccadeCandidates[:, 1] == fixationCandidates[index, 0])[0]
            if len(prevSaccadeIndex) != 1:
                continue
            nextSaccadeIndex = prevSaccadeIndex+1
            if nextSaccadeIndex >= saccadeCandidates.shape[0]:  # there is no following saccade.
                continue
            saccadeCandidates[prevSaccadeIndex, 1] = saccadeCandidates[nextSaccadeIndex, 1]
            # saccadeCandidates[prevSaccadeIndex, 4] = saccadeCandidates[nextSaccadeIndex, 4]
            saccadeCandidates[prevSaccadeIndex, 2] = T[int(saccadeCandidates[nextSaccadeIndex, 1])]-T[int(saccadeCandidates[prevSaccadeIndex, 0])]
            saccadeCandidates = numpy.delete(saccadeCandidates, nextSaccadeIndex, 0)

        fixationCandidates = fixationCandidates[fixationCandidates[:, 2] > config.FIXATION_MINIMUM_DURATION, :]

    else:  # no saccade candidate is found.
        fixationCandidates = numpy.array([[0, len(T)-1, T[-1]-T[0]]])

    # find blinks
    # TODO: check break of fixation and saccades by blink.
    if len(blinkCandidates) > 0:
        blinkCandidates = blinkCandidates[blinkCandidates[:, 2] > config.BLINK_MINIMUM_DURATION]

    # bulild lists
    saccadeList = []
    fixationList = []
    blinkList = []

    for s in saccadeCandidates:
        sx = HV[s[0], 0]
        sy = HV[s[0], 1]
        ex = HV[s[1], 0]
        ey = HV[s[1], 1]
        amp = numpy.linalg.norm((pix2deg[0]*(ex-sx), pix2deg[1]*(ey-sy)))
        saccadeList.append(GazeParser.SaccadeData((T[s[0]], T[s[1]]), (s[2], sx, sy, ex, ey, amp), T))

    if not numpy.isnan(HV[:, 0]).all():  # Fixation is not appended if all values are none.
        for f in fixationCandidates:
            cx = nanmean(HV[f[0]:f[1]+1, 0])
            cy = nanmean(HV[f[0]:f[1]+1, 1])
            fixationList.append(GazeParser.FixationData((T[f[0]], T[f[1]]), (f[2], cx, cy), T))

    for b in blinkCandidates:
        blinkList.append(GazeParser.BlinkData((T[b[0]], T[b[1]]), b[2], T))

    return (saccadeList, fixationList, blinkList)


def buildMsgList(M):
    msglist = []
    for i in range(len(M)):
        msglist.append(GazeParser.MessageData(M[i]))

    return msglist


def rectifyData(T, HV, frequency):
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


def rectifyTimeStamp(t, threshold=None):
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


def TrackerToGazeParser(inputfile, overwrite=False, config=None, useFileParameters=True):
    """
    Convert an SimpleGazeTracker data file to a GazeParser file.
    If GazeTracker data file name is 'foo.csv', the output file name is 'foo.db'

    :param str inputfile:
        name of GazeParser file to be converted.
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
    """
    (workDir, srcFilename) = os.path.split(os.path.abspath(inputfile))
    filenameRoot, ext = os.path.splitext(srcFilename)
    inputfileFullpath = os.path.join(workDir, srcFilename)
    dstFileName = os.path.join(workDir, filenameRoot+'.db')
    additionalDataFileName = os.path.join(workDir, filenameRoot+'.txt')
    usbioFormat = None

    print '------------------------------------------------------------'
    print 'TrackerToGazeParser start.'
    print 'source file: %s' % inputfile
    if os.path.exists(dstFileName) and (not overwrite):
        print 'Target file (%s) already exist.' % dstFileName
        return 'TARGET_FILE_ALREADY_EXISTS'

    if not isinstance(config, GazeParser.Configuration.Config):
        if isinstance(config, str) or isinstance(config, unicode):
            print 'Load configuration file: %s' % config
            config = GazeParser.Configuration.Config(ConfigFile=config)
        elif config is None:
            print 'Use default configuration.'
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
    print 'parsing...'

    for line in fid:
        itemList = line[:-1].rstrip().split(',')
        if itemList[0][0] == '#':  # Messages
            if itemList[0] == '#START_REC':
                startRec = map(int, itemList[1:])
                flgInBlock = True

            elif itemList[0] == '#STOP_REC':
                if config.RECORDED_EYE == 'B':
                    if config.RESAMPLING > 0:
                        tmpT, tmpLHV = rectifyData(numpy.array(T), numpy.array(LHV), config.RESAMPLING)
                        tmpT, tmpRHV = rectifyData(numpy.array(T), numpy.array(LHV), config.RESAMPLING)

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
                            Tlist, tmpHV = rectifyData(numpy.array(T), numpy.array(HV), config.RESAMPLING)
                            Llist = applyFilter(Tlist, tmpHV, config, decimals=effectiveDigit)
                        else:
                            Tlist = numpy.array(T)
                            Llist = applyFilter(Tlist, numpy.array(HV), config, decimals=effectiveDigit)
                        (SacList, FixList, BlinkList) = buildEventListMonocular(Tlist, Llist, config)
                        Rlist = None
                    elif config.RECORDED_EYE == 'R':
                        if config.RESAMPLING > 0:
                            Tlist, tmpHV = rectifyData(numpy.array(T), numpy.array(HV), config.RESAMPLING)
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
                print itemList, config.RECORDED_EYE, itemList[1:3], accuracy, precision
                CALPOINT.append(GazeParser.CalPointData(itemList[1:3],accuracy,precision,config.RECORDED_EYE))
                
            elif itemList[0] == '#CALDATA':
                pass
            
            if not flgInBlock:
                if useFileParameters:
                    # SimpleGazeTracker options
                    if itemList[0] == '#DATAFORMAT':
                        idxT = idxX = idxY = idxP = idxC = idxUSBIO = None
                        idxLX = idxLY = idxRX = idxRY = idxLP = idxRP = idxC = None
                        tmp = []
                        for i in range(len(itemList)-1):
                            if itemList[i+1].find('USBIO;') == 0:  # support USBIO
                                cmd = 'idxUSBIO=' + str(i)
                                usbioFormat = itemList[i+1][6:].split(';')
                                if len(usbioFormat[-1]) == 0:  # remove last item if empty
                                    usbioFormat.pop(-1)
                            else:
                                cmd = 'idx'+itemList[i+1] + '=' + str(i)
                            exec cmd
                            tmp.append(cmd)
                        print 'DATAFORMAT: %s' % (','.join(tmp))

                    # GazeParser options
                    optName = itemList[0][1:]
                    if optName in GazeParser.Configuration.GazeParserDefaults:
                        if type(GazeParser.Configuration.GazeParserDefaults[optName]) == float:
                            setattr(config, optName, float(itemList[1]))
                            print '%s = %f' % (optName, getattr(config, optName))
                        elif type(GazeParser.Configuration.GazeParserDefaults[optName]) == int:
                            setattr(config, optName, int(itemList[1]))
                            print '%s = %d' % (optName, getattr(config, optName))
                        else:  # str
                            setattr(config, optName, itemList[1])
                            print '%s = %s' % (optName, getattr(config, optName))

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
                    tmp = map(int, tmp)
                    USBIO.append(tmp)
                except:
                    C.append(itemList[idxUSBIO])

    print 'saving...'
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

    print 'done.'
    return 'SUCCESS'


def TobiiToGazeParser(inputfile, overwrite=False, config=None):
    """
    Convert an Tobii TSV file to a GazeParser file.
    Text export configuration should be 'All data'.
    If TSV file name is 'foo.tsv', the output file name is 'foo.db'

    :param str inputfile:
        name of TSV file to be converted.
    :param Boolean overwrite:
        If this parameter is true, output file is overwritten.
        The default value is False.
    :param GazeParser.Configuration, str config:
        An instance of GazeParser.Configuration that Specifies
        conversion configurations.  If value is a string, it is
        interpreted as a filename of GazeParser.configuration file.
        If value is none, default configuration is used.
        The default value is None.
    """
    (workDir, srcFilename) = os.path.split(os.path.abspath(inputfile))
    filenameRoot, ext = os.path.splitext(srcFilename)
    inputfileFullpath = os.path.join(workDir, srcFilename)
    dstFileName = os.path.join(workDir, filenameRoot+'.db')
    additionalDataFileName = os.path.join(workDir, filenameRoot+'.txt')

    print 'TobiiToGazeParser start.'
    if os.path.exists(dstFileName) and (not overwrite):
        print 'Can not open %s.' % dstFileName
        return 'CANNOT_OPEN_OUTPUT_FILE'

    if not isinstance(config, GazeParser.Configuration.Config):
        if isinstance(config, str) or isinstance(config, unicode):
            print 'Load configuration file: %s' % config
            config = GazeParser.Configuration.Config(ConfigFile=config)
        elif config is None:
            print 'Use default configuration.'
            config = GazeParser.Configuration.Config()
        else:
            raise ValueError('config must be GazeParser.Configuration.Config, str, unicode or None.')

    fid = open(inputfileFullpath, "r")

    field = {}
    # read header part
    for line in fid:
        itemList = line.rstrip().split('\t')
        if itemList[0] == 'Recording resolution:':
            config.SCREEN_WIDTH = int(itemList[1].split('x')[0])
            config.SCREEN_HEIGHT = int(itemList[1].split('x')[1])
            print 'SCREEN_WIDTH: %d' % config.SCREEN_WIDTH
            print 'SCREEN_HEIGHT: %d' % config.SCREEN_HEIGHT
        elif itemList[0] == 'Timestamp':
            # read column header
            for i in range(len(itemList)):
                field[itemList[i]] = i
            break

    Data = []

    T = []
    LHV = []
    RHV = []
    M = []
    FIX = []
    GAZE = []

    currentFixationIndex = -1

    for line in fid:
        itemList = line.rstrip().split('\t')

        isGazeDataAvailable = False
        # record gaze position
        if itemList[field['GazePointXLeft']] != '':
            isGazeDataAvailable = True
            if itemList[field['ValidityLeft']] != '4':
                LHV.append((float(itemList[field['GazePointXLeft']]), float(itemList[field['GazePointYLeft']])))
            else:  # pupil was not found
                LHV.append((numpy.NaN, numpy.NaN))

        if itemList[field['GazePointXRight']] != '':
            isGazeDataAvailable = True
            if itemList[field['ValidityRight']] != '4':
                RHV.append((float(itemList[field['GazePointXRight']]), float(itemList[field['GazePointYRight']])))
            else:  # pupil was not found
                RHV.append((numpy.NaN, numpy.NaN))

        # record timestamp if gaze data is available
        if isGazeDataAvailable:
            T.append(int(itemList[field['Timestamp']]))
            GAZE.append((float(itemList[field['GazePointX']]), float(itemList[field['GazePointY']])))

        # record fixation
        if itemList[field['FixationIndex']] != '':
            if int(itemList[field['FixationIndex']]) > currentFixationIndex:
                FIX.append(int(itemList[field['Timestamp']]))
                currentFixationIndex = int(itemList[field['FixationIndex']])

        # record event
        if itemList[field['Event']] != '':
            message = ','.join((itemList[field['Event']], itemList[field['EventKey']], itemList[field['Data1']], itemList[field['Data2']], itemList[field['Descriptor']]))
            M.append((int(itemList[field['Timestamp']]), message))

    # last fixation ... check exact format of Tobii data later.
    # FIX.append(int(itemList[field['Timestamp']]))

    # convert to numpy.ndarray
    Tlist = numpy.array(T)
    Llist = numpy.array(LHV)
    Rlist = numpy.array(RHV)
    Glist = numpy.array(GAZE)

    # build FixationData
    FixList = []
    for fi in range(len(FIX)-1):
        startTime = FIX[fi]
        endTime = FIX[fi+1]
        startIndex = numpy.where(startTime == Tlist)[0][0]
        endIndex = numpy.where(endTime == Tlist)[0][0]-1
        duration = endTime-startTime
        (cogx, cogy) = numpy.mean(Glist[startIndex:endIndex, :], axis=0)
        FixList.append(GazeParser.FixationData((startTime, endTime), (duration, cogx, cogy), Tlist))

    # build MessageData
    MsgList = []
    for msg in range(len(M)):
        MsgList.append(GazeParser.MessageData(M[msg]))

    # build GazeData
    G = GazeParser.GazeData(Tlist, Llist, Rlist, [], FixList, MsgList, [], 'B', config=config)

    Data.append(G)

    if os.path.exists(additionalDataFileName):
        print 'Additional data file is found.'
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

    return 'SUCCESS'
