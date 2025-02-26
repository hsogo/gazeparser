#!/usr/bin/env python

import re
import distutils.version

s = re.compile('\d+\.\d+\.\d')
files = ['GazeParser/pyproject.toml',
         'GazeParser/GazeParser/__init__.py',
         'GazeParser/Readme.md',
         'GazeParser/GazeParser/app/viewer.cfg',
         'GazeParser/debian/changelog',
         'SimpleGazeTracker/configure.ac',
         'SimpleGazeTracker/NEWS',
         'SimpleGazeTracker/ChangeLog',
         'SimpleGazeTracker/common/GazeTrackerCommon.h',
         'SimpleGazeTracker/debian_flycap/changelog',
         'SimpleGazeTracker/debian_opencv/changelog',
         'SimpleGazeTracker/debian_spinnaker/changelog',
         ]

for file in files:
    latest = '0.0.0'
    fp = open(file,'r')
    for line in fp:
        m =s.search(line)
        if m is not None:
            if(distutils.version.StrictVersion(latest) < distutils.version.StrictVersion(m.group(0)) ):
                latest = m.group(0)
    print(latest, file)
