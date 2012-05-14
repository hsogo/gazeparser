"""
.. Part of GazeParser package.
.. Copyright (C) 2012 Hiroyuki Sogo.
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
'DOTS_PER_CENTIMETER_H': 24.260000000000002,
'DOTS_PER_CENTIMETER_V': 24.260000000000002,
'SACCADE_VELOCITY_THRESHOLD': 20.0,
'SACCADE_ACCELERATION_THRESHOLD': 3800.0,
'SACCADE_MINIMUM_DURATION': 12,
'FIXATION_MINIMUM_DURATION': 12,
'FILTER_TYPE':'identity',
'FILTER_WN':0.2,
'FILTER_SIZE':5,
'FILTER_ORDER':3,
'BLINK_MINIMUM_DURATION':50
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
                     'FIXATION_MINIMUM_DURATION',
                     'BLINK_MINIMUM_DURATION',
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
        if (ConfigFile == None):
            ConfigFile = os.path.join(GazeParser.configDir, 'GazeParser.cfg')
            if not os.path.isfile(ConfigFile):
                ConfigFile = os.path.join(GazeParser.appDir, 'GazeParser.cfg')
                if not os.path.isfile(ConfigFile):
                    print ('GazeParser.Config: Warning: configuration file (%s) was not found.' % ConfigFile)
                    print 'Default parameters were set.'
                    self.ConfigFile = None
        self.ConfigFile = ConfigFile
        #cfgp.add_section('GazeParser')
        #for option in GazeParserDefaults.keys():
        #    cfgp.set('GazeParser', option, str(GazeParserDefaults[option]))
        
        cfgp.read(ConfigFile)
        options = cfgp.options('GazeParser')
        self._optionDict = {}
        for option in options:
            name = option.upper()
            if (name not in GazeParserDefaults.keys()):
                raise ValueError, (name + ' is not GazeParser option.')
            value = cfgp.get('GazeParser', option)
            if isinstance(GazeParserDefaults[name], int):
                setattr(self, name, int(value))
                self._optionDict[name] = int(value)
            elif isinstance(GazeParserDefaults[name], float):
                setattr(self, name, float(value))
                self._optionDict[name] = float(value)
            else:
                setattr(self, name, value)
                self._optionDict[name] = value
        
        
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
