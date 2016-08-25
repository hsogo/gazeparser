#!/usr/bin/env/python

import sys
import os

if '-h' in sys.argv:
    print """setup_for_psychopy.py: install GazeParser to PsychoPy'
  options:
    -h Show this help.
    -u Only update "Components Folder" of PsychoPy.
"""
    sys.exit(0)

try:
    import psychopy
except:
    print 'PsychoPy is not found. Please install PsychoPy in advance.'
    sys.exit(-1)

# Install GazeParser

if not '-u' in sys.argv:
    import runpy

    if len(sys.argv)==1:
        sys.argv.append('install')
    else:
        sys.argv[1]='install'

    runpy.run_path("setup.py")


# Set "Components Folder"

try:
    import GazeParser
except:
    print 'GazeParser is not correctly installed. Abort.'
    sys.exit(-1)


gpComponentDir = os.path.join(os.path.split(GazeParser.__file__)[0],'PsychoPyComponents')
if sys.platform.startswith('win'):
    gpcDir = gpComponentDir.lower()
    cmpDir = [s.lower() for s in psychopy.prefs.builder['componentsFolders']]
else:
    gpcDir = gpComponentDir
    cmpDir = psychopy.prefs.builder['componentsFolders']

if not gpcDir in cmpDir:
    print 'Add GazeParser PsychoPyComponent directory (%s) to ComponentsFolders' % gpComponentDir
    psychopy.prefs.builder['componentsFolders'].append(gpComponentDir)
    psychopy.prefs.saveUserPrefs()
else:
    print 'GazeParser PsychoPyComponent directory (%s) is already in ComponentsFolders. ComponentsFolders was not updated.' % gpComponentDir
