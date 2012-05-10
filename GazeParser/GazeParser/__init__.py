"""
Part of GazeParser package.
Copyright (C) 2012 Hiroyuki Sogo.
Distributed under the terms of the GNU General Public License (GPL).
"""

release_name = '0.4.0'

__version__ = release_name

import os
import sys

appDir = os.path.abspath(os.path.dirname(__file__))
if sys.platform == 'win32':
    homeDir = os.environ['HOMEPATH']
    if homeDir[0] == '\\':
        homeDir = os.environ['HOMEDRIVE'] + homeDir
    configDir = os.path.join(homeDir,'GazeParser')
else:
    homeDir = os.environ['HOME']
    configDir = os.path.join(homeDir,'GazeParser')
    

from GazeParser.Core import *
from GazeParser.Utility import save, load
import GazeParser.Configuration

if not os.path.exists(GazeParser.configDir):
    print 'GazeParser: Warning: configDir (%s) does not exist.' % (GazeParser.configDir)
    print 'Call GazeParser.Utility.createConfigDir() to create configDir.'

config = GazeParser.Configuration.Config()


