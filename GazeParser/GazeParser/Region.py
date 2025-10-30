"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2025 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
import numpy as np
import warnings


class CircleRegion(object):
    def __init__(self, x, y, r):
        """
        Create a circular region.

        :param float x:
            X coordinate of the center of the region.
        :param float y:
            Y coordinate of the center of the region.
        :param float r:
            Radius of the region.
        """
        for val in x, y, r:
            try:
                float(val)
            except:
                raise ValueError('{} is not a number.'.format(val))
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
                        if np.linalg.norm((p[0]-self.x, p[1]-self.y)) >= self.r:
                            return False
                    return True
            else:  # any
                if hasattr(data[0], '__iter__'):  # assume list of points
                    for p in data:
                        if np.linalg.norm((p[0]-self.x, p[1]-self.y)) < self.r:
                            return True
                    return False

        else:  # point
            if np.linalg.norm((data[0]-self.x, data[1]-self.y)) < self.r:
                return True
            else:
                return False

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)
        
        msg += 'center=[{},{}], radius={}>'.format(
            self.x, self.y, self.r)
        
        return msg


class RectRegion(object):
    def __init__(self, x1, x2, y1, y2):
        """
        Create a rectangular region.
        Vertices 1 and 2 must be diagonal. if x2 is smaller than
        than x1, they are swapped (same for y1 and y2).

        :param float x1:
            X coordinate of the vertex 1
        :param float x2:
            X coordinate of the vertex 2
        :param float y1:
            Y coordinate of the vertex 1
        :param float y2:
            Y coordinate of the vertex 2
        """
        if x1 >= x2:
            tmp = x2
            x2 = x1
            x1 = tmp
        if y1 >= y2:
            tmp = y2
            y2 = y1
            y1 = tmp

        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2

    def contains(self, data, mode='all'):
        if mode.lower() not in ('all', 'any'):
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

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)
        
        msg += 'x1,x2,y1,y2=[{},{},{},{}], width={} height={}>'.format(
            self.x1, self.x2, self.y1, self.y2, self.x2-self.x1, self.y2-self.y1)
        
        return msg

class ImageRegion(object):
    def __init__(self, image, origin='center'):
        if not isinstance(image, np.ndarray):
            try:
                image = np.asarray(image)
            except:
                raise ValueError('Cannot convert image to numpy.ndarray')
        
        if image.ndim != 2:
            raise ValueError('Image must be 2D (monochrome) array')

        self.imageArray = image

    def contains(self, data, mode='all'):
        if not mode.lower() in ('all', 'any'):
            raise ValueError('mode must be "all" or "any".')

        if not isinstance(data, np.ndarray):
            data = np.asarray(data)

        if hasattr(data[0], '__iter__'):  # assume list of points
            # y, x
            values = self.imageArray[data[:,1],data[:,0]]
            if mode.lower() == 'all':
                return values.all()
            else:  # any
                return values.any()

        else:  # point
            if self.imageArray[data[1],data[0]] > 0:
                return True
            else:
                return False

    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)
        
        msg += 'shape={}>'.format(
            self.imageArray.shape)
        
        return msg


def getFixationsInRegion(data, region, period=[None, None], useCenter=True, containsTime='all', containsTraj='all', eye=None, byIndices=False):
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
    :param str eye:
        When the data is binocular, gaze position of the left and right eye
        is averaged by default.  If you want to use only left eye, set 'L' to 
        this parameter.  Similary, set 'R' for right eye.  If the data is
        monocular, this parameter will be ignored.
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
                if data.recordedEye == 'B':
                    if eye is None:
                        bintraj = data.Fix[fi].getTraj()
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", category=RuntimeWarning)
                            traj = np.nanmean(bintraj, axis=0)
                    elif eye == 'L':
                        traj = data.Fix[fi].getTraj(eye='L')
                    elif eye == 'R':
                        traj = data.Fix[fi].getTraj(eye='R')
                    else:
                        raise ValueError("eye must be 'L', 'R' or None")
                    if region.contains(traj, mode=containsTraj):
                        fixlist.append(fi)
                else:
                    if region.contains(data.Fix[fi].getTraj(), mode=containsTraj):
                        fixlist.append(fi)

    if byIndices:
        return fixlist
    else:
        return data.Fix[fixlist]
