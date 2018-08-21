#!/usr/bin/env/python

import sys
import os

def findGazeparser():
    for path in sys.path[1:]:
        for root, dirs, files in os.walk(path):
            if root.endswith('GazeParser') and '__init__.py' in files:
                return root
    return None

if '-h' in sys.argv:
    print """setup_for_psychopy.py: install GazeParser to PsychoPy'
  options:
    -h Show this help.
    -u Only update "Components Folder" of PsychoPy.
"""
    sys.exit(0)

try:
    import psychopy
    import psychopy.app.dialogs
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

    try:
        runpy.run_path("setup.py")
    except:
        dlg = psychopy.app.dialogs.MessageDialog(message='GazeParser installation failed. Abort.', type='Info')
        dlg.Show()
        sys.exit(-1)
    
    dlg = psychopy.app.dialogs.MessageDialog(message='GazeParser installation finished. ComponentsFolders will be configured next.', type='Info')
    dlg.Show()


try:
    import GazeParser
except:
    print 'Could not import GazeParser. Abort.'
    dlg = psychopy.app.dialogs.MessageDialog(message='Could not import GazeParser. Abort.', type='Info')
    dlg.Show()
    sys.exit(-1)

GazeParserInstallDir = findGazeparser()

if GazeParserInstallDir is None:
    print 'Could not find GazeParser Package directory. Abort.'
    dlg = psychopy.app.dialogs.MessageDialog(message='Could not find GazeParser Package directory. Abort.', type='Info')
    dlg.Show()
    sys.exit(-1)

#check psychopy version

ver = map(int, psychopy.__version__.split('.'))
if ver[0]>1 or (ver[0] == 1 and ver[1] >= 84):
    componentsSourceDir = 'GazeParserComponents'
else: #old version
    print 'To use GazeParser PsychoPy components, PsychoPy version must be 1.84.0 or later (current: %s).  Components were not set up.' % psychopy.__version__
    dlg = psychopy.app.dialogs.MessageDialog(message='To use GazeParser PsychoPy components, PsychoPy version must be 1.84.00 or later (current: %s).\nComponents were not set up.' % psychopy.__version__, type='Info')
    dlg.Show()
    sys.exit(-1)

# Set "Components Folder"

gpComponentDir = os.path.join(GazeParserInstallDir, componentsSourceDir)
if sys.platform.startswith('win'):
    gpcDir = gpComponentDir.lower()
    cmpDir = [s.lower() for s in psychopy.prefs.builder['componentsFolders']]
else:
    gpcDir = gpComponentDir
    cmpDir = psychopy.prefs.builder['componentsFolders']

if not gpcDir in cmpDir:
    psychopy.prefs.builder['componentsFolders'].append(gpComponentDir)
    psychopy.prefs.saveUserPrefs()
    print 'Setup was finished.\nGazeParser PsychoPyComponent directory (%s) was added to ComponentsFolders' % gpComponentDir
    dlg = psychopy.app.dialogs.MessageDialog(message='Setup was finished.\nGazeParser PsychoPyComponent directory (%s) was added to ComponentsFolders' % gpComponentDir, type='Info')
    dlg.Show()
else:
    print 'Setup was finished.\nGazeParser PsychoPyComponent directory (%s) is already in ComponentsFolders. ComponentsFolders was not updated.' % gpComponentDir
    dlg = psychopy.app.dialogs.MessageDialog(message='Setup was finished.\nGazeParser PsychoPyComponent directory (%s) is already in ComponentsFolders. ComponentsFolders was not updated.' % gpComponentDir, type='Info')
    dlg.Show()
