"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy


class CircleRegion(object):
    def __init__(self, x, y, r):
        if r <= 0:
            raise ValueError('r must be a positive value')

        self.x = x
        self.y = y
        self.r = r

    def contains(self, data, mode='all'):
        if not mode.lower() in ('all', 'any'):
            raise ValueError('mode must be "all" or "any".')

        if hasattr(data[0], '__iter__'):  # assume list of points
            if mode.lower() == 'all':
                    for p in data:
                        if numpy.linalg.norm((p[0]-self.x, p[1]-self.y)) >= self.r:
                            return False
                    return True
            else:  # any
                if hasattr(data[0], '__iter__'):  # assume list of points
                    for p in data:
                        if numpy.linalg.norm((p[0]-self.x, p[1]-self.y)) < self.r:
                            return True
                    return False

        else:  # point
            if numpy.linalg.norm((data[0]-self.x, data[1]-self.y)) < self.r:
                return True
            else:
                return False


class RectRegion(object):
    def __init__(self, x1, x2, y1, y2):
        if x1 >= x2:
            raise ValueError('x1 must be smaller than x2')
        if y1 >= y2:
            raise ValueError('y1 must be smaller than y2')

        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2

    def contains(self, data, mode='all'):
        if not mode.lower() in ('all', 'any'):
            raise ValueError('mode must be "all" or "any".')

        if hasattr(data[0], '__iter__'):  # assume list of points
            if mode.lower() == 'all':
                for p in data:
                    if not (self.x1 < p[0] < self.x2 and self.y1 < p[1] < self.y2):
                        return False
                return True
            else:  # any
                for p in data:
                    if self.x1 < p[0] < self.x2 and self.y1 < p[1] < self.y2:
                        return True
                return False

        else:  # point
            if self.x1 < data[0] < self.x2 and self.y1 < data[1] < self.y2:
                return True
            else:
                return False


def getFixationsInRegion(data, region, period=[None, None], useCenter=True, containsTime='all', containsTraj='all', byIndices=False):
    """
    Get a list of fixations which are included in a region.

    :param data:
        An instance of :class:`~GazeParser.Core.GazeData`.
    :param region:
        An instance of :class:`~GazeParser.Region.CircleRegion` or
        :class:`~GazeParser.Region.RectRegion`.
    :param period:
        A list of two positive float values.  Only fixations which occured
        between period[0] and period[1] are counted.  Use None to specify
        the beginning and the end of the data.
        Default value is [None, None].
    :param bool useCenter:
        If True, 'center' attribute of fixation is used for judgement.
        Otherwise, trajectory of fixation is used.
        Default value is True.
    :param str containsTime:
        'any' or 'all'. If 'all', the staring and finish time of fixation must
        be included in a period specified by 'period' parameter.
        Default value is 'all'.
    :param str containsTraj:
        'any' or 'all'. If 'all', the whole trajectory of fixation must be
        included in a region specified by 'region' parameter. If useCenter is
        True, this parameter is ignored.
        Default value is 'all'.
    :param bool byIndices:
        If True, a list of indices are returned instead of
        :class:`~GazeParser.Core.FixationData` object.
        Default value is False.

    :return:
        A list of :class:`~GazeParser.Core.FixationData` object.
        If byIndices is True, a list of indices are returned.
    """
    fixlist = []
    if period[0] is None:
        period[0] = data.T[0]
    if period[1] is None:
        period[1] = data.T[-1]

    if containsTime == 'all':
        fromAttr = 'startTime'
        toAttr = 'endTime'
    else:
        fromAttr = 'endTime'
        toAttr = 'startTime'

    for fi in range(len(data.Fix)):
        if period[0] <= getattr(data.Fix[fi], fromAttr) and getattr(data.Fix[fi], toAttr) <= period[1]:
            if useCenter:
                if region.contains(data.Fix[fi].center, mode=containsTraj):
                    fixlist.append(fi)
            else:
                if region.contains(data.Fix[fi].getTraj(), mode=containsTraj):
                    fixlist.append(fi)

    if byIndices:
        return fixlist
    else:
        return data.Fix[fixlist]
