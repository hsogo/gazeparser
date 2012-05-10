"""
Part of GazeParser package.
Copyright (C) 2012 Hiroyuki Sogo.
Distributed under the terms of the GNU General Public License (GPL).


.. note:: This module is under construction. Functions have not been tested.
"""

import numpy

def getAreaCurvature(traj,absolute=False):
    """
    Get are curvature of a trajectory. The area curvature is defined as the area 
    surrounded by the X axis and the tracjectory.  The origin and direction of the 
    trajectory must be normalized in advance.
    
    :param traj: Nomalized trajectory.
    :param absolute: If False, the area below the X axis has a negative value.
        Default value is False.
    """
    if absolute:
        y = abs(traj[:,1])
    else:
        y = traj[:,1]
    return numpy.trapz(y,traj[:,0])

def getInitialDirection(traj,index,unit='rad'):
    """
    Get the initila direction of the trajectory.
    The origin and direction of the trajectory must be normalized in advance.
    
    :param traj: Nomalized trajectory.
    :param index: Specify which sample is used to calculate direction. For example,
        the third sample is used if this parameter is 2.
        Note that the index of the origin is zero.
    :param unit: Specify unit of the returned value. Either 'deg' or 'rad' is accepted.
    """
    r = numpy.arctan2(traj[index,1],traj[index,0])
    if unit.lower() == 'rad':
        return r
    elif unit.lower() == 'deg':
        return r*180.0/numpy.pi
    else:
        raise 'unit must be \'rad\' or \'deg\''

def getMaximumDeviation(traj):
    """
    Get maximum deviation of trajectory from the X axis.
    The origin and direction of the trajectory must be normalized in advance.
    
    :param traj: Nomalized trajectory.
    """
    absY = numpy.abs(traj[:,1])
    idx = numpy.where(absY == numpy.max(absY))[0][0]
    return traj[idx,1]


def getRotatedTrajectory(sac,refPoint=None,refPointRelative=None,rot=None,unit='rad',normalize=0,origin=(0,0)):
    '''
    Rotate, shift and normalize trajectory. Rotation can be specified in three ways.
    
    If 'refPoint' is given, saccade trajectory is rotated so that the end point of the 
    trajectory points to the direction of 'refPoint'. For example, suppose that saccade 
    trajectory starts from (100,120) and (100,0) is given as 'refPoint'. In this case, 
    the rotated trajectory points to the direction parallel to the Y axis (note that 
    X component of the origin of the trajectory and 'refPoint' are the same value).
    
    'refPointRelative' is similar to 'refPoint' except that the value is interpreted 
    as indicating the point relative to the origin of the saccade trajectory.
    For example, suppose that saccade trajectory starts from (100,120) and (100,0) is
    given as 'refPointRelative'. In this case, the rotated trajectory points to the 
    direction parallel to the X axis.
    
    If you want to specify the angle of rotation directly, set the value to the 
    parameter 'rot'. Unit of the 'rot' is radian in default. If you prefer to 
    use degree as the unit, set 'deg' to the parameter 'unit'.
    
    'refPoint', refPointRelative' and 'rot' can not be specified simultaneously.
    
    The trajectory is shifted so that the origin of the trajectory matches to (0,0).
    If it is preferable that the origin of the rotated trajectory is the same to 
    that of the original trajectory, set 'original' to the parameter 'origin'.
    
    :param sac: :class: An instance of `~GazeParser.Core.SaccadeData`.
    :param refPoint: The reference point for rotation. See above for detail.
    :param refPointRelative: The reference point for rotation. See above for detail.
    :param rot: The angle of rotation.
    :param unit: Specify unit of the rotation angle. Either 'deg' or 'rad' is accepted.
    :param normalize: If this value is not zero, the distance between the start and the 
        end point of the trajectory is normalized to the given value.  If zero, the 
        distance is the same to that of the original trajectory.  Default value is zero.
    :param origin: Specify the origin of the rotated trajectory. If the value is 'original',
        the origin of the rotated trajectory is the same as that of the original trajectory.
        If a tuple of two values are given, the rotated trajectory is shifeted by these values.
        Note that this parameter does NOT specify the center of rotation.
    '''
    if [refPoint,refPointRelative,rot].count(None) < 2:
        raise 'Only one of refPoint, refPointRelative, rot can be specified.'
        return
        
    if refPoint != None:
        mode = 'RefPoint'
    elif refPointRelative != None:
        mode = 'RefPointRelative'
    elif rot != None:
        mode = 'Rot'
    else:
        mode = 'ScreenCoordinate'
    
    print rot
    
    sp = sac.start
    e = sac.end
    traj = sac.getTraj() - sp
    if mode=='RefPoint':
        rot = -numpy.arctan2(e[1]-sp[1],e[0]-sp[0])
        rot += numpy.arctan2(refPoint[1]-sp[1],refPoint[0]-sp[0])
    elif mode=='RefPointRelative':
        rot = -numpy.arctan2(e[1]-sp[1],e[0]-sp[0])
        rot += numpy.arctan2(refPointRelative[1],refPointRelative[0])
    elif mode=='Rot':
        if unit.lower()=='rad':
            pass
        if unit.lower()=='deg':
            rot = numpy.pi / 180.0 * rot
        else:
            raise 'unit must be \'rad\' or \'deg\''
    else: #ScreenCoordinate
        rot = -numpy.arctan2(e[1]-sp[1],e[0]-sp[0])
    
    print rot,mode
    
    rotmat = numpy.array([[numpy.cos(rot),-numpy.sin(rot)],[numpy.sin(rot),numpy.cos(rot)]])
    rottraj = numpy.zeros(traj.shape)
    for i in range(traj.shape[0]):
        rottraj[i,:] = numpy.dot(rotmat,traj[i,:])
    
    if normalize != 0:
        l = numpy.linalg.norm(rottraj[-1,:])
        rottraj = rottraj/l*normalize
    
    if origin.lower()=='original':
        return rottraj + sp
    else:
        return rottraj + origin

