#!/usr/bin/env python

import re

s = re.compile('\d+\.\d+\.\d')
files = ['GazeParser/setup.py',
         'GazeParser/GazeParser/__init__.py',
         'GazeParser/Readme.rst',
         'GazeParser/GazeParser/app/viewer.cfg',
         'GazeParser/debian/changelog',
         'SimpleGazeTracker/configure.ac',
         'SimpleGazeTracker/NEWS',
         'SimpleGazeTracker/ChangeLog',
         'SimpleGazeTracker/common/GazeTrackerCommon.h',
         'SimpleGazeTracker/debian_flycap/changelog',
         'SimpleGazeTracker/debian_opencv/changelog',
         ]

for file in files:
    print(file)
    fp = open(file,'r')
    for line in fp:
        m =s.search(line)
        if m != None:
            print(m.group(0))
