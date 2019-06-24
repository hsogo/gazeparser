"""
.. Part of GazeParser package.
.. Copyright (C) 2012-2015 Hiroyuki Sogo.
.. Distributed under the terms of the GNU General Public License (GPL).
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

release_name = '0.11.1'

__version__ = release_name

import os
import sys

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


