#!python

import sys
import os
import shutil

if len(sys.argv) > 1:
    if sys.argv[1] == '-install':
        try:
            # Create shortcut directory
            progDir = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
            shortcuts = os.path.join(progDir, 'GazeParser')
            if not os.path.isdir(shortcuts):
                os.mkdir(shortcuts)
                directory_created(shortcuts)

            # Create config directory in %APPDATA%
            appdataDir = get_special_folder_path("CSIDL_APPDATA")
            configDir = os.path.join(appdataDir, 'GazeParser')
            if not os.path.isdir(configDir):
                os.mkdir(configDir)
                directory_created(configDir)

            # Copy config files to config directory
            gazeparserConfigFile = os.path.join(sys.prefix, 'lib', 'site-packages', 'GazeParser', 'GazeParser.cfg')
            trackingtoolsConfigFile = os.path.join(sys.prefix, 'lib', 'site-packages', 'GazeParser', 'TrackingTools.cfg')
            shutil.copy(gazeparserConfigFile, configDir)
            shutil.copy(trackingtoolsConfigFile, configDir)
            file_created(os.path.join(configDir, 'GazeParser.cfg'))
            file_created(os.path.join(configDir, 'TrackingTools.cfg'))

            # Link to GazeParser Project Page
            homepageLink = os.path.join(shortcuts, 'GazeParserProjectPage.lnk')
            if os.path.isfile(homepageLink):
                os.remove(homepageLink)
            create_shortcut(r'http://gazeparser.sourceforge.net/', 'GazeParser project page', homepageLink)
            file_created(homepageLink)

            # Link to GazeParser Config Directory
            configdirLink = os.path.join(shortcuts, 'GazeParserConfigDir.lnk')
            if os.path.isfile(configdirLink):
                os.remove(configdirLink)
            create_shortcut(configDir, 'GazeParser ConfigFile Directory', configdirLink)
            file_created(configdirLink)

            # Link to Viewer.py
            viewerPath = os.path.join(sys.prefix, 'lib', 'site-packages', 'GazeParser', 'app', 'Viewer.py')
            viewerIconPath = os.path.join(sys.prefix, 'lib', 'site-packages', 'GazeParser', 'app', 'img', 'viewer.ico')
            viewerLink = os.path.join(shortcuts, 'Viewer.lnk')
            if os.path.isfile(viewerLink):
                os.remove(viewerLink)
            create_shortcut(viewerPath, 'GazeParser Data Viewer', viewerLink, '', '', viewerIconPath)
            file_created(viewerLink)
        except:
            print "failed to install shortcuts"
            exc = sys.exc_info()
            print exc[0], exc[1]
