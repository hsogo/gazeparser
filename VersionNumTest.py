import re

s = re.compile('\d+\.\d+\.\d')
files = ['GazeParser/GazeParser/__init__.py',
         'GazeParser/Readme.rst',
         'GazeParser/GazeParser/app/viewer.cfg',
         'GazeParser/debian/changelog',
         'SimpleGazeTracker/configure.in',
         'SimpleGazeTracker/NEWS',
         'SimpleGazeTracker/common/GazeTrackerCommon.h',
         'SimpleGazeTracker/debian/changelog',
         'SimpleGazeTracker/debian/files',
         ]

for file in files:
    print file
    fp = open(file,'r')
    for line in fp:
        m =s.search(line)
        if m != None:
            print m.group(0)
