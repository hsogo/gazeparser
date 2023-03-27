#!/usr/bin/env python
from setuptools import setup, find_packages
import sys
import os

from GazeParser import __version__

version = '0.12.1'

setup(name='GazeParser',
      version=version,
      description='Gaze tracking, parsing and visualization tools',
      long_description="""
The GazeParser is a package intended for research on eye movement.
This package compries comprises several functions for gaze data analysis, 
including saccade and fixation detection, scan path plotting and comparison,
and saccade trajectory curvature calculation.
Additionally, this package provides a module to control SimpleGazeTracker 
(an open-source video-based eye-tracking application) from PsychoPy.
""",
      classifiers=[
          # http://pypi.python.org/pypi?%3Aaction=list_classifiers
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: MacOS',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering',
      ],
      keywords='gaze tracking, eye tracking, eye movement',
      author='Hiroyuki Sogo',
      author_email='hsogo12600@gmail.com',
      url='http://sourceforge.net/p/gazeparser/',
      license='GNU GPL',
      install_requires=[],
      packages=['GazeParser', 'GazeParser.app', 'GazeParser.TrackingTools'],
      package_data={'GazeParser': ['*.cfg','GazeParserComponents/*.*'],
                    'GazeParser.app': ['img/*.png', 'img/*.ico',
                                       'img/*.gif', '*.cfg']},
      scripts=['gazeparser_viewer']
      )
