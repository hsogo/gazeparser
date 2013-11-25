"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2013 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""

import os
import ConfigParser
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
'SACCADE_MINIMUM_AMPLITUDE':0.2,
'FIXATION_MINIMUM_DURATION': 12,
'FILTER_TYPE':'identity',
'FILTER_WN':0.2,
'FILTER_SIZE':5,
'FILTER_ORDER':3,
'BLINK_MINIMUM_DURATION':50,
'RESAMPLING':0
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
    def __init__(self, ConfigFile = None):
        """
        Create GazeParser.Configuration.Config object.
        
        :param str ConfigFile: constructor reads parameters from this file.
            If None, constructor firstly try to read GazeParser.cfg in the configuration 
            directory. If GazeParser.cfg is not found in the configuration directory, 
            then read GazeParser.cfg in the application directory.
            Default value is None.
        """
        cfgp = ConfigParser.SafeConfigParser()
        cfgp.optionxform = str
        if (ConfigFile == None):
            ConfigFile = os.path.join(GazeParser.configDir, 'GazeParser.cfg')
            if not os.path.isfile(ConfigFile):
                ConfigFile = os.path.join(GazeParser.appDir, 'GazeParser.cfg')
                if not os.path.isfile(ConfigFile):
                    print ('GazeParser.Config: Warning: configuration file (%s) was not found.' % ConfigFile)
                    print 'Default parameters were set.'
                    self.ConfigFile = None
        self.ConfigFile = ConfigFile
        
        cfgp.read(ConfigFile)
        self._optionDict = {}
        for option in GazeParserDefaults:
            try:
                value = cfgp.get('GazeParser', option)
                if isinstance(GazeParserDefaults[option], int):
                    if value == 'True':
                        value = True
                    elif value == 'False':
                        value = True
                    setattr(self, option, int(value))
                    self._optionDict[option] = int(value)
                elif isinstance(GazeParserDefaults[option], float):
                    setattr(self, option, float(value))
                    self._optionDict[option] = float(value)
                else:
                    setattr(self, option, value)
                    self._optionDict[option] = value
            except:
                print 'Warning: %s is not properly defined in GazeParser configuration file. Default value is used.' % (option)
                setattr(self, option, GazeParserDefaults[option])
                self._optionDict[option] = GazeParserDefaults[option]
        
        
    def save(self, ConfigFile = None):
        """
        Save configuration to a file.
        
        :param str ConfigFile: File name to which configuration is saved.
            If None, a file name from which parameters were read when constructing 
            this object. Defaut value is None.
        """
        if (ConfigFile == None):
            ConfigFile = self.ConfigFile
        fp = open(ConfigFile, 'w')
        
        optionNames = GazeParserDefaults.keys()
        
        fp.write('[GazeParser]\n')
        for key in GazeParserOptions:
            fp.write('%s = %s\n' % (key, getattr(self, key)))
        
        fp.close()
    
    def printParameters(self):
        """
        Print all parameters holded in this object.
        """
        for key in GazeParserOptions:
            print '%s = %s' % (key, getattr(self, key))
    
    def getParametersAsDict(self):
        return self._optionDict
