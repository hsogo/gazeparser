"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
if sys.version_info[0] == 2:
    import ConfigParser as configparser
else:
    import configparser
import GazeParser

GazeParserDefaults = {
    'RECORDED_EYE': 'L',
    'SCREEN_ORIGIN': 'BottomLeft',
    'TRACKER_ORIGIN': 'BottomLeft',
    'SCREEN_WIDTH': 1024,
    'SCREEN_HEIGHT': 768,
    'VIEWING_DISTANCE': 57.295779513082323,
    'DOTS_PER_CENTIMETER_H': 24.26,
    'DOTS_PER_CENTIMETER_V': 24.26,
    'SACCADE_VELOCITY_THRESHOLD': 20.0,
    'SACCADE_ACCELERATION_THRESHOLD': 3800.0,
    'SACCADE_MINIMUM_DURATION': 12,
    'SACCADE_MINIMUM_AMPLITUDE': 0.2,
    'FIXATION_MINIMUM_DURATION': 12,
    'BLINK_MINIMUM_DURATION': 50,
    'RESAMPLING': 0,
    'FILTER_TYPE': 'identity',
    'FILTER_WN': 0.2,
    'FILTER_SIZE': 5,
    'FILTER_ORDER': 3
}

GazeParserOptions = ['RECORDED_EYE',
                     'SCREEN_ORIGIN',
                     'TRACKER_ORIGIN',
                     'SCREEN_WIDTH',
                     'SCREEN_HEIGHT',
                     'DOTS_PER_CENTIMETER_H',
                     'DOTS_PER_CENTIMETER_V',
                     'VIEWING_DISTANCE',
                     'SACCADE_VELOCITY_THRESHOLD',
                     'SACCADE_ACCELERATION_THRESHOLD',
                     'SACCADE_MINIMUM_DURATION',
                     'SACCADE_MINIMUM_AMPLITUDE',
                     'FIXATION_MINIMUM_DURATION',
                     'BLINK_MINIMUM_DURATION',
                     'RESAMPLING',
                     'FILTER_TYPE',
                     'FILTER_WN',
                     'FILTER_SIZE',
                     'FILTER_ORDER'
                     ]


class Config(object):
    def __init__(self, ConfigFile=None):
        """
        Create GazeParser.Configuration.Config object.

        :param str ConfigFile: constructor reads parameters from this file.
            If None, constructor firstly try to read GazeParser.cfg in the
            configuration directory. If GazeParser.cfg is not found in the
            configuration directory, then read GazeParser.cfg in the
            application directory.
            Default value is None.
        """
        cfgp = configparser.SafeConfigParser()
        cfgp.optionxform = str
        if ConfigFile is None:
            ConfigFile = os.path.join(GazeParser.configDir, 'GazeParser.cfg')
            if not os.path.isfile(ConfigFile):
                ConfigFile = os.path.join(GazeParser.appDir, 'GazeParser.cfg')
                if not os.path.isfile(ConfigFile):
                    print('Warning: configuration file (%s) was not found. Default parameters were set.' % ConfigFile)
                    self.ConfigFile = None
        self.ConfigFile = ConfigFile

        cfgp.read(ConfigFile)
        optionDict = {}
        for option in GazeParserDefaults:
            try:
                value = cfgp.get('GazeParser', option)
                if isinstance(GazeParserDefaults[option], int):
                    if value == 'True':
                        value = True
                    elif value == 'False':
                        value = True
                    setattr(self, option, int(value))
                    optionDict[option] = int(value)
                elif isinstance(GazeParserDefaults[option], float):
                    setattr(self, option, float(value))
                    optionDict[option] = float(value)
                else:
                    setattr(self, option, value)
                    optionDict[option] = value
            except:
                print('Warning: %s is not properly defined in GazeParser configuration file(%s). Default value is used.' % (option, self.ConfigFile))
                setattr(self, option, GazeParserDefaults[option])
                optionDict[option] = GazeParserDefaults[option]

    def save(self, ConfigFile=None):
        """
        Save configuration to a file.

        :param str ConfigFile: File name to which configuration is saved.
            If None, a file name from which parameters were read when
            constructing this object. Defaut value is None.
        """
        if ConfigFile is None:
            ConfigFile = self.ConfigFile
        fp = open(ConfigFile, 'w')

        # optionNames = GazeParserDefaults.keys()

        fp.write('[GazeParser]\n')
        for key in GazeParserOptions:
            fp.write('%s = %s\n' % (key, getattr(self, key)))

        fp.close()

    def printParameters(self):
        """
        Print all parameters holded in this object.
        """
        missing = []
        for key in GazeParserOptions:
            if hasattr(self, key):
                print('%s = %s' % (key, getattr(self, key)))
            else:
                missing.append(key)
            
        if len(missing)>0:
            print('Warining: missing parameters: {}'.format(', '.join(missing)))

    def getParametersAsDict(self):
        """
        Get parameters as a dict object.
        """
        optionDict = {}
        for key in GazeParserOptions:
            optionDict[key] = getattr(self, key)
        return optionDict
    
    def __repr__(self):
        msg = '<{}.{}, '.format(self.__class__.__module__,
                                self.__class__.__name__)
        params = []
        missing = []
        for key in GazeParserOptions:
            if hasattr(self, key):
                params.append('{}:{}'.format(key, getattr(self, key)))
            else:
                missing.append(key)
        
        msg += ', '.join(params)
        
        if len(missing)>0:
            msg += ', Warining: missing parameters:{}'.format(', '.join(missing))
        
        msg += '>'
        
        return msg

    def __str__(self):
        msg = '<{}.{}\n'.format(self.__class__.__module__,
                                self.__class__.__name__)
        params = []
        missing = []
        for key in GazeParserOptions:
            if hasattr(self, key):
                params.append(' {} = {}'.format(key, getattr(self, key)))
            else:
                missing.append(key)
        
        msg += '\n'.join(params)
        
        if len(missing)>0:
            msg += '\nWarining: missing parameters:{}'.format(', '.join(missing))
        
        msg += '>'
        
        return msg
