"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).

Detecting microsaccades with the method of Engbert & Kliegl (2003).
The class Microsacc and the binsacc function are port of Engbert and Kliel's
matlab scripts.

Example
---------
::

    import GazeParser
    (data, additionalData) = GazeParser.load('datafile.db')
    from GazeParser.MicroSacc import MicroSacc, buildMicroSaccadesListMonocular

    #get a list of microsaccades in the same format
    # as that of the original matlab function.
    microsacc = MicroSacc(data[0].L, 250)

    #get a list of microsaccades as a list of the GazeParser.Core.Saccade objects.
    microsacc = buildMicroSaccadesListMonocular(data[0].L, samplingFreq=250)


REFERENCE:
 Engbert, R., & Kliegl, R. (2003). Microsaccades uncover the orientation
 of covert attention. Vision Res, 43(9), 1035-1045.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy
from GazeParser.Core import SaccadeData


class MicroSacc(object):
    """
    """
    def __init__(self, data, samplingFreq, velocityType='slow', vfac=6, minSamples=3):
        """
        :param numpy.ndarray data: gaze data.
        :param float samplingFreq: sampling frequency.
        :param str velocityType: 'slow' or 'fast'. See Engbert & Kliegl (2003) for detail.
            Default value is 'slow'.
        :param int vfac: Modifying threshold for microsaccade detection. See Engbert & Kliegl (2003) for detail.
            Default value is 6.
        :param int minSamples: Microsaccades must have samples equal or larger than this value.
            Default value is 3.

        :return: An nx7 array which holds detected microsaccades

        ====== ==================================================
        column description
        ====== ==================================================
        0      index of the starting point of the microsaccade
        1      index of the termination pointof the microsaccade
        2      peak velocity
        3      amplitude
        4      direction
        5      holizontal amplitude
        6      vertical amplitude
        ====== ==================================================

        """
        if velocityType not in ['slow', 'fast']:
            raise ValueError('Invalid velocityType.')

        self.samplingFreq = samplingFreq
        self.velocityType = velocityType
        self.vfac = vfac
        self.minSamples = minSamples

        if data.shape[1] == 2:
            v = self._vecvel(data)
            self.ms = self._microsacc(data, v)
        else:
            # self.ms = self._binsacc(data[:, 0:2], data[:, 2:4])
            lms = self._microsacc(data[:, 0:2], v)
            rms = self._microsacc(data[:, 2:4], v)
            self.ms = self._binsacc(lms, rms)

    def _vecvel(self, data):
        N = len(data)
        v = numpy.zeros((N, 2))
        if self.velocityType == 'fast':
            v[1:-1] = self.samplingFreq/2.0 * (data[2:]-data[:-2])
        elif self.velocityType == 'slow':
            v[2:-2] = self.samplingFreq/6.0 * (data[4:]+data[3:-1]-data[1:-3]-data[:-4])
        return v

    def _microsacc(self, data, vdata):
        msdx = numpy.sqrt(numpy.nanmedian(vdata[:, 0]**2) - numpy.nanmedian(vdata[:, 0])**2)
        msdy = numpy.sqrt(numpy.nanmedian(vdata[:, 1]**2) - numpy.nanmedian(vdata[:, 1])**2)
        radiusX = self.vfac * msdx
        radiusY = self.vfac * msdy
        
        #idx = numpy.where(((vdata[:, 0]/radiusX)**2 + (vdata[:, 1]/radiusY)**2) > 1)[0]
        idx = numpy.where(nan_greater((vdata[:, 0]/radiusX)**2 + (vdata[:, 1]/radiusY)**2, 1))[0]

        N = len(idx)
        sac = []
        nsac = 0
        dur = 1
        a = 1
        k = 0

        while k < N-1:
            if idx[k+1]-idx[k] == 1:
                dur = dur+1
            else:
                if dur >= self.minSamples:
                    b = k
                    sac.append([idx[a], idx[b]])
                    nsac += 1
                a = k+1
                dur = 1
            k += 1
        if dur >= self.minSamples:
            b = k
            sac.append([idx[a], idx[b]])
            nsac += 1

        sac = numpy.array(sac)
        sac = numpy.hstack((sac, numpy.zeros((nsac, 5))))
        vabs = numpy.sqrt(vdata[:, 0]**2+vdata[:, 1]**2)
        for s in range(len(sac)):
            a = int(sac[s, 0])
            b = int(sac[s, 1])
            vpeak = numpy.max(vabs[a:b+1])
            ampl = numpy.linalg.norm(data[a, :2]-data[b, :2])
            sac[s, 2] = vpeak
            sac[s, 3] = ampl
            delx = data[b, 0] - data[a, 0]
            dely = data[b, 1] - data[a, 1]
            phi = 180/numpy.pi*numpy.arctan2(dely, delx)
            sac[s, 4] = phi
            sac[s, 5] = delx
            sac[s, 6] = dely

        return sac

    ms = None


