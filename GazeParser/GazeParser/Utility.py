"""
.. Part of GazeParser library.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import numpy
import warnings
if sys.version_info[0] == 2:
    import cPickle as pickle
    import anydbm
else:
    import pickle
import zlib
import shutil
import GazeParser
import GazeParser.Core


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

    if sys.version_info[0] == 2:
        if isinstance(filename, unicode):
            filename = filename.encode(sys.getfilesystemencoding())

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

    if sys.version_info[0] == 2:
        if isinstance(filename, unicode):
            filename = filename.encode(sys.getfilesystemencoding())
    
    fp = open(filename, 'rb')
    try:
        s = zlib.decompress(fp.read())
        if sys.version_info[0] == 2:
            data_dict = pickle.loads(s)
        else:
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
        if sys.version_info[0] == 2:
            db = anydbm.open(filename, 'r')
            s = zlib.decompress(db['GazeData'])
            D = pickle.loads(s)
            if 'AdditionalData' in db:
                s = zlib.decompress(db['AdditionalData'])
                A = pickle.loads(s)
            else:
                A = None
            db.close()
        else:
            try:
                import bsddb3
            except ImportError:
                raise RuntimeError('bsddb3 is necessary to read old GazePaser data file in Python3.')
            db = bsddb3.hashopen(filename, 'r')
            s = zlib.decompress(db[b'GazeData'])
            D = pickle.loads(s, encoding='latin-1')
            if b'AdditionalData' in db:
                s = zlib.decompress(db[b'AdditionalData'])
                A = pickle.loads(s, encoding='latin-1')
            else:
                A = None
            db.close()
    
    # if libraryVersion > dataVersion:
    if compareVersion(D[0].__version__, GazeParser.__version__) < 0 and checkVersion:
        lackingattributes = checkAttributes(D[0])
        if len(lackingattributes) > 0:
            print('Version of the data file is older than GazeParser version. Some features may not work correctly. (lacking attributes:%s)' % ','.join(lackingattributes))
    return (D, A)


def compareVersion(testVersion, baseVersion):
    """
    Compare Version numbers. If testVersion is newer than baseVersion, positive
    number is returned. If testVersion is older than baseVersion, negative number
    is returned. Otherwise, 0 is returned.

    :param str testVersion:
        A string which represents version number.
    :param str baseVersion:
        A string which represents version number.
    :return:
        See above.
    """
    baseVer = list(map(int, baseVersion.split('.')))
    testVer = list(map(int, testVersion.split('.')))
    if testVer > baseVer:
        return 1
    elif testVer < baseVer:
        return -1

    # equal
    return 0


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
    ndx = numpy.arange(len(d))
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
