"""
.. Part of GazeParser library.
.. Copyright (C) 2012-2025 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import numpy as np
import warnings
import pickle
import zlib
import shutil
import platform
import GazeParser
import GazeParser.Core
from packaging import version


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

    with open(filename, 'wb') as fp:
        data_dict = {'GazeData':data, 'AdditionalData':additionalData}
        s = pickle.dumps(data_dict, protocol=2)
        fp.write(zlib.compress(s))


def load(filename, checkVersion=True):
    """
    Load GazeParser data from a file.  A return value is a tuple of two elements.
    The first element is a list of GazeParser.GazeData objects.  The second
    element is an additional data saved within the file.  If no additional data
    is included in the file, additional data is None.

    :param str filename:
        Filename.
    :param bool checkVersion:
        If True, version of data file is checked.  If the file is generated 
        in an old version of GazeParser, warning message is shown. To suppress
        warning, set False to this option.  Default value is True.
    """
    if not os.path.isfile(filename):
        raise ValueError('%s is not exist.' % filename)

    fp = open(filename, 'rb')
    try:
        s = zlib.decompress(fp.read())
        try:
            data_dict = pickle.loads(s)
        except UnicodeDecodeError:
            data_dict = pickle.loads(s, encoding='latin-1')
        D = data_dict['GazeData']
        A = data_dict['AdditionalData']
        fp.close()
    except:
        fp.close()
        # old data file
        print('Warning: This data file is made by old GazeParser. It is recommended to re-save data in the new file format.')
        warnings.warn('loading old-format data file', DeprecationWarning)
        try:
            import bsddb3
        except ImportError:
            raise RuntimeError('bsddb3 is necessary to read old GazePaser data file in Python3.')
        db = bsddb3.hashopen(str(filename), 'r')
        s = zlib.decompress(db[b'GazeData'])
        D = pickle.loads(s, encoding='latin-1')
        if b'AdditionalData' in db:
            s = zlib.decompress(db[b'AdditionalData'])
            A = pickle.loads(s, encoding='latin-1')
        else:
            A = None
        db.close()
    
    # if libraryVersion > dataVersion:
    #if compareVersion(D[0].__version__, GazeParser.__version__) < 0 and checkVersion:
    if checkVersion and version.parse(D[0].__version__) < version.parse(GazeParser.__version__):
        lackingattributes = checkAttributes(D[0])
        if len(lackingattributes) > 0:
            print('Version of the data file is older than GazeParser version. Some features may not work. (lacking attributes:%s)' % ','.join(lackingattributes))
    return (D, A)


def join(newFileName, fileList):
    """
    Combine GazeParser data files into a single file.
    If some files have addional data and the others don't have, missing
    additional data is filled with empty lists.

    :param str newFileName:
        Name of combined data file.
    :param sequence fileList:
        A list of file names to be combined.
    """
    newD = []
    newA = []
    found = False
    for f in fileList:
        print(f + '...')
        (D, A) = load(f)
        newD.extend(D)
        if A is not None:
            found = True
            newA.extend(A)
        else:
            newA.extend([]*len(D))
    if not found:
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
        if os.getuid() == 0:  # running as root
            print('Warning: GazeParser.Utility.createConfigDir do nothing because process is runnging as root (uid=0).')
            return

    AppDir = os.path.abspath(os.path.dirname(__file__))

    if sys.platform == 'win32':
        homeDir = os.environ['USERPROFILE']
        appdataDir = os.environ['APPDATA']
        configDir = os.path.join(appdataDir, 'GazeParser')
    else:
        homeDir = os.environ['HOME']
        configDir = os.path.join(homeDir, '.GazeParser')

    if not os.path.exists(configDir):
        os.mkdir(configDir)
        print('GazeParser: ConfigDir is successfully created.')
    else:
        print('GazeParser: ConfigDir is exsiting.')

    src = []
    dst = []
    for fname in os.listdir(AppDir):
        if fname[-4:] == '.cfg':
            src.append(os.path.join(AppDir, fname))
            dst.append(os.path.join(configDir, fname[:-4]+'.cfg'))

    for i in range(len(src)):
        if overwrite or not os.path.exists(dst[i]):
            print('%s -> %s' % (src[i], dst[i]))
            shutil.copyfile(src[i], dst[i])
        else:
            print('%s is existing.' % (dst[i]))


def sortrows(d, cols, order=None):
    """
    Matlab-like sort function.

    :param d: an array to be sorted.
    :param cols: a list of columns used for sorting.
    :param order: a list of boolian values.
        Set True for ascending order and False for decending order.
    :return:
        Indices.
    """
    if order is None:
        order = [True for i in range(len(cols))]
    ndx = np.arange(len(d))
    for i in range(len(cols)-1, -1, -1):
        if order[i]:
            idx = d[ndx, cols[i]].argsort(kind='mergesort')
        else:
            idx = (-d[ndx, cols[i]]).argsort(kind='mergesort')
        ndx = ndx[idx]
    return ndx


def splitFilenames(filenames):
    """
    Split return value of tkFileDialog.askopenfilenames.
    On Windows, tkFileDialog.askopenfilenames does not return list of file names
    but an unicode string. This function splits the unicode string into a list.

    :param unicode filenames:
        return value of tkFileDialog.askopenfilenames.
    :return:
        List of filenames.
    """
    tmplist = filenames.split(' ')
    newFilenames = []
    i = 0
    while i < len(tmplist):
        if tmplist[i][0] == '{':  # space is included
            s = i
            while tmplist[i][-1] != '}':
                i += 1
            fname = ' '.join(tmplist[s:i+1])
            newFilenames.append(fname[1:-1])
        elif tmplist[i][-1] == '\\':
            s = i
            while tmplist[i][-1] == '\\':
                i += 1
            fname = ' '.join(tmplist[s:i+1])
            newFilenames.append(fname.replace('\\', ''))
        else:
            newFilenames.append(tmplist[i].replace('\\', ''))
        i += 1
    return newFilenames


def checkAttributes(gazeData):
    """
    Check attributes of GazeParser.Core.GazeData object and returns a list of
    lacking attributes. This function is used to check whether data built by
    old versions of GazeParser have all attributes defined in the current

    :param GazeParser.Core.GazeData gazeData:
        GazeParser.Core.GazeData object to be checked.
    :return:
        List of lacking attributes.
    """
    if not isinstance(gazeData, GazeParser.Core.GazeData):
        raise ValueError('Not a GazeParser.Core.GazeData object.')

    dummyData = GazeParser.Core.GazeData(list(range(10)), [], [], [], [],  # Tlist, Llist, Rlist, SacList, FixList
                                         [], [], [], 'B')  # MsgList, BlinkList, PupilList, recordingEye
    dummyAttributes = set(dir(dummyData))
    dataAttributes = set(dir(gazeData))

    return list(dummyAttributes-dataAttributes)


def rebuildData(gazeData):
    """
    Try to rebuild data from the data built by older versions of GazeParser.
    Missing attributes are filled by default values. If you want to speficy
    parameters, please rebuild data by using GazeParser.Converter module.

    :param GazeParser.Core.GazeData gazeData:
        GazeParser.Core.GazeData object to be rebuilt.
    :return:
        Rebuilt data.
    """
    if isinstance(gazeData, GazeParser.Core.GazeData):
        if hasattr(gazeData, 'config'):
            config = gazeData.config
        else:
            config = None
        if hasattr(gazeData, 'recordingDate'):
            recordingDate = gazeData.recordingDate
        else:
            print('Warning: recording date can not be recovered from data. If recording date is necessary, please build GazeData object from SimpleGazeTracker CSV file.')
            recordingDate = None
        newdata = GazeParser.Core.GazeData(
            gazeData.T,
            gazeData.L,
            gazeData.R,
            gazeData.Sac,
            gazeData.Fix,
            gazeData.Msg,
            gazeData.Blink,
            gazeData.Pupil,
            gazeData.recordedEye,
            config,
            recordingDate)
        return newdata

    elif hasattr(gazeData, '__iter__'):
        newdatalist = []
        for data in gazeData:
            if not isinstance(data, GazeParser.Core.GazeData):
                raise ValueError('Non-GazeParser.Core.GazeData object is found in the list.')

            if hasattr(data, 'config'):
                config = data.config
            else:
                config = None
            if hasattr(data, 'recordingDate'):
                recordingDate = data.recordingDate
            else:
                print('Warning: recording date can not be recovered from data. If recording date is necessary, please build GazeData object from SimpleGazeTracker CSV file.')
                recordingDate = None
            newdata = GazeParser.Core.GazeData(
                data.T,
                data.L,
                data.R,
                data.Sac,
                data.Fix,
                data.Msg,
                data.Blink,
                data.Pupil,
                data.recordedEye,
                config,
                recordingDate)
            newdatalist.append(newdata)
        return newdatalist

    else:
        raise ValueError('Parameter must be a GazeParser.Core.GazeData object or a list of GazeParser.Core.GazeData object')

    return None

def appendAdditionalData(filename, data, newFilename=None, key=None, replace=False, asDict=True):
    """
    Append additional data to GazeParser data file.
    By default, the additional data is supposed as a Dictionary object 
    and the data is appended to it.  In order to append data as-is,
    set asDict=False.

    :param str filename:
        Name of GazeParser data file to which the data will be appended.
    :param any data:
        Data to be appended.
    :param str newFilename:
        Specify the name of output file.  If this parameter is None,
        the source data file will be overwritten.
        Default value is None.
    :param str key:
        The key to get value from dictionary object.
        This parameter is required if asDict=True.
    :param bool replace:
        If True, Existing additional data will be replaced.
        Default value is False.
    :param bool asDict:
        If True, the additional data is supposed as a Dictionary object 
        and the data is appended to it.  Default value is True.
    :return:
        True if scceed.
    """
    D, A = load(filename)
    if (A is not None) and (not replace):
        raise ValueError('{} already has additional data. Set replace=True to replace it with new data'.format(filename))
    
    if asDict:
        if A is None:
            A = {}
        if isinstance(A, dict):
            A[key] = data
        else:
            raise ValueError('Additional data in {} is not a dict object.'.format(filename))

    else:
        A = data
    
    if newFilename is None:
        save(filename, D, A)
    else:
        save(newFilename, D, A)
    
    return True

def embedStimImages(filename, imageDict, newFilename=None, replace=False):
    """
    Embed stimulus images to GazeParser data file.
    
    :param str filename:
        Name of GazeParser data file to which the data will be appended.
    :param dict imageDict:
        A dictionary object that contains name of images and image data.
        The dictionay must have keys named 'NAMES' and 'IMAGES'.
        A list of image names must be paierd with 'NAMES' and a list of 
        image data must be paired with 'IMAGES'. The N-th name is treated
        as the N-th image.
    :param str newFilename:
        Specify the name of output file.  If this parameter is None,
        the source data file will be overwritten.
        Default value is None.
    :param bool replace:
        If True, Existing embedded images will be replaced.
        Default value is False.
    :return:
        True if scceed.
    """
    D, A = load(filename)
    if (A is not None) and (not isinstance(A, dict)) and (not replace):
        raise ValueError('Additonal data in {} is not a dict object. replace=True to replace it with new data'.format(filename))

    if isinstance(A, dict) and 'EMBEDDED_IMAGES' in A and (not replace):
        raise ValueError('{} already has embedded images. replace=True to replace it with new data'.format(filename))

    if not isinstance(imageDict, dict):
        raise ValueError('Images must be a dictionary object.')

    if not ('NAMES' in imageDict and 'IMAGES' in imageDict):
        raise ValueError('Images must have keys named \'NAMES\' and \'IMAGES\'.')
    
    if len(imageDict['NAMES']) != len(imageDict['IMAGES']):
        raise ValueError('Length of NAMES and IMAGES must be equal.')

    if not isinstance(A, dict):
        # If replace=False, exception has already been raised.
        # So we can replace original A with an empty dictionary object.
        A = {}
    
    A['EMBEDDED_IMAGES'] = imageDict

    if newFilename is None:
        save(filename, D, A)
    else:
        save(newFilename, D, A)
    
    return True

def removeEmbeddedImages(filename, newFilename=None):
    """
    Remove embedded stimulus images from GazeParser data file.
    
    :param str filename:
        Name of GazeParser data file from which the data will be removed.
    :param str newFilename:
        Specify the name of output file.  If this parameter is None,
        the source data file will be overwritten.
        Default value is None.
    :return:
        Removed image data.
    """
    D, A = load(filename)
    try:
        images = A.pop('EMBEDDED_IMAGES')
    except:
        raise KeyError('Stimulus images are not embedded in {}'.format(filename))
    
    if newFilename is None:
        save(filename, D, A)
    else:
        save(newFilename, D, A)

    return images

def openLocation(path):
    """
    Open location in GUI

    :param str path: Path to the location.
    """

    os_name = platform.system()
    if os_name == 'Windows':
        os.system('start {}'.format(path))
    elif os_name == 'Darwin':
        os.system('open {}'.format(path))
    elif os_name == 'Linux':
        os.system('xdg-open {}'.format(path))
    else:
        raise RuntimeError('openLocation: {} is not supported.'.format(os_name))
