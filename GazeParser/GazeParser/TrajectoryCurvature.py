"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).

.. note:: This module is under construction. Functions have not been tested.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import GazeParser.Core
import numpy


def getAreaCurvature(traj, absolute=False, ignoreNaN=False):
    """
    Get area curvature of a trajectory. The area curvature is defined as the
    area surrounded by the X axis and the tracjectory.  The origin and
    direction of the trajectory must be normalized in advance.

    :param numpy.ndarray traj:
        Nomalized trajectory (binocular data is not currently supported).
    :param bool absolute:
        If False, the area below the X axis has a negative value.
        Default value is False.
    :param bool ignoreNone:
        If True, NaNs in the trajectory are removed before calculating
        area curvature. Default value is False.
    """
    if traj.shape[1] != 2:
        raise ValueError('size of the trajectory must be n x 2.')

    if absolute:
        y = abs(traj[:, 1])
    else:
        y = traj[:, 1]
    x = traj[:, 0]

    if ignoreNaN:
        idx = y == y  # numpy.isnan(y) = =False
        y = y[idx]
        x = x[idx]

    return numpy.trapz(y, x)


def getInitialDirection(traj, index, unit='rad'):
    """
    Get the initila direction of the trajectory.
    The origin and direction of the trajectory must be normalized in advance.

    :param numpy.ndarray traj:
        Nomalized trajectory (binocular data is not currently supported).
    :param int index: Specify which sample is used to calculate direction.
        For example, the third sample is used if this parameter is 2.
        Note that the index of the origin is zero.
    :param unit: Specify unit of the returned value ('deg' or 'rad').
    """
    if traj.shape[1] != 2:
        raise ValueError('size of the trajectory must be n x 2.')

    r = numpy.arctan2(traj[index, 1], traj[index, 0])
    if unit.lower() == 'rad':
        return r
    elif unit.lower() == 'deg':
        return r*180.0/numpy.pi
    else:
        raise ValueError('unit must be \'rad\' or \'deg\'')


def getMaximumDeviation(traj):
    """
    Get maximum deviation of trajectory from the X axis.
    The origin and direction of the trajectory must be normalized in advance.

    :param numpy.ndarray traj:
        Nomalized trajectory (binocular data is not currently supported).
    """
    if traj.shape[1] != 2:
        raise ValueError('size of the trajectory must be n x 2.')

    absY = numpy.abs(traj[:, 1])
    idx = numpy.where(absY == numpy.max(absY))[0][0]
    return traj[idx, 1]


def getRotatedTrajectory(sac, refPoint=None, refPointRelative=None, rot=None, unit='rad', normalize=0, origin=(0, 0)):
    """
    Rotate, shift and normalize trajectory. Rotation can be specified in three
    ways.

    If 'refPoint' is given, saccade trajectory is rotated so that the end point
    of the trajectory points to the direction of 'refPoint'. For example,
    suppose that saccade trajectory starts from (100, 120) and (100, 0) is given
    as 'refPoint'. In this case, the rotated trajectory points to the direction
    parallel to the Y axis (note that X component of the origin of the
    trajectory and 'refPoint' are the same value).

    'refPointRelative' is similar to 'refPoint' except that the value is
    interpreted as indicating the point relative to the origin of the saccade
    trajectory. For example, suppose that saccade trajectory starts from
    (100, 120) and (100, 0) is given as 'refPointRelative'. In this case, the
    rotated trajectory points to the direction parallel to the X axis.

    If you want to specify the angle of rotation directly, set the value to the
    parameter 'rot'. Unit of the 'rot' is radian in default. If you prefer to
    use degree as the unit, set 'deg' to the parameter 'unit'.

    'refPoint', refPointRelative' and 'rot' can not be specified
    simultaneously.

    The trajectory is shifted so that the origin of the trajectory matches to
    (0, 0). If it is preferable that the origin of the rotated trajectory is
    the same to that of the original trajectory, set 'original' to the
    parameter 'origin'.

    :param sac: An instance of :class:`~GazeParser.Core.SaccadeData` or an
        an array of saccade trajectory.
    :param refPoint: The reference point for rotation. See above for detail.
    :param refPointRelative: The reference point for rotation. See above for
        detail.
    :param float rot: The angle of rotation.
    :param unit: Specify unit of the rotation angle ('deg' or 'rad').
    :param float normalize: If this value is not zero, the distance between the start
        and the end point of the trajectory is normalized to the given value.
        If zero, the distance is the same to that of the original trajectory.
        Default value is zero.
    :param origin: Specify the origin of the rotated trajectory. If the value
        is 'original', the origin of the rotated trajectory is the same as that
        of the original trajectory. If a tuple of two values are given, the
        rotated trajectory is shifeted by these values.
        Note that this parameter does NOT specify the center of rotation.
    """
    if [refPoint, refPointRelative, rot].count(None) < 2:
        raise ValueError('Only one of refPoint, refPointRelative, rot can be specified.')
        return

    if refPoint is not None:
        mode = 'RefPoint'
    elif refPointRelative is not None:
        mode = 'RefPointRelative'
    elif rot is not None:
        mode = 'Rot'
    else:
        mode = 'ScreenCoordinate'

    if isinstance(sac, GazeParser.Core.SaccadeData):
        if sac._parent._recordedEye == 'B':
            raise ValueError('Binocular data is nor currently supported. Get left or right eye\' trajectory using getTraj().')
        sp = sac.start
        e = sac.end
        traj = sac.getTraj() - sp
    else:
        sp = sac[0, :]
        e = sac[-1, :]
        traj = sac-sp

    if mode == 'RefPoint':
        rot = -numpy.arctan2(e[1]-sp[1], e[0]-sp[0])
        rot += numpy.arctan2(refPoint[1]-sp[1], refPoint[0]-sp[0])
    elif mode == 'RefPointRelative':
        rot = -numpy.arctan2(e[1]-sp[1], e[0]-sp[0])
        rot += numpy.arctan2(refPointRelative[1], refPointRelative[0])
    elif mode == 'Rot':
        if unit.lower() == 'rad':
            pass
        if unit.lower() == 'deg':
            rot = numpy.pi / 180.0 * rot
        else:
            raise ValueError('unit must be \'rad\' or \'deg\'')
    else:  # ScreenCoordinate
        rot = -numpy.arctan2(e[1]-sp[1], e[0]-sp[0])

    rotmat = numpy.array([[numpy.cos(rot), -numpy.sin(rot)], [numpy.sin(rot), numpy.cos(rot)]])
    rottraj = numpy.zeros(traj.shape)
    for i in range(traj.shape[0]):
        rottraj[i, :] = numpy.dot(rotmat, traj[i, :])

    if normalize != 0:
        l = numpy.linalg.norm(rottraj[-1, :])
        rottraj = rottraj/l*normalize

    if isinstance(origin, str) and origin.lower() == 'original':
        return rottraj + sp
    else:
        return rottraj + origin
