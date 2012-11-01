"""
.. Part of GazeParser library.
.. Copyright (C) 2012 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""

import numpy
import anydbm
import cPickle
import zlib
import os
import sys
import shutil

def save(filename, data, additionalData=None):
    """
    Save GazeParser objects to a file.
    
    :param str filename:
        Filename.
    :param data:
        List of GazeParser.GazeData objects.
    :param additionalData:
        Additional data (if necessary).
    """
    db = anydbm.open(filename, 'c')
    s = cPickle.dumps(data)
    db['GazeData'] = zlib.compress(s)
    if additionalData != None:
        s = cPickle.dumps(additionalData)
        db['AdditionalData'] = zlib.compress(s)
    db.close()

def load(filename):
    """
    Load GazeParser data from a file.  A return value is a tuple of two elements.
    The first element is a list of GazeParser.GazeData objects.  The second
    element is an additional data saved within the file.  If no additional data 
    is included in the file, additional data is None.
    
    :param str filename:
        Filename.
    """
    if not os.path.isfile(filename):
        raise ValueError, '%s is not exist.' % filename
    
    db = anydbm.open(filename, 'r')
    s = zlib.decompress(db['GazeData'])
    D = cPickle.loads(s)
    if 'AdditionalData' in db:
        s = zlib.decompress(db['AdditionalData'])
        A = cPickle.loads(s)
    else:
        A = None
    db.close()
    return (D, A)

def join(newFileName, fileList):
    """
    Combine GazeParser data files into a single file.
    
    :param str newFileName:
        Name of combined data file.
    :param sequence fileList:
        A list of file names to be combined.
        
    ..  todo:: deal with mixure of datafiles with out without additional data.
    """
    newD = []
    newA = []
    for f in fileList:
        print f + '...'
        (D,A) = load(f)
        newD.extend(D)
        if A != None:
            newA.extend(A)
    if A == []:
        save(newFileName, newD)
    else:
        save(newFileName, newD, additionalData=newA)


def createConfigDir(overwrite=False):
    """
    Create ConfigDir, where GazeParser user configuration files are located.
    If process is running as root (uid=0), this method do nothing.
    
    :param bool overwrite: If ture, existing configuration files are overwritten.
        Default value is False.
    """
    if sys.platform != 'win32':
        if os.getuid() == 0: #running as root
            print 'Warning: GazeParser.Utility.createConfigDir do nothing because process is runnging as root (uid=0).'
            return
    
    AppDir = os.path.abspath(os.path.dirname(__file__))
    
    if sys.platform == 'win32':
	    homeDir = os.environ['USERPROFILE']
	    appdataDir = os.environ['APPDATA']
	    configDir = os.path.join(appdataDir,'GazeParser')
    else:
        homeDir = os.environ['HOME']
        configDir = os.path.join(homeDir,'.GazeParser')
    
    if not os.path.exists(configDir):
        os.mkdir(configDir)
        print 'GazeParser: ConfigDir is successfully created.'
    else:
        print 'GazeParser: ConfigDir is exsiting.'
    
    src = []
    dst = []
    for fname in os.listdir(AppDir):
        if fname[-4:] == '.cfg':
            src.append(os.path.join(AppDir,fname))
            dst.append(os.path.join(configDir,fname[:-4]+'.cfg'))
    
    for i in range(len(src)):
        if overwrite or not os.path.exists(dst[i]):
            print '%s -> %s' % (src[i], dst[i])
            shutil.copyfile(src[i],dst[i])
        else:
            print '%s is existing.' % (dst[i])
    

def sortrows(d,cols,order=None):
    """
    Matlab-like sort function.
    
    :param d: an array to be sorted.
    :param cols: a list of columns used for sorting.
    :param order: a list of boolian values.
        Set True for ascending order and False for decending order.
    """
    if order == None:
        order = [True for i in range(len(cols))]
    ndx = numpy.arange(len(d))
    for i in range(len(cols)-1,-1,-1):
        if order[i]:
            idx = d[ndx,cols[i]].argsort(kind='mergesort')
        else:
            idx = (-d[ndx,cols[i]]).argsort(kind='mergesort')
        ndx = ndx[idx]
    return ndx
    