def _binsacc(L, R):
    """
    :param numpy.ndarray L: left eye's microsaccades, detected by MicroSacc.
    :param numpy.ndarray R: right eye's microsaccades, detected by MicroSacc.
    """
    NL = L.shape[0]
    # NR = R.shape[0]

    sac = []
    nsac = 0
    for i in range(NL):
        l1 = L[i, 0]
        l2 = L[i, 1]
        overlap = numpy.where((R[:, 1] >= l1) & (R[:, 0] <= l2))[0]
        if len(overlap) > 0:
            r1 = R[overlap[0], 0]
            r2 = R[overlap[0], 1]
            vl = L[i, 2]
            vr = R[overlap[0], 2]
            ampl = L[i, 3]
            ampr = R[overlap[0], 3]
            dxl = L[i, 5]
            dyl = L[i, 6]
            dxr = R[overlap[0], 5]
            dyr = R[overlap[0], 6]
            dx = dxl+dxr
            dy = dyl+dyr
            phi = 180/numpy.pi*numpy.arctan2(dy, dx)
            sac.append([min([l1, r1]), max([l2, r2]), (vl+vr)/2.0, (ampl+ampr)/2.0,
                        phi, (dxl+dxr)/2.0, (dyr+dyl)/2.0])
            nsac += 1

    k = 0
    while k < nsac:
        if sac[k][1]+3 <= sac[k+1][0]:
            k += 1
        else:
            sac[k][1] = sac[k+1][1]
            sac[k][2] = max([sac[k, 2], sac[k+1][2]])
            dx1 = sac[k][5]
            dy1 = sac[k][6]
            dx2 = sac[k+1][5]
            dy2 = sac[k+1][6]
            dx = dx1+dx2
            dy = dy1+dy2
            amp = numpy.sqrt(dx**2+dy**2)
            phi = 180/numpy.pi*numpy.arctan2(dy, dx)
            sac[k][3] = amp
            sac[k][4] = phi
            sac[k][5] = dx
            sac[k][6] = dy
            del sac[k+1]
            nsac -= 1

    return numpy.array(sac)


def buildMicroSaccadesListMonocular(gazeData, eye, samplingFreq=None, velocityType='slow', vfac=6, minSamples=3):
    """
    Get a list of microsaccades as a list of the GazeParser.Core.Saccade objects.

    :param gazeData: an instance of :class:`~GazeParser.Core.GazeData`
    :param str eye: 'L' or 'R'
    :samplingFreq: sampling frequency of the data. If None, sampling frequency
        is calculated from the data.  Default value is None.
    :param str velocityType: 'slow' or 'fast'. See Engbert & Kliegl (2003) for detail.
        Default value is 'slow'.
    :param int vfac: Modifying threshold for microsaccade detection. See Engbert & Kliegl (2003) for detail.
        Default value is 6.
    :param int minSamples: Microsaccades must have samples equal or larger than this value.
        Default value is 3.
    """
    T = gazeData.T
    if eye == 'L':
        HV = gazeData.L
    elif eye == 'R':
        HV = gazeData.R

    if samplingFreq is None:
        samplingFreq = 1000.0/numpy.mean(numpy.diff(T))

    msobj = MicroSacc(HV, samplingFreq, velocityType, vfac, minSamples)
    ms = msobj.ms

    saclist = []
    for index in range(len(saclist)):
        sx = HV[ms[index, 0], 0]
        sy = HV[ms[index, 0], 1]
        ex = HV[ms[index, 1], 0]
        ey = HV[ms[index, 1], 1]
        saclist.append(SaccadeData((T[ms[index, 0]], T[ms[index, 1]]),
                                   (sx, sy, ex, ey, ms[index, 3], gazeData.Pix2Deg(ms[index, 3])),
                                   T))

    return numpy.array(saclist)


def buildMicroSaccadeListBinocular(gazeData, samplingFreq=None, velocityType='slow', vfac=6, minSamples=3):
    """
    Get a list of binocular microsaccades as a list of the GazeParser.Core.Saccade objects.

    :param gazeData: an instance of :class:`~GazeParser.Core.GazeData`
    :samplingFreq: sampling frequency of the data. If None, sampling frequency
        is calculated from the data.  Default value is None.
    :param str velocityType: 'slow' or 'fast'. See Engbert & Kliegl (2003) for detail.
        Default value is 'slow'.
    :param int vfac: Modifying threshold for microsaccade detection. See Engbert & Kliegl (2003) for detail.
        Default value is 6.
    :param int minSamples: Microsaccades must have samples equal or larger than this value.
        Default value is 3.
    """
    if samplingFreq is None:
        samplingFreq = 1000.0/numpy.mean(numpy.diff(gazeData.T))

    msL = MicroSacc(gazeData.L, samplingFreq, velocityType, vfac, minSamples).ms
    msR = MicroSacc(gazeData.R, samplingFreq, velocityType, vfac, minSamples).ms

    ms = _binsacc(msL, msR)

    T = gazeData.T
    HV = (gazeData.L + gazeData.R / 2.0)

    # TODO check results
    saclist = []
    for index in range(len(saclist)):
        sx = HV[ms[index, 0], 0]
        sy = HV[ms[index, 0], 1]
        ex = HV[ms[index, 1], 0]
        ey = HV[ms[index, 1], 1]
        saclist.append(SaccadeData((T[ms[index, 0]], T[ms[index, 1]]),
                                   (sx, sy, ex, ey, ms[index, 3], gazeData.Pix2Deg(ms[index, 3])),
                                   T))

    return numpy.array(saclist)


def nan_greater(v1, v2):
    idx = numpy.where(v1!=v1)[0]
    if idx == []:
        return v1 > v2
    
    val = numpy.zeros(v1.shape, dtype=numpy.bool)
    val[idx] = False
    idx = numpy.where(v1==v1)[0]
    val[idx] = (v1[idx] > v2)
    
    return val
