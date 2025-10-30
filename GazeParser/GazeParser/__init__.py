"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2025 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""

import os
import sys
from importlib.metadata import version

__version__ = version(__package__)

appDir = os.path.abspath(os.path.dirname(__file__))
if sys.platform == 'win32': #Windows
    homeDir = os.environ['USERPROFILE']
    appdataDir = os.environ['APPDATA']
    configDir = os.path.join(appdataDir,'GazeParser')
else: #MacOS X and Linux
    homeDir = os.environ['HOME']
    configDir = os.path.join(homeDir,'.GazeParser')

from GazeParser.Core import *
from GazeParser.Utility import save, load
import GazeParser.Configuration

#create config directory if not exist.
if not os.path.exists(GazeParser.configDir):
    from GazeParser.Utility import createConfigDir
    createConfigDir()

config = GazeParser.Configuration.Config()


